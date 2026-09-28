"""
Telegram akkaunt (Telethon) mijozini yaratish — panel (ulash) va userbot (ishlatish) uchun umumiy.

Har bir ulanish o'zining API kalitidan (my.telegram.org'dan olingan api_id / api_hash)
foydalanadi. Faqat asosiy (Saidex) ish maydoni o'z kaliti bo'lmasa .env'dagi umumiy
kalitga tayanadi.
"""
from django.conf import settings
from telethon import TelegramClient
from telethon.sessions import StringSession

# Telegram'dagi "Qurilmalar" ro'yxatida shunday ko'rinadi (standart "PC 64bit / Telethon" o'rniga).
DEVICE_KWARGS = {
    "device_model": "Saidex AI Assistant",
    "system_version": "1.0",
    "app_version": "1.0",
    "lang_code": "uz",
    "system_lang_code": "uz",
}


def api_credentials(connection):
    """(api_id, api_hash) yoki None — ulanishning o'z kaliti, bo'lmasa (faqat asosiy ish maydoni uchun) .env."""
    if connection.api_id and connection.api_hash:
        return connection.api_id, connection.api_hash
    if connection.workspace.is_main and settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH:
        return int(settings.TELEGRAM_API_ID), settings.TELEGRAM_API_HASH
    return None


def make_client(connection, session_string: str = "") -> TelegramClient:
    api_id, api_hash = api_credentials(connection)
    return TelegramClient(StringSession(session_string), api_id, api_hash, **DEVICE_KWARGS)
