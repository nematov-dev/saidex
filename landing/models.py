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

    name = models.CharField(max_length=100)
    price = models.CharField(max_length=100, help_text="Masalan: 650 000 so'm")
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
