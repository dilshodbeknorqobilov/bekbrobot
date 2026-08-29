import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.http import HttpRequest

logger = logging.getLogger(__name__)


def verify_telegram_init_data(
    init_data_str: str,
    bot_token: Optional[str] = None,
    max_age_seconds: int = 86400 * 7,  # 7 kunlik amal qilish muddati
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """Telegram WebApp initData satrini HMAC-SHA256 yordamida tekshiradi.

    Telegram rasmiy hujjatlariga mos:
    1. initData parse qilinadi, 'hash' ajratib olinadi.
    2. Qolgan juftliklar alifbo bo'yicha saralanib, '\\n' bilan birlashtiriladi.
    3. secret_key = HMAC_SHA256("WebAppData", bot_token)
    4. hisoblangan hash = HMAC_SHA256(secret_key, data_check_string).hexdigest()
    5. Ikkala hash solishtiriladi va 'user' ma'lumotlari qaytariladi.
    """
    if not init_data_str:
        return False, None, "initData berilmagan."

    token = bot_token or getattr(settings, "BOT_TOKEN", "")
    if not token:
        return False, None, "BOT_TOKEN topilmadi."

    try:
        parsed = dict(urllib.parse.parse_qsl(init_data_str, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return False, None, "initData ichida 'hash' parametri yo'q."

        # auth_date tekshiruvi
        auth_date_str = parsed.get("auth_date")
        if auth_date_str:
            auth_date = int(auth_date_str)
            if time.time() - auth_date > max_age_seconds:
                return False, None, "Sessiya muddati o'tgan (auth_date expired)."

        # Saralangan data-check-string tayyorlash
        data_check_list = [f"{k}={v}" for k, v in sorted(parsed.items())]
        data_check_string = "\n".join(data_check_list)

        # HMAC hisoblash
        secret_key = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return False, None, "Imzo (hash) tasdiqlanmadi. Soxta so'rov."

        user_raw = parsed.get("user")
        user_data = json.loads(user_raw) if user_raw else {}
        return True, user_data, None
    except Exception as exc:
        logger.warning("Telegram initData tekshirishda xatolik: %s", exc)
        return False, None, f"Tekshirish xatosi: {str(exc)}"


def get_telegram_user_from_request(
    request: HttpRequest,
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """HTTP so'rovdan (Header, POST yoki GET) initData ni oladi va tekshiradi."""
    init_data = ""

    # 1. Authorization header: "Bearer <init_data>" yoki "tma <init_data>"
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        init_data = auth_header[7:].strip()
    elif auth_header.startswith("tma "):
        init_data = auth_header[4:].strip()

    # 2. Maxsus header: X-Telegram-Init-Data
    if not init_data:
        init_data = request.headers.get("X-Telegram-Init-Data", "").strip()

    # 3. POST / GET parametri
    if not init_data:
        init_data = request.POST.get("init_data") or request.GET.get("init_data") or ""

    return verify_telegram_init_data(init_data)
