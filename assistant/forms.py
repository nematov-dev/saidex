from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from landing.models import Tariff
from .models import Document, BotConfig, ProjectSubscription, Workspace
from .services.phone import normalize_phone


def _clean_unique_phone(value: str, exclude_workspace=None) -> str:
    """Telefonni +998XXXXXXXXX ko'rinishiga keltiradi va boshqa hisobda band emasligini tekshiradi."""
    phone = normalize_phone(value)
    if not phone:
        raise forms.ValidationError(_("Telefon raqamini to'g'ri kiriting, masalan: +998901234567"))
    qs = Workspace.objects.filter(phone=phone)
    if exclude_workspace is not None:
        qs = qs.exclude(pk=exclude_workspace.pk)
    if qs.exists():
        raise forms.ValidationError(_("Bu telefon raqami bilan hisob allaqachon mavjud."))
    return phone


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
    phone = forms.CharField(
        label=_("Telefon raqami"), required=False, max_length=32,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+998 90 123 45 67", "inputmode": "tel"}),
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

    def clean_phone(self):
        value = self.cleaned_data.get("phone", "").strip()
        if not value:
            return ""
        return _clean_unique_phone(value)

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    @transaction.atomic
    def save(self) -> Workspace:
        email = self.cleaned_data["email"]
        user = User.objects.create_user(username=email, email=email, password=self.cleaned_data["password"])
        workspace = Workspace.objects.create(
            owner=user, name=self.cleaned_data.get("name") or email, phone=self.cleaned_data.get("phone", ""),
        )
        workspace.config  # boshlang'ich AI sozlamalari (umumiy prompt) yaratiladi
        subscription = workspace.subscription
        subscription.free_question_limit = Tariff.free_question_limit()
        subscription.save(update_fields=["free_question_limit"])
        if self.cleaned_data.get("plan") == "pro":
            subscription.extend(self.cleaned_data.get("pro_days") or 30)
        return workspace


class WorkspaceUserUpdateForm(forms.Form):
    """Super admin: foydalanuvchining email (login), telefon va biznes nomini tahrirlash."""

    email = forms.CharField(
        label=_("Email / login"), max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        label=_("Telefon raqami"), required=False, max_length=32,
        widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "tel"}),
    )
    name = forms.CharField(
        label=_("Biznes nomi"), required=False, max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, workspace: Workspace, **kwargs):
        self.workspace = workspace
        kwargs.setdefault("initial", {
            "email": workspace.owner.get_username(), "phone": workspace.phone, "name": workspace.name,
        })
        super().__init__(*args, **kwargs)

    def clean_email(self):
        value = self.cleaned_data["email"].strip()
        if "@" in value:
            value = value.lower()
        taken = User.objects.filter(Q(username__iexact=value) | Q(email__iexact=value)).exclude(pk=self.workspace.owner_id)
        if taken.exists():
            raise forms.ValidationError(_("Bu email/login boshqa hisobda band."))
        return value

    def clean_phone(self):
        value = self.cleaned_data.get("phone", "").strip()
        return _clean_unique_phone(value, exclude_workspace=self.workspace) if value else ""

    @transaction.atomic
    def save(self):
        owner = self.workspace.owner
        owner.username = self.cleaned_data["email"]
        if "@" in owner.username:
            owner.email = owner.username
        owner.save(update_fields=["username", "email"])
        self.workspace.phone = self.cleaned_data["phone"]
        self.workspace.name = self.cleaned_data["name"]
        self.workspace.save(update_fields=["phone", "name"])
