from django.conf import settings
from django.db import models
from django.utils.translation import get_language, gettext_lazy as _


class TranslatedFieldsMixin:
    """
    Saytdagi kontent (tariflar, mijozlar fikri, qilingan ishlar) bazada saqlanadi — shablon
    tarjimasi ({% trans %}) unga ta'sir qilmaydi. Shu sababli har bir matn maydonining
    ruscha/inglizcha nusxasi alohida maydonda (masalan text_ru, text_en) saqlanadi va sayt
    tanlangan tildagisini ko'rsatadi; tarjima bo'sh bo'lsa — asosiy (o'zbekcha) matn.
    """

    def translated(self, field: str) -> str:
        lang = (get_language() or "uz")[:2]
        if lang in ("ru", "en"):
            value = getattr(self, f"{field}_{lang}", "")
            if value:
                return value
        return getattr(self, field)


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


class Tariff(TranslatedFieldsMixin, models.Model):
    PERIOD_CHOICES = [
        ("monthly", _("Oylik")),
        ("yearly", _("Yillik")),
    ]
    PLAN_CODE_CHOICES = [
        ("", _("— (faqat saytda ko'rinadi)")),
        ("free", _("Bepul obuna")),
        ("pro", _("Pro obuna")),
    ]

    name = models.CharField(_("Nomi"), max_length=100)
    name_ru = models.CharField(_("Nomi (ruscha)"), max_length=100, blank=True, default="")
    name_en = models.CharField(_("Nomi (inglizcha)"), max_length=100, blank=True, default="")
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
    features_ru = models.TextField(_("Imkoniyatlar (ruscha)"), blank=True, default="")
    features_en = models.TextField(_("Imkoniyatlar (inglizcha)"), blank=True, default="")
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
    def local_name(self) -> str:
        return self.translated("name")

    @property
    def feature_list(self) -> list[str]:
        return [line.strip() for line in self.translated("features").splitlines() if line.strip()]


class PortfolioItem(TranslatedFieldsMixin, models.Model):
    title = models.CharField(_("Nomi"), max_length=255)
    title_ru = models.CharField(_("Nomi (ruscha)"), max_length=255, blank=True, default="")
    title_en = models.CharField(_("Nomi (inglizcha)"), max_length=255, blank=True, default="")
    description = models.TextField(_("Tavsif"), blank=True, default="")
    description_ru = models.TextField(_("Tavsif (ruscha)"), blank=True, default="")
    description_en = models.TextField(_("Tavsif (inglizcha)"), blank=True, default="")
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


class Testimonial(TranslatedFieldsMixin, models.Model):
    author_name = models.CharField(_("Ism"), max_length=255)
    author_role = models.CharField(_("Lavozimi"), max_length=255, blank=True, default="")
    author_role_ru = models.CharField(_("Lavozimi (ruscha)"), max_length=255, blank=True, default="")
    author_role_en = models.CharField(_("Lavozimi (inglizcha)"), max_length=255, blank=True, default="")
    text = models.TextField(_("Matn"))
    text_ru = models.TextField(_("Matn (ruscha)"), blank=True, default="")
    text_en = models.TextField(_("Matn (inglizcha)"), blank=True, default="")
    avatar = models.ImageField(upload_to="landing/testimonials/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("Mijoz fikri")
        verbose_name_plural = _("Mijozlar fikri")

    def __str__(self):
        return self.author_name


def _add_local_properties(model, fields):
    for field in fields:
        setattr(model, f"local_{field}", property(lambda self, f=field: self.translated(f)))


_add_local_properties(PortfolioItem, ["title", "description"])
_add_local_properties(Testimonial, ["author_role", "text"])
