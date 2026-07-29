import logging

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.config import ADMIN_IDS
from bot.keyboards import NAZORATCHI_BTN, approval_keyboard, guest_menu, nazoratchi_menu
from core.models import Nazoratchi

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    nazoratchi = await Nazoratchi.objects.filter(telegram_id=message.from_user.id).afirst()

    if nazoratchi and nazoratchi.status == Nazoratchi.Status.APPROVED:
        await message.answer(
            "Xush kelibsiz! Talabgor qo'shishingiz mumkin.",
            reply_markup=nazoratchi_menu(),
        )
        return

    if nazoratchi and nazoratchi.status == Nazoratchi.Status.PENDING:
        await message.answer("So'rovingiz hali ko'rib chiqilmoqda. Iltimos, kuting.")
        return

    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "Nazoratchi bo'lish uchun quyidagi tugmani bosing.\n"
        "Test natijasini bilish uchun esa 4 yoki 6 xonali ID raqamni shunchaki yozib yuboring.",
        reply_markup=guest_menu(),
    )


@router.message(F.text == NAZORATCHI_BTN)
async def request_nazoratchi(message: Message, bot: Bot) -> None:
    telegram_id = message.from_user.id

    nazoratchi, _ = await Nazoratchi.objects.aupdate_or_create(
        telegram_id=telegram_id,
        defaults={
            "username": message.from_user.username or "",
            "full_name": message.from_user.full_name,
        },
    )

    if nazoratchi.status == Nazoratchi.Status.APPROVED:
        await message.answer("Siz allaqachon nazoratchisiz.", reply_markup=nazoratchi_menu())
        return

    if nazoratchi.status == Nazoratchi.Status.PENDING:
        await message.answer("So'rovingiz allaqachon yuborilgan. Javobni kuting.")
        return

    nazoratchi.status = Nazoratchi.Status.PENDING
    nazoratchi.decided_at = None
    await nazoratchi.asave()

    await message.answer("So'rovingiz adminga yuborildi. Javobni kuting.")

    if not ADMIN_IDS:
        return

    text = (
        "🆕 Yangi Nazoratchi so'rovi:\n"
        f"Ism: {nazoratchi.full_name}\n"
        f"Username: @{nazoratchi.username or '-'}\n"
        f"Telegram ID: {telegram_id}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text, reply_markup=approval_keyboard(telegram_id))
        except Exception:
            # Admin botga hali /start bosmagan yoki uni bloklagan bo'lishi mumkin.
            logger.warning(
                "Nazoratchi so'rovini adminga (%s) yuborib bo'lmadi. "
                "Admin botga /start bosganini tekshiring.",
                admin_id,
                exc_info=True,
            )
            continue
