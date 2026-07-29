from typing import Optional

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile

from bot.keyboards import CANCEL_BTN, TALABGOR_BTN, cancel_keyboard, nazoratchi_menu
from bot.states import TalabgorForm
from bot.utils import ID_PATTERN, normalize_phone
from core.models import Nazoratchi, Talabgor

router = Router()


async def _get_approved_nazoratchi(telegram_id: int) -> Optional[Nazoratchi]:
    nazoratchi = await Nazoratchi.objects.filter(telegram_id=telegram_id).afirst()
    if nazoratchi and nazoratchi.status == Nazoratchi.Status.APPROVED:
        return nazoratchi
    return None


@router.message(~StateFilter(None), F.text == CANCEL_BTN)
async def cancel_talabgor(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Jarayon bekor qilindi.", reply_markup=nazoratchi_menu())


@router.message(StateFilter(None), F.text == TALABGOR_BTN)
async def start_add_talabgor(message: Message, state: FSMContext) -> None:
    nazoratchi = await _get_approved_nazoratchi(message.from_user.id)
    if not nazoratchi:
        await message.answer("Bu funksiya faqat tasdiqlangan nazoratchilar uchun mavjud.")
        return

    await state.update_data(nazoratchi_id=nazoratchi.id)
    await state.set_state(TalabgorForm.familiya)
    await message.answer("Talabgorning familiyasini kiriting:", reply_markup=cancel_keyboard())


@router.message(TalabgorForm.familiya, F.text)
async def get_familiya(message: Message, state: FSMContext) -> None:
    await state.update_data(familiya=message.text.strip())
    await state.set_state(TalabgorForm.ism)
    await message.answer("Ismini kiriting:", reply_markup=cancel_keyboard())


@router.message(TalabgorForm.ism, F.text)
async def get_ism(message: Message, state: FSMContext) -> None:
    await state.update_data(ism=message.text.strip())
    await state.set_state(TalabgorForm.otasining_ismi)
    await message.answer("Otasining ismini kiriting:", reply_markup=cancel_keyboard())


@router.message(TalabgorForm.otasining_ismi, F.text)
async def get_otasining_ismi(message: Message, state: FSMContext) -> None:
    await state.update_data(otasining_ismi=message.text.strip())
    await state.set_state(TalabgorForm.telefon)
    await message.answer(
        "Telefon raqamini kiriting (faqat raqam, masalan: 881144101):",
        reply_markup=cancel_keyboard(),
    )


@router.message(TalabgorForm.telefon, F.contact)
async def get_telefon_contact(message: Message, state: FSMContext) -> None:
    normalized = normalize_phone(message.contact.phone_number)
    if not normalized:
        await message.answer(
            "Telefon raqam noto'g'ri formatda. Qaytadan to'g'ri formatda kiriting "
            "(faqat raqam, masalan: 881144101):",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(telefon=normalized)
    await state.set_state(TalabgorForm.photo)
    await message.answer("Talabgorning rasmini yuboring (photo shaklida):", reply_markup=cancel_keyboard())


@router.message(TalabgorForm.telefon, F.text)
async def get_telefon_text(message: Message, state: FSMContext) -> None:
    normalized = normalize_phone(message.text)
    if not normalized:
        await message.answer(
            "Telefon raqam noto'g'ri formatda. Qaytadan to'g'ri formatda kiriting "
            "(faqat raqam, masalan: 881144101):",
            reply_markup=cancel_keyboard(),
        )
        return

    await state.update_data(telefon=normalized)
    await state.set_state(TalabgorForm.photo)
    await message.answer("Talabgorning rasmini yuboring (photo shaklida):", reply_markup=cancel_keyboard())


@router.message(TalabgorForm.photo, F.photo)
async def get_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    buffer = await bot.download_file(file.file_path)
    await state.update_data(
        photo_bytes=buffer.read(),
        photo_name=f"{photo.file_unique_id}.jpg",
        photo_file_id=photo.file_id,
    )
    await state.set_state(TalabgorForm.id_raqam)
    await message.answer("ID raqamni kiriting (4 yoki 6 xonali):", reply_markup=cancel_keyboard())


@router.message(TalabgorForm.photo)
async def get_photo_invalid(message: Message) -> None:
    await message.answer("Iltimos, rasmni photo (surat) shaklida yuboring.", reply_markup=cancel_keyboard())


@router.message(TalabgorForm.id_raqam, F.text)
async def get_id_raqam(message: Message, state: FSMContext) -> None:
    id_raqam = message.text.strip()

    if not ID_PATTERN.match(id_raqam):
        await message.answer(
            "ID raqam 4 yoki 6 xonali son bo'lishi kerak. Qaytadan to'g'ri raqamni kiriting:",
            reply_markup=cancel_keyboard(),
        )
        return

    exists = await Talabgor.objects.filter(id_raqam=id_raqam).aexists()
    if exists:
        await message.answer(
            "❌ Bu ID raqam allaqachon bazada mavjud. Qaytadan to'g'ri (band bo'lmagan) "
            "ID raqamni kiriting:",
            reply_markup=cancel_keyboard(),
        )
        return

    data = await state.get_data()

    talabgor = Talabgor(
        familiya=data["familiya"],
        ism=data["ism"],
        otasining_ismi=data["otasining_ismi"],
        telefon=data["telefon"],
        id_raqam=id_raqam,
        nazoratchi_id=data["nazoratchi_id"],
    )
    await sync_to_async(talabgor.photo.save)(
        data["photo_name"], ContentFile(data["photo_bytes"]), save=False
    )
    await talabgor.asave()

    await message.answer_photo(
        data["photo_file_id"],
        caption=(
            "✅ Ma'lumot muvaffaqiyatli saqlandi!\n\n"
            f"Familiya: {talabgor.familiya}\n"
            f"Ism: {talabgor.ism}\n"
            f"Otasining ismi: {talabgor.otasining_ismi}\n"
            f"Telefon: {talabgor.telefon}\n"
            f"ID raqam: {talabgor.id_raqam}\n\n"
            "Yana yangi talabgor qo'shishingiz mumkin."
        ),
        reply_markup=nazoratchi_menu(),
    )
    await state.clear()


@router.message(TalabgorForm.id_raqam)
async def get_id_raqam_invalid(message: Message) -> None:
    await message.answer("ID raqamni matn (son) sifatida yuboring.", reply_markup=cancel_keyboard())


@router.message(
    StateFilter(
        TalabgorForm.familiya,
        TalabgorForm.ism,
        TalabgorForm.otasining_ismi,
        TalabgorForm.telefon,
    )
)
async def invalid_step_input(message: Message) -> None:
    await message.answer("Iltimos, matn ko'rinishida javob yuboring.", reply_markup=cancel_keyboard())
