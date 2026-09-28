"""Telefon raqamlarini bir xil ko'rinishga keltirish (ro'yxatdan o'tish, Telegram ulash, ariza yig'ish)."""
import re

_DIGITS_RE = re.compile(r"[^\d+]")


def normalize_phone(text: str) -> str | None:
    """
    Matndan telefon raqamini ajratib, +998XXXXXXXXX ko'rinishida qaytaradi —
    foydalanuvchi qanday formatda yozishidan qat'iy nazar (bo'shliq, tire, qavs,
    +998 bilan yoki bilarsiz). Mos raqam topilmasa None qaytaradi.
    """
    digits = _DIGITS_RE.sub("", text or "")
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
