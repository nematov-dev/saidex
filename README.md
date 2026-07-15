# Saidex AI Agent

Biznes uchun AI-yordamchi: admin panel, RAG (hujjatlar asosida javob) va
Telegram AKKAUNT orqali ishlash, obuna va loyihani boshqarish uchun
o'zingizga (super admin) tegishli maxsus bo'lim bilan.

## Tuzilma

```
saidex_ai_agent/
├── manage.py
├── requirements.txt
├── .env                     # maxfiy sozlamalar (repo'ga tushmaydi)
├── .env.example
├── docker-compose.yml       # PostgreSQL (pgvector) + Redis
├── config/                  # Django sozlamalari (settings/urls/wsgi/asgi)
├── assistant/                # Asosiy ilova: modellar, admin panel, RAG servislar
│   ├── models.py             # BotConfig, ProjectSubscription, Document(Chunk), Lead, ConversationLog
│   ├── views.py               # Admin panel + Super Admin view'lari
│   ├── services/              # embeddings.py, rag.py, llm.py, chunking.py, document_loader.py
│   ├── management/commands/   # check_subscription_alert — obuna ogohlantirishi
│   └── templates/assistant/   # Admin panel HTML sahifalari
├── userbot/                  # Telegram AKKAUNT (Telethon)
├── scripts/                  # Nginx generatori, Postgres init skripti
└── deploy/                   # Nginx va systemd shablonlari (production uchun)
```

Bitta, to'liq mustaqil Django loyiha — ortiqcha "shablon" yoki "mijozlar papkasi"
qatlami yo'q, hammasi shu yerda.

## Texnologiyalar

- **Django 5** — admin panel va backend
- **PostgreSQL + pgvector** — ma'lumotlar bazasi va RAG uchun vektor qidiruv
- **Vertex AI (`gemini-embedding-001`)** — hujjatlarni embedding qilish
- **Vertex AI Gemini** (2.5 Flash / Flash-Lite / Pro — super admin panelda tanlanadi) — javob generatsiyasi
- **Telethon** — Telegram AKKAUNT sifatida ulanish

## Ikki xil admin darajasi

| Daraja | Kim | Nima qila oladi |
|---|---|---|
| **Biznes admin** | Xodim (`is_staff=True`) | Hujjat yuklash/o'chirish, prompt sozlash, AI'ni yoq-o'chir, arizalarni ko'rish va holatini belgilash, guruhlarni boshqarish |
| **Super admin** | Siz (`is_superuser=True`) | Yuqoridagilar **+** `/saidex/`: obuna muddati, uzaytirish, loyihani **butunlay** yoqish/o'chirish, **AI modelini tanlash** (Flash-Lite / Flash / Pro), Telegram akkaunt ulash/uzish |

`python manage.py createsuperuser` bilan yaratilgan hisob avtomatik super admin
bo'ladi. Super admin bo'limi butunlay alohida — biznes admin panelida unga
hech qanday havola ko'rsatilmaydi, faqat `/saidex/login/` manzili orqali kiriladi.

## O'rnatish (Docker bilan — bitta buyruq bilan hammasi ishga tushadi)

`.env` faylini to'ldirgach (pastga qarang), quyidagi BITTA buyruq bilan
Postgres (pgvector), Redis, Django admin panel VA Telegram AKKAUNT (userbot)
— hammasi birga ishga tushadi:

```bash
docker compose up --build
```

- Admin panel: http://localhost:8000/
- `web` konteyneri migratsiyalarni o'zi bajaradi, keyin serverni ko'taradi.
- `userbot` konteyneri, agar hali hech qanday Telegram akkaunt ulanmagan bo'lsa,
  xatolik bilan to'xtaydi va `restart: on-failure` tufayli avtomatik qayta urinib
  turadi — admin panel > Super Admin (`/saidex/`) > "Telegram akkaunt" orqali
  akkauntni ulaganingizdan so'ng, keyingi qayta urinishda o'zi ishga tushadi
  (konteynerni qo'lda qayta ishga tushirish shart emas).
- Kodni o'zgartirsangiz konteynerlarni qayta build qilish shart emas (loyiha
  papkasi konteynerlar ichiga bind-mount qilingan) — faqat `runserver`
  avtomatik qayta yuklanadi, `userbot`ni esa `docker compose restart userbot`
  bilan qayta ishga tushirish kerak.

Superuser (super admin hisobi) yaratish uchun:

```bash
docker compose exec web python manage.py createsuperuser
```

### Docker'siz, qo'lda ishga tushirish (muqobil)

```bash
# 1) Faqat Postgres va Redisni konteynerda ishga tushirish
docker compose up -d postgres redis

# 2) Kutubxonalar
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3) .env faylini to'ldiring:
#    - TELEGRAM_BOT_TOKEN                -> @BotFather'dan (faqat obuna ogohlantirishi uchun)
#    - GCP_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS -> Google Cloud service account JSON
#    - SUPERADMIN_TELEGRAM_ID            -> shaxsiy Telegram ID'ingiz (obuna ogohlantirishi uchun)
#    - TELEGRAM_API_ID/HASH              -> pastga qarang (Telegram akkaunt uchun)

# 4) Migratsiya va superuser (bu hisob = super admin)
python manage.py migrate
python manage.py createsuperuser

# 5) Ishga tushirish (har biri alohida terminalda)
python manage.py runserver 0.0.0.0:8000   # admin panel: http://localhost:8000/
python userbot/run.py                      # Telegram AKKAUNT
```

## Admin panel imkoniyatlari

1. **Hujjatlar** — PDF/DOCX/TXT yuklaysiz, avtomatik bo'laklarga bo'linib Vertex AI
   orqali embedding qilinadi va pgvector'da saqlanadi.
2. **Prompt/sozlamalar** — AI "shaxsiyati", salomlashish/zaxira xabarlari, va
   **"xarid niyati" so'zlari** (masalan "narxi", "sotib olaman") — shu so'zlar
   yozilsa AI avtomatik ism/telefon so'rab ariza yaratadi.
3. Bosh sahifada AI uchun yagona yoq/o'chir tugmasi.
4. **Arizalar** — voronka: Yangi → Bog'lanildi → Qiziqmoqda → Mijoz bo'ldi /
   Qiziqmas / Olmadi / Keyinroq oladi — holatni o'zgartirib, izoh yozib turasiz.
5. **Guruhlar** — Telegram guruhlarida AI javob berish-bermasligini, javob
   berish tartibini va kalit so'zlarni boshqarasiz (pastga qarang).
6. **Super Admin** (faqat sizga ko'rinadi) — obuna muddati, uzaytirish, loyihani
   butunlay o'chirish/yoqish, va **AI modelini tanlash** (Gemini 2.5 Flash-Lite/Flash/Pro —
   narx va sifat orasida tanlov, faqat sizga ko'rinadi va faqat siz o'zgartira olasiz).

## Telegram AKKAUNT sifatida ulash (Telethon)

Akkaunt ulash to'liq **admin panel orqali**, terminalga kod yozish shart emas:

1. `.env` fayliga `TELEGRAM_API_ID` va `TELEGRAM_API_HASH`ni kiriting
   (https://my.telegram.org/apps dan olinadi), dasturni qayta ishga tushiring.
2. Admin panelga superuser bilan kiring → chap menyudan **"Telegram akkaunt"** ni oching.
3. Telefon raqamni kiritib **"Kod yuborish"** tugmasini bosing — Telegram ilovangizga kod keladi.
4. Kodni kiritib tasdiqlang (agar 2 bosqichli parol yoqilgan bo'lsa, u ham so'raladi).
5. Ulangach, alohida terminalda ishga tushiring:

```bash
python userbot/run.py
```

Bir vaqtning o'zida faqat **bitta** akkaunt ulanishi mumkin — yangisini ulashdan oldin
avval joriysini shu sahifadagi **"Akkauntni uzish"** tugmasi orqali uzish kerak.

Ishlash tartibi: foydalanuvchi yozadi → "yozmoqda..." holati ko'rinadi → RAG orqali
javob beriladi → xarid niyati so'zlari aniqlansa, ism va telefon so'rab avtomatik
ariza yaratiladi. Bosh sahifadagi **AI** tugmasi esa AI'ning javob berish-bermasligini
boshqaradi (ulanish/uzishdan alohida — bu shunchaki AI javobini vaqtincha to'xtatib
turish uchun).

**Barqarorlik:** Vertex AI vaqtinchalik xatolik bersa (masalan kvota "burst"i —
429), tizim avtomatik 4 marta (jami 5 urinish) qayta urinadi. Agar shundan
keyin ham ishlamasa, foydalanuvchiga **hech qanday xabar yuborilmaydi** (xato
matni ko'rsatilmaydi, bot shunchaki jim qoladi) — faqat xatolik serverda
log'ga yoziladi. Xarid niyati (ariza so'rash) esa AI'dan mustaqil, kalit
so'zga asoslangan mantiq bo'lgani uchun, AI butunlay ishlamay qolgan
taqdirda ham ariza yig'ish davom etadi.

## Guruhlar (Telegram group chat)

Telegram AKKAUNT endi shaxsiy yozishmalardan tashqari **guruhlarda** ham javob
bera oladi. Ishlash tartibi:

1. Akkauntingiz a'zo bo'lgan biror guruhga birinchi xabar kelganda, guruh
   avtomatik ravishda admin panel > **Guruhlar** sahifasiga qo'shiladi
   (standart holatda AI o'chirilgan holda).
2. Guruh qatorida **AI yoqilganmi** tugmachasini yoqasiz.
3. **Javob berish tartibi**ni tanlaysiz:
   - *Kalit so'z bilan* — AI faqat `/ai`, `ai`, `#savol`, `/savol`, `savol`
     (yoki shu sahifada o'zingiz sozlagan boshqa so'zlar) yozilganda javob beradi.
   - *Kalitsiz* — guruhdagi har bir xabarga javob beradi.
4. **Kimga javob berish**ni tanlaysiz: barchaga, faqat oddiy foydalanuvchilarga
   (guruh adminlariga emas), yoki faqat guruh adminlariga.
5. Kalit so'zlarning o'zi ham shu sahifaning yuqorisidagi maydonda sozlanadi
   (vergul bilan ajratilgan, masalan `ai,savol`) — `/`, `#` prefikslari
   avtomatik tanib olinadi.

Guruhlarda ariza (lead) yig'ish oqimi ishlamaydi — bu faqat shaxsiy
yozishmalar uchun mo'ljallangan (guruh ichida notanish odamdan ism/telefon
so'rash noqulay bo'lardi).

## Obuna tugashi haqida ogohlantirish

Obuna tugashiga 5 kun (yoki kamroq) qolganda `.env` dagi `SUPERADMIN_TELEGRAM_ID`ga
`TELEGRAM_BOT_TOKEN` orqali avtomatik xabar boradi. Kunlik cron kerak:

```bash
crontab -e
0 9 * * * cd /opt/saidex_ai_agent && venv/bin/python manage.py check_subscription_alert
```

## Domen va production joylashtirish

```bash
# Nginx config
./scripts/generate_nginx.sh <domen.uz> /opt/saidex_ai_agent
sudo cp deploy/nginx/saidex.conf /etc/nginx/sites-available/saidex.conf
sudo ln -s /etc/nginx/sites-available/saidex.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d <domen.uz>        # bepul SSL, avtomatik yangilanadi

# systemd xizmatlari
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now saidex-web
sudo systemctl enable --now saidex-userbot   # Telegram akkaunt uchun
```

## Postgres — alohida foydalanuvchi (xavfsizlik uchun tavsiya)

`.env` faylida `POSTGRES_USER`/`POSTGRES_PASSWORD` allaqachon o'zingizga xos
qiymatlar bilan generatsiya qilingan. Productionda server birinchi marta
sozlanayotganda quyidagi SQL orqali shu foydalanuvchi/bazani yaratib qo'ying
(docker-compose ishlatilsa bu avtomatik bajariladi):

```sql
CREATE ROLE saidex_ai_agent_user WITH LOGIN PASSWORD '...';
CREATE DATABASE saidex_ai_agent OWNER saidex_ai_agent_user;
\connect saidex_ai_agent
CREATE EXTENSION IF NOT EXISTS vector;
```

## Narx haqida qisqacha

- Vertex AI embedding (`gemini-embedding-001`): 1000 savolga taxminan $0.005 — deyarli sezilmaydi.
- Gemini 2.5 Flash javob generatsiyasi: taxminan 1000 savolga $1 atrofida (kontekst+javob hajmiga qarab farqlanadi). Bu — asosiy xarajat manbai, embeddingdan ancha qimmatroq.

## Keyingi qadamlar (ixtiyoriy yaxshilashlar)

- Hozir hujjat indekslash **sinxron** — katta hajm bo'lsa Celery/RQ + Redis orqali
  fonga chiqarish tavsiya etiladi.
- Xarid niyatini aniqlash hozircha kalit so'zlar ro'yxati orqali (`Prompt/sozlamalar`
  bo'limida sozlanadi) — kelajakda LLM-based intent classification bilan aniqroq qilish mumkin.
- Productionda `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS` to'g'ri sozlansin.
