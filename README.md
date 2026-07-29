# Bekzodbro — aiogram 3 + Django 5.2 + PostgreSQL bot

## Loyiha haqida

Bitta Django loyihasi ichida ikkita jarayon ishlaydi va bitta PostgreSQL
bazasidan foydalanadi:

- **Django admin** — Nazoratchi va Talabgor ma'lumotlarini ko'rish/boshqarish uchun.
- **Telegram bot** (`bot/main.py`, aiogram 3, polling) — quyidagi funksiyalarni bajaradi:
  1. **Nazoratchi bo'lish** — foydalanuvchi so'rov yuboradi, admin Ha/Yo'q orqali tasdiqlaydi.
  2. **Talabgor qo'shish** — tasdiqlangan Nazoratchi Familiya, Ism, Otasining ismi,
     Telefon, Rasm va unikal ID raqamni ketma-ket kiritadi. ID band bo'lsa,
     jarayon saqlanmasdan to'xtaydi.
  3. **PDF qidirish** — istalgan foydalanuvchi 4 yoki 6 xonali ID raqam yuborsa,
     `testpdf/` papkasidan shu ID bilan boshlanuvchi PDF fayl topilib yuboriladi.

Bot Django ORM'dan to'g'ridan-to'g'ri (async metodlar orqali) foydalanadi,
alohida API kerak emas.

## Talablar

- Python 3.11+
- PostgreSQL (Windows'da mahalliy o'rnatilgan versiyangiz ishlaydi)
- Telegram bot tokeni (@BotFather)

## Windows'da mahalliy ishga tushirish

1. **Virtual environment yaratish:**

   ```powershell
   cd C:\worker\bekzodbro
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **PostgreSQL'da baza yaratish** (pgAdmin yoki psql orqali):

   ```sql
   CREATE DATABASE botdb;
   CREATE USER botuser WITH PASSWORD 'parol123';
   GRANT ALL PRIVILEGES ON DATABASE botdb TO botuser;
   ```

3. **.env faylini yaratish:**

   ```powershell
   copy .env.example .env
   ```

   `.env` faylini oching va to'ldiring:

   ```
   SECRET_KEY=har-qanday-uzun-tasodifiy-matn
   DEBUG=True
   ALLOWED_HOSTS=127.0.0.1,localhost
   DATABASE_URL=postgres://botuser:parol123@127.0.0.1:5432/botdb
   BOT_TOKEN=<BotFather'dan olingan token>
   ADMIN_IDS=<sizning Telegram ID raqamingiz>
   TESTPDF_DIR=testpdf
   ```

   O'zingizning Telegram ID raqamingizni bilish uchun Telegram'da
   **@userinfobot** ga yozing.

4. **Migratsiyalarni bajarish va admin yaratish:**

   ```powershell
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Django admin panelni ishga tushirish** (1-terminal):

   ```powershell
   venv\Scripts\activate
   python manage.py runserver
   ```

   Admin panel: http://127.0.0.1:8000/admin/

6. **Botni ishga tushirish** (2-terminal, alohida oyna):

   ```powershell
   venv\Scripts\activate
   python bot\main.py
   ```

7. **testpdf papkasiga PDF fayllar qo'yish:**

   Fayl nomi ID raqam bilan boshlanishi kerak, masalan: `123456_natija.pdf`
   yoki `1234_natija.pdf`.

## Loyiha tuzilishi

```
bekzodbro/
├── manage.py
├── config/            # Django sozlamalari (settings, urls, wsgi, asgi)
├── core/               # Nazoratchi va Talabgor modellari + admin
├── bot/
│   ├── main.py         # Bot kirish nuqtasi
│   ├── config.py       # BOT_TOKEN, ADMIN_IDS, TESTPDF_DIR
│   ├── states.py        # FSM holatlar (Talabgor qo'shish)
│   ├── keyboards.py     # Klaviaturalar
│   ├── utils.py          # ID regex, PDF qidirish
│   └── handlers/
│       ├── start.py             # /start, Nazoratchi so'rovi
│       ├── admin_approval.py     # Admin Ha/Yo'q javobi
│       ├── talabgor.py            # Talabgor qo'shish FSM
│       └── pdf_search.py           # ID bo'yicha PDF qidirish
├── testpdf/            # PDF fayllar shu yerda saqlanadi
├── requirements.txt
├── .env.example
└── DEPLOY.md            # Ubuntu serverga joylash yo'riqnomasi
```

## Production serverga joylash

Docker ishlatilmaydi. Ubuntu server uchun to'liq qo'llanma **DEPLOY.md**
faylida — PostgreSQL o'rnatish, systemd xizmatlari (bot va Django alohida),
nginx va HTTPS sozlash bosqichma-bosqich yozilgan.
