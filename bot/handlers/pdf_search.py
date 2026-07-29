from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import FSInputFile, Message

from bot.config import TESTPDF_DIR
from bot.utils import ID_REGEX, find_pdf

router = Router()


@router.message(StateFilter(None), F.text.regexp(ID_REGEX))
async def search_pdf(message: Message) -> None:
    id_raqam = message.text.strip()
    pdf_path = find_pdf(TESTPDF_DIR, id_raqam)

    if pdf_path:
        await message.answer_document(FSInputFile(pdf_path))
    else:
        await message.answer(f"'{id_raqam}' ID raqam bo'yicha PDF topilmadi.")
