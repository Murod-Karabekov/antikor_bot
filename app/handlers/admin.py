import html
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.config import Settings
from app.keyboards.inline import admin_keyboard
from app.services.certificate import render_certificate
from app.services.telegram_membership import bot_is_group_admin
from app.utils.rate_limit import ActionGuard

logger = logging.getLogger(__name__)

router = Router(name="admin")

SAMPLE_NAME = "Test Foydalanuvchi"
DENIED_TEXT = "⛔ Ruxsat yo‘q."


def is_admin(user_id: int | None, settings: Settings) -> bool:
    """Authorization uses numeric Telegram IDs only."""
    return user_id is not None and user_id in settings.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message, settings: Settings) -> None:
    # Non-admins get no response, so the menu's existence is not revealed.
    if not is_admin(message.from_user.id if message.from_user else None, settings):
        return
    await message.answer("🛠 <b>Admin menyu</b>", reply_markup=admin_keyboard())


async def _status_text(bot: Bot, settings: Settings) -> str:
    me = await bot.get_me()
    admin_state = await bot_is_group_admin(bot, settings.group_id)
    admin_line = {
        True: "✅ ha",
        False: "❌ yo‘q (botni guruhga administrator qiling)",
        None: "⚠️ aniqlab bo‘lmadi",
    }[admin_state]
    return (
        "📊 <b>Bot holati</b>\n\n"
        f"Bot: @{html.escape(me.username or 'noma’lum')}\n"
        "Rejim: long polling\n"
        f"Guruhda administrator: {admin_line}"
    )


async def _group_text(bot: Bot, settings: Settings) -> str:
    try:
        chat = await bot.get_chat(settings.group_id)
        count = await bot.get_chat_member_count(settings.group_id)
    except TelegramAPIError:
        return "⚠️ Guruh ma’lumotini olib bo‘lmadi. GROUP_ID va bot huquqlarini tekshiring."
    return (
        "👥 <b>Guruh ma’lumoti</b>\n\n"
        f"Nomi: {html.escape(chat.title or '-')}\n"
        f"Turi: {html.escape(str(chat.type))}\n"
        f"A’zolar soni: {count}\n"
        f"GROUP_ID: <code>{settings.group_id}</code>"
    )


@router.callback_query(F.data.startswith("adm:"))
async def admin_callbacks(
    callback: CallbackQuery,
    bot: Bot,
    settings: Settings,
    action_guard: ActionGuard,
) -> None:
    # Authorization is checked on every callback, not only on the menu command.
    if not is_admin(callback.from_user.id, settings):
        await callback.answer(DENIED_TEXT, show_alert=True)
        return
    await callback.answer()
    if callback.message is None:
        return

    action = callback.data
    if action == "adm:status":
        await callback.message.answer(await _status_text(bot, settings))
    elif action == "adm:group":
        await callback.message.answer(await _group_text(bot, settings))
    elif action == "adm:test_cert":
        user_id = callback.from_user.id
        if not action_guard.try_acquire(user_id):
            return
        try:
            png = render_certificate(SAMPLE_NAME, settings.club_logo_path)
            await callback.message.answer_photo(
                BufferedInputFile(png, filename="sinov_tabriknoma.png"),
                caption="🧪 Sinov tabriknomasi (namunaviy ism).",
            )
        finally:
            action_guard.release(user_id)
