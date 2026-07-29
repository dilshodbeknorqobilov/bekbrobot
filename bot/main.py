import asyncio
import logging
import os
import sys
from pathlib import Path

# Loyihaning bosh papkasini sys.path ga qo'shamiz — bu fayl to'g'ridan-to'g'ri
# ("python bot\\main.py") ishga tushirilganda ham "config" va "core" paketlari
# to'g'ri topilishi (va boshqa nomdosh paketlar bilan chalkashmasligi) uchun kerak.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402
from aiogram.enums import ParseMode  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402

from bot.config import BOT_TOKEN  # noqa: E402
from bot.handlers import admin_approval, pdf_search, start, talabgor  # noqa: E402

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan.")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(admin_approval.router)
    dp.include_router(talabgor.router)
    dp.include_router(pdf_search.router)

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot ishga tushdi (polling).")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
