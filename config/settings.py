"""
Django sozlamalari — client_template
Bu fayl har bir mijoz (biznes) uchun .env fayli orqali to'liq moslashadi.
Yangi mijoz yaratganda kodni o'zgartirish shart emas — faqat .env yangilanadi.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# MUHIM: override=False (standart) — agar POSTGRES_HOST/PORT yoki boshqa
# o'zgaruvchilar allaqachon OS environment'da o'rnatilgan bo'lsa (masalan
# docker-compose.yml'dagi "environment:" bloki orqali web/userbot konteynerlari
# ichida "postgres"/5432 qilib beriladi), .env fayli ularni QAYTA yozib
# YUBORMAYDI. .env faqat hali o'rnatilmagan qiymatlarni to'ldiradi. Bu ayniqsa
# muhim, chunki .env fayli konteynerlarga bind-mount qilingan va localhost:5433
# (host mashinadan tashqarida ishlaydigan qiymatlar) saqlaydi.
load_dotenv(BASE_DIR / ".env")

# ---- Umumiy ----
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-CHANGE-ME")
DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# MUHIM: sayt Nginx (va undan oldin Cloudflare) orqali reverse-proxy qilib
# ishlaydi — Django'ning o'zi to'g'ridan-to'g'ri HTTPS qabul qilmaydi, faqat
# Nginx'dan HTTP orqali so'rov oladi. Shu sabab ikkita narsa kerak:
# 1) SECURE_PROXY_SSL_HEADER — Nginx yuborgan "X-Forwarded-Proto: https"
#    headerini ko'rib, Django so'rovni HTTPS deb to'g'ri aniqlashi uchun
#    (aks holda CSRF cookie va boshqa "secure" tekshiruvlar chalkashadi).
# 2) CSRF_TRUSTED_ORIGINS — Django 4+ da POST so'rovlar (masalan login
#    formasi) uchun brauzer yuborgan "Origin: https://domen.uz" headeri
#    ALLOWED_HOSTS'da emas, aynan shu ro'yxatda bo'lishi shart, aks holda
#    "CSRF tekshiruvi amalga oshmadi" (403) xatosi chiqadi.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = [
    f"https://{host.strip()}"
    for host in ALLOWED_HOSTS
    if host.strip() and host.strip() not in ("localhost", "127.0.0.1")
]

BUSINESS_NAME = os.getenv("BUSINESS_NAME", "AI Assistant")
BUSINESS_SLUG = os.getenv("BUSINESS_SLUG", "business")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "assistant",
    "landing",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "assistant" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "assistant.context_processors.business_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---- Ma'lumotlar bazasi: PostgreSQL + pgvector ----
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "afu_ai_assistant"),
        "USER": os.getenv("POSTGRES_USER", "afu_admin"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "change_me"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

# ---- Admin panel tili (uz/ru/en) — foydalanuvchi panel ichidan tanlaydi ----
LANGUAGES = [
    ("uz", "O'zbekcha"),
    ("ru", "Русский"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Redis (rate-limit uchun — ochiq landing page'dagi ovozli AI-demo
# anonim so'rovlarini cheklash uchun ishlatiladi, docker-compose'dagi
# "redis" konteyneriga ulanadi) ----
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
    }
}

LOGIN_URL = "assistant:login"
LOGIN_REDIRECT_URL = "assistant:dashboard"
LOGOUT_REDIRECT_URL = "assistant:login"

# ---- Telegram (obuna ogohlantirishi uchun, check_subscription_alert.py ishlatadi) ----
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ---- Vertex AI (embedding) ----
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
VERTEX_EMBEDDING_MODEL = os.getenv("VERTEX_EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIMENSIONS = 768  # gemini-embedding-001 uchun tavsiya etilgan o'lcham

# ---- LLM javob generatsiyasi: Vertex AI Gemini ----
# Standart model — super admin panel orqali ProjectSubscription.llm_model bilan
# har bir loyiha uchun o'zgartirilishi mumkin.
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gemini-2.5-flash")
AVAILABLE_LLM_MODELS = [
    ("gemini-2.5-flash-lite", "Gemini 2.5 Flash-Lite (eng arzon, tez)"),
    ("gemini-2.5-flash", "Gemini 2.5 Flash (tavsiya etiladi)"),
    ("gemini-2.5-pro", "Gemini 2.5 Pro (eng aniq, qimmatroq)"),
]

# ---- Super admin bilan ichki aloqa uchun ----
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")

RAG_CHUNK_SIZE = 800          # belgi (character)
RAG_CHUNK_OVERLAP = 100
RAG_TOP_K = 4                 # javob berishda nechta parcha olinadi

# ---- Telethon (Telegram AKKAUNT sifatida ulanish) ----
# Sessiya endi .env emas — admin panel > Super Admin > "Telegram akkaunt" orqali
# ulanadi va TelegramAccountConnection modelida (bazada) saqlanadi.
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")

# ---- Obuna tugashi haqida ogohlantirish yuboriladigan Telegram ID (super admin) ----
SUPERADMIN_TELEGRAM_ID = os.getenv("SUPERADMIN_TELEGRAM_ID", "")
