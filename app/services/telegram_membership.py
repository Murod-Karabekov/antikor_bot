"""Group membership checks through the real Telegram Bot API."""

from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError

logger = logging.getLogger(__name__)

ACCEPTED_STATUSES = {
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.MEMBER,
}


class MembershipConfigError(RuntimeError):
    """Group is unreachable for the bot: wrong GROUP_ID, bot not in group or not admin."""


class MembershipUnavailableError(RuntimeError):
    """Temporary Telegram API failure; the user may retry."""


def is_active_member(member: Any) -> bool:
    """Decide membership from a ChatMember object."""
    status = member.status
    if status in ACCEPTED_STATUSES:
        return True
    if status == ChatMemberStatus.RESTRICTED:
        return bool(getattr(member, "is_member", False))
    # left, kicked and anything unknown are rejected
    return False


async def check_membership(bot: Bot, group_id: int, user_id: int) -> bool:
    """Return True when the user is an active member of the group."""
    try:
        member = await bot.get_chat_member(chat_id=group_id, user_id=user_id)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.error("Group membership check misconfigured: %s", type(exc).__name__)
        raise MembershipConfigError from exc
    except TelegramAPIError as exc:
        logger.warning("Telegram API error during membership check: %s", type(exc).__name__)
        raise MembershipUnavailableError from exc
    return is_active_member(member)


async def bot_is_group_admin(bot: Bot, group_id: int) -> bool | None:
    """Return whether the bot is an administrator of the group (None if unknown)."""
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=group_id, user_id=me.id)
    except TelegramAPIError:
        return None
    return member.status == ChatMemberStatus.ADMINISTRATOR
