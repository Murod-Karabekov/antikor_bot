import html

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Settings
from app.keyboards.inline import confirm_keyboard, join_keyboard
from app.states.registration import RegistrationStates
from app.utils.validation import NameValidationError, validate_name

router = Router(name="registration")

ASK_FIRST_NAME = "👤 Ismingizni kiriting:"
ASK_LAST_NAME = "👤 Familiyangizni kiriting:"
RESTART_HINT = "⚠️ Ro‘yxatdan o‘tish sessiyasi tugagan. Iltimos, /start buyrug‘ini yuboring."
JOIN_TEXT = "👥 Endi Antikorrupsiya klubining rasmiy Telegram guruhiga qo‘shiling."


def _summary(first: str, last: str) -> str:
    return (
        "📋 Ma’lumotlaringiz:\n\n"
        f"Ism: {html.escape(first)}\n"
        f"Familiya: {html.escape(last)}\n\n"
        "Ma’lumotlaringiz to‘g‘rimi?"
    )


@router.callback_query(F.data == "reg:begin")
async def begin_registration(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(RegistrationStates.first_name)
    if callback.message:
        await callback.message.answer(ASK_FIRST_NAME)


@router.message(RegistrationStates.first_name, F.text)
async def first_name_entered(message: Message, state: FSMContext) -> None:
    try:
        first = validate_name(message.text)
    except NameValidationError as exc:
        await message.answer(f"❌ {exc}")
        return
    await state.update_data(first_name=first)
    await state.set_state(RegistrationStates.last_name)
    await message.answer(ASK_LAST_NAME)


@router.message(RegistrationStates.first_name)
async def first_name_not_text(message: Message) -> None:
    await message.answer("❌ Iltimos, ismingizni matn ko‘rinishida kiriting.")


@router.message(RegistrationStates.last_name, F.text)
async def last_name_entered(message: Message, state: FSMContext) -> None:
    try:
        last = validate_name(message.text)
    except NameValidationError as exc:
        await message.answer(f"❌ {exc}")
        return
    data = await state.get_data()
    await state.update_data(last_name=last)
    await state.set_state(RegistrationStates.confirm)
    await message.answer(
        _summary(data.get("first_name", ""), last), reply_markup=confirm_keyboard()
    )


@router.message(RegistrationStates.last_name)
async def last_name_not_text(message: Message) -> None:
    await message.answer("❌ Iltimos, familiyangizni matn ko‘rinishida kiriting.")


@router.callback_query(F.data == "reg:confirm", RegistrationStates.confirm)
async def confirm_registration(
    callback: CallbackQuery, state: FSMContext, settings: Settings
) -> None:
    await callback.answer()
    data = await state.get_data()
    first, last = data.get("first_name"), data.get("last_name")
    if not first or not last:
        await state.clear()
        if callback.message:
            await callback.message.answer(RESTART_HINT)
        return

    # Only the combined full name is kept in temporary (memory) state.
    await state.update_data(first_name=None, last_name=None, full_name=f"{first} {last}")
    await state.set_state(RegistrationStates.joined)
    if callback.message:
        await callback.message.answer(
            JOIN_TEXT, reply_markup=join_keyboard(settings.group_invite_url)
        )


@router.callback_query(F.data == "reg:redo")
async def redo_registration(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(RegistrationStates.first_name)
    if callback.message:
        await callback.message.answer(ASK_FIRST_NAME)


@router.callback_query(F.data.startswith("reg:"))
async def stale_registration_callback(callback: CallbackQuery) -> None:
    # Button from an earlier session (e.g. before a restart) or a duplicate tap.
    await callback.answer()
    if callback.message:
        await callback.message.answer(RESTART_HINT)
