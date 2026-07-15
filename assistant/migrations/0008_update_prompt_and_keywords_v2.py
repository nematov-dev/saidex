from django.db import migrations

# V0 — eng birinchi, asl standart prompt (0001_initial'da yozilgan)
PROMPT_V0 = (
    "Sen foydali AI-yordamchisan. Faqat berilgan hujjatlar asosida, "
    "aniq va qisqa javob ber. Agar javob hujjatlarda bo'lmasa, "
    "buni ochiq ayt va operatorga murojaat qilishni taklif qil."
)

# V1 — 0006-migratsiyada joriy qilingan "professional" versiya
PROMPT_V1 = (
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

# V2 — hozirgi standart: salomlashish + ariza so'ralganda qisqa javob berish
# haqida aniq ko'rsatma qo'shilgan versiya.
PROMPT_V2 = (
    "Siz ushbu biznesning rasmiy AI-yordamchisisiz. Muloqotni doim samimiy, "
    "professional va qisqa tarzda olib borasiz.\n\n"
    "Salomlashish: Foydalanuvchi salom bersa yoki suhbatni boshlasa, iliq va qisqa "
    "salomlashib, qanday yordam bera olishingizni so'rang.\n\n"
    "Qoidalar:\n"
    "1. Faqat sizga berilgan ma'lumotlar (hujjatlar) asosida javob bering — "
    "shu ma'lumotlar doirasidan chiqmang va hech narsani o'zingizdan to'qib chiqarmang.\n"
    "2. Agar savolga javob ma'lumotlar orasida topilmasa, buni ochiq ayting va "
    "operatorga murojaat qilishni taklif qiling.\n"
    "3. Javoblaringiz aniq, tushunarli va imkon qadar qisqa bo'lsin — keraksiz "
    "cho'zib yozmang.\n"
    "4. Foydalanuvchi narx, buyurtma, ariza yoki xarid haqida qiziqish bildirsa — "
    "bu jarayonni uzoq tushuntirib o'tirmang. Qisqa va iliq tasdiqlovchi javob bering "
    "(masalan: \"Albatta, hoziroq bog'lab qo'yamiz!\") — tizim o'zi keyingi xabarda "
    "avtomatik ravishda ism va telefon raqamini so'raydi."
)

KEYWORDS_V0 = (
    "narxi,qancha turadi,sotib olaman,buyurtma,bog'lanish,qanday buyurtma,"
    "qiziqdim,skidka,chegirma"
)

KEYWORDS_V1 = (
    "narxi,qancha turadi,sotib olaman,buyurtma,bog'lanish,qanday buyurtma,qiziqdim,"
    "skidka,chegirma,ariza,ariza qoldirmoqchiman,murojaat,bog'lanmoqchiman,qiziqaman,aloqa"
)


def update_forward(apps, schema_editor):
    """
    Faqat hali sozlanmagan (standart qiymatda qolgan) yozuvlarni yangilaymiz —
    admin o'zi qo'lda o'zgartirgan bo'lsa, tegilmaymiz.
    """
    BotConfig = apps.get_model("assistant", "BotConfig")
    BotConfig.objects.filter(system_prompt__in=[PROMPT_V0, PROMPT_V1]).update(
        system_prompt=PROMPT_V2
    )
    BotConfig.objects.filter(lead_trigger_keywords=KEYWORDS_V0).update(
        lead_trigger_keywords=KEYWORDS_V1
    )


def update_reverse(apps, schema_editor):
    BotConfig = apps.get_model("assistant", "BotConfig")
    BotConfig.objects.filter(system_prompt=PROMPT_V2).update(system_prompt=PROMPT_V1)
    BotConfig.objects.filter(lead_trigger_keywords=KEYWORDS_V1).update(
        lead_trigger_keywords=KEYWORDS_V0
    )


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0007_alter_botconfig_system_prompt"),
    ]

    operations = [
        migrations.RunPython(update_forward, update_reverse),
    ]
