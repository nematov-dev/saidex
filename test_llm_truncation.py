# -*- coding: utf-8 -*-
"""
llm.generate_answer'dagi MAX_TOKENS (javob gap o'rtasida kesilib qolishi)
holatini qayta urinish orqali tuzatish mantiqining sandbox testi.

Haqiqiy Vertex AI'ga ulanmasdan, GenerativeModel butunlay mock qilinadi —
faqat generate_answer'ning finish_reason tekshiruvi va qayta urinish
mantig'i sinaladi.

Ishga tushirish: python3 test_llm_truncation.py
"""
import os
import sys
from unittest.mock import patch, MagicMock

PROJECT_DIR = "/sessions/quirky-beautiful-cray/mnt/agent_shablon"
sys.path.insert(0, PROJECT_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from vertexai.generative_models import FinishReason  # noqa: E402
from assistant.services import llm  # noqa: E402

PASS = []
FAIL = []


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print("OK   " + name)
    else:
        FAIL.append(name)
        print("FAIL " + name + "  " + detail)


class FakeUsage:
    def __init__(self, in_tok, out_tok):
        self.prompt_token_count = in_tok
        self.candidates_token_count = out_tok


class FakeCandidate:
    def __init__(self, finish_reason):
        self.finish_reason = finish_reason


class FakeResponse:
    def __init__(self, text, finish_reason, in_tok=10, out_tok=10):
        self.text = text
        self.candidates = [FakeCandidate(finish_reason)]
        self.usage_metadata = FakeUsage(in_tok, out_tok)


# 1) Oddiy holat (finish_reason=STOP) - qayta urinish bo'lmasligi kerak
with patch.object(llm, "_ensure_init"):
    fake_model = MagicMock()
    fake_model.generate_content.return_value = FakeResponse("To'liq javob.", FinishReason.STOP)
    with patch.object(llm, "GenerativeModel", return_value=fake_model):
        answer, in_tok, out_tok = llm.generate_answer("prompt", "context", "savol")
        check(
            "1.1 STOP holatida faqat bitta chaqiruv bo'ladi",
            fake_model.generate_content.call_count == 1,
            "got call_count=" + str(fake_model.generate_content.call_count),
        )
        check("1.2 javob to'g'ri qaytadi", answer == "To'liq javob.")

# 2) MAX_TOKENS holati - kattaroq byudjet bilan avtomatik qayta urinishi va
# to'liqroq (qayta urinishdagi) javobni ishlatishi kerak (real bug: "...ismi
# ko'rsatilmagan. Biroq" kabi tugallanmagan javoblar kuzatilgan edi)
with patch.object(llm, "_ensure_init"):
    fake_model = MagicMock()
    truncated = FakeResponse("Bu javob gap o'rtasida kesilib", FinishReason.MAX_TOKENS)
    full = FakeResponse("Bu to'liq va tugallangan javob.", FinishReason.STOP)
    fake_model.generate_content.side_effect = [truncated, full]
    with patch.object(llm, "GenerativeModel", return_value=fake_model):
        answer, in_tok, out_tok = llm.generate_answer("prompt", "context", "savol")
        check(
            "2.1 MAX_TOKENS holatida ikkinchi marta (kattaroq byudjet bilan) qayta urinadi",
            fake_model.generate_content.call_count == 2,
            "got call_count=" + str(fake_model.generate_content.call_count),
        )
        check(
            "2.2 qayta urinishdan keyingi to'liq javob qaytariladi (kesilgani emas)",
            answer == "Bu to'liq va tugallangan javob.",
            "got answer=" + repr(answer),
        )

# 3) MAX_TOKENS holati, lekin qayta urinish ham xatolik bersa (masalan 429) -
# hech bo'lmasa birinchi (kesilgan) javobni qaytarishi kerak, exception
# tashlamasligi kerak (silent-fail dizayniga mos)
with patch.object(llm, "_ensure_init"):
    fake_model = MagicMock()
    from google.api_core.exceptions import ResourceExhausted

    truncated = FakeResponse("Qisman javob", FinishReason.MAX_TOKENS)
    fake_model.generate_content.side_effect = [truncated, ResourceExhausted("kvota tugadi")]
    with patch.object(llm, "GenerativeModel", return_value=fake_model):
        try:
            answer, in_tok, out_tok = llm.generate_answer("prompt", "context", "savol")
            check(
                "3.1 qayta urinish xatolik bersa ham, birinchi (qisman) javob qaytariladi",
                answer == "Qisman javob",
                "got answer=" + repr(answer),
            )
        except Exception as exc:  # noqa: BLE001
            check("3.1 qayta urinish xatolik bersa ham, birinchi (qisman) javob qaytariladi", False, repr(exc))

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
