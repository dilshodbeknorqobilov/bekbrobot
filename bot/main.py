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
from bot.middlewares import DjangoDbConnectionMiddleware  # noqa: E402

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

    # PostgreSQL ulanishlarini har bir Telegram so'rovida tozalash va tiklash:
    dp.update.outer_middleware(DjangoDbConnectionMiddleware())

    dp.include_router(start.router)
    dp.include_router(admin_approval.router)
    dp.include_router(talabgor.router)
    dp.include_router(pdf_search.router)

    # Tarmoq uzilishlari paytida xavfsiz webhook o'chirish (5 marta urinish)
    for attempt in range(1, 6):
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            break
        except Exception as exc:
            logger.warning(
                "Webhookni o'chirishda xatolik (urinish %s/5): %s. 3 soniyadan so'ng qayta uriniladi...",
                attempt,
                exc,
            )
            await asyncio.sleep(3)

    try:
        logger.info("Bot ishga tushdi (polling).")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        logger.info("Bot to'xtatilmoqda, aiohttp sessiyasi yopilmoqda...")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
