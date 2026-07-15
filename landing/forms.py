from django import forms
from django.utils.translation import gettext_lazy as _

from .models import LandingSettings, Tariff, PortfolioItem, Testimonial


class ContactLeadForm(forms.Form):
    """Ochiq bosh sahifadagi aloqa formasi — Lead(channel='website') yaratadi."""

    full_name = forms.CharField(
        max_length=255, label=_("Ismingiz"),
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Ismingiz")}),
    )
    phone = forms.CharField(
        max_length=32, label=_("Telefon"),
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+998 __ ___ __ __"}),
    )
    message = forms.CharField(
        label=_("Xabar"), required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": _("Loyihangiz haqida qisqacha...")}),
    )


class LandingSettingsForm(forms.ModelForm):
    class Meta:
        model = LandingSettings
        fields = [
            "logo", "admin_phone", "admin_telegram_username",
            "instagram_url", "telegram_url", "linkedin_url", "facebook_url", "youtube_url", "x_url",
        ]
        widgets = {
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "admin_phone": forms.TextInput(attrs={"class": "form-control"}),
            "admin_telegram_username": forms.TextInput(attrs={"class": "form-control", "placeholder": "@username"}),
            "instagram_url": forms.URLInput(attrs={"class": "form-control"}),
            "telegram_url": forms.URLInput(attrs={"class": "form-control"}),
            "linkedin_url": forms.URLInput(attrs={"class": "form-control"}),
            "facebook_url": forms.URLInput(attrs={"class": "form-control"}),
            "youtube_url": forms.URLInput(attrs={"class": "form-control"}),
            "x_url": forms.URLInput(attrs={"class": "form-control"}),
        }


class TariffForm(forms.ModelForm):
    class Meta:
        model = Tariff
        fields = ["name", "price", "period", "features", "is_featured", "is_active", "order"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Tarif nomi")}),
            "price": forms.TextInput(attrs={"class": "form-control", "placeholder": "650 000 so'm"}),
            "period": forms.Select(attrs={"class": "form-select"}),
            "features": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": _("Har qatorda bitta xususiyat")}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "style": "max-width:100px;"}),
        }


class PortfolioItemForm(forms.ModelForm):
    class Meta:
        model = PortfolioItem
        fields = ["title", "description", "image", "url", "is_active", "order"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Loyiha nomi")}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "style": "max-width:100px;"}),
        }


class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ["author_name", "author_role", "text", "avatar", "is_active", "order"]
        widgets = {
            "author_name": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Ism-familiya")}),
            "author_role": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Lavozimi / biznesi")}),
            "text": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "style": "max-width:100px;"}),
        }
