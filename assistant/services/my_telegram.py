"""
my.telegram.org orqali foydalanuvchining O'Z Telegram API kalitini (api_id / api_hash) olish.

Nega kerak: barcha mijozlar akkauntini bitta umumiy API kalit bilan ulash Telegram'ga
ommaviy akkaunt boshqaruvidek ko'rinadi va u kod yuborishni to'xtatadi. Shuning uchun har
bir mijoz o'z kalitidan foydalanadi — uni qo'lda my.telegram.org'dan olish o'rniga, sayt
shu jarayonni mijoz nomidan bajaradi:

  1. send_password(phone)  -> Telegram ilovasiga tasdiqlash kodi keladi, random_hash qaytadi;
  2. fetch_api_credentials(phone, random_hash, code) -> my.telegram.org'ga kiradi, ilova
     bo'lmasa yaratadi va (api_id, api_hash) ni qaytaradi.
"""
import logging
import random
import re
import string

import requests
from django.conf import settings
from django.utils.translation import gettext as _

BASE_URL = "https://my.telegram.org"
TIMEOUT = 25
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/auth",
    "X-Requested-With": "XMLHttpRequest",
}

_API_ID_RE = re.compile(r"App api_id:.*?<strong>\s*(\d+)\s*</strong>", re.S)
_API_HASH_RE = re.compile(r"App api_hash:.*?>\s*([0-9a-f]{32})\s*<", re.S)
_CREATE_HASH_RE = re.compile(r'name="hash"\s+value="([^"]+)"')

logger = logging.getLogger(__name__)

# Ilova yaratishga urinishlar: my.telegram.org birinchisini "ERROR" bilan rad etsa, boshqa
# nom/platforma bilan yana urinib ko'riladi.
CREATE_ATTEMPTS = [
    ("Saidex AI Assistant", "desktop"),
    ("Saidex Helper App", "other"),
]


def _proxies() -> dict | None:
    """.env'dagi MY_TELEGRAM_PROXY_URL — server IP'si rad etilmasligi uchun (bo'sh bo'lsa proksisiz).
    socks5h:// — DNS ham proksi orqali (socks5:// shunga aylantiriladi)."""
    url = settings.MY_TELEGRAM_PROXY_URL.strip()
    if not url:
        return None
    if url.startswith("socks5://"):
        url = "socks5h://" + url[len("socks5://"):]
    return {"http": url, "https": url}


class MyTelegramError(Exception):
    """Foydalanuvchiga ko'rsatiladigan (tarjima qilingan) xato matni bilan."""


def _friendly_error(text: str) -> str:
    text = (text or "").strip()
    lowered = text.lower()
    if "too many tries" in lowered:
        return _("my.telegram.org: urinishlar juda ko'p. Birozdan keyin (bir necha soat) qayta urinib ko'ring.")
    if "invalid confirmation code" in lowered or "invalid code" in lowered:
        return _("Kod noto'g'ri. Telegram ilovasiga kelgan kodni aynan o'zidek kiriting.")
    if "phone" in lowered and "invalid" in lowered:
        return _("Telefon raqami noto'g'ri. Xalqaro formatda kiriting, masalan: +998901234567")
    return _("my.telegram.org xatoligi: %(text)s") % {"text": text[:200] or _("javob bo'sh")}


def send_password(phone: str) -> str:
    """Telegram ilovasiga my.telegram.org tasdiqlash kodini yuboradi, random_hash'ni qaytaradi."""
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/send_password", data={"phone": phone}, headers=HEADERS, timeout=TIMEOUT,
            proxies=_proxies(),
        )
    except requests.RequestException as exc:
        raise MyTelegramError(_("my.telegram.org'ga ulanib bo'lmadi: %(error)s") % {"error": exc}) from exc
    try:
        data = resp.json()
    except ValueError:
        raise MyTelegramError(_friendly_error(resp.text)) from None
    random_hash = data.get("random_hash") if isinstance(data, dict) else None
    if not random_hash:
        raise MyTelegramError(_friendly_error(resp.text))
    return random_hash


def _parse_credentials(html: str):
    id_match, hash_match = _API_ID_RE.search(html), _API_HASH_RE.search(html)
    if id_match and hash_match:
        return int(id_match.group(1)), hash_match.group(1)
    return None


def _random_shortname() -> str:
    return "saidex" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def _create_app(session: requests.Session, form_hash: str):
    """Ilova yaratadi (brauzerdagidek /apps sahifasidan). "ERROR" javobidan keyin ham ilova
    ba'zan baribir yaratilgan bo'ladi — shuning uchun har urinishdan keyin sahifa qayta o'qiladi."""
    last_response = ""
    for title, platform in CREATE_ATTEMPTS:
        create = session.post(f"{BASE_URL}/apps/create", data={
            "hash": form_hash,
            "app_title": title,
            "app_shortname": _random_shortname(),
            "app_url": "",
            "app_platform": platform,
            "app_desc": "",
        }, headers={"Referer": f"{BASE_URL}/apps"}, timeout=TIMEOUT)
        last_response = create.text.strip()
        html = session.get(f"{BASE_URL}/apps", timeout=TIMEOUT).text
        credentials = _parse_credentials(html)
        if credentials:
            return credentials
        logger.warning("my.telegram.org ilova yaratish javobi (%s/%s): %r", title, platform, last_response[:300])
        match = _CREATE_HASH_RE.search(html)
        if match:
            form_hash = match.group(1)

    raise MyTelegramError(_(
        "my.telegram.org ilova yaratishni rad etdi. Bu odatda server (hosting) IP manzili sababli bo'ladi. "
        "Kalitni qo'lda oling: telefoningizda my.telegram.org saytini oching, \"API development tools\" "
        "bo'limida ilova yarating va App api_id hamda App api_hash qiymatlarini pastdagi "
        "\"Kalitni qo'lda kiritish\" bo'limiga kiriting."
    ))


def fetch_api_credentials(phone: str, random_hash: str, code: str) -> tuple[int, str]:
    """my.telegram.org'ga kiradi va (api_id, api_hash) ni qaytaradi — ilova bo'lmasa yaratadi."""
    session = requests.Session()
    session.headers.update(HEADERS)
    proxies = _proxies()
    if proxies:
        session.proxies.update(proxies)
    try:
        resp = session.post(
            f"{BASE_URL}/auth/login",
            data={"phone": phone, "random_hash": random_hash, "password": code.strip()},
            timeout=TIMEOUT,
        )
        if resp.text.strip() != "true":
            raise MyTelegramError(_friendly_error(resp.text))

        html = session.get(f"{BASE_URL}/apps", timeout=TIMEOUT).text
        credentials = _parse_credentials(html)
        if credentials is None:
            match = _CREATE_HASH_RE.search(html)
            if not match:
                raise MyTelegramError(_("my.telegram.org'da ilovalar sahifasini o'qib bo'lmadi. Kalitni qo'lda kiriting."))
            credentials = _create_app(session, match.group(1))
        return credentials
    except requests.RequestException as exc:
        raise MyTelegramError(_("my.telegram.org'ga ulanib bo'lmadi: %(error)s") % {"error": exc}) from exc
    finally:
        try:
            session.get(f"{BASE_URL}/auth/logout", timeout=10)
        except requests.RequestException:
            pass
        session.close()
