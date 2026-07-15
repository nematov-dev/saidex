from django.db import migrations

# V2 — 0012-migratsiyada joriy qilingan versiya.
KEYWORDS_V2 = "narxi,qancha turadi,sotib ol,buyurtma,bog'lanish,qanday buyurtma,qiziqdim,skidka,chegirma,ariza,ariza qoldirmoqchiman,murojaat,bog'lanmoqchiman,qiziqaman,aloqa"

# V3 — real foydalanuvchi suhbatida "olaman" (masalan "10 ta olaman") va
# "bog'lansam"/"bog'lanaman" kabi "bog'lan" ildizidan boshqa shakllar
# ushlanmagani sababli qo'shildi/almashtirildi: "olaman" yangi so'z sifatida
# qo'shildi, "bog'lanish"+"bog'lanmoqchiman" o'rniga ularning ikkalasini ham
# (va boshqa barcha "bog'lan*" shakllarini) qamrab oladigan qisqaroq "bog'lan"
# ildizi qo'yildi.
KEYWORDS_V3 = "narxi,qancha turadi,sotib ol,olaman,buyurtma,bog'lan,qanday buyurtma,qiziqdim,skidka,chegirma,ariza,ariza qoldirmoqchiman,murojaat,qiziqaman,aloqa"


def update_forward(apps, schema_editor):
    """
    Faqat hali sozlanmagan (V2 standart qiymatida qolgan) yozuvlarni
    yangilaymiz — admin o'zi qo'lda o'zgartirgan bo'lsa, tegilmaymiz.
    """
    BotConfig = apps.get_model("assistant", "BotConfig")
    BotConfig.objects.filter(lead_trigger_keywords=KEYWORDS_V2).update(
        lead_trigger_keywords=KEYWORDS_V3
    )


def update_reverse(apps, schema_editor):
    BotConfig = apps.get_model("assistant", "BotConfig")
    BotConfig.objects.filter(lead_trigger_keywords=KEYWORDS_V3).update(
        lead_trigger_keywords=KEYWORDS_V2
    )


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0013_alter_botconfig_lead_trigger_keywords"),
    ]

    operations = [
        migrations.RunPython(update_forward, update_reverse),
    ]
