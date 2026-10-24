"""Entry point: Telegram long polling, graceful shutdown on SIGINT/SIGTERM."""

from __future__ import annotations

import asyncio
import logging
import signal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import ConfigError, Settings, load_settings
from app.handlers import admin, membership, registration, start
from app.utils.rate_limit import ActionGuard, SlidingWindowLimiter
from app.utils.throttling import ThrottleMiddleware

# Never log user-entered names: handlers only log event types and error classes.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("antikorrupsiya-bot")


def build_dispatcher(settings: Settings) -> Dispatcher:
    # MemoryStorage: registration progress is intentionally temporary (no database).
    dp = Dispatcher(storage=MemoryStorage())
    dp["settings"] = settings
    dp["action_guard"] = ActionGuard(cooldown=5.0)

    dp.message.middleware(ThrottleMiddleware(SlidingWindowLimiter(max_events=5, window=3.0)))
    dp.callback_query.middleware(ThrottleMiddleware(SlidingWindowLimiter(max_events=8, window=3.0)))

    dp.include_routers(start.router, registration.router, membership.router, admin.router)
    return dp


async def run() -> None:
    settings = load_settings()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher(settings)

    polling = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, polling.cancel)

    logger.info("Bot polling started")
    try:
        await polling
    except asyncio.CancelledError:
        logger.info("Shutdown requested; stopping polling")
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


def main() -> None:
    try:
        asyncio.run(run())
    except ConfigError as exc:
        logging.error("Configuration error: %s", exc)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
