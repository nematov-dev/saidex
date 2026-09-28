# Landing tariflarini yangi obuna tizimiga moslash:
#   - "Bepul": ro'yxatdan o'tganda beriladigan 20 ta bepul savol-javob;
#   - "Standart" -> "Pro" ($59/oy, Telegram orqali murojaat qilib olinadi).
from django.db import migrations

FREE_FEATURES = (
    "20 ta bepul savol-javob\n"
    "Hujjat yuklash va AI sozlamalari\n"
    "Telegram akkaunt ulash\n"
    "Arizalar (CRM)"
)
OLD_FREE_FEATURES = "1 ta AI-yordamchi\n50 tagacha savol-javob / oy\nEmail orqali yordam"


def forward(apps, schema_editor):
    Tariff = apps.get_model("landing", "Tariff")
    Tariff.objects.filter(name="Bepul").update(features=FREE_FEATURES)
    Tariff.objects.filter(name="Standart").update(name="Pro")


def reverse(apps, schema_editor):
    Tariff = apps.get_model("landing", "Tariff")
    Tariff.objects.filter(name="Pro").update(name="Standart")
    Tariff.objects.filter(name="Bepul").update(features=OLD_FREE_FEATURES)


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0005_tariff_price_usd"),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
