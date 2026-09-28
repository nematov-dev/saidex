from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class LandingSettings(models.Model):
    """Ochiq (public) bosh sahifaning yagona sozlamasi — logo, aloqa
    ma'lumotlari va ijtimoiy tarmoq havolalari. BotConfig.get_solo()
    andozasi bo'yicha singleton."""

    logo = models.ImageField(upload_to="landing/", null=True, blank=True)
    admin_phone = models.CharField(max_length=32, blank=True, default="")
    admin_telegram_username = models.CharField(max_length=255, blank=True, default="")
    instagram_url = models.URLField(blank=True, default="")
    telegram_url = models.URLField(blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    facebook_url = models.URLField(blank=True, default="")
    youtube_url = models.URLField(blank=True, default="")
    x_url = models.URLField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Sayt sozlamalari")
        verbose_name_plural = _("Sayt sozlamalari")

    def __str__(self):
        return "Landing sozlamalari"

    @classmethod
    def get_solo(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj


class Tariff(models.Model):
    PERIOD_CHOICES = [
        ("monthly", _("Oylik")),
        ("yearly", _("Yillik")),
    ]
    PLAN_CODE_CHOICES = [
        ("", _("— (faqat saytda ko'rinadi)")),
        ("free", _("Bepul obuna")),
        ("pro", _("Pro obuna")),
    ]

    name = models.CharField(max_length=100)
    plan_code = models.CharField(
        max_length=10, choices=PLAN_CODE_CHOICES, blank=True, default="",
        help_text="Qaysi obunaga tegishli: panelda ko'rsatiladigan narx va bepul limit shu yerdan olinadi.",
    )
    question_limit = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Faqat Bepul obuna uchun: yangi ro'yxatdan o'tganlarga beriladigan savol-javoblar soni.",
    )
    price = models.CharField(max_length=100, help_text="Masalan: $59")
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default="monthly")
    features = models.TextField(help_text="Har bir xususiyat alohida qatorda yoziladi.")
    is_featured = models.BooleanField(default=False, help_text="Eng ommabop deb belgilash.")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("Tarif")
        verbose_name_plural = _("Tariflar")

    def __str__(self):
        return f"{self.name} ({self.get_period_display()})"

    @property
    def is_free(self) -> bool:
        """Bepul obuna tarifi (yoki obunaga bog'lanmagan, narxida noldan boshqa raqam yo'q tarif)."""
        if self.plan_code:
            return self.plan_code == "free"
        return not any(ch in "123456789" for ch in self.price)

    @classmethod
    def for_plan(cls, plan_code: str):
        return cls.objects.filter(plan_code=plan_code).order_by("order", "id").first()

    @classmethod
    def pro_price(cls) -> str:
        """Panel va saytda ko'rsatiladigan Pro narxi — "Pro obuna" tarifidan, bo'lmasa .env'dan."""
        tariff = cls.for_plan("pro")
        return tariff.price if tariff else settings.PRO_PLAN_PRICE

    @classmethod
    def free_question_limit(cls) -> int:
        """Yangi ro'yxatdan o'tganlarga beriladigan bepul savollar soni — "Bepul obuna" tarifidan, bo'lmasa .env'dan."""
        tariff = cls.for_plan("free")
        if tariff and tariff.question_limit is not None:
            return tariff.question_limit
        return settings.FREE_PLAN_QUESTION_LIMIT

    @property
    def feature_list(self) -> list[str]:
        return [line.strip() for line in self.features.splitlines() if line.strip()]


class PortfolioItem(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to="landing/portfolio/", null=True, blank=True)
    url = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("Qilingan ish")
        verbose_name_plural = _("Qilingan ishlar")

    def __str__(self):
        return self.title


class Testimonial(models.Model):
    author_name = models.CharField(max_length=255)
    author_role = models.CharField(max_length=255, blank=True, default="")
    text = models.TextField()
    avatar = models.ImageField(upload_to="landing/testimonials/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("Mijoz fikri")
        verbose_name_plural = _("Mijozlar fikri")

    def __str__(self):
        return self.author_name
