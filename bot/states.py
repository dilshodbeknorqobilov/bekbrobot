from aiogram.fsm.state import State, StatesGroup


class TalabgorForm(StatesGroup):
    familiya = State()
    ism = State()
    otasining_ismi = State()
    telefon = State()
    photo = State()
    id_raqam = State()
