"""Handler-level tests with mocked Telegram objects and in-memory FSM storage."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import GetChatMember

from app.config import Settings
from app.handlers import admin, membership, registration, start
from app.keyboards.inline import admin_keyboard
from app.states.registration import RegistrationStates
from app.utils.rate_limit import ActionGuard

USER_ID = 42
GROUP_ID = -1001234567890
SETTINGS = Settings(
    bot_token="123:TEST",
    group_id=GROUP_ID,
    group_invite_url="https://t.me/example_group",
    admin_ids=frozenset({USER_ID}),
)


def make_ctx(storage: MemoryStorage | None = None) -> FSMContext:
    storage = storage or MemoryStorage()
    return FSMContext(storage=storage, key=StorageKey(bot_id=1, chat_id=USER_ID, user_id=USER_ID))


def make_message(text: str | None = None, user_id: int = USER_ID) -> MagicMock:
    msg = MagicMock()
    msg.text = text
    msg.from_user = SimpleNamespace(id=user_id)
    msg.answer = AsyncMock()
    msg.answer_photo = AsyncMock()
    return msg


def make_callback(data: str, user_id: int = USER_ID) -> MagicMock:
    cb = MagicMock()
    cb.data = data
    cb.from_user = SimpleNamespace(id=user_id)
    cb.answer = AsyncMock()
    cb.message = make_message()
    return cb


def sent_texts(msg: AsyncMock) -> list[str]:
    return [c.args[0] for c in msg.answer.await_args_list if c.args]


def run_registration(ctx: FSMContext, first: str, last: str) -> None:
    async def flow():
        await registration.begin_registration(make_callback("reg:begin"), ctx)
        await registration.first_name_entered(make_message(first), ctx)
        await registration.last_name_entered(make_message(last), ctx)
        await registration.confirm_registration(make_callback("reg:confirm"), ctx, SETTINGS)

    asyncio.run(flow())


# --- /start workflow -------------------------------------------------------


def test_start_shows_welcome_with_begin_button_and_clears_state():
    ctx = make_ctx()
    msg = make_message("/start")
    asyncio.run(ctx.set_state(RegistrationStates.last_name))
    asyncio.run(start.cmd_start(msg, ctx))
    assert "Assalomu alaykum" in msg.answer.await_args.args[0]
    markup = msg.answer.await_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].text == "📝 Boshlash"
    assert asyncio.run(ctx.get_state()) is None


# --- name validation and confirmation ------------------------------------


def test_invalid_first_name_keeps_user_in_first_name_state():
    ctx = make_ctx()
    msg = make_message("Ali123")
    asyncio.run(ctx.set_state(RegistrationStates.first_name))
    asyncio.run(registration.first_name_entered(msg, ctx))
    assert asyncio.run(ctx.get_state()) == RegistrationStates.first_name.state
    assert sent_texts(msg)[0].startswith("❌")


def test_full_registration_stores_full_name_and_moves_to_join_step():
    ctx = make_ctx()
    run_registration(ctx, "Ўлмас", "Ғаффоров")
    data = asyncio.run(ctx.get_data())
    assert data["full_name"] == "Ўлмас Ғаффоров"
    assert asyncio.run(ctx.get_state()) == RegistrationStates.joined.state


def test_correction_restarts_name_entry():
    ctx = make_ctx()

    async def flow():
        await registration.begin_registration(make_callback("reg:begin"), ctx)
        await registration.first_name_entered(make_message("Ali"), ctx)
        await registration.last_name_entered(make_message("Vali"), ctx)
        await registration.redo_registration(make_callback("reg:redo"), ctx)

    asyncio.run(flow())
    assert asyncio.run(ctx.get_state()) == RegistrationStates.first_name.state


def test_summary_escapes_html():
    text = registration._summary("<i>Ali</i>", "Vali")
    assert "&lt;i&gt;Ali&lt;/i&gt;" in text


# --- membership and certificate issuance ----------------------------------


def _bot(status="member", error=None):
    bot = AsyncMock()
    if error is not None:
        bot.get_chat_member.side_effect = error
    else:
        bot.get_chat_member.return_value = SimpleNamespace(status=status, is_member=None)
    return bot


def test_member_receives_png_card():
    msg = make_message()
    sent = asyncio.run(
        membership.verify_and_issue(msg, _bot("member"), SETTINGS, USER_ID, "Ali Vali")
    )
    assert sent is True
    kwargs = msg.answer_photo.await_args.kwargs
    assert "Tabriknoma" in kwargs["caption"] or "tabriknoma" in kwargs["caption"].lower()
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == "cert:reissue"


def test_non_member_is_rejected_with_join_prompt():
    msg = make_message()
    sent = asyncio.run(
        membership.verify_and_issue(msg, _bot("left"), SETTINGS, USER_ID, "Ali Vali")
    )
    assert sent is False
    assert sent_texts(msg)[0] == membership.NOT_MEMBER_TEXT
    msg.answer_photo.assert_not_awaited()


def test_api_config_error_is_reported_separately():
    method = GetChatMember(chat_id=GROUP_ID, user_id=USER_ID)
    msg = make_message()
    err = TelegramBadRequest(method=method, message="chat not found")
    asyncio.run(membership.verify_and_issue(msg, _bot(error=err), SETTINGS, USER_ID, "Ali"))
    assert sent_texts(msg)[0] == membership.CONFIG_ERROR_TEXT


def test_repeated_certificate_callback_is_ignored_while_busy():
    guard = ActionGuard(cooldown=5.0)
    assert guard.try_acquire(USER_ID)  # first tap is in progress
    cb = make_callback("grp:check")
    asyncio.run(
        membership._handle_certificate_request(cb, make_ctx(), _bot("member"), SETTINGS, guard)
    )
    cb.answer.assert_awaited_once()
    assert cb.answer.await_args.args[0] == membership.BUSY_TEXT
    cb.message.answer_photo.assert_not_awaited()


def test_reissue_without_stored_name_asks_to_restart():
    cb = make_callback("cert:reissue")
    asyncio.run(
        membership._handle_certificate_request(
            cb, make_ctx(), _bot("member"), SETTINGS, ActionGuard()
        )
    )
    assert sent_texts(cb.message)[0] == membership.RESTART_TEXT


def test_restart_loses_registration_state_with_new_memory_storage():
    storage = MemoryStorage()
    run_registration(make_ctx(storage), "Ali", "Vali")
    # A restarted bot gets a fresh MemoryStorage: no state, no name.
    fresh = make_ctx(MemoryStorage())
    assert asyncio.run(fresh.get_state()) is None
    assert asyncio.run(fresh.get_data()) == {}


# --- admin authorization ---------------------------------------------------


def test_non_admin_gets_no_admin_menu():
    msg = make_message(user_id=999)
    asyncio.run(admin.cmd_admin(msg, SETTINGS))
    msg.answer.assert_not_awaited()


def test_admin_gets_menu():
    msg = make_message(user_id=USER_ID)
    asyncio.run(admin.cmd_admin(msg, SETTINGS))
    assert msg.answer.await_args.kwargs["reply_markup"] == admin_keyboard()


def test_non_admin_callback_is_denied():
    cb = make_callback("adm:status", user_id=999)
    asyncio.run(admin.admin_callbacks(cb, _bot(), SETTINGS, ActionGuard()))
    assert cb.answer.await_args.kwargs.get("show_alert") is True
    cb.message.answer.assert_not_awaited()
