from typing import Optional

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from bot.config import MINI_APP_URL

NAZORATCHI_BTN = "🧑‍💼 Nazoratchi bo'lish"
TALABGOR_BTN = "➕ Talabgor qo'shish"
CANCEL_BTN = "❌ Bekor qilish"
MINIAPP_BTN = "📱 Mini ilovani ochish"


def guest_menu() -> ReplyKeyboardMarkup:
    """Hali Nazoratchi bo'lmagan / rad etilgan foydalanuvchi menyusi."""
    buttons = []
    if MINI_APP_URL:
        buttons.append([KeyboardButton(text=MINIAPP_BTN, web_app=WebAppInfo(url=MINI_APP_URL))])
    buttons.append([KeyboardButton(text=NAZORATCHI_BTN)])
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
    )


def nazoratchi_menu() -> ReplyKeyboardMarkup:
    """Tasdiqlangan Nazoratchi menyusi."""
    buttons = []
    if MINI_APP_URL:
        buttons.append([KeyboardButton(text=MINIAPP_BTN, web_app=WebAppInfo(url=MINI_APP_URL))])
    buttons.append([KeyboardButton(text=TALABGOR_BTN)])
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
    )


def miniapp_inline_keyboard() -> Optional[InlineKeyboardMarkup]:
    """Mini Appni ochish uchun inline klaviatura."""
    if not MINI_APP_URL:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 Mini Ilovani ochish", web_app=WebAppInfo(url=MINI_APP_URL))]
        ]
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Talabgor qo'shish jarayonida ko'rsatiladigan Bekor qilish klaviaturasi."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_BTN)]],
        resize_keyboard=True,
    )


def approval_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Adminga yuboriladigan Ha/Yo'q inline klaviaturasi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data=f"nazoratchi_yes:{telegram_id}"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=f"nazoratchi_no:{telegram_id}"),
            ]
        ]
    )
