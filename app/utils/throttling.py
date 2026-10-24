"""Middleware that silently drops updates from users who exceed the message rate."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.utils.rate_limit import SlidingWindowLimiter


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, limiter: SlidingWindowLimiter) -> None:
        self._limiter = limiter

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and not self._limiter.allow(user.id):
            return None
        return await handler(event, data)
