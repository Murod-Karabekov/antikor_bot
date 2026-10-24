"""PNG congratulation card rendering. Pure Pillow, no Telegram code, nothing written to disk."""

from __future__ import annotations

import io
import logging
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 1600, 900
FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"

FONT_SANS = "DejaVuSans.ttf"
FONT_SANS_BOLD = "DejaVuSans-Bold.ttf"
FONT_SERIF_BOLD = "DejaVuSerif-Bold.ttf"

EMERALD_DARK = (6, 49, 38)
EMERALD = (11, 93, 69)
EMERALD_LIGHT = (20, 120, 88)
WHITE = (255, 255, 255)
GOLD = (184, 150, 46)
GOLD_TEXT = (150, 117, 25)
GRAY_TEXT = (74, 90, 85)

CONTENT_WIDTH = 1100
HEADER_TEXT = "ANTIKORRUPSIYA KLUBI"
TITLE_TEXT = "TABRIKNOMA"
GREETING_TEXT = "Hurmatli,"
BODY_TEXT = "Sizni Antikorrupsiya klubi a’zoligiga qo‘shilganingiz bilan samimiy tabriklaymiz!"
MOTTO_TEXT = "Halollik, shaffoflik va adolat — bizning qadriyatlarimiz!"


class CertificateError(ValueError):
    pass


@lru_cache(maxsize=32)
def _font(file_name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / file_name), size)


def wrap_text(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> list[str]:
    """Word-wrap text; words longer than max_width are split by character so nothing is clipped."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}" if current else word
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        if draw.textlength(word, font=font) <= max_width:
            current = word
            continue
        chunk = ""
        for ch in word:
            if draw.textlength(chunk + ch, font=font) <= max_width:
                chunk += ch
            else:
                lines.append(chunk)
                chunk = ch
        current = chunk
    if current:
        lines.append(current)
    return lines or [""]


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_file: str,
    max_width: int,
    max_height: int,
    max_size: int,
    min_size: int,
    max_lines: int,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Pick the largest font size whose wrapped lines fit in the given box."""
    for size in range(max_size, min_size - 1, -2):
        font = _font(font_file, size)
        lines = wrap_text(draw, text, font, max_width)
        if len(lines) > max_lines:
            continue
        if len(lines) * _line_height(font) <= max_height:
            return font, lines
    font = _font(font_file, min_size)
    return font, wrap_text(draw, text, font, max_width)


def _line_height(font: ImageFont.FreeTypeFont) -> int:
    top, _, _, bottom = font.getbbox("Ayg")
    return int((bottom - top) * 1.25)


def _draw_centered(draw: ImageDraw.ImageDraw, y: int, text: str, font, fill) -> int:
    draw.text((WIDTH // 2, y), text, font=font, fill=fill, anchor="mt")
    return y + _line_height(font)


def _draw_tracked(draw: ImageDraw.ImageDraw, y: int, text: str, font, fill, spacing: int) -> int:
    total = sum(draw.textlength(ch, font=font) for ch in text) + spacing * (len(text) - 1)
    x = (WIDTH - total) / 2
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing
    return y + _line_height(font)


def _diamond(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill) -> None:
    draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)


def _background() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), EMERALD_DARK)
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        color = tuple(
            int(a + (b - a) * t) for a, b in zip(EMERALD_LIGHT, EMERALD_DARK, strict=True)
        )
        draw.line([(0, y), (WIDTH, y)], fill=color)
    return img


def _frame(draw: ImageDraw.ImageDraw) -> None:
    draw.rounded_rectangle((60, 60, WIDTH - 60, HEIGHT - 60), radius=28, fill=WHITE)
    draw.rounded_rectangle((84, 84, WIDTH - 84, HEIGHT - 84), radius=18, outline=GOLD, width=3)
    draw.rounded_rectangle((98, 98, WIDTH - 98, HEIGHT - 98), radius=14, outline=GOLD, width=1)
    for x in (84, WIDTH - 84):
        for y in (84, HEIGHT - 84):
            _diamond(draw, x, y, 16, GOLD)
    for y in (84, HEIGHT - 84):
        _diamond(draw, WIDTH // 2, y, 10, GOLD)


def _divider(draw: ImageDraw.ImageDraw, y: int, half: int = 140) -> None:
    draw.line([(WIDTH // 2 - half, y), (WIDTH // 2 + half, y)], fill=GOLD, width=2)
    _diamond(draw, WIDTH // 2, y, 7, GOLD)


def _paste_logo(img: Image.Image, logo_path: Path | None) -> None:
    if logo_path is None:
        return
    try:
        with Image.open(logo_path) as logo:
            logo = logo.convert("RGBA")
            logo.thumbnail((120, 120))
            img.paste(logo, (120, 118), logo)
    except OSError:
        logger.warning("Club logo could not be loaded; rendering without it")


def render_certificate(full_name: str, logo_path: Path | None = None) -> bytes:
    """Render the congratulation card and return PNG bytes (kept in memory only)."""
    name = " ".join(full_name.split())
    if not name:
        raise CertificateError("Ism bo‘sh")

    img = _background()
    draw = ImageDraw.Draw(img)
    _frame(draw)
    _paste_logo(img, logo_path)

    y = _draw_tracked(draw, 118, HEADER_TEXT, _font(FONT_SANS_BOLD, 34), EMERALD, spacing=6)
    y = _draw_centered(draw, 175, TITLE_TEXT, _font(FONT_SERIF_BOLD, 88), EMERALD)
    _divider(draw, y + 22)

    y = _draw_centered(draw, y + 50, GREETING_TEXT, _font(FONT_SANS, 36), GRAY_TEXT)

    name_font, name_lines = fit_text(
        draw,
        name,
        FONT_SANS_BOLD,
        CONTENT_WIDTH,
        max_height=150,
        max_size=100,
        min_size=40,
        max_lines=2,
    )
    for line in name_lines:
        y = _draw_centered(draw, y + 4, line, name_font, EMERALD_DARK)

    body_font = _font(FONT_SANS, 28)
    y += 26
    for line in wrap_text(draw, BODY_TEXT, body_font, CONTENT_WIDTH):
        y = _draw_centered(draw, y, line, body_font, GRAY_TEXT)

    y += 22
    y = _draw_centered(draw, y, MOTTO_TEXT, _font(FONT_SANS_BOLD, 30), GOLD_TEXT)

    _divider(draw, HEIGHT - 160, half=90)
    _draw_tracked(draw, HEIGHT - 140, HEADER_TEXT, _font(FONT_SANS_BOLD, 24), EMERALD, spacing=5)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
