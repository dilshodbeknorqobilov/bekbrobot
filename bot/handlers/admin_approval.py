import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from django.utils import timezone

from bot.config import ADMIN_IDS
from bot.keyboards import nazoratchi_menu
from core.models import Nazoratchi

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("nazoratchi_yes:") | F.data.startswith("nazoratchi_no:"))
async def handle_approval(call: CallbackQuery, bot: Bot) -> None:
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("Sizda bu amal uchun ruxsat yo'q.", show_alert=True)
        return

    action, raw_id = call.data.split(":", maxsplit=1)
    telegram_id = int(raw_id)

    nazoratchi = await Nazoratchi.objects.filter(telegram_id=telegram_id).afirst()
    if not nazoratchi:
        await call.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return

    original_text = call.message.text or ""

    if action == "nazoratchi_yes":
        nazoratchi.status = Nazoratchi.Status.APPROVED
        nazoratchi.decided_at = timezone.now()
        await nazoratchi.asave()

        await call.message.edit_text(original_text + "\n\n✅ Tasdiqlandi")
        response_text = (
            "🎉 Tabriklaymiz! Siz Nazoratchi sifatida tasdiqlandingiz.\n"
            "Endi Talabgor qo'shishingiz mumkin."
        )
        response_markup = nazoratchi_menu()
        alert_text = "✅ Foydalanuvchi tasdiqlandi."
    else:
        nazoratchi.status = Nazoratchi.Status.REJECTED
        nazoratchi.decided_at = timezone.now()
        await nazoratchi.asave()

        await call.message.edit_text(original_text + "\n\n❌ Rad etildi")
        response_text = "Afsuski, Nazoratchilik so'rovingiz rad etildi."
        response_markup = None
        alert_text = "❌ Foydalanuvchi rad etildi."

    try:
        await bot.send_message(telegram_id, response_text, reply_markup=response_markup)
    except Exception:
        # Foydalanuvchi botni bloklagan yoki hisobi o'chirilgan bo'lishi mumkin.
        logger.warning(
            "Javobni foydalanuvchiga (%s) yuborib bo'lmadi.",
            telegram_id,
            exc_info=True,
        )
        alert_text += " (Foydalanuvchiga xabar yetkazilmadi — botni bloklagan bo'lishi mumkin.)"

    await call.answer(alert_text)
