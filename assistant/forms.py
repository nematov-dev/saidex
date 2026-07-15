from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Document, BotConfig


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["title", "file"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Hujjat nomi")}),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class BotConfigForm(forms.ModelForm):
    """
    Kundalik foydalanish uchun soddalashtirilgan forma — faqat BITTA asosiy
    AI prompt maydoni va yoq/yondir tugmasi. Biznes nomi, salomlashish va
    fallback xabari kabi texnik/kam ishlatiladigan maydonlar endi shu yerda
    ko'rsatilmaydi (ular Django admin: /admin/assistant/botconfig/ orqali
    hali ham tahrirlanishi mumkin, lekin kundalik promptni yagona joyda —
    shu formada — yozish tavsiya etiladi).
    """

    class Meta:
        model = BotConfig
        fields = ["system_prompt", "ai_enabled"]
        widgets = {
            "system_prompt": forms.Textarea(attrs={"class": "form-control", "rows": 14}),
            "ai_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
