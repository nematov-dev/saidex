# Multi-user (SaaS) ga o'tish: avvalgi bitta-biznes rejimidagi BARCHA ma'lumotlar
# (AI sozlamalari, obuna, Telegram akkaunt, hujjatlar, arizalar, suhbatlar,
# guruhlar) asosiy — Saidex'ning o'z — ish maydoniga (is_main=True) o'tkaziladi.
#
# Asosiy ish maydoni egasi: birinchi faol ODDIY (super admin bo'lmagan)
# foydalanuvchi — ya'ni avval biznes panelga kirib yurgan admin; bunday
# foydalanuvchi bo'lmasa, birinchi super admin. Avvalgi obuna Pro sifatida
# saqlanadi (muddati o'zgarmaydi).
from django.contrib.auth.hashers import make_password
from django.db import migrations

SINGLETON_MODELS = ["BotConfig", "ProjectSubscription", "TelegramAccountConnection"]
PER_ROW_MODELS = ["Document", "Lead", "PendingLead", "ConversationLog", "TelegramGroup"]


def _has_legacy_data(apps):
    return any(
        apps.get_model("assistant", name).objects.filter(workspace__isnull=True).exists()
        for name in SINGLETON_MODELS + PER_ROW_MODELS
    )


def _pick_owner(apps):
    User = apps.get_model("auth", "User")
    owner = (
        User.objects.filter(is_active=True, is_superuser=False).order_by("pk").first()
        or User.objects.filter(is_superuser=True).order_by("pk").first()
    )
    if owner is None:
        owner = User.objects.create(username="saidex", password=make_password(None), is_active=True)
    return owner


def forward(apps, schema_editor):
    if not _has_legacy_data(apps):
        return

    Workspace = apps.get_model("assistant", "Workspace")
    BotConfig = apps.get_model("assistant", "BotConfig")

    legacy_config = BotConfig.objects.filter(workspace__isnull=True).order_by("pk").first()
    owner = _pick_owner(apps)
    workspace, _ = Workspace.objects.get_or_create(
        owner=owner,
        defaults={"name": legacy_config.business_name if legacy_config else "Saidex", "is_main": True},
    )
    if not workspace.is_main:
        workspace.is_main = True
        workspace.save(update_fields=["is_main"])

    for name in SINGLETON_MODELS:
        Model = apps.get_model("assistant", name)
        rows = list(Model.objects.filter(workspace__isnull=True).order_by("pk"))
        if not rows:
            continue
        if not Model.objects.filter(workspace=workspace).exists():
            first = rows.pop(0)
            first.workspace = workspace
            if name == "ProjectSubscription":
                first.plan = "pro"
            first.save()
        for extra in rows:
            extra.delete()

    for name in PER_ROW_MODELS:
        apps.get_model("assistant", name).objects.filter(workspace__isnull=True).update(workspace=workspace)


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0027_workspaces"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
