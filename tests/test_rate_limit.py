from app.utils.rate_limit import ActionGuard, SlidingWindowLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_sliding_window_limits_events_per_key():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(max_events=2, window=3.0, clock=clock)
    assert limiter.allow(1) and limiter.allow(1)
    assert not limiter.allow(1)
    assert limiter.allow(2)  # other users are independent
    clock.now = 3.0
    assert limiter.allow(1)


def test_action_guard_blocks_duplicate_concurrent_callbacks():
    guard = ActionGuard(cooldown=5.0, clock=FakeClock())
    assert guard.try_acquire(7) is True
    assert guard.try_acquire(7) is False  # repeated tap while busy
    guard.release(7)
    assert guard.try_acquire(7) is False  # still inside cooldown


def test_action_guard_allows_again_after_cooldown():
    clock = FakeClock()
    guard = ActionGuard(cooldown=5.0, clock=clock)
    assert guard.try_acquire(7)
    guard.release(7)
    clock.now = 5.0
    assert guard.try_acquire(7)
