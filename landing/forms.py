from django import forms
from django.utils.translation import gettext_lazy as _

from assistant.forms import WorkspaceUserCreateForm

from .models import LandingSettings, Tariff, PortfolioItem, Testimonial


class RegistrationForm(WorkspaceUserCreateForm):
    """
    Landing page'dagi ro'yxatdan o'tish (email + parol). Har doim bepul tarif
    bilan boshlanadi — Pro'ga faqat super admin o'tkazadi (Telegram orqali murojaatdan keyin).
    """

    field_order = ["email", "phone", "name", "password", "password2"]
    plan = None
    pro_days = None
    password2 = forms.CharField(
        label=_("Parolni takrorlang"),
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].required = True

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("password") != cleaned.get("password2"):
            self.add_error("password2", _("Parollar bir xil emas."))
        return cleaned


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
        fields = [
            "name", "plan_code", "price", "question_limit", "period", "features", "is_featured", "is_active", "order",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Tarif nomi")}),
            "plan_code": forms.Select(attrs={"class": "form-select"}),
            "question_limit": forms.NumberInput(attrs={"class": "form-control", "placeholder": "20"}),
            "price": forms.TextInput(attrs={"class": "form-control", "placeholder": "$59"}),
            "period": forms.Select(attrs={"class": "form-select"}),
            "features": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": _("Har qatorda bitta xususiyat")}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "style": "max-width:100px;"}),
        }

    def clean_plan_code(self):
        plan_code = self.cleaned_data.get("plan_code", "")
        if plan_code:
            taken = Tariff.objects.filter(plan_code=plan_code).exclude(pk=self.instance.pk)
            if taken.exists():
                raise forms.ValidationError(_("Bu obunaga boshqa tarif allaqachon bog'langan."))
        return plan_code


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
