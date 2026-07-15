"""
Telegram AKKAUNT (Telethon) sifatida ishga tushirish nuqtasi.
Ishga tushirish: python userbot/run.py

Akkaunt sessiyasi endi .env emas -- admin panel > Super Admin > "Telegram akkaunt"
bo'limida ulanadi va bazada (TelegramAccountConnection) saqlanadi.
"""
import asyncio
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402
django.setup()

from asgiref.sync import sync_to_async  # noqa: E402
from django.conf import settings  # noqa: E402
from telethon import TelegramClient
from telethon.sessions import StringSession

from userbot.handlers import register_handlers  # noqa: E402


@sync_to_async
def get_connection():
    from assistant.models import TelegramAccountConnection
    return TelegramAccountConnection.get_solo()


async def main():
    if not (settings.TELEGRAM_API_ID and settings.TELEGRAM_API_HASH):
        raise RuntimeError(
            "TELEGRAM_API_ID / TELEGRAM_API_HASH .env faylida to'liq emas. "
            "https://my.telegram.org/apps dan oling."
        )

    connection = await get_connection()
    if not connection.is_connected:
        raise RuntimeError(
            "Hech qanday Telegram akkaunt ulanmagan. Admin panelga kiring, "
            "Super Admin bo'limidagi 'Telegram akkaunt' orqali ulang, "
            "so'ng bu skriptni qayta ishga tushiring."
        )

    client = TelegramClient(
        StringSession(connection.session_string),
        int(settings.TELEGRAM_API_ID),
        settings.TELEGRAM_API_HASH,
    )
    register_handlers(client)

    print(f"[{settings.BUSINESS_NAME}] Telegram akkaunt (userbot) ishga tushdi: {connection.phone_number}")
    await client.start()
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
