import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from django.db import close_old_connections

logger = logging.getLogger(__name__)


class DjangoDbConnectionMiddleware(BaseMiddleware):
    """Har bir Telegram so'rovi (update) oldidan va keyin Django DB ulanishini tekshirib,
    eskirgan yoki uzilib qolgan ulanishlarni tozalaydi.

    Bu PostgreSQL dagi "server closed the connection unexpectedly" va
    "SSL SYSCALL error: EOF detected" kabi xatolarni butunlay oldini oladi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        close_old_connections()
        try:
            return await handler(event, data)
        finally:
            close_old_connections()
