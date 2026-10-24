"""Simple in-memory rate limiting. State is lost on restart by design."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable


class SlidingWindowLimiter:
    """Allow at most `max_events` per `window` seconds for each key."""

    def __init__(
        self, max_events: int, window: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._max = max_events
        self._window = window
        self._clock = clock
        self._hits: dict[int, deque[float]] = {}

    def allow(self, key: int) -> bool:
        now = self._clock()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= self._window:
            hits.popleft()
        if len(hits) >= self._max:
            return False
        hits.append(now)
        return True


class ActionGuard:
    """Prevents duplicate concurrent actions and enforces a cooldown per user.

    Used for certificate generation so repeated button taps cannot trigger
    uncontrolled image generation.
    """

    def __init__(self, cooldown: float = 5.0, clock: Callable[[], float] = time.monotonic) -> None:
        self._cooldown = cooldown
        self._clock = clock
        self._last: dict[int, float] = {}
        self._busy: set[int] = set()

    def try_acquire(self, user_id: int) -> bool:
        if user_id in self._busy:
            return False
        now = self._clock()
        last = self._last.get(user_id)
        if last is not None and now - last < self._cooldown:
            return False
        self._busy.add(user_id)
        self._last[user_id] = now
        return True

    def release(self, user_id: int) -> None:
        self._busy.discard(user_id)
