"""Validation of student names (Uzbek Latin and Cyrillic)."""

from __future__ import annotations

import re

APOSTROPHES = "'’ʻʼ`‘"
MIN_NAME_LETTERS = 2
MAX_NAME_LENGTH = 40

_NAME_RE = re.compile(
    r"^[A-Za-zЀ-ӿ]"
    r"(?:[A-Za-zЀ-ӿ\s" + re.escape(APOSTROPHES) + r"\-]*[A-Za-zЀ-ӿ])?$"
)
_DOUBLE_SEPARATOR_RE = re.compile(r"[" + re.escape(APOSTROPHES) + r"\-]{2,}|\s{2,}")


class NameValidationError(ValueError):
    """Raised with a user-facing (Uzbek) message when a name is invalid."""


def normalize_name(raw: str) -> str:
    return " ".join(raw.split())


def validate_name(raw: str | None) -> str:
    """Return the normalized name or raise NameValidationError."""
    if raw is None:
        raise NameValidationError("Iltimos, matn kiriting.")

    name = normalize_name(raw)
    if not name:
        raise NameValidationError("Ism bo‘sh bo‘lishi mumkin emas.")
    if len(name) > MAX_NAME_LENGTH:
        raise NameValidationError(f"Ism {MAX_NAME_LENGTH} belgidan oshmasligi kerak.")

    letters = sum(1 for ch in name if ch.isalpha())
    if letters < MIN_NAME_LETTERS:
        raise NameValidationError("Ism kamida 2 ta harfdan iborat bo‘lishi kerak.")

    if not _NAME_RE.fullmatch(name) or _DOUBLE_SEPARATOR_RE.search(name):
        raise NameValidationError(
            "Ism faqat lotin yoki kirill harflari, bo‘sh joy, tire va apostrof (’) "
            "belgilaridan iborat bo‘lishi kerak."
        )
    return name
