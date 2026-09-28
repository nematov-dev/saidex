"""
Telegram AKKAUNT (Telethon) sifatida ishga tushirish nuqtasi.
Ishga tushirish: python userbot/run.py

Multi-user rejim: har bir ish maydoni (foydalanuvchi) o'z panelidagi "Telegram
akkaunt" bo'limida o'z akkauntini ulaydi (TelegramAccountConnection, bazada).
Bu jarayon BITTA bo'lib, barcha ulangan akkauntlarni bir vaqtda ishlatadi va
har SYNC_INTERVAL soniyada bazani tekshirib turadi:
  - yangi ulangan akkaunt -> avtomatik ishga tushiriladi (qayta ishga tushirishsiz);
  - uzilgan yoki sessiyasi almashgan akkaunt -> to'xtatiladi.
"""
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402
django.setup()

from asgiref.sync import sync_to_async  # noqa: E402
from django.conf import settings  # noqa: E402
from telethon import TelegramClient  # noqa: E402
from telethon.sessions import StringSession  # noqa: E402

from assistant.services.telegram_client import DEVICE_KWARGS  # noqa: E402
from userbot.handlers import register_handlers  # noqa: E402

logger = logging.getLogger("userbot")

SYNC_INTERVAL = 20  # soniya
# Xato bilan to'xtagan akkaunt (masalan tarmoq uzilishi) shuncha soniyadan keyin qayta ishga tushiriladi.
RETRY_AFTER = 300


@sync_to_async
def get_connected_sessions() -> dict[int, tuple]:
    """{workspace_id: (session_string, phone_number, api_id, api_hash)} — hozir ulangan barcha akkauntlar.
    Har bir akkaunt o'zining API kaliti bilan ishlaydi (kaliti yo'qlari o'tkazib yuboriladi)."""
    from assistant.models import TelegramAccountConnection
    from assistant.services.telegram_client import api_credentials

    sessions = {}
    connections = (
        TelegramAccountConnection.objects.filter(status="connected").exclude(session_string="")
        .select_related("workspace")
    )
    for conn in connections:
        credentials = api_credentials(conn)
        if credentials is None:
            logger.warning("Ish maydoni #%s: API kaliti yo'q — akkaunt ishga tushirilmadi.", conn.workspace_id)
            continue
        sessions[conn.workspace_id] = (conn.session_string, conn.phone_number, *credentials)
    return sessions


@sync_to_async
def remember_telegram_user_id(workspace_id: int, telegram_user_id: int):
    """Avval ulangan (ID'si saqlanmagan) akkauntlar uchun Telegram ID'ni yozib qo'yadi —
    bitta Telegram akkauntni ikkinchi hisobga ulashning oldini olish shunga tayanadi."""
    from assistant.models import TelegramAccountConnection
    TelegramAccountConnection.objects.filter(workspace_id=workspace_id, connected_user_id__isnull=True).update(
        connected_user_id=telegram_user_id,
    )


class AccountRunner:
    """Bitta ish maydonining Telegram akkauntini alohida asyncio vazifasi sifatida ishlatadi."""

    def __init__(self, workspace_id: int, session_string: str, phone: str, api_id: int, api_hash: str):
        self.workspace_id = workspace_id
        self.session_string = session_string
        self.phone = phone
        self.client = TelegramClient(StringSession(session_string), api_id, api_hash, **DEVICE_KWARGS)
        register_handlers(self.client, workspace_id)
        self.stopped_at = None
        self.task = asyncio.create_task(self._run())

    async def _run(self):
        try:
            await self.client.connect()
            if not await self.client.is_user_authorized():
                logger.warning("Ish maydoni #%s: sessiya yaroqsiz (%s) — o'tkazib yuborildi.", self.workspace_id, self.phone)
                return
            me = await self.client.get_me()
            await remember_telegram_user_id(self.workspace_id, me.id)
            print(f"[workspace #{self.workspace_id}] Telegram akkaunt ishga tushdi: {self.phone}", flush=True)
            await self.client.run_until_disconnected()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - bitta akkauntdagi xato boshqalarini to'xtatmasligi kerak
            logger.exception("Ish maydoni #%s: Telegram akkaunt xatolik bilan to'xtadi.", self.workspace_id)
        finally:
            self.stopped_at = time.monotonic()

    @property
    def should_retry(self) -> bool:
        return self.task.done() and self.stopped_at is not None and time.monotonic() - self.stopped_at > RETRY_AFTER

    async def stop(self):
        try:
            await self.client.disconnect()
        except Exception:  # noqa: BLE001
            pass
        self.task.cancel()
        try:
            await self.task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        print(f"[workspace #{self.workspace_id}] Telegram akkaunt to'xtatildi: {self.phone}", flush=True)


async def main():
    logging.basicConfig(level=logging.INFO)

    runners: dict[int, AccountRunner] = {}
    print(f"[{settings.BUSINESS_NAME}] Userbot menejeri ishga tushdi (har {SYNC_INTERVAL} soniyada tekshiradi).", flush=True)

    while True:
        try:
            sessions = await get_connected_sessions()
        except Exception:  # noqa: BLE001 - baza vaqtincha ishlamasa, keyingi tekshiruvda qayta urinamiz
            logger.exception("Ulangan akkauntlarni o'qib bo'lmadi.")
            sessions = None

        if sessions is not None:
            for workspace_id, runner in list(runners.items()):
                current = sessions.get(workspace_id)
                if current is None or current[0] != runner.session_string or runner.should_retry:
                    await runner.stop()
                    del runners[workspace_id]

            for workspace_id, (session_string, phone, api_id, api_hash) in sessions.items():
                if workspace_id not in runners:
                    runners[workspace_id] = AccountRunner(workspace_id, session_string, phone, api_id, api_hash)

        await asyncio.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
