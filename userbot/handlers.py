"""
Telethon (Telegram AKKAUNT) uchun xabar handlerlari.
Django ORM sinxron bo'lgani uchun barcha chaqiruvlar sync_to_async orqali bajariladi.

Ariza (lead) bosqichma-bosqich yig'ilishi uchun bazada saqlanadigan
PendingLead modelidan foydalaniladi (Telethon'da FSM mexanizmi bo'lmagani
uchun DB-based holat mashinasi ishlatiladi).

Guruh (group chat) qo'llab-quvvatlashi: shaxsiy yozishmalardan farqli
o'laroq, guruhda AI faqat administrator shu guruhni yoqib qo'ygan va
(agar rejim shunday sozlangan bo'lsa) kalit so'z bilan chaqirilgan yoki
userbotning oldingi xabariga reply qilingan taqdirdagina javob beradi
(reply — bu ham aniq signal, kalit so'zsiz ham ishlaydi). Har bir
foydalanuvchining shu guruhdagi shaxsiy tarixi (boshqalarnikidan va
boshqa guruhlarnikidan alohida) AI'ga kontekst sifatida beriladi. Xarid
niyati aniqlansa, guruhda DM'dagidek bosqichma-bosqich ism/telefon
SO'RALMAYDI (bu noqulay) — ariza to'g'ridan-to'g'ri, qo'lda bor Telegram
ism/username bilan saytga (Arizalar, channel="group") yoziladi.

Xabar yuborish har doim _send_message() orqali amalga oshiriladi — bu
funksiya (1) Telegram flood-limitiga tushib qolmaslik uchun har bir xabar
oldidan ozgina kechikish qo'shadi va Telethon FloodWaitError yuz bersa
kutib qayta yuboradi, (2) uzun javoblarni xatboshi/gap bo'yicha bo'laklarga
bo'lib, odam yozayotgandek ketma-ket bir nechta xabar sifatida yuboradi.
"""
import asyncio
import logging
import random
import re

from asgiref.sync import sync_to_async
from telethon import events
from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)

# Ism xabaridan tez-tez uchraydigan kirish so'zlarini olib tashlaydi
# ("Mening ismim Ali" -> "Ali"). AI so'roviga murojaat qilinmaydi — bu
# Vertex AI kvotasini tejash uchun oddiy, tez va bepul regex orqali qilinadi.
_NAME_PREFIX_RE = re.compile(
    r"(?i)^\s*(mening\s+ismim|ismim|ism-familiyam|men)\s*[:\-]?\s*"
)

# Telefon raqamini matndan ajratib olish uchun — foydalanuvchi qanday
# formatda yozishidan qat'iy nazar (bo'shliq, tire, qavs, +998 bilan yoki
# bilarsiz) ishlaydigan oddiy validator. Bu ham AI so'rovisiz, regex orqali.
_DIGITS_RE = re.compile(r"[^\d+]")

# Guruh xabarlaridagi so'zlardan boshida/oxirida turadigan tinish
# belgilarini olib tashlash uchun (kalit so'zni aniqroq taqqoslash uchun).
_PUNCT_STRIP = ".,!?:;()\"'«»"

# Matn ichida telefon-ga o'xshash raqamlar ketma-ketligini topish uchun
# (ism va telefonni BITTA xabarda ajratib olishda ishlatiladi).
_PHONE_LIKE_RE = re.compile(r"[+\d][\d\s\-()]{6,}\d")

# Uzun javoblarni gap bo'yicha bo'lib yuborish uchun (nuqta/undov/so'roq
# belgisidan keyingi bo'shliqda bo'linadi).
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Bitta Telegram xabari qancha uzun bo'lishi mumkinligining chegarasi — bundan
# uzun javoblar bir nechta xabarga bo'linadi (odam yozgandek tabiiyroq
# ko'rinishi va o'qishga qulayroq bo'lishi uchun).
# MUHIM: avval 350 edi — bu juda kichik bo'lgani uchun o'rtacha javob ham
# 3-4 bo'lakka bo'linib, har bir bo'lak orasidagi kechikish qo'shilib,
# umumiy javob "juda sekin" bo'lib qolardi. Oshirilgach, bo'laklar soni
# kamayadi (Telegram xabar chegarasi — 4096 belgi, bundan hali ham ancha uzoq).
_MAX_MESSAGE_LEN = 700


def _clean_name(text: str) -> str:
    cleaned = _NAME_PREFIX_RE.sub("", text).strip()
    return cleaned or text.strip()


def _try_extract_name_and_phone(text: str):
    """
    Foydalanuvchi ism va telefon raqamini BITTA xabarda yozgan bo'lishi
    mumkin (masalan "Saidakbar +998910010101") — real suhbatda bu holat
    kuzatilgan va avvalgi mantiq butun xabarni "ism" sifatida qabul qilib,
    keyin yana bekorga telefon so'rardi. Bu funksiya matndan telefonga
    o'xshash ketma-ketlikni ajratib, qolgan qismini ism sifatida qaytaradi.
    Muvaffaqiyatli bo'lsa (full_name, phone), aks holda (None, None).
    """
    match = _PHONE_LIKE_RE.search(text)
    if not match:
        return None, None
    phone = _extract_phone(match.group(0))
    if not phone:
        return None, None
    remainder = (text[:match.start()] + text[match.end():]).strip()
    remainder = remainder.strip(_PUNCT_STRIP + " ")
    if not remainder:
        return None, None
    full_name = _clean_name(remainder)
    if not full_name:
        return None, None
    return full_name, phone


def _extract_phone(text: str) -> str | None:
    """
    Matndan O'zbekiston formatidagi telefon raqamini ajratib, +998XXXXXXXXX
    ko'rinishida qaytaradi. Mos raqam topilmasa None qaytaradi.
    """
    digits = _DIGITS_RE.sub("", text)
    has_plus = digits.startswith("+")
    core = digits[1:] if has_plus else digits
    if not core.isdigit():
        return None

    if len(core) == 9:
        # masalan: 901234567
        return "+998" + core
    if len(core) == 12 and core.startswith("998"):
        return "+" + core
    if 9 <= len(core) <= 13:
        # boshqa davlat kodi bo'lishi mumkin — bor holicha, "+" bilan qaytaramiz
        return "+" + core if not has_plus else digits
    return None


def _normalize_token(token: str) -> str:
    return token.strip(_PUNCT_STRIP).lower().lstrip("/#")


def _group_message_matches_keyword(text: str, keywords: list[str]) -> bool:
    """
    Guruh xabari kalit so'zlardan birortasini o'z ichiga oladimi, tekshiradi.
    "/ai", "ai", "#savol", "/savol", "savol" kabi barcha shakllar bir xil
    deb hisoblanadi — chunki har bir so'z prefiksdan (/, #) tozalanadi.
    """
    if not keywords:
        return False
    tokens = {_normalize_token(tok) for tok in text.split()}
    return any(kw in tokens for kw in keywords)


def _strip_leading_trigger(text: str, keywords: list[str]) -> str:
    """
    Agar xabar aynan kalit so'z bilan boshlangan bo'lsa ("/ai narxi qancha?"),
    shu kalit so'zni olib tashlab, qolgan qismini AI'ga savol sifatida beradi.
    Kalit so'z gap ichida boshqa joyda bo'lsa, matn o'zgarishsiz qaytariladi.
    """
    parts = text.split(None, 1)
    if not parts:
        return text
    if _normalize_token(parts[0]) in keywords:
        return parts[1].strip() if len(parts) > 1 else ""
    return text


def _split_into_chunks(text: str, max_len: int = _MAX_MESSAGE_LEN) -> list[str]:
    """
    Uzun javobni bir nechta tabiiy ko'rinishdagi xabarga bo'ladi — avval
    xatboshilar (bo'sh qatordan ajratilgan) bo'yicha, so'ng juda uzun
    xatboshilarni gap (nuqta/undov/so'roq belgisi) bo'yicha, har biri
    max_len atrofida bo'ladigan qilib guruhlaydi. Qisqa javoblar (max_len
    dan kichik) bitta xabar sifatida (bo'linmasdan) qaytariladi.
    """
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_len:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()] or [text]
    chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= max_len:
            chunks.append(para)
            continue
        sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(para) if s.strip()] or [para]
        current = ""
        for sent in sentences:
            candidate = (current + " " + sent).strip() if current else sent
            if current and len(candidate) > max_len:
                chunks.append(current.strip())
                current = sent
            else:
                current = candidate
        if current:
            chunks.append(current.strip())
    return chunks if chunks else [text]


async def _send_message(event, text: str, use_reply: bool = False) -> None:
    """
    Xabarni Telegram flood-limitlarini hisobga olgan holda yuboradi.

    MUHIM: Telethon orqali ishlayotgan oddiy foydalanuvchi akkaunti (bot API
    emas) juda tez-tez xabar yuborsa, Telegram tomonidan vaqtinchalik
    cheklanishi (FloodWaitError) mumkin. Buning oldini olish uchun:
    (1) har bir xabar oldidan ozgina (odam yozayotgandek) tasodifiy
        kechikish qo'shiladi;
    (2) agar baribir FloodWaitError yuz bersa, Telegram ko'rsatgan vaqtni
        kutib, keyin qayta yuboriladi (foydalanuvchi xatoni sezmaydi);
    (3) uzun javob avval xatboshi/gap bo'yicha bo'laklarga bo'linadi va har
        bir bo'lak orasida ham kechikish bilan ketma-ket yuboriladi — bu ham
        flood-limitdan saqlaydi, ham javobni tabiiyroq ko'rinishga keltiradi.
    """
    chunks = _split_into_chunks(text)
    if not chunks:
        return

    send_reply_fn = event.reply if use_reply else event.respond

    for i, chunk in enumerate(chunks):
        # Har bir xabar (birinchisi ham) oldidan ozgina kutamiz — flood-limit
        # va ozgina "odamdek" tuyulishi uchun. MUHIM: bu qiymat 0.6-1.6 dan
        # 1.6-3.2 gacha oshirilgan, keyin 0.9-1.8 ga tushirilgan edi — lekin
        # foydalanuvchi hamon "juda sekin" deb shikoyat qildi (ayniqsa
        # _MAX_MESSAGE_LEN kichik bo'lgani uchun ko'p bo'lakka bo'linganda).
        # Endi tezlik ustunlik qiladi — chegara sezilarli qisqartirildi.
        await asyncio.sleep(random.uniform(0.35, 0.8))
        send_fn = send_reply_fn if i == 0 else event.respond
        try:
            await send_fn(chunk)
        except FloodWaitError as exc:
            wait_seconds = exc.seconds + 1
            logger.warning(
                "Telegram flood-limit: %s soniya kutib, qayta yuborishga harakat qilinmoqda.",
                wait_seconds,
            )
            await asyncio.sleep(wait_seconds)
            await send_fn(chunk)


async def _mark_read(event) -> None:
    """
    Xabarni "o'qilgan" deb belgilaydi (ikkita ko'k ptichka). MUHIM: bu FAQAT
    botning o'zi haqiqatan ham javob yubora olganda chaqiriladi — agar Vertex
    AI barcha qayta urinishlardan keyin ham ishlamay qolsa (javob=None), xabar
    ATAYIN o'qilmagan holda qoldiriladi, shunda operator qaysi xabarga AI
    javob berolmaganini Telegram'ning o'zida (o'qilmagan belgisi orqali)
    darhol ko'rib, qo'lda javob berishi mumkin.
    """
    try:
        await event.mark_read()
    except Exception:  # noqa: BLE001 - read-receipt ixtiyoriy, muhim emas
        pass


@sync_to_async
def ask_ai(question: str, user_id: int):
    from assistant.models import ConversationLog
    from assistant.services.rag import answer_question

    # Oxirgi 10 ta savol-javobni (kamida 10 ta "tepadagi yozilgan" xabarni) olib,
    # AI kontekstiga va xarid niyatini aniqlashga beramiz.
    recent = list(
        ConversationLog.objects.filter(telegram_user_id=user_id, channel="userbot")
        .order_by("-created_at")[:10]
    )
    recent.reverse()  # eskidan yangiga
    history = []
    for log in recent:
        history.append({"role": "user", "content": log.question})
        history.append({"role": "assistant", "content": log.answer})

    return answer_question(question, channel="userbot", history=history)


@sync_to_async
def ask_ai_group(question: str, user_id: int, chat_id: int):
    """
    Guruh uchun ham endi shaxsiy tarix (history) beriladi — lekin FAQAT shu
    foydalanuvchining O'ZI shu GURUHDA yozgan oxirgi xabarlari (boshqa
    a'zolarning yozishmalari aralashtirilmaydi, va bitta odam bir nechta
    guruhda bo'lsa, guruhlar tarixi ham bir-biriga aralashmaydi — chat_id
    bo'yicha alohida ajratiladi).
    """
    from assistant.models import ConversationLog
    from assistant.services.rag import answer_question

    recent = list(
        ConversationLog.objects.filter(telegram_user_id=user_id, channel="group", chat_id=chat_id)
        .order_by("-created_at")[:10]
    )
    recent.reverse()
    history = []
    for log in recent:
        history.append({"role": "user", "content": log.question})
        history.append({"role": "assistant", "content": log.answer})

    return answer_question(question, channel="group", history=history)


@sync_to_async
def create_group_lead(user_id, username, full_name, message):
    """
    Guruhda xarid niyati aniqlansa, DM'dagidek bosqichma-bosqich ism/telefon
    so'ralmaydi (guruh ichida notanish odamdan so'rash noqulay) — buning
    o'rniga ariza to'g'ridan-to'g'ri, qo'lda bor ma'lumot (Telegram username,
    ism-familiya, xabar matni) bilan saytga (Arizalar) yoziladi, telefonsiz.
    """
    from assistant.models import Lead
    Lead.objects.create(
        telegram_user_id=user_id,
        telegram_username=username or "",
        full_name=full_name or "",
        phone="",
        message=message,
        channel="group",
    )


@sync_to_async
def transcribe_voice(audio_bytes: bytes, mime_type: str):
    from assistant.services.llm import transcribe_audio
    return transcribe_audio(audio_bytes, mime_type=mime_type)


@sync_to_async
def log_conversation(user_id, question, answer, answered_by_ai, in_tok=0, out_tok=0, channel="userbot", chat_id=None):
    from assistant.models import ConversationLog
    ConversationLog.objects.create(
        telegram_user_id=user_id, question=question, answer=answer,
        answered_by_ai=answered_by_ai, input_tokens=in_tok, output_tokens=out_tok,
        channel=channel, chat_id=chat_id,
    )


async def _is_reply_to_bot(event) -> bool:
    """
    Foydalanuvchi guruhda userbotning O'ZINING oldingi xabariga reply
    qilganini aniqlaydi. Bunday holda kalit so'z ("keyword" rejimi) talab
    qilinmaydi — reply qilishning o'zi allaqachon aniq signal (foydalanuvchi
    ayni shu xabarni botga qaratmoqda).
    """
    if not event.message.is_reply:
        return False
    try:
        replied = await event.message.get_reply_message()
    except Exception:  # noqa: BLE001 - reply xabari o'chirilgan/topilmasa oddiy tekshiruv
        return False
    return bool(replied and replied.out)


@sync_to_async
def get_pending_lead(user_id):
    from assistant.models import PendingLead
    return PendingLead.objects.filter(telegram_user_id=user_id).first()


@sync_to_async
def start_pending_lead(user_id, username, original_message):
    from assistant.models import PendingLead
    PendingLead.objects.update_or_create(
        telegram_user_id=user_id,
        defaults={"telegram_username": username or "", "original_message": original_message, "step": "name"},
    )


@sync_to_async
def advance_pending_lead_to_phone(pending_id, full_name):
    from assistant.models import PendingLead
    PendingLead.objects.filter(pk=pending_id).update(full_name=full_name, step="phone")


@sync_to_async
def finalize_pending_lead(pending):
    from assistant.models import Lead, PendingLead
    Lead.objects.create(
        telegram_user_id=pending.telegram_user_id,
        telegram_username=pending.telegram_username,
        full_name=pending.full_name,
        phone="",  # quyida to'ldiriladi (chaqiruvchi joyida)
        message=pending.original_message,
        channel="userbot",
    )
    PendingLead.objects.filter(pk=pending.pk).delete()


@sync_to_async
def finalize_pending_lead_with_phone(pending, phone):
    from assistant.models import Lead, PendingLead
    Lead.objects.create(
        telegram_user_id=pending.telegram_user_id,
        telegram_username=pending.telegram_username,
        full_name=pending.full_name,
        phone=phone,
        message=pending.original_message,
        channel="userbot",
    )
    PendingLead.objects.filter(pk=pending.pk).delete()


@sync_to_async
def finalize_pending_lead_combined(pending, full_name, phone):
    """
    Foydalanuvchi ism va telefonni BITTA xabarda yuborganda ("name"
    bosqichida) ishlatiladi — alohida "phone" bosqichiga o'tmasdan,
    to'g'ridan-to'g'ri Lead yaratib, PendingLead'ni yakunlaydi.
    """
    from assistant.models import Lead, PendingLead
    Lead.objects.create(
        telegram_user_id=pending.telegram_user_id,
        telegram_username=pending.telegram_username,
        full_name=full_name,
        phone=phone,
        message=pending.original_message,
        channel="userbot",
    )
    PendingLead.objects.filter(pk=pending.pk).delete()


@sync_to_async
def get_or_create_group(chat_id: int, title: str):
    from assistant.models import TelegramGroup
    group, created = TelegramGroup.objects.get_or_create(
        chat_id=chat_id, defaults={"title": title or ""},
    )
    if not created:
        update_fields = ["last_seen_at"]
        if title and group.title != title:
            group.title = title
            update_fields.append("title")
        group.save(update_fields=update_fields)
    return group


@sync_to_async
def get_group_trigger_keywords():
    from assistant.models import BotConfig
    return BotConfig.get_solo().group_trigger_list


def register_handlers(client):

    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def handle_message(event):
        user_id = event.sender_id

        # MUHIM: real Telegram akkauntga (userbot) doim spam-botlar
        # ("qiz topdim", "anonim savol keldi", "yangi film" va h.k.) yozib
        # turadi — bular haqiqiy mijoz emas, shuning uchun AI ularga javob
        # bermasligi, ariza/statistikaga ham qo'shilmasligi kerak. Ikki
        # ishonchli belgi: (1) xabar forward qilingan (haqiqiy mijoz odatda
        # o'zi yozadi, forward qilmaydi), (2) yuboruvchining o'zi bot akkaunt.
        if event.message.forward:
            return
        sender = await event.get_sender()
        if getattr(sender, "bot", False):
            return

        is_voice = bool(getattr(event.message, "voice", None))
        if not is_voice:
            text = (event.raw_text or "").strip()
            if not text:
                return

        # MUHIM: "yozmoqda..." indikatori endi FAQAT AI javob tayyorlashda
        # emas, balki javob to'liq YUBORILGUNCHA (shu jumladan _send_message
        # ichidagi bo'lak-bo'lak, kechikish bilan yuborish jarayonida ham)
        # ko'rinib turadi — aks holda AI javob tayyorlagandan keyin, xabar
        # bo'laklab yuborilayotganda foydalanuvchi hech narsa ko'rmay, botga
        # o'xshamay qolar edi. Telethon shu blok ochiq turgan davomida
        # "typing" holatini o'zi davriy ravishda qayta yuborib turadi.
        async with event.client.action(event.chat_id, "typing"):
            if is_voice:
                audio_bytes = await event.download_media(bytes)
                mime_type = getattr(event.message.file, "mime_type", None) or "audio/ogg"
                text = await transcribe_voice(audio_bytes, mime_type)
                if not text:
                    await _send_message(
                        event,
                        "Kechirasiz, ovozli xabaringizni tushuna olmadim. "
                        "Matn ko'rinishida yozib yuborsangiz bo'ladimi?",
                    )
                    await _mark_read(event)
                    return

            username = getattr(sender, "username", None)

            pending = await get_pending_lead(user_id)

            if pending and pending.step == "name":
                from assistant.services.rag import is_identity_question, OPERATOR_IDENTITY_RESPONSE

                # Foydalanuvchi ism o'rniga "siz kimsiz?" kabi savol yozsa, buni
                # ism sifatida qabul qilib olmaymiz — operator javobini berib,
                # ismni yana so'raymiz (aks holda arizada "Siz kimsiz" degan
                # chalkash ism saqlanib qolar edi).
                if is_identity_question(text):
                    await _send_message(event, OPERATOR_IDENTITY_RESPONSE)
                    await _send_message(event, "Ismingizni yozib qoldirasizmi?")
                    await _mark_read(event)
                    return

                # Foydalanuvchi ism va telefonni bitta xabarda yuborgan bo'lishi
                # mumkin (masalan "Saidakbar +998910010101") — real suhbatda bu
                # holat kuzatilgan. Bunday bo'lsa, alohida "phone" bosqichiga
                # o'tmasdan, to'g'ridan-to'g'ri arizani yakunlaymiz.
                combined_name, combined_phone = _try_extract_name_and_phone(text)
                if combined_name and combined_phone:
                    await finalize_pending_lead_combined(pending, combined_name, combined_phone)
                    await _send_message(event, "Rahmat! Arizangiz qabul qilindi, tez orada siz bilan bog'lanamiz.")
                    await _mark_read(event)
                    return

                full_name = _clean_name(text)
                await advance_pending_lead_to_phone(pending.pk, full_name=full_name)
                await _send_message(
                    event, "Rahmat! Endi telefon raqamingizni yozing (masalan: +998901234567):"
                )
                await _mark_read(event)
                return

            if pending and pending.step == "phone":
                phone = _extract_phone(text)
                if not phone:
                    await _send_message(
                        event,
                        "Kechirasiz, telefon raqamini to'g'ri kiritmadingiz. "
                        "Iltimos, faqat raqamlar bilan yozing, masalan: +998901234567",
                    )
                    await _mark_read(event)
                    return
                await finalize_pending_lead_with_phone(pending, phone=phone)
                await _send_message(event, "Rahmat! Arizangiz qabul qilindi, tez orada siz bilan bog'lanamiz.")
                await _mark_read(event)
                return

            # Oddiy savol — RAG orqali javob
            answer, in_tok, out_tok, answered_by_ai, wants_lead = await ask_ai(text, user_id)

            await log_conversation(user_id, text, answer or "", answered_by_ai, in_tok, out_tok)

            # MUHIM: agar Vertex AI barcha qayta urinishlardan keyin ham xatolik
            # bergan bo'lsa, rag.answer_question answer=None qaytaradi — bunday
            # holatda foydalanuvchiga HECH QANDAY xabar (hattoki "band" degan
            # xabar ham) yuborilmaydi, bot jim qoladi — VA xabar ATAYIN
            # o'qilmagan holda qoldiriladi (mark_read chaqirilmaydi), shunda
            # operator qaysi savolga AI javob berolmaganini darhol ko'radi.
            sent_any = False
            if answer:
                await _send_message(event, answer)
                sent_any = True

            # MUHIM: wants_lead endi answered_by_ai'dan mustaqil tekshiriladi — hujjatda
            # mos ma'lumot topilmagan (masalan narx haqida hujjat yo'q) yoki AI umuman
            # ishlamay qolgan taqdirda ham, foydalanuvchi xarid niyatini bildirgan bo'lsa,
            # ariza baribir yig'iladi (bu kalit so'zga asoslangan, AI'siz mantiq).
            if wants_lead and not pending:
                await start_pending_lead(user_id, username, original_message=text)
                await _send_message(event, "Bu bilan qiziqsangiz, ismingizni yozing — operatorimiz siz bilan bog'lanadi:")
                sent_any = True

            if sent_any:
                await _mark_read(event)

    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_group))
    async def handle_group_message(event):
        text = (event.raw_text or "").strip()
        if not text:
            return

        # Spam/forward/bot-akkaunt xabarlarga javob bermaymiz (DM'dagi bilan
        # bir xil mantiq — handle_message'dagi izohga qarang).
        if event.message.forward:
            return
        sender = await event.get_sender()
        if getattr(sender, "bot", False):
            return

        # Guruhni avtomatik ro'yxatga olamiz (yoki mavjudini yangilaymiz) —
        # admin panel > Guruhlar sahifasida shu yerda ko'rinadi.
        chat = await event.get_chat()
        title = getattr(chat, "title", "") or ""
        group = await get_or_create_group(event.chat_id, title)

        if not group.is_ai_enabled:
            return

        question = text
        if group.reply_mode == "keyword" and not await _is_reply_to_bot(event):
            keywords = await get_group_trigger_keywords()
            if not _group_message_matches_keyword(text, keywords):
                return
            question = _strip_leading_trigger(text, keywords) or text

        if group.sender_filter != "everyone":
            try:
                perms = await event.client.get_permissions(event.chat_id, event.sender_id)
                is_admin = bool(getattr(perms, "is_admin", False) or getattr(perms, "is_creator", False))
            except Exception:  # noqa: BLE001 - ruxsatni tekshirib bo'lmasa, oddiy foydalanuvchi deb hisoblaymiz
                is_admin = False
            if group.sender_filter == "admins" and not is_admin:
                return
            if group.sender_filter == "users" and is_admin:
                return

        # MUHIM: "yozmoqda..." endi javob TO'LIQ yuborilguncha (bo'lak-bo'lak,
        # kechikish bilan yuborish jarayonida ham) ko'rinib turadi — shaxsiy
        # yozishmadagi bilan bir xil mantiq (handle_message'dagi izohga qarang).
        user_id = event.sender_id
        async with event.client.action(event.chat_id, "typing"):
            answer, in_tok, out_tok, answered_by_ai, wants_lead = await ask_ai_group(question, user_id, event.chat_id)

            await log_conversation(
                user_id, question, answer or "", answered_by_ai, in_tok, out_tok,
                channel="group", chat_id=event.chat_id,
            )

            # MUHIM: bosqichma-bosqich ism/telefon so'rash (DM'dagidek) guruhda
            # noqulay bo'lgani uchun ishlatilmaydi — lekin ariza qo'lda bor
            # ma'lumot (Telegram ism/username) bilan to'g'ridan-to'g'ri saytga
            # (Arizalar) yoziladi, hech qanday qo'shimcha xabar yuborilmasdan.
            if wants_lead:
                username = getattr(sender, "username", None)
                full_name = " ".join(
                    filter(None, [getattr(sender, "first_name", None), getattr(sender, "last_name", None)])
                ).strip()
                await create_group_lead(user_id, username, full_name, question)

            # MUHIM: guruhda ham xuddi shaxsiy yozishmadagidek — AI barcha qayta
            # urinishlardan keyin ham xatolik bersa, HECH QANDAY xabar yuborilmaydi
            # va xabar ATAYIN o'qilmagan qoldiriladi (operator darhol ko'rishi
            # uchun) — mark_read faqat javob haqiqatan yuborilganda chaqiriladi.
            if answer:
                await _send_message(event, answer, use_reply=True)
                await _mark_read(event)
