"""Bot uchun sozlamalar — Django settings orqali .env dan o'qiladi.

Bu modul import qilinishidan oldin bot/main.py ichida django.setup()
chaqirilgan bo'lishi shart.
"""
from django.conf import settings

BOT_TOKEN: str = settings.BOT_TOKEN
ADMIN_IDS: list[int] = settings.ADMIN_IDS
TESTPDF_DIR: str = settings.TESTPDF_DIR
MINI_APP_URL: str = getattr(settings, "MINI_APP_URL", "")
