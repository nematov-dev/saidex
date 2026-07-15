"""Vertex AI Gemini orqali javob generatsiyasi va ovozli xabarlarni matnga o'girish."""
import logging
import threading
import time

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Content, Part, FinishReason
from django.conf import settings
from google.api_core.exceptions import (
    ResourceExhausted,
    ServiceUnavailable,
    InternalServerError,
    TooManyRequests,
)

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_initialized = False

# Vaqtinchalik (transient) deb hisoblanadigan xatoliklar — bular uchun qayta
# urinib ko'ramiz, chunki ko'pincha bir necha soniyadan keyin o'zi tuzaladi
# (masalan 429 kvota "burst"i yoki Google tomonidagi qisqa uzilish).
_RETRYABLE_ERRORS = (ResourceExhausted, ServiceUnavailable, InternalServerError, TooManyRequests)


def _ensure_init():
    global _initialized
    with _lock:
        if not _initialized:
            vertexai.init(project=settings.GCP_PROJECT_ID, location=settings.GCP_LOCATION)
            _initialized = True


def generate_answer(
    system_prompt: str,
    context: str,
    question: str,
    history: list[dict] | None = None,
    model_name: str | None = None,
    max_retries: int = 8,
) -> tuple[str, int, int]:
    """
    Qaytaradi: (javob_matni, input_token, output_token)
    model_name berilmasa settings.DEFAULT_LLM_MODEL ishlatiladi
    (super admin panel orqali ProjectSubscription.llm_model bilan sozlanadi).

    BARQARORLIK: Vertex AI vaqtinchalik xatolik bersa (masalan 429
    ResourceExhausted — kvota "burst"i), avtomatik ravishda bir necha marta
    (max_retries, standart 8 marta — jami 9 ta urinish) ozgina kutib qayta
    urinadi, shunda foydalanuvchi buni umuman sezmaydi. Faqat BARCHA
    urinishlar muvaffaqiyatsiz bo'lsagina xatolik chaqiruvchi tomonga
    (rag.py) uzatiladi — u yerda foydalanuvchiga hech qanday xabar
    ko'rsatilmaydi (butunlay sukut/silent fail, xato matni ko'rsatilmaydi).
    MUHIM: avval max_retries=4 edi — real foydalanuvchi talabiga ko'ra
    "iloji boricha qayta-qayta urinib ko'rish" uchun oshirildi.
    """
    _ensure_init()
    model_name = model_name or settings.DEFAULT_LLM_MODEL

    full_system = (
        f"{system_prompt}\n\n"
        f"Quyida faqat shu biznesga tegishli hujjatlardan olingan ma'lumot bor. "
        f"Shu ma'lumot asosida javob ber, undan tashqariga chiqma:\n\n---\n{context}\n---"
    )

    model = GenerativeModel(model_name, system_instruction=full_system)

    contents = []
    for msg in (history or [])[-10:]:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(Content(role=role, parts=[Part.from_text(msg["content"])]))
    contents.append(Content(role="user", parts=[Part.from_text(question)]))

    # MUHIM: avval max_output_tokens=600 edi — real foydalanuvchi suhbatida
    # javob ba'zan gap o'rtasida tugallanmagan holda kesilib qolgani
    # kuzatildi (masalan "...ismi ko'rsatilmagan. Biroq" kabi). Buning sababi
    # Gemini javobni shu chegarada to'xtatishi (finish_reason=MAX_TOKENS) edi.
    # Byudjet oshirildi va pastda, agar baribir kesilib qolsa, kattaroq
    # byudjet bilan bir marta qayta urinish qo'shildi.
    # MUHIM: avval temperature=0.3 edi — bu juda past bo'lgani uchun AI turli
    # foydalanuvchilarga deyarli bir xil so'zlar bilan, "shablon" javob berardi
    # (real foydalanuvchi shikoyati: "hammaga bir xil javob beryapti"). Odam
    # yozayotgandek tabiiy, har safar turlicha javob uchun harorat oshirildi —
    # RAG konteksti (system_prompt) baribir faqat hujjatlar doirasida javob
    # berishni talab qilgani uchun, bu asosiy ma'lumotni o'zgartirmaydi, faqat
    # so'z tanlovi/uslubni tabiiylashtiradi.
    base_max_tokens = 2048
    generation_config = GenerationConfig(temperature=0.9, max_output_tokens=base_max_tokens)

    attempt = 0
    while True:
        try:
            response = model.generate_content(contents, generation_config=generation_config)
            break
        except _RETRYABLE_ERRORS as exc:
            attempt += 1
            if attempt > max_retries:
                logger.warning(
                    "Vertex AI %s marta urinishdan keyin ham xatolik berdi: %s",
                    attempt, exc,
                )
                raise
            # MUHIM: avval min(1.5*attempt, 10.0) edi — real foydalanuvchi
            # "juda sekin" deb shikoyat qildi, chunki xatolik (masalan 429
            # kvota) ko'p marta takrorlansa, kutish umumiy ~50 soniyagacha
            # cho'zilib ketardi. Qayta urinishlar soni (max_retries) saqlanib
            # qoldi, lekin har biri orasidagi kutish sezilarli qisqartirildi.
            wait_seconds = min(0.6 * attempt, 3.0)
            logger.info(
                "Vertex AI vaqtinchalik xatolik (%s-urinish), %.1f soniyadan keyin qayta urinamiz: %s",
                attempt, wait_seconds, exc,
            )
            time.sleep(wait_seconds)

    finish_reason = response.candidates[0].finish_reason if response.candidates else None
    if finish_reason == FinishReason.MAX_TOKENS:
        logger.warning(
            "Vertex AI javobi MAX_TOKENS (%s) chegarasida kesilib qoldi — "
            "kattaroq token byudjeti bilan qayta urinilmoqda.", base_max_tokens,
        )
        retry_config = GenerationConfig(temperature=0.9, max_output_tokens=base_max_tokens * 2)
        try:
            retry_response = model.generate_content(contents, generation_config=retry_config)
            # Qayta urinish ham yana kesilib qolsa ham, hech bo'lmasa
            # birinchisidan uzunroq (to'liqroq) javob bo'lgani uchun shuni
            # ishlatamiz.
            response = retry_response
        except _RETRYABLE_ERRORS:
            # Qayta urinish muvaffaqiyatsiz bo'lsa, birinchi (kesilgan)
            # javobni ishlatamiz — hech bo'lmasa qisman javob mavjud.
            pass

    answer = response.text
    usage = response.usage_metadata
    input_tokens = usage.prompt_token_count if usage else 0
    output_tokens = usage.candidates_token_count if usage else 0
    return answer, input_tokens, output_tokens


def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """
    Ovozli xabarni (Telegram voice note) Gemini multimodal orqali matnga o'giradi.
    Xatolik yuz bersa, bo'sh satr qaytaradi (chaqiruvchi tomon buni tekshirib,
    foydalanuvchiga tushunarli xabar ko'rsatishi kerak) — hech qachon exception
    tashlamaydi, chunki bu funksiya userbot handlerida "typing" bloki ichida
    chaqiriladi va xato yuz berganda ham javobsiz qolib ketmasligi kerak.
    """
    _ensure_init()
    try:
        model = GenerativeModel(settings.DEFAULT_LLM_MODEL)
        audio_part = Part.from_data(data=audio_bytes, mime_type=mime_type)
        instruction_part = Part.from_text(
            "Ushbu audio xabardagi gapni so'zma-so'z, faqat matn shaklida yozib ber. "
            "Boshqa hech qanday izoh, tirnoq belgisi yoki qo'shimcha so'z qo'shma."
        )
        response = model.generate_content(
            [audio_part, instruction_part],
            generation_config=GenerationConfig(temperature=0.0, max_output_tokens=300),
        )
        return (response.text or "").strip()
    except Exception:  # noqa: BLE001
        logger.exception("Ovozli xabarni matnga o'girishda xatolik")
        return ""
