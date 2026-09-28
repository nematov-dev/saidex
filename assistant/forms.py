from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from .models import Document, BotConfig, ProjectSubscription, Workspace


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


class WorkspaceUserCreateForm(forms.Form):
    """
    Yangi foydalanuvchi (biznes) + uning ish maydonini yaratadi. Login sifatida
    email ishlatiladi (username=email, kichik harflarda). Super admin panelida
    shu forma ishlatiladi; landing page'dagi ro'yxatdan o'tish formasi
    (landing.forms.RegistrationForm) ham shu mantiqqa tayanadi.
    """

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "email@example.com"}),
    )
    name = forms.CharField(
        label=_("Biznes nomi"), required=False, max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Biznes nomi (ixtiyoriy)")}),
    )
    password = forms.CharField(
        label=_("Parol"), min_length=8,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    plan = forms.ChoiceField(
        label=_("Tarif"), choices=ProjectSubscription.PLAN_CHOICES, initial="free",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    pro_days = forms.IntegerField(
        label=_("Pro muddati (kun)"), required=False, min_value=1, initial=30,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
            raise forms.ValidationError(_("Bu email bilan hisob allaqachon mavjud."))
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    @transaction.atomic
    def save(self) -> Workspace:
        email = self.cleaned_data["email"]
        user = User.objects.create_user(username=email, email=email, password=self.cleaned_data["password"])
        workspace = Workspace.objects.create(owner=user, name=self.cleaned_data.get("name") or email)
        workspace.config  # boshlang'ich AI sozlamalari (umumiy prompt) yaratiladi
        subscription = workspace.subscription
        if self.cleaned_data.get("plan") == "pro":
            subscription.extend(self.cleaned_data.get("pro_days") or 30)
        return workspace
