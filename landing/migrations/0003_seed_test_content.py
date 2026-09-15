# Test uchun landing page kontentini shakllantiradi:
#   1) 3 ta tarif: Bepul, Standart, Premium (tariff-card sifatida ko'rinadi)
#   2) 3 ta mijoz fikri (Testimonial) - "Mijozlar fikri" bo'limini to'ldirish uchun
#   3) Mavjud "Qilingan ishlar" (Portfolio) yozuvlari is_active=False qilinadi -
#      shu bilan {% if portfolio_items %} False bo'lib, bo'lim saytdan yo'qoladi
#      (foydalanuvchi so'rovi: "ishlarimizni olib tashla")
from django.db import migrations

TARIFFS = [
    {
        "name": "Bepul",
        "price": "0 so'm",
        "period": "monthly",
        "features": "1 ta AI-yordamchi\n50 tagacha savol-javob / oy\nEmail orqali yordam",
        "is_featured": False,
        "order": 1,
    },
    {
        "name": "Standart",
        "price": "650 000 so'm",
        "period": "monthly",
        "features": "Cheksiz savol-javob\nTelegram orqali avtomatlashtirish\nBoshqaruv paneli\nUstuvor yordam",
        "is_featured": True,
        "order": 2,
    },
    {
        "name": "Premium",
        "price": "1 200 000 so'm",
        "period": "monthly",
        "features": "Standart tarifning barcha imkoniyatlari\nVeb-sayt uchun AI-chat\nShaxsiy menejer\n24/7 qo'llab-quvvatlash",
        "is_featured": False,
        "order": 3,
    },
]

TESTIMONIALS = [
    {
        "author_name": "Aziz Karimov",
        "author_role": "\"TechMart\" onlayn do'koni asoschisi",
        "text": "Saidex bilan ishlaganimizga bir oy bo'ldi — mijozlarning aksariyat savoliga AI o'zi javob beryapti, biz esa faqat murakkab holatlarga vaqt ajratamiz.",
        "order": 1,
    },
    {
        "author_name": "Dilnoza Yusupova",
        "author_role": "Marketing menejeri, \"Beauty Line\"",
        "text": "Telegram orqali kelayotgan buyurtmalarni endi AI o'zi qabul qiladi va ariza sifatida bizga yetkazadi — juda qulay bo'ldi.",
        "order": 2,
    },
    {
        "author_name": "Sardor Rahimov",
        "author_role": "\"Rahimov Group\" direktori",
        "text": "Boshqaruv panel juda tushunarli — hujjatlarni yuklab, AI'ni sozlash bir necha daqiqada bo'ldi.",
        "order": 3,
    },
]


def seed_forward(apps, schema_editor):
    Tariff = apps.get_model("landing", "Tariff")
    Testimonial = apps.get_model("landing", "Testimonial")
    PortfolioItem = apps.get_model("landing", "PortfolioItem")

    for data in TARIFFS:
        Tariff.objects.get_or_create(name=data["name"], defaults=data)

    for data in TESTIMONIALS:
        Testimonial.objects.get_or_create(author_name=data["author_name"], defaults=data)

    PortfolioItem.objects.update(is_active=False)


def seed_reverse(apps, schema_editor):
    Tariff = apps.get_model("landing", "Tariff")
    Testimonial = apps.get_model("landing", "Testimonial")
    PortfolioItem = apps.get_model("landing", "PortfolioItem")

    Tariff.objects.filter(name__in=[t["name"] for t in TARIFFS]).delete()
    Testimonial.objects.filter(author_name__in=[t["author_name"] for t in TESTIMONIALS]).delete()
    # Eslatma: qaysi portfolio yozuvlari avval faol bo'lganini bilmaymiz,
    # shuning uchun reverse hammasini qayta faollashtiradi (taxminiy qaytarish).
    PortfolioItem.objects.update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ("landing", "0002_remove_landingsettings_hero_subtitle_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
