# Ubuntu serverga joylash (Docker'siz)

Bu yo'riqnoma toza Ubuntu 22.04/24.04 serverda loyihani ishga tushirish uchun.
Ikkita alohida jarayon ishlaydi: Django (gunicorn orqali, admin panel uchun) va
Telegram bot (`bot/main.py`, uzluksiz polling jarayoni). Ikkalasi ham bitta
PostgreSQL bazasidan foydalanadi.

## 1. Tizimni tayyorlash

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib nginx git
```

## 2. PostgreSQL bazasini yaratish

```bash
sudo -u postgres psql
```

psql ichida:

```sql
CREATE DATABASE botdb;
CREATE USER botuser WITH PASSWORD 'kuchli-parol';
ALTER ROLE botuser SET client_encoding TO 'utf8';
ALTER ROLE botuser SET timezone TO 'Asia/Tashkent';
GRANT ALL PRIVILEGES ON DATABASE botdb TO botuser;
\q
```

## 3. Loyihani serverga joylashtirish

```bash
sudo mkdir -p /opt/bekzodbro
sudo chown $USER:$USER /opt/bekzodbro
git clone https://github.com/dilshodbeknorqobilov/bekbrobot.git /opt/bekzodbro
cd /opt/bekzodbro

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> Repozitoriy **private** bo'lsa, `git clone` so'ragan joyda GitHub username va
> Personal Access Token (parol o'rniga) so'raladi. Yoki serverda SSH kalit
> sozlab, `git clone git@github.com:dilshodbeknorqobilov/bekbrobot.git` dan
> foydalaning.

## 4. .env faylini sozlash

```bash
cp .env.example .env
nano .env
```

`.env` ichida quyidagilarni to'ldiring:

- `SECRET_KEY` — tasodifiy uzun matn (masalan: `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
- `DEBUG=False`
- `ALLOWED_HOSTS` — domen yoki server IP manzili
- `DATABASE_URL=postgres://botuser:kuchli-parol@127.0.0.1:5432/botdb`
- `BOT_TOKEN` — @BotFather'dan olingan token
- `ADMIN_IDS` — admin(lar)ning Telegram ID raqami(lari), vergul bilan
- `TESTPDF_DIR` — masalan `/opt/bekzodbro/testpdf` (PDF fayllar shu papkaga joylanadi)

## 5. Migratsiya va statik fayllar

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

## 6. Bot uchun systemd xizmati

Tayyor fayl repoda: `deploy/bekzodbro-bot.service`. Uni to'g'ridan-to'g'ri
nusxalash kifoya:

```bash
sudo cp /opt/bekzodbro/deploy/bekzodbro-bot.service /etc/systemd/system/bekzodbro-bot.service
```

Fayl mazmuni (agar qo'lda tahrirlamoqchi bo'lsangiz — `sudo nano /etc/systemd/system/bekzodbro-bot.service`):

```ini
[Unit]
Description=Bekzodbro Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/bekzodbro
EnvironmentFile=/opt/bekzodbro/.env
ExecStart=/opt/bekzodbro/venv/bin/python /opt/bekzodbro/bot/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 7. Django admin uchun gunicorn systemd xizmati

Django admin **8090** portda ishga tushadi. `0.0.0.0:8090` — bu server tashqi
IP manzili orqali (masalan `http://SERVER_IP:8090/admin/`) to'g'ridan-to'g'ri
ulanish imkonini beradi, nginx shart emas.

Tayyor fayl repoda: `deploy/bekzodbro-web.service`:

```bash
sudo cp /opt/bekzodbro/deploy/bekzodbro-web.service /etc/systemd/system/bekzodbro-web.service
```

Fayl mazmuni:

```ini
[Unit]
Description=Bekzodbro Django (gunicorn)
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/bekzodbro
EnvironmentFile=/opt/bekzodbro/.env
ExecStart=/opt/bekzodbro/venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8090 --workers 3
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ruxsatlarni sozlang va xizmatlarni ishga tushiring:

```bash
sudo chown -R www-data:www-data /opt/bekzodbro
sudo systemctl daemon-reload
sudo systemctl enable --now bekzodbro-bot bekzodbro-web
sudo systemctl status bekzodbro-bot bekzodbro-web
```

`.env` faylida `ALLOWED_HOSTS` ga server IP manzilini (yoki domenni) qo'shishni
unutmang, aks holda Django `Bad Request (400)` qaytaradi:

```
ALLOWED_HOSTS=SERVER_IP,your-domain.com
```

Endi `http://SERVER_IP:8090/admin/` manzilidan admin panelga kirish mumkin
(pastdagi 9-bandda 8090 portni firewall'da ochish kerak).

## 8. Nginx (ixtiyoriy — domen va HTTPS uchun)

Agar keyinchalik domen ulab, standart 80/443 portlar orqali (HTTPS bilan)
ishlatmoqchi bo'lsangiz, nginx'ni 8090-portga proxy qilib sozlang. Tayyor fayl
repoda: `deploy/nginx/bekzodbro.conf`.

```bash
sudo cp /opt/bekzodbro/deploy/nginx/bekzodbro.conf /etc/nginx/sites-available/bekzodbro
sudo nano /etc/nginx/sites-available/bekzodbro   # your-domain.com ni o'z domeningizga almashtiring
```

Fayl mazmuni:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /static/ {
        alias /opt/bekzodbro/staticfiles/;
    }

    location /media/ {
        alias /opt/bekzodbro/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/bekzodbro /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

HTTPS uchun (tavsiya etiladi):

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

> Eslatma: agar nginx orqali (domen bilan) ishlatsangiz, xavfsizlik uchun
> gunicorn'ni faqat ichki tarmoqqa ochish tavsiya etiladi — yuqoridagi
> `--bind 0.0.0.0:8090` ni `--bind 127.0.0.1:8090` ga o'zgartiring va 9-banddagi
> `8090/tcp` qoidasini ufw'dan olib tashlang (chunki tashqi kirish endi faqat
> nginx orqali, 80/443 portda bo'ladi).

## 9. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 8090/tcp
sudo ufw enable
```

Agar nginx ham ishlatilsa (8-band), qo'shimcha:

```bash
sudo ufw allow 'Nginx Full'
```

## 10. Loglarni kuzatish

```bash
sudo journalctl -u bekzodbro-bot -f
sudo journalctl -u bekzodbro-web -f
```

## 11. Yangilash (kod o'zgarganda)

```bash
cd /opt/bekzodbro
source venv/bin/activate
git pull   # yoki fayllarni qayta nusxalang
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart bekzodbro-bot bekzodbro-web
```

## PDF fayllar haqida eslatma

`testpdf` papkasiga `123456_biror-nom.pdf` yoki `1234_biror-nom.pdf` kabi
4 yoki 6 xonali ID bilan boshlanuvchi nomda PDF fayllar joylang. Foydalanuvchi
botga shu ID raqamni yuborganda mos fayl avtomatik yuboriladi.
