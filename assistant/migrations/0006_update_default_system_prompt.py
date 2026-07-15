from django.db import migrations

OLD_DEFAULT = (
    "Sen foydali AI-yordamchisan. Faqat berilgan hujjatlar asosida, "
    "aniq va qisqa javob ber. Agar javob hujjatlarda bo'lmasa, "
    "buni ochiq ayt va operatorga murojaat qilishni taklif qil."
)

NEW_DEFAULT = (
    "Siz ushbu biznesning rasmiy AI-yordamchisisiz. Muloqotni doim samimiy, "
    "professional va qisqa tarzda olib borasiz.\n\n"
    "Qoidalar:\n"
    "1. Faqat sizga berilgan ma'lumotlar (hujjatlar) asosida javob bering — "
    "shu ma'lumotlar doirasidan chiqmang va hech narsani o'zingizdan to'qib chiqarmang.\n"
    "2. Agar savolga javob ma'lumotlar orasida topilmasa, buni ochiq ayting va "
    "operatorga murojaat qilishni taklif qiling.\n"
    "3. Javoblaringiz aniq, tushunarli va imkon qadar qisqa bo'lsin.\n"
    "4. Foydalanuvchi narx, buyurtma yoki xarid haqida qiziqish bildirsa, "
    "ishonchli va do'stona ohangda javob bering."
)


def update_default_prompt(apps, schema_editor):
    """
    Mavjud BotConfig yozuvi (pk=1) hali ESKI standart promptni saqlab turgan
    bo'lsa (ya'ni admin panel orqali hech qachon o'zgartirilmagan bo'lsa),
    uni yangi, professionalroq standart matn bilan almashtiramiz.
    Agar biznes admin o'z promptini yozgan bo'lsa (matn boshqacha), tegilmaydi.
    """
    BotConfig = apps.get_model("assistant", "BotConfig")
    BotConfig.objects.filter(system_prompt=OLD_DEFAULT).update(system_prompt=NEW_DEFAULT)


def reverse_update_default_prompt(apps, schema_editor):
    BotConfig = apps.get_model("assistant", "BotConfig")
    BotConfig.objects.filter(system_prompt=NEW_DEFAULT).update(system_prompt=OLD_DEFAULT)


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0005_remove_botconfig_userbot_enabled_and_more"),
    ]

    operations = [
        migrations.RunPython(update_default_prompt, reverse_update_default_prompt),
    ]
