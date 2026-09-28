# Mavjud (boshlang'ich) tariflar va mijozlar fikrining ruscha/inglizcha tarjimalarini to'ldiradi.
# Faqat o'zbekcha matni boshlang'ich holatda qolgan va tarjimasi hali bo'sh yozuvlar yangilanadi —
# admin o'zgartirgan matnlarga tegilmaydi.
from django.db import migrations

TARIFFS = [
    {
        "name": "Bepul",
        "features": "20 ta bepul savol-javob\nHujjat yuklash va AI sozlamalari\nTelegram akkaunt ulash\nArizalar (CRM)",
        "name_ru": "Бесплатный",
        "name_en": "Free",
        "features_ru": "20 бесплатных вопросов-ответов\nЗагрузка документов и настройки ИИ\nПодключение Telegram-аккаунта\nЗаявки (CRM)",
        "features_en": "20 free questions and answers\nDocument upload and AI settings\nTelegram account connection\nLeads (CRM)",
    },
    {
        "name": "Pro",
        "features": "Cheksiz savol-javob\nTelegram orqali avtomatlashtirish\nBoshqaruv paneli\nUstuvor yordam",
        "name_ru": "Pro",
        "name_en": "Pro",
        "features_ru": "Безлимитные вопросы-ответы\nАвтоматизация через Telegram\nПанель управления\nПриоритетная поддержка",
        "features_en": "Unlimited questions and answers\nTelegram automation\nAdmin dashboard\nPriority support",
    },
]

TESTIMONIALS = [
    {
        "author_name": "Aziz Karimov",
        "text": "Saidex bilan ishlaganimizga bir oy bo'ldi — mijozlarning aksariyat savoliga AI o'zi javob beryapti, biz esa faqat murakkab holatlarga vaqt ajratamiz.",
        "author_role_ru": "Основатель интернет-магазина «TechMart»",
        "author_role_en": "Founder of the \"TechMart\" online store",
        "text_ru": "Мы работаем с Saidex уже месяц — на большинство вопросов клиентов ИИ отвечает сам, а мы уделяем время только сложным случаям.",
        "text_en": "We've been working with Saidex for a month — the AI answers most customer questions on its own, and we only spend time on complex cases.",
    },
    {
        "author_name": "Dilnoza Yusupova",
        "text": "Telegram orqali kelayotgan buyurtmalarni endi AI o'zi qabul qiladi va ariza sifatida bizga yetkazadi — juda qulay bo'ldi.",
        "author_role_ru": "Маркетинг-менеджер, «Beauty Line»",
        "author_role_en": "Marketing manager, \"Beauty Line\"",
        "text_ru": "Заказы из Telegram теперь принимает ИИ и передаёт их нам в виде заявок — очень удобно.",
        "text_en": "The AI now takes orders coming in through Telegram and passes them to us as leads — it's very convenient.",
    },
    {
        "author_name": "Sardor Rahimov",
        "text": "Boshqaruv panel juda tushunarli — hujjatlarni yuklab, AI'ni sozlash bir necha daqiqada bo'ldi.",
        "author_role_ru": "Директор «Rahimov Group»",
        "author_role_en": "Director of \"Rahimov Group\"",
        "text_ru": "Панель управления очень понятная — загрузить документы и настроить ИИ удалось за несколько минут.",
        "text_en": "The dashboard is very intuitive — uploading documents and setting up the AI took just a few minutes.",
    },
]


def forward(apps, schema_editor):
    Tariff = apps.get_model("landing", "Tariff")
    Testimonial = apps.get_model("landing", "Testimonial")

    for data in TARIFFS:
        Tariff.objects.filter(name=data["name"], features=data["features"], name_ru="", features_ru="").update(
            name_ru=data["name_ru"], name_en=data["name_en"],
            features_ru=data["features_ru"], features_en=data["features_en"],
        )

    for data in TESTIMONIALS:
        Testimonial.objects.filter(author_name=data["author_name"], text=data["text"], text_ru="").update(
            author_role_ru=data["author_role_ru"], author_role_en=data["author_role_en"],
            text_ru=data["text_ru"], text_en=data["text_en"],
        )


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0008_content_translations"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
