# Landing tariflarini yangilash:
#   1) "Premium" tarifi olib tashlanadi
#   2) "Standart" tarifi narxi 699 000 so'm qilinadi
from django.db import migrations


def update_forward(apps, schema_editor):
    Tariff = apps.get_model("landing", "Tariff")
    Tariff.objects.filter(name="Premium").delete()
    Tariff.objects.filter(name="Standart").update(price="699 000 so'm")


def update_reverse(apps, schema_editor):
    Tariff = apps.get_model("landing", "Tariff")
    Tariff.objects.filter(name="Standart").update(price="650 000 so'm")
    Tariff.objects.get_or_create(
        name="Premium",
        defaults={
            "price": "1 200 000 so'm",
            "period": "monthly",
            "features": "Standart tarifning barcha imkoniyatlari\nVeb-sayt uchun AI-chat\nShaxsiy menejer\n24/7 qo'llab-quvvatlash",
            "is_featured": False,
            "order": 3,
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0003_seed_test_content"),
    ]

    operations = [
        migrations.RunPython(update_forward, update_reverse),
    ]
