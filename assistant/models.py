from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
from pgvector.django import VectorField
from django.conf import settings


class BotConfig(models.Model):
    """Har bir biznes uchun bitta yozuv — AI sozlamalari (biznes admin boshqaradi)."""

    business_name = models.CharField(max_length=255, default="AI Assistant")
    system_prompt = models.TextField(
        default="Siz ushbu biznesning OPERATORISIZ — hech qachon o'zingizni AI, bot, dastur yoki "
                "sun'iy intellekt deb tanishtirmaysiz. Kimligingiz so'ralsa (\"siz kimsiz\", \"bot "
                "bilan gaplashyapmanmi\" va h.k.), o'zingizni shu biznesning xodimi/operatori sifatida "
                "tanishtiring (masalan: \"Men operatorman, sizga yordam berish uchun shu yerdaman!\") — "
                "\"AI\", \"bot\", \"sun'iy intellekt\", \"avtomatik tizim\" kabi so'zlarni hech qachon "
                "ishlatmang.\n\n"
                "Muloqotni doim samimiy, professional va qisqa tarzda, xuddi jonli odam yozayotgandek "
                "olib borasiz.\n\n"
                "Salomlashish: Foydalanuvchi salom bersa yoki suhbatni boshlasa, iliq va qisqa "
                "salomlashib, qanday yordam bera olishingizni so'rang.\n\n"
                "Qoidalar:\n"
                "1. Faqat sizga berilgan ma'lumotlar (hujjatlar) asosida javob bering — "
                "shu ma'lumotlar doirasidan chiqmang va hech narsani o'zingizdan to'qib chiqarmang.\n"
                "2. Agar savolga javob ma'lumotlar orasida topilmasa, buni ochiq ayting va "
                "operatorga murojaat qilishni taklif qiling.\n"
                "3. Javoblaringiz aniq, tushunarli va imkon qadar qisqa bo'lsin — keraksiz "
                "cho'zib yozmang.\n"
                "4. Foydalanuvchi narx, buyurtma, ariza yoki xarid haqida qiziqish bildirsa (masalan "
                "\"sotib olsam bo'ladimi\", \"qanday buyurtma qilaman\" va h.k.) — bu jarayonni HECH "
                "QACHON tushuntirmang va \"tizim\", \"avtomatik\", \"keyingi xabarda so'raydi\" kabi "
                "ichki mexanizmni ochib beruvchi so'zlarni ishlatmang. Faqat qisqa va iliq tasdiqlovchi "
                "javob bering (masalan: \"Albatta, hoziroq bog'lab qo'yamiz!\" yoki \"Ha, albatta! Ism "
                "va telefon raqamingizni yozib qoldiring, tez orada bog'lanamiz.\") — qolganini tizim "
                "o'zi keyingi xabarda bajaradi, buni foydalanuvchiga aytmang.\n"
                "5. Foydalanuvchi qaysi tilda yozsa (o'zbek, rus, ingliz yoki boshqa til), siz ham "
                "AYNAN o'sha tilda javob bering — foydalanuvchining tilini har bir xabarda avtomatik "
                "aniqlab, javobingizni doim shu tilga moslang.\n"
                "6. Agar foydalanuvchi o'zining biznesi uchun AI-yordamchi yoki AI operator sotib "
                "olishga qiziqish bildirsa (masalan \"AI operator olmoqchiman\", \"sizdagidek AI "
                "botim bo'lsa\", \"AI xizmatingiz qancha turadi\" kabi — ya'ni hujjatlardagi "
                "mahsulot emas, aynan shu AI xizmatining o'zini so'rayotgan bo'lsa), hech qachon "
                "bitta qisqa jumla bilan javob berib qo'ymang, balki tajribali savdo maslahatchisi "
                "kabi muloqotga kiring: avval \"Hozircha Telegram yoki Instagramda mijozlarga javob "
                "beradigan operatoringiz bormi? Nechta kishi va oyiga qancha maosh to'laysiz?\" deb "
                "hozirgi holatini so'rang; agar operatori bo'lmasa, AI qanchalik foydali (tezkor "
                "javob, mijozni qo'ldan chiqarmaslik, doimiy ishlashi) ekanini qiziqarli "
                "tushuntiring; agar operatori bor va unga maosh to'lasa, o'sha maoshni AI xizmati "
                "narxi (oyiga taxminan 650 000 so'm) bilan solishtirib, oyiga aniq qancha "
                "tejashini raqamda ko'rsatib ishontiring; AI hech qachon dam olmasligini, kasal "
                "bo'lib qolmasligini va kecha-kunduz (24/7) bir vaqtning o'zida ko'plab mijoz bilan "
                "gaplasha olishini albatta ta'kidlang; javobingizni mijozning aytganiga moslab, "
                "suhbatni davom ettiruvchi savol bilan yakunlang — xuddi jonli, tajribali sotuvchi "
                "bilan gaplashayotgandek; qiziqishi ortsa, ismi va telefon raqamini qoldirishga "
                "chorlang (qolganini tizim avtomatik davom ettiradi, buni ochiq aytmang).\n"
                "7. Umuman, javoblaringiz hech qachon bir xil andoza/shablon bo'lib qolmasin — har "
                "bir xabarga foydalanuvchining aynan aytganiga qarab, tirik odam kabi tabiiy va har "
                "safar turlicha javob bering, imkon qadar suhbatni savol bilan davom ettirib, "
                "mijozni suhbatda faol ushlab turing.",
        help_text="Yagona asosiy prompt — biznes haqida ma'lumot, salomlashish uslubi, javob "
                  "berish tarzi va hokazolarning HAMMASI shu yerda yoziladi. Admin panel > "
                  "Prompt/sozlamalar orqali tahrirlanadi.",
    )
    ai_enabled = models.BooleanField(default=True, help_text="Telegram akkaunt uchun AI yoq/yondir.")
    welcome_message = models.TextField(
        default="Assalomu alaykum! Savolingizni yozing.",
        help_text="Hozircha kod ichida ishlatilmaydi — zaxira maydon (kelajakda kerak bo'lishi mumkin).",
    )
    fallback_message = models.TextField(
        default="Kechirasiz, bu savolga hozircha javob bera olmayman. "
                "Arizangizni qoldiring, operatorimiz siz bilan bog'lanadi.",
        help_text="Texnik xabar — AI o'chirilganda yoki mos hujjat topilmaganda ishlatiladi. "
                  "Kamdan-kam o'zgartiriladi, Django admin orqali tahrirlanadi.",
    )
    lead_trigger_keywords = models.TextField(
        default="narxi,qancha turadi,sotib ol,olaman,buyurtma,bog'lan,qanday buyurtma,qiziqdim,"
                "skidka,chegirma,ariza,ariza qoldirmoqchiman,murojaat,qiziqaman,aloqa",
        help_text="Vergul bilan ajratilgan so'zlar — foydalanuvchi JORIY xabarida shu so'zlardan "
                  "birini yozsa, AI ism/telefon so'rab ariza olishga o'tadi. Faqat joriy xabar "
                  "tekshiriladi (avvalgi xabarlar emas) — shuning uchun bog'liqsiz keyingi "
                  "savollarda ariza oqimi bekorga qayta ishga tushmaydi.",
    )
    group_trigger_keywords = models.TextField(
        default="ai,savol",
        help_text="Guruhlarda AI javob berishi uchun kerakli kalit so'zlar (vergul bilan ajratilgan). "
                  "Masalan 'ai,savol' yozilsa — guruhda '/ai', 'ai', '#savol', '/savol', 'savol' "
                  "kabi barcha shakllar avtomatik tanib olinadi (prefikslar o'zi olib tashlanadi). "
                  "Faqat 'reply_mode=Kalit so'z bilan' rejimidagi guruhlar uchun ishlatiladi.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Bot sozlamasi")
        verbose_name_plural = _("Bot sozlamalari")

    def __str__(self):
        return f"{self.business_name} sozlamalari"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def lead_trigger_list(self) -> list[str]:
        return [w.strip().lower() for w in self.lead_trigger_keywords.split(",") if w.strip()]

    @property
    def group_trigger_list(self) -> list[str]:
        return [
            w.strip().lower().lstrip("/#")
            for w in self.group_trigger_keywords.split(",")
            if w.strip()
        ]


class ProjectSubscription(models.Model):
    """
    Loyihaning obuna holati — FAQAT super admin (siz) boshqaradi.
    Bu BotConfig.ai_enabled'dan mustaqil, umumiy "asosiy kalit" hisoblanadi:
    agar is_active=False bo'lsa, Telegram akkaunt ishlamaydi — mijoz ai_enabled'ni
    o'ziga yoqib qo'yolmaydi.
    """

    is_active = models.BooleanField(default=True, help_text="Loyihani butunlay yoqish/o'chirish (super admin).")
    subscription_start = models.DateField(default=timezone.now)
    subscription_end = models.DateField(default=timezone.now)
    last_alert_sent_at = models.DateField(null=True, blank=True)
    llm_model = models.CharField(
        max_length=50,
        default="gemini-2.5-flash",
        help_text="AI javob berishda ishlatiladigan Gemini modeli (faqat super admin o'zgartiradi).",
    )
    notes = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Obuna")
        verbose_name_plural = _("Obuna")

    def __str__(self):
        return f"Obuna: {self.subscription_end}"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            "subscription_end": timezone.now().date() + timedelta(days=30)
        })
        return obj

    @property
    def days_left(self) -> int:
        return (self.subscription_end - timezone.now().date()).days

    @property
    def status(self) -> str:
        if not self.is_active:
            return "to'xtatilgan"
        days = self.days_left
        if days < 0:
            return "muddati tugagan"
        if days <= 5:
            return "tez orada tugaydi"
        return "faol"

    @property
    def is_service_active(self) -> bool:
        """Bot/userbot ishlashi kerakmi — obuna faol va muddati o'tmagan bo'lsa."""
        return self.is_active and self.days_left >= 0

    def extend(self, days: int):
        base = self.subscription_end if self.subscription_end >= timezone.now().date() else timezone.now().date()
        self.subscription_end = base + timedelta(days=days)
        self.is_active = True
        self.save(update_fields=["subscription_end", "is_active"])


class Document(models.Model):
    """Admin panel orqali yuklangan RAG hujjati (pdf/docx/txt)."""

    STATUS_CHOICES = [
        ("pending", _("Navbatda")),
        ("processing", _("Qayta ishlanmoqda")),
        ("ready", _("Tayyor")),
        ("error", _("Xatolik")),
    ]

    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/%Y/%m/")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True, default="")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Hujjat")
        verbose_name_plural = _("Hujjatlar")

    def __str__(self):
        return self.title

    @property
    def chunk_count(self):
        return self.chunks.count()


class DocumentChunk(models.Model):
    """Hujjatning bir bo'lagi + uning embedding vektori (pgvector)."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    content = models.TextField()
    embedding = VectorField(dimensions=settings.EMBEDDING_DIMENSIONS, null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document", "order"]
        verbose_name = _("Hujjat qismi")
        verbose_name_plural = _("Hujjat qismlari")

    def __str__(self):
        return f"{self.document.title} — bo'lak {self.order}"


class Lead(models.Model):
    """Foydalanuvchi qoldirgan ariza / murojaat (CRM voronkasi)."""

    CHANNEL_CHOICES = [
        ("bot", _("Telegram bot")),
        ("userbot", _("Telegram akkaunt")),
        ("group", _("Telegram guruh")),
        ("website", _("Veb-sayt")),
    ]

    STATUS_CHOICES = [
        ("new", _("Yangi")),
        ("contacted", _("Bog'lanildi")),
        ("interested", _("Qiziqmoqda")),
        ("customer", _("Mijoz bo'ldi")),
        ("not_interested", _("Qiziqmas")),
        ("no_purchase", _("Olmadi")),
        ("will_buy_later", _("Keyinroq oladi")),
    ]

    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default="bot")
    telegram_user_id = models.BigIntegerField()
    telegram_username = models.CharField(max_length=255, blank=True, default="")
    full_name = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    admin_note = models.TextField(blank=True, default="", help_text="Admin mijoz bilan gaplashgandan keyingi izohi.")
    is_archived = models.BooleanField(
        default=False,
        help_text="Arxivlangan arizalar asosiy 'Arizalar' ro'yxatida ko'rinmaydi, alohida 'Arxiv' sahifasida turadi.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Ariza")
        verbose_name_plural = _("Arizalar")

    def __str__(self):
        return f"{self.full_name or self.telegram_user_id} — {self.created_at:%Y-%m-%d}"


class PendingLead(models.Model):
    """
    Userbot (Telethon) uchun bosqichma-bosqich ariza yig'ish holati —
    bazada saqlanadigan oddiy holat mashinasi.
    """

    STEP_CHOICES = [("name", _("Ism kutilmoqda")), ("phone", _("Telefon kutilmoqda"))]

    telegram_user_id = models.BigIntegerField(unique=True)
    telegram_username = models.CharField(max_length=255, blank=True, default="")
    original_message = models.TextField()
    step = models.CharField(max_length=10, choices=STEP_CHOICES, default="name")
    full_name = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Kutilayotgan ariza")
        verbose_name_plural = _("Kutilayotgan arizalar")


class ConversationLog(models.Model):
    """Har bir savol-javobning statistikasi uchun yozuvi."""

    CHANNEL_CHOICES = [
        ("bot", _("Telegram bot")),
        ("userbot", _("Telegram akkaunt")),
        ("group", _("Telegram guruh")),
        ("website", _("Veb-sayt")),
    ]

    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default="bot")
    telegram_user_id = models.BigIntegerField()
    chat_id = models.BigIntegerField(
        null=True, blank=True,
        help_text="Guruh suhbatlari uchun — qaysi guruhda yozilgani (bir foydalanuvchi bir "
                  "nechta guruhda bo'lsa, tarixni guruhlar aralashtirib yubormasligi uchun).",
    )
    question = models.TextField()
    answer = models.TextField()
    answered_by_ai = models.BooleanField(default=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Suhbat yozuvi")
        verbose_name_plural = _("Suhbat yozuvlari")

    def __str__(self):
        return f"{self.telegram_user_id}: {self.question[:40]}"


class TelegramAccountConnection(models.Model):
    """
    Admin panel orqali ulanadigan Telegram AKKAUNT (Telethon userbot) holati.
    Bir vaqtning o'zida faqat bitta akkaunt ulanishi mumkin (singleton).
    """

    STATUS_CHOICES = [
        ("disconnected", _("Ulanmagan")),
        ("pending_code", _("SMS kod kutilmoqda")),
        ("pending_password", _("2FA parol kutilmoqda")),
        ("connected", _("Ulangan")),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="disconnected")
    phone_number = models.CharField(max_length=32, blank=True, default="")
    session_string = models.TextField(blank=True, default="")
    phone_code_hash = models.CharField(max_length=255, blank=True, default="")
    connected_username = models.CharField(max_length=255, blank=True, default="")
    connected_first_name = models.CharField(max_length=255, blank=True, default="")
    connected_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Telegram akkaunt ulanishi")
        verbose_name_plural = _("Telegram akkaunt ulanishi")

    def __str__(self):
        return f"Telegram akkaunt: {self.get_status_display()}"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def is_connected(self) -> bool:
        return self.status == "connected" and bool(self.session_string)


class TelegramGroup(models.Model):
    """
    Userbot (Telethon akkaunt) a'zo bo'lgan Telegram guruh — birinchi xabar
    kelganda avtomatik ro'yxatga olinadi (get_or_create), keyin admin panel
    orqali shu guruhda AI javob berish-bermasligi va qanday javob berish
    tartibi sozlanadi.
    """

    REPLY_MODE_CHOICES = [
        ("keyword", _("Kalit so'z bilan (masalan: /ai, savol)")),
        ("all", _("Kalitsiz — har bir xabarga javob")),
    ]
    SENDER_FILTER_CHOICES = [
        ("everyone", _("Guruhdagi barchaga")),
        ("users", _("Faqat oddiy foydalanuvchilarga (adminlarga emas)")),
        ("admins", _("Faqat guruh adminlariga")),
    ]

    chat_id = models.BigIntegerField(unique=True)
    title = models.CharField(max_length=255, blank=True, default="")
    is_ai_enabled = models.BooleanField(
        default=False,
        help_text="Ushbu guruhda AI javob berishi uchun bu yoqilishi kerak (standart holatda o'chirilgan).",
    )
    reply_mode = models.CharField(max_length=10, choices=REPLY_MODE_CHOICES, default="keyword")
    sender_filter = models.CharField(max_length=10, choices=SENDER_FILTER_CHOICES, default="everyone")
    added_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]
        verbose_name = _("Telegram guruh")
        verbose_name_plural = _("Telegram guruhlar")

    def __str__(self):
        return self.title or str(self.chat_id)
