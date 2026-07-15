# -*- coding: utf-8 -*-
"""
Ariza (lead) oqimining to'liq sandbox testi.

Haqiqiy Postgres/pgvector va Vertex AI'ga ulanmasdan, faqat SQLite (xotirada)
va mock (soxta) LLM javoblari orqali butun mantiqni sinaydi:
  1) detect_buying_intent - FAQAT joriy xabarda kalit so'z bo'lsa ishlaydi
     (tarix/history endi umuman tekshirilmaydi - bu avvalgi bug'ning tuzatilishi)
  2) answer_question - wants_lead answered_by_ai'dan mustaqilligi (context
     topilmasa ham lead ishlashi kerak; AI barcha urinishdan keyin ham
     xato bersa answer=None qaytishi va userga HECH NIMA yubormaslik kerak)
  3) PendingLead -> Lead to'liq zanjiri (ism tozalash, telefon validatsiya)
  4) is_identity_question / OPERATOR_IDENTITY_RESPONSE - "siz kimsiz" kabi
     savollarga LLM'siz, doim bir xil operator javobi qaytishi
  5) Guruh (group chat) kalit so'z aniqlash va TelegramGroup avtomatik
     ro'yxatga olish mantiqi

Ishga tushirish: python3 test_lead_flow.py
"""
import os
import sys

PROJECT_DIR = "/sessions/quirky-beautiful-cray/mnt/agent_shablon"
sys.path.insert(0, PROJECT_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import config.settings as settings_module  # noqa: E402

settings_module.DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}

import django  # noqa: E402

django.setup()

from django.db import connection  # noqa: E402
from assistant.models import (  # noqa: E402
    BotConfig, ProjectSubscription, Lead, PendingLead, ConversationLog, TelegramGroup,
)

print("Ishlatilayotgan DB backend:", connection.settings_dict["ENGINE"])
assert connection.settings_dict["ENGINE"] == "django.db.backends.sqlite3", (
    "SQLite'ga o'tolmadik - hali ham boshqa DB ishlatilmoqda!"
)

with connection.schema_editor() as schema_editor:
    for model in (BotConfig, ProjectSubscription, Lead, PendingLead, ConversationLog, TelegramGroup):
        schema_editor.create_model(model)

from unittest.mock import patch  # noqa: E402
from assistant.services import rag  # noqa: E402
from userbot import handlers  # noqa: E402

PASS = []
FAIL = []


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print("OK   " + name)
    else:
        FAIL.append(name)
        print("FAIL " + name + "  " + detail)


config = BotConfig.get_solo()
ProjectSubscription.get_solo()

check(
    "1.1 'narxi' so'zi joriy xabarda aniqlanadi",
    rag.detect_buying_intent("Mahsulot narxi qancha?", config) is True,
)
check(
    "1.2 oddiy salomlashishda xarid niyati yo'q",
    rag.detect_buying_intent("Salom, qalaysiz?", config) is False,
)
check(
    "1.3 yangi 'ariza' kalit so'zi ishlaydi",
    rag.detect_buying_intent("Ariza qoldirmoqchiman", config) is True,
)
check(
    "1.4 tarix (history) endi tekshirilmaydi - avvalgi xabarda kalit so'z "
    "bo'lsa ham, joriy xabarda bo'lmasa aniqlanmaydi (bug tuzatilishi)",
    rag.detect_buying_intent("Ha, mayli bo'ladi", config) is False,
)
check(
    "1.5 'olaman' yangi kalit so'zi joriy xabarda aniqlanadi",
    rag.detect_buying_intent("10 ta olaman", config) is True,
)
check(
    "1.6 'bog'lan' ildizi turli shakllarda ham aniqlanadi",
    rag.detect_buying_intent("Qanday bog'lansam bo'ladi?", config) is True
    and rag.detect_buying_intent("Bog'lanmoqchiman sizlar bilan", config) is True,
)
check(
    "1.7 'siz kimsiz' savoli xarid niyati sifatida aniqlanmaydi",
    rag.detect_buying_intent("Siz kimsiz?", config) is False,
)
check(
    "1.8 is_identity_question('Siz kimsiz?') -> True",
    rag.is_identity_question("Siz kimsiz?") is True,
)
check(
    "1.9 is_identity_question('Botmisiz?') -> True",
    rag.is_identity_question("Botmisiz?") is True,
)
check(
    "1.10 is_identity_question oddiy savolda False",
    rag.is_identity_question("Ish vaqtingiz qanday?") is False,
)
check(
    "1.10b is_identity_question apostrofsiz 'Kimsiz ozi' -> True (real bug)",
    rag.is_identity_question("Kimsiz ozi") is True,
)
check(
    "1.10c detect_buying_intent apostrofsiz 'boglanaman' -> True",
    rag.detect_buying_intent("Sizlar bilan boglanaman", config) is True,
)

with patch.object(rag, "retrieve_context") as mock_retrieve:
    answer, in_tok, out_tok, answered_by_ai, wants_lead = rag.answer_question(
        "Siz kimsiz, bot bilan gaplashyapmanmi?", channel="userbot"
    )
    check(
        "1.11 identity savolida LLM/context'ga umuman murojaat qilinmaydi",
        mock_retrieve.called is False,
    )
    check(
        "1.12 identity savolida doim OPERATOR_IDENTITY_RESPONSE qaytadi",
        answer == rag.OPERATOR_IDENTITY_RESPONSE and answered_by_ai is True,
        "got answer=" + repr(answer),
    )

with patch.object(rag, "retrieve_context", return_value=""):
    answer, in_tok, out_tok, answered_by_ai, wants_lead = rag.answer_question(
        "Narxi qancha turadi?", channel="userbot"
    )
    check(
        "2.1 context topilmasa ham wants_lead=True",
        wants_lead is True and answered_by_ai is False,
        "got wants_lead=" + str(wants_lead) + " answered_by_ai=" + str(answered_by_ai),
    )
    check("2.1b fallback_message qaytadi", answer == config.fallback_message)

with patch.object(rag, "retrieve_context", return_value="Bizning mahsulotlar haqida ma'lumot."):
    with patch.object(rag, "generate_answer", side_effect=RuntimeError("429 ResourceExhausted (simulyatsiya)")):
        answer, in_tok, out_tok, answered_by_ai, wants_lead = rag.answer_question(
            "Sotib olaman, qanday buyurtma beraman?", channel="userbot"
        )
        check(
            "2.2 Vertex AI barcha urinishdan keyin ham xato bersa answer=None (sukut, userga hech nima)",
            answer is None and answered_by_ai is False,
            "got answer=" + repr(answer),
        )
        check("2.2b xato bo'lsa ham wants_lead=True saqlanadi (ariza oqimi AI'siz ham ishlaydi)", wants_lead is True)

with patch.object(rag, "retrieve_context", return_value="Mahsulot narxi 100000 so'm."):
    with patch.object(rag, "generate_answer", return_value=("Narxi 100000 so'm.", 50, 20)):
        answer, in_tok, out_tok, answered_by_ai, wants_lead = rag.answer_question(
            "Narxi qancha?", channel="userbot"
        )
        check("2.3 normal holatda AI javob beradi", answered_by_ai is True and answer == "Narxi 100000 so'm.")
        check("2.3b normal holatda ham wants_lead=True", wants_lead is True)

config.ai_enabled = False
config.save(update_fields=["ai_enabled"])
answer, in_tok, out_tok, answered_by_ai, wants_lead = rag.answer_question(
    "Narxi qancha?", channel="userbot"
)
check("2.4 AI o'chirilganda javob bermaydi", answered_by_ai is False)
check("2.4b AI o'chirilganda wants_lead=False", wants_lead is False)
config.ai_enabled = True
config.save(update_fields=["ai_enabled"])

USER_ID = 555111222
USERNAME = "test_mijoz"

PendingLead.objects.filter(telegram_user_id=USER_ID).delete()
PendingLead.objects.update_or_create(
    telegram_user_id=USER_ID,
    defaults={"telegram_username": USERNAME, "original_message": "Narxi qancha turadi?", "step": "name"},
)
pending = PendingLead.objects.get(telegram_user_id=USER_ID)
check("3.1 PendingLead 'name' bosqichida yaratildi", pending.step == "name")

raw_name_message = "Mening ismim Aziz"
cleaned = handlers._clean_name(raw_name_message)
check("3.2 ism 'Mening ismim...' prefiksidan tozalanadi", cleaned == "Aziz", "got " + repr(cleaned))

PendingLead.objects.filter(pk=pending.pk).update(full_name=cleaned, step="phone")
pending.refresh_from_db()
check("3.3 PendingLead 'phone' bosqichiga o'tdi", pending.step == "phone" and pending.full_name == "Aziz")

phone_cases = {
    "901234567": "+998901234567",
    "+998 90 123 45 67": "+998901234567",
    "998901234567": "+998901234567",
    "salom bu telefon emas": None,
}
for raw, expected in phone_cases.items():
    got = handlers._extract_phone(raw)
    check("3.4 telefon parsing: " + repr(raw) + " -> " + repr(expected), got == expected, "got " + repr(got))

valid_phone = handlers._extract_phone("+998901234567")
Lead.objects.create(
    telegram_user_id=pending.telegram_user_id,
    telegram_username=pending.telegram_username,
    full_name=pending.full_name,
    phone=valid_phone,
    message=pending.original_message,
    channel="userbot",
)
PendingLead.objects.filter(pk=pending.pk).delete()

lead = Lead.objects.filter(telegram_user_id=USER_ID).first()
check("3.5 Lead (ariza) DB'da yaratildi", lead is not None)
check("3.6 Lead'da ism to'g'ri", lead.full_name == "Aziz")
check("3.7 Lead'da telefon to'g'ri", lead.phone == "+998901234567")
check("3.8 Lead'da xabar (original_message) saqlangan", lead.message == "Narxi qancha turadi?")
check("3.9 Lead kanal='userbot'", lead.channel == "userbot")
check("3.10 PendingLead o'chirildi (yakunlangach)", not PendingLead.objects.filter(telegram_user_id=USER_ID).exists())
check("3.11 Lead status='new' (standart)", lead.status == "new")

PendingLead.objects.update_or_create(
    telegram_user_id=999888777,
    defaults={"telegram_username": "ikkinchi_mijoz", "original_message": "Sotib olaman", "step": "phone", "full_name": "Vali"},
)
bad_phone = handlers._extract_phone("bugun ob-havo yaxshi")
check("4.1 noto'g'ri matn telefon sifatida qabul qilinmaydi", bad_phone is None)
leads_before = Lead.objects.filter(telegram_user_id=999888777).count()
check("4.2 noto'g'ri telefon bilan Lead yaratilmagan (hali)", leads_before == 0)

# ---------------------------------------------------------------------------
# 4b) Real transkriptda topilgan 2 ta bug: (1) AI o'zi ism/telefon so'rasa ham
# wants_lead=False qolib ariza saqlanmasligi, (2) ism+telefon bitta xabarda
# yuborilganda ikkalasi ham ajratib olinishi.
# ---------------------------------------------------------------------------
check(
    "4.3 answer_implies_contact_collection: ism+telefon so'ralsa True",
    rag.answer_implies_contact_collection(
        "Iltimos, ismingizni va telefon raqamingizni qoldirsangiz, mutaxassisimiz bog'lanadi."
    ) is True,
)
check(
    "4.4 answer_implies_contact_collection: oddiy javobda False",
    rag.answer_implies_contact_collection(
        "Bizning xizmatlarimiz: AI-yordamchi, Telegram avtomatlashtirish."
    ) is False,
)
with patch.object(rag, "retrieve_context", return_value="Saidex xizmatlari haqida ma'lumot."):
    with patch.object(
        rag, "generate_answer",
        return_value=("Iltimos, ismingizni va telefon raqamingizni qoldirsangiz, bog'lanamiz.", 10, 10),
    ):
        answer, in_tok, out_tok, answered_by_ai, wants_lead = rag.answer_question(
            "Man ham qildirmoqchi edim", channel="userbot"
        )
        check(
            "4.5 keyword mos kelmasa-da, AI ism/telefon so'rasa wants_lead=True "
            "(real bug: mijoz ma'lumot qoldirdi deb o'ylagan, lekin saqlanmagan edi)",
            wants_lead is True,
            "got wants_lead=" + str(wants_lead),
        )

name_phone_cases = [
    ("Saidakbar +998910010101", "Saidakbar", "+998910010101"),
    ("Aziz, 901234567", "Aziz", "+998901234567"),
    ("Faqat ism, telefonsiz", None, None),
]
for raw, expect_name, expect_phone in name_phone_cases:
    got_name, got_phone = handlers._try_extract_name_and_phone(raw)
    check(
        "4.6 ism+telefonni bitta xabardan ajratish: " + repr(raw) + " -> "
        + repr((expect_name, expect_phone)),
        got_name == expect_name and got_phone == expect_phone,
        "got " + repr((got_name, got_phone)),
    )

# ---------------------------------------------------------------------------
# 5) Guruh (group chat) kalit so'z aniqlash mantiqi
# ---------------------------------------------------------------------------
group_keywords = ["ai", "savol"]
group_cases = [
    ("/ai narxi qancha?", True, "narxi qancha?"),
    ("ai, xizmatlaringiz haqida gapirib bering", True, "xizmatlaringiz haqida gapirib bering"),
    ("#savol qachon ishlaysiz?", True, "qachon ishlaysiz?"),
    ("savol bor edi", True, "bor edi"),
    ("assalomu alaykum hammaga", False, None),
    ("bugun ob-havo yaxshi ekan", False, None),
]
for text, expect_match, expect_stripped in group_cases:
    matched = handlers._group_message_matches_keyword(text, group_keywords)
    check(
        "5.1 guruh kalit so'z aniqlash: " + repr(text) + " -> " + str(expect_match),
        matched == expect_match,
        "got " + repr(matched),
    )
    if matched:
        stripped = handlers._strip_leading_trigger(text, group_keywords)
        check(
            "5.2 guruh kalit so'zni olib tashlash: " + repr(text) + " -> " + repr(expect_stripped),
            stripped == expect_stripped,
            "got " + repr(stripped),
        )

group, created = TelegramGroup.objects.get_or_create(chat_id=-100123456789, defaults={"title": "Test guruh"})
check("5.3 TelegramGroup avtomatik yaratiladi", created is True)
check("5.4 TelegramGroup standart holatda is_ai_enabled=False", group.is_ai_enabled is False)
check("5.5 TelegramGroup standart reply_mode='keyword'", group.reply_mode == "keyword")
check("5.6 TelegramGroup standart sender_filter='everyone'", group.sender_filter == "everyone")

config.group_trigger_keywords = "ai,savol"
config.save(update_fields=["group_trigger_keywords"])
check(
    "5.7 BotConfig.group_trigger_list prefikslarni tozalaydi",
    config.group_trigger_list == ["ai", "savol"],
    "got " + repr(config.group_trigger_list),
)

# ---------------------------------------------------------------------------
# 6) Uzun javoblarni xatboshi/gap bo'yicha bo'laklarga bo'lish
# (foydalanuvchi so'rovi: uzun javob "xatboshilik-nuqtalik" bo'lib-bo'lib
# yuborilsin, Telegram flood-limitiga tushib qolmaslik uchun)
# ---------------------------------------------------------------------------
check("6.1 bo'sh matn -> bo'sh ro'yxat", handlers._split_into_chunks("") == [])

short_text = "Bu qisqa javob."
check(
    "6.2 qisqa matn (max_len dan kichik) bo'linmaydi",
    handlers._split_into_chunks(short_text) == [short_text],
)

two_para = "Birinchi xatboshi haqida gap." + "\n\n" + "Ikkinchi xatboshi haqida gap."
para_chunks = handlers._split_into_chunks(two_para, max_len=10)
check(
    "6.3 ikkita xatboshi (umumiy uzunlik max_len dan katta) alohida bo'laklarga bo'linadi",
    para_chunks == ["Birinchi xatboshi haqida gap.", "Ikkinchi xatboshi haqida gap."],
    "got " + repr(para_chunks),
)

long_para = "Birinchi gap. Ikkinchi gap. Uchinchi gap. To'rtinchi gap. Beshinchi gap."
sent_chunks = handlers._split_into_chunks(long_para, max_len=20)
check(
    "6.4 uzun xatboshi bir nechta bo'lakka bo'linadi",
    len(sent_chunks) > 1,
    "got " + repr(sent_chunks),
)
check(
    "6.4b bo'laklarga bo'linganda hech qanday so'z yo'qolmaydi",
    " ".join(sent_chunks).replace("  ", " ") == long_para,
    "got " + repr(" ".join(sent_chunks)),
)
check(
    "6.4c hech bir bo'lak asl matndan uzun emas",
    all(len(c) <= len(long_para) for c in sent_chunks),
)

print("")
print("=" * 60)
print("JAMI: " + str(len(PASS)) + " OK, " + str(len(FAIL)) + " FAIL")
if FAIL:
    print("Muvaffaqiyatsiz testlar:")
    for f in FAIL:
        print("  - " + f)
    sys.exit(1)
else:
    print("BARCHA TESTLAR MUVAFFAQIYATLI O'TDI.")
    sys.exit(0)
