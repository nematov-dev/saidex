"""
Ochiq (public, autentifikatsiyasiz) landing page'dagi ovozli/matnli AI-demo
uchun IP-asoslangan oddiy "fixed window" rate-limit. Bu demo haqiqiy pullik
Vertex AI so'rovlarini chaqiradi — himoyasiz qoldirilsa, bitta tashrif
buyuruvchi tabni ochiq qoldirib ko'p marta yuborishi yoki maqsadli suiiste'mol
qilishi mumkin.
"""
import zlib

from django.core.cache import cache

# Bitta IP uchun DEMO_WINDOW_SECONDS oralig'ida DEMO_LIMIT martadan ko'p
# so'rovga ruxsat berilmaydi (ovozli va matnli demo birgalikda hisoblanadi).
DEMO_LIMIT = 20
DEMO_WINDOW_SECONDS = 600  # 10 daqiqa


def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def get_pseudo_user_id(ip: str) -> int:
    """IP manzildan statistikada foydalanish uchun barqaror (lekin shaxsni
    aniqlamaydigan) sonli identifikator hosil qiladi — real Telegram ID
    bo'lmagani uchun ConversationLog.telegram_user_id maydoniga shu qo'yiladi."""
    return zlib.crc32(ip.encode("utf-8"))


def is_rate_limited(request, key_prefix: str = "demo", limit: int = DEMO_LIMIT,
                     window_seconds: int = DEMO_WINDOW_SECONDS) -> bool:
    ip = get_client_ip(request)
    cache_key = f"ratelimit:{key_prefix}:{ip}"
    try:
        count = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window_seconds)
        count = 1
    return count > limit
