"""Environment-based configuration. No secrets are hardcoded."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(repr=False)
    group_id: int
    group_invite_url: str
    admin_ids: frozenset[int]
    club_logo_path: Path | None = None


def _parse_admin_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.lstrip("-").isdigit():
            raise ConfigError("ADMIN_TELEGRAM_IDS faqat raqamlardan iborat bo‘lishi kerak")
        ids.add(int(part))
    return frozenset(ids)


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Load settings from environment variables (or the given mapping)."""
    source = os.environ if env is None else env

    token = source.get("BOT_TOKEN", "").strip()
    if not token or ":" not in token:
        raise ConfigError("BOT_TOKEN sozlanmagan yoki noto‘g‘ri")

    group_raw = source.get("GROUP_ID", "").strip()
    if not group_raw.lstrip("-").isdigit():
        raise ConfigError("GROUP_ID raqam bo‘lishi kerak (masalan -1001234567890)")

    invite = source.get("GROUP_INVITE_URL", "").strip()
    if not invite.startswith("https://"):
        raise ConfigError("GROUP_INVITE_URL https:// bilan boshlanishi kerak")

    logo_raw = source.get("CLUB_LOGO_PATH", "").strip()

    return Settings(
        bot_token=token,
        group_id=int(group_raw),
        group_invite_url=invite,
        admin_ids=_parse_admin_ids(source.get("ADMIN_TELEGRAM_IDS", "")),
        club_logo_path=Path(logo_raw) if logo_raw else None,
    )
