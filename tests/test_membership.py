import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError
from aiogram.methods import GetChatMember

from app.services.telegram_membership import (
    MembershipConfigError,
    MembershipUnavailableError,
    check_membership,
    is_active_member,
)

GROUP_ID = -1001234567890
USER_ID = 42


def member(status, is_member=None):
    return SimpleNamespace(status=status, is_member=is_member)


@pytest.mark.parametrize(
    "member_obj, expected",
    [
        (member("creator"), True),
        (member("administrator"), True),
        (member("member"), True),
        (member("restricted", is_member=True), True),
        (member("restricted", is_member=False), False),
        (member("left"), False),
        (member("kicked"), False),
        (member("unknown-status"), False),
    ],
)
def test_membership_status_matrix(member_obj, expected):
    assert is_active_member(member_obj) is expected


def _bot_returning(result=None, error=None):
    bot = AsyncMock()
    if error is not None:
        bot.get_chat_member.side_effect = error
    else:
        bot.get_chat_member.return_value = result
    return bot


def _method():
    return GetChatMember(chat_id=GROUP_ID, user_id=USER_ID)


def test_check_membership_uses_real_api_call_arguments():
    bot = _bot_returning(member("member"))
    assert asyncio.run(check_membership(bot, GROUP_ID, USER_ID)) is True
    bot.get_chat_member.assert_awaited_once_with(chat_id=GROUP_ID, user_id=USER_ID)


def test_non_member_is_rejected():
    bot = _bot_returning(member("left"))
    assert asyncio.run(check_membership(bot, GROUP_ID, USER_ID)) is False


def test_bad_request_is_config_error():
    bot = _bot_returning(error=TelegramBadRequest(method=_method(), message="chat not found"))
    with pytest.raises(MembershipConfigError):
        asyncio.run(check_membership(bot, GROUP_ID, USER_ID))


def test_forbidden_is_config_error():
    bot = _bot_returning(error=TelegramForbiddenError(method=_method(), message="bot kicked"))
    with pytest.raises(MembershipConfigError):
        asyncio.run(check_membership(bot, GROUP_ID, USER_ID))


def test_network_error_is_unavailable_not_rejection():
    bot = _bot_returning(error=TelegramNetworkError(method=_method(), message="timeout"))
    with pytest.raises(MembershipUnavailableError):
        asyncio.run(check_membership(bot, GROUP_ID, USER_ID))
