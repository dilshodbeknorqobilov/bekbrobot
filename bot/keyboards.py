from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

NAZORATCHI_BTN = "🧑‍💼 Nazoratchi bo'lish"
TALABGOR_BTN = "➕ Talabgor qo'shish"
CANCEL_BTN = "❌ Bekor qilish"


def guest_menu() -> ReplyKeyboardMarkup:
    """Hali Nazoratchi bo'lmagan / rad etilgan foydalanuvchi menyusi."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=NAZORATCHI_BTN)]],
        resize_keyboard=True,
    )


def nazoratchi_menu() -> ReplyKeyboardMarkup:
    """Tasdiqlangan Nazoratchi menyusi."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=TALABGOR_BTN)]],
        resize_keyboard=True,
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
