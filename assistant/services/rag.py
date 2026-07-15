"""RAG orkestratsiyasi: hujjatni indekslash va savolga javob topish."""
import logging

from django.conf import settings
from pgvector.django import CosineDistance

from ..models import Document, DocumentChunk, BotConfig, ProjectSubscription
from .document_loader import extract_text
from .chunking import split_text
from .embeddings import embed_texts, embed_query
from .llm import generate_answer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# "Siz kimsiz?" turidagi savollarga har doim bir xil, ishonchli javob berish
# uchun — bu AI'ning o'zgaruvchan javobiga ishonib qolmaydi (LLM ba'zan
# ko'rsatmaga qaramay o'zini AI deb oshkor qilishi mumkin edi). Shu turdagi
# savol aniqlansa, LLM'ga umuman murojaat qilinmaydi — javob har doim
# operator sifatidagi tayyor matn bo'ladi.
# ---------------------------------------------------------------------------
IDENTITY_TRIGGERS = [
    "siz kimsiz", "sen kimsan", "kimsiz siz", "kimsiz o'zi", "kimsiz o`zi",
    "bot bilan gaplash", "botmisiz", "bot emasmisiz", "bot emasmisan",
    "ai misiz", "ai misan", "aimisiz", "aimisan",
    "sun'iy intellekt", "sun`iy intellekt", "sunʼiy intellekt",
    "haqiqiy odammisiz", "odammisiz siz", "odammisiz",
    "avtomatik tizim", "avtomatik javob", "robotmisiz", "robot emasmisiz",
    "dasturmisiz", "dastur emasmisiz",
]

OPERATOR_IDENTITY_RESPONSE = (
    "Men Saidex.uz operatori Umarbekman, sizga yordam berish uchun shu yerdaman! "
    "Savolingiz bo'lsa, bemalol yozavering."
)

# Foydalanuvchilar ko'pincha apostrofni umuman tashlab yozadi (masalan
# "kimsiz o'zi" o'rniga "kimsiz ozi", "bog'lanaman" o'rniga "boglanaman").
# Shuning uchun solishtirishdan oldin har ikki tarafdan (matn va kalit so'z)
# barcha apostrof-shakldagi belgilarni olib tashlaymiz — aks holda faqat
# apostrof yo'qligi sababli mos kalit so'z topilmay qolishi mumkin edi
# (real holatda "Kimsiz ozi" IDENTITY_TRIGGERS'dagi "kimsiz o'zi" bilan mos
# kelmagan edi).
_APOSTROPHE_CHARS = "'`ʼʻʹ’‘"


def _normalize_uz(text: str) -> str:
    for ch in _APOSTROPHE_CHARS:
        text = text.replace(ch, "")
    return text.lower()


def is_identity_question(text: str) -> bool:
    """Foydalanuvchi "siz kimsiz", "bot emasmisiz" kabi kimlikni surishtiruvchi
    savol berayotganini aniqlaydi (oddiy substring qidiruvi orqali, AI'siz).
    Apostrofsiz yozilgan shakllar ham (masalan "kimsiz ozi") aniqlanadi."""
    t = _normalize_uz(text)
    return any(_normalize_uz(trigger) in t for trigger in IDENTITY_TRIGGERS)


def answer_implies_contact_collection(answer: str) -> bool:
    """
    AI javobining o'zi allaqachon "ismingizni va telefon raqamingizni
    qoldiring" kabi ariza yig'ish taklifini berganini aniqlaydi.

    MUHIM: real foydalanuvchi suhbatida bu holat aniqlangan bug — user
    xabari (masalan "Men ham qilmoqchi edim") lead_trigger_keywords
    ro'yxatidagi hech qanday so'zga mos kelmagani uchun wants_lead=False
    bo'lib qolgan, lekin AI system_prompt ko'rsatmasiga ko'ra o'zi
    "Ismingizni va telefon raqamingizni qoldirsangiz..." deb so'ragan.
    Natijada mijoz ma'lumot qoldirganiga ishongan, lekin PendingLead oqimi
    hech qachon boshlanmagani uchun HECH NARSA saqlanmagan (ariza panelda
    ko'rinmagan). Bu funksiya shu holatni orqadan ushlab, wants_lead=True
    qilib beradi — AI o'zi va'da bergan narsani backend albatta bajaradi.
    """
    t = _normalize_uz(answer)
    has_name_word = "ism" in t
    has_contact_word = "telefon" in t or "raqam" in t
    return has_name_word and has_contact_word


def index_document(document: Document) -> None:
    """Hujjatni o'qib, bo'laklarga bo'lib, embedding qilib bazaga yozadi."""
    document.status = "processing"
    document.save(update_fields=["status"])
    try:
        text = extract_text(document.file.path)
        chunks = split_text(text)
        if not chunks:
            raise ValueError("Hujjatdan matn topilmadi (bo'sh yoki noto'g'ri format)")

        vectors = embed_texts(chunks, task_type="RETRIEVAL_DOCUMENT")

        DocumentChunk.objects.filter(document=document).delete()
        objs = [
            DocumentChunk(document=document, content=chunk, embedding=vector, order=i)
            for i, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]
        DocumentChunk.objects.bulk_create(objs)

        document.status = "ready"
        document.error_message = ""
    except Exception as exc:  # noqa: BLE001 - foydalanuvchiga sabab ko'rsatiladi
        document.status = "error"
        document.error_message = str(exc)
    document.save()


def retrieve_context(question: str, top_k: int | None = None) -> str:
    """Savolga eng yaqin bo'laklarni pgvector cosine distance orqali topadi."""
    top_k = top_k or settings.RAG_TOP_K
    query_vector = embed_query(question)

    chunks = (
        DocumentChunk.objects.filter(document__status="ready")
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[:top_k]
    )
    return "\n\n".join(c.content for c in chunks)


def detect_buying_intent(question: str, config: BotConfig) -> bool:
    """
    Xarid niyatini aniqlaydi — FAQAT joriy xabarda kalit so'z bor-yo'qligini
    tekshiradi.

    MUHIM: avval bu funksiya suhbatning oxirgi 10 ta xabarini ham tekshirar
    edi — bu bug'ga olib kelgan: foydalanuvchi bir marta "narxi qancha?" deb
    yozib ariza qoldirgach, keyingi butunlay bog'liqsiz xabarlarida ham
    (masalan "siz kimsiz?") ariza oqimi bekorga qayta ishga tushib, "ismingizni
    yozing" degan taklif qayta-qayta yuborilardi. Endi faqat JORIY xabarda
    kalit so'z aniq aytilgan bo'lsagina ariza oqimi boshlanadi.

    Solishtirish apostrofsiz shakllarni ham hisobga oladi (masalan
    "bog'lan" kalit so'zi "boglanaman" kabi apostrofsiz yozilgan xabarda
    ham topiladi) — _normalize_uz orqali.
    """
    t = _normalize_uz(question)
    return any(_normalize_uz(keyword) in t for keyword in config.lead_trigger_list)


def answer_question(question: str, channel: str = "userbot", history: list[dict] | None = None):
    """
    Qaytaradi: (javob, input_token, output_token, ai_javob_berdimi: bool, ariza_kerakmi: bool)

    MUHIM #1: ariza_kerakmi (wants_lead) AI javob bera oldi-yo'qmi (answered_by_ai)
    holatidan mustaqil hisoblanadi va qaytariladi — hujjatlarda mos ma'lumot
    topilmasa ham (masalan narx haqida hujjat yuklanmagan bo'lsa), foydalanuvchi
    xarid niyatini bildirgan bo'lsa, ariza baribir yig'ilishi kerak.

    MUHIM #2: Vertex AI chaqiruvi (generate_answer) llm.py ichida avtomatik
    bir necha marta qayta urinadi (max_retries). Agar BARCHA urinishlar ham
    muvaffaqiyatsiz bo'lsa (masalan kvota butunlay tugagan bo'lsa), bu
    funksiya hech qachon exception tashlamaydi — lekin foydalanuvchiga HECH
    QANDAY xabar ham qaytarilmaydi: answer=None qaytariladi va xatolik faqat
    log'ga yoziladi. userbot/handlers.py buni tekshirib, javob yubormasdan
    jim qoladi (foydalanuvchi AI'da muammo borligini sezmasligi kerak).
    wants_lead esa (agar foydalanuvchi xarid niyatini bildirgan bo'lsa)
    baribir saqlanadi — bu AI'dan mustaqil, kalit so'zga asoslangan mantiq,
    shuning uchun ariza yig'ish oqimi AI ishlamay qolganda ham davom etadi.
    """
    subscription = ProjectSubscription.get_solo()
    if not subscription.is_service_active:
        # MUHIM: obuna faol emasligi haqida foydalanuvchiga HECH QANDAY xabar
        # yuborilmaydi (AI butunlay ishlamay qolganda ham qo'llaniladigan
        # sukut mantiqi bilan bir xil) — bot shunchaki jim qoladi, "xizmat
        # to'xtatilgan" kabi ichki holatni oshkor qilmaydi.
        return (None, 0, 0, False, False)

    config = BotConfig.get_solo()
    if not config.ai_enabled:
        return config.fallback_message, 0, 0, False, False

    wants_lead = detect_buying_intent(question, config)

    # "Siz kimsiz" kabi kimlikni surishtiruvchi savollarga LLM'ga umuman
    # murojaat qilmasdan, har doim bir xil operator javobini beramiz — LLM
    # ba'zan ko'rsatmaga qaramay o'zini AI/bot deb oshkor qilib qo'yishi
    # mumkin edi, bu esa buni butunlay istisno qiladi.
    if is_identity_question(question):
        return OPERATOR_IDENTITY_RESPONSE, 0, 0, True, wants_lead

    # MUHIM: avval retrieve_context() bu try/except tashqarisida edi — Vertex
    # AI embedding chaqiruvi vaqtinchalik xatolik bersa (masalan 503), butun
    # jarayon HECH QANDAY qayta urinishsiz, tutilmagan (unhandled) xatolik
    # bilan to'xtab qolardi. Endi embeddings.py'ning o'zi ham qayta uringani
    # uchun, va bu yerda ham generate_answer bilan bir xil try/except ostiga
    # olingani uchun, oxir-oqibat baribir "sukut" bilan yakunlanadi.
    try:
        context = retrieve_context(question)
        if not context.strip():
            return config.fallback_message, 0, 0, False, wants_lead

        answer, in_tok, out_tok = generate_answer(
            config.system_prompt, context, question, history, model_name=subscription.llm_model
        )
    except Exception as exc:  # noqa: BLE001 - barcha urinishlar tugagach shu yerga tushadi
        logger.exception(
            "Vertex AI barcha qayta urinishlardan keyin ham xatolik berdi — "
            "userga hech qanday xabar yuborilmaydi (sukut saqlanadi): %s", exc,
        )
        return None, 0, 0, False, wants_lead

    # Agar user xabarida kalit so'z bo'lmasa-yu, AI o'zi (system_prompt
    # ko'rsatmasiga ko'ra) ism/telefon so'ragan bo'lsa — bu ham ariza yig'ish
    # boshlanishi kerakligini bildiradi (aks holda AI va'da bergani backend'da
    # hech qachon saqlanmay qoladi).
    if not wants_lead and answer_implies_contact_collection(answer):
        wants_lead = True

    return answer, in_tok, out_tok, True, wants_lead
