import asyncio

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.config import Settings
from app.keyboards.inline import join_keyboard, reissue_keyboard
from app.services.certificate import render_certificate
from app.services.telegram_membership import (
    MembershipConfigError,
    MembershipUnavailableError,
    check_membership,
)
from app.utils.rate_limit import ActionGuard

router = Router(name="membership")

NOT_MEMBER_TEXT = "❌ Siz hali guruhga a’zo emassiz. Iltimos, avval guruhga qo‘shiling."
CONFIG_ERROR_TEXT = (
    "⚠️ Guruh bilan bog‘lanishda sozlama xatosi yuz berdi. "
    "Iltimos, klub administratoriga murojaat qiling."
)
UNAVAILABLE_TEXT = (
    "⚠️ Telegram bilan vaqtincha bog‘lanib bo‘lmadi. Iltimos, birozdan so‘ng qayta urinib ko‘ring."
)
BUSY_TEXT = (
    "⏳ So‘rovingiz allaqachon bajarilmoqda yoki juda tez yuborildi. "
    "Biroz kutib qayta urinib ko‘ring."
)
RESTART_TEXT = "⚠️ Ro‘yxatdan o‘tish sessiyasi tugagan. Iltimos, /start buyrug‘ini yuboring."
CERTIFICATE_CAPTION = (
    "🎉 Tabriknomangiz tayyor! Antikorrupsiya klubiga a’zo bo‘lganingiz bilan tabriklaymiz.\n\n"
    "🔒 Tabriknoma saqlanmaydi. Qayta olish uchun tugmani bosing."
)


async def verify_and_issue(
    message: Message,
    bot: Bot,
    settings: Settings,
    user_id: int,
    full_name: str,
) -> bool:
    """Re-check membership via the Telegram API, then send a freshly rendered card."""
    try:
        is_member = await check_membership(bot, settings.group_id, user_id)
    except MembershipConfigError:
        await message.answer(CONFIG_ERROR_TEXT)
        return False
    except MembershipUnavailableError:
        await message.answer(UNAVAILABLE_TEXT)
        return False

    if not is_member:
        await message.answer(NOT_MEMBER_TEXT, reply_markup=join_keyboard(settings.group_invite_url))
        return False

    # Rendering is CPU-bound; keep the event loop responsive.
    png = await asyncio.to_thread(render_certificate, full_name, settings.club_logo_path)
    await message.answer_photo(
        BufferedInputFile(png, filename="tabriknoma.png"),
        caption=CERTIFICATE_CAPTION,
        reply_markup=reissue_keyboard(),
    )
    return True


async def _handle_certificate_request(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    action_guard: ActionGuard,
) -> None:
    user_id = callback.from_user.id
    if callback.message is None:
        await callback.answer()
        return
    if not action_guard.try_acquire(user_id):
        await callback.answer(BUSY_TEXT, show_alert=False)
        return

    await callback.answer()
    try:
        data = await state.get_data()
        full_name = data.get("full_name")
        if not full_name:
            await callback.message.answer(RESTART_TEXT)
            return
        await verify_and_issue(callback.message, bot, settings, user_id, full_name)
    finally:
        action_guard.release(user_id)


@router.callback_query(F.data == "grp:check")
async def check_membership_callback(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    action_guard: ActionGuard,
) -> None:
    await _handle_certificate_request(callback, state, bot, settings, action_guard)


@router.callback_query(F.data == "cert:reissue")
async def reissue_callback(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    action_guard: ActionGuard,
) -> None:
    # Membership is re-checked inside verify_and_issue before any reissue.
    await _handle_certificate_request(callback, state, bot, settings, action_guard)
