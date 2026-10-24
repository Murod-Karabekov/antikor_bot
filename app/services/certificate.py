"""Certificate rendering: the approved template with the student's name inserted.

The template (assets/templates/antikorrupsiya_certificate.png) is the final design and is
never redrawn. Only the empty gold-bordered name field below "Hurmatli," is filled in.
Rendering happens in memory; nothing is written to disk.
"""

from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT / "assets" / "templates" / "antikorrupsiya_certificate.png"
FONT_PATH = ROOT / "assets" / "fonts" / "DejaVuSerif-Bold.ttf"

# Measured from the approved 1672x941 template (inclusive pixel bounds of the cream interior,
# inside the gold border). Verified by tests/test_certificate.py.
TEMPLATE_SIZE = (1672, 941)
NAME_FIELD = (421, 492, 1253, 571)
NAME_PADDING = 12  # clearance between the text and the gold border
NAME_COLOR = (7, 63, 50)  # #073F32
MAX_FONT_SIZE = 64
MIN_FONT_SIZE = 20
LINE_GAP_RATIO = 0.12


class CertificateError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _template() -> Image.Image:
    try:
        with Image.open(TEMPLATE_PATH) as img:
            img = img.convert("RGB")
            img.load()
    except OSError as exc:
        raise CertificateError("Certificate template is missing or unreadable") from exc
    if img.size != TEMPLATE_SIZE:
        raise CertificateError(f"Unexpected template size {img.size}, expected {TEMPLATE_SIZE}")
    return img


@lru_cache(maxsize=128)
def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def name_box() -> tuple[int, int, int, int]:
    """Usable area for the name, inside the border and the padding."""
    left, top, right, bottom = NAME_FIELD
    return (
        left + NAME_PADDING,
        top + NAME_PADDING,
        right - NAME_PADDING,
        bottom - NAME_PADDING,
    )


def wrap_text(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int
) -> list[str]:
    """Word-wrap; words longer than max_width are split by character so nothing is dropped."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}" if current else word
        if _width(draw, candidate, font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        if _width(draw, word, font) <= max_width:
            current = word
            continue
        chunk = ""
        for ch in word:
            if _width(draw, chunk + ch, font) <= max_width:
                chunk += ch
            else:
                lines.append(chunk)
                chunk = ch
        current = chunk
    if current:
        lines.append(current)
    return lines or [""]


def _width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def _ink_height(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    _, top, _, bottom = draw.textbbox((0, 0), text, font=font)
    return bottom - top


def fit_name(draw: ImageDraw.ImageDraw, text: str) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Largest font size at which the name fits the name box (one line preferred)."""
    left, top, right, bottom = name_box()
    max_w, max_h = right - left, bottom - top
    for size in range(MAX_FONT_SIZE, MIN_FONT_SIZE - 1, -1):
        font = _font(size)
        lines = wrap_text(draw, text, font, max_w)
        if len(lines) > 2:
            continue
        gap = int(size * LINE_GAP_RATIO) if len(lines) > 1 else 0
        block_h = sum(_ink_height(draw, ln, font) for ln in lines) + gap * (len(lines) - 1)
        if block_h <= max_h and all(_width(draw, ln, font) <= max_w for ln in lines):
            return font, lines
    # Nothing fits even at the minimum size; the smallest size is still the best available.
    font = _font(MIN_FONT_SIZE)
    return font, wrap_text(draw, text, font, max_w)


def _draw_name(draw: ImageDraw.ImageDraw, text: str) -> None:
    left, top, right, bottom = name_box()
    center_x = (left + right) / 2
    center_y = (top + bottom) / 2

    font, lines = fit_name(draw, text)
    gap = int(font.size * LINE_GAP_RATIO) if len(lines) > 1 else 0
    heights = [_ink_height(draw, ln, font) for ln in lines]
    y = center_y - (sum(heights) + gap * (len(lines) - 1)) / 2

    for line, height in zip(lines, heights, strict=True):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = center_x - (bbox[0] + bbox[2]) / 2
        draw.text((x, y - bbox[1]), line, font=font, fill=NAME_COLOR)
        y += height + gap


def render_certificate(full_name: str, logo_path: Path | None = None) -> bytes:
    """Return PNG bytes of the template with the student's full name in the name field.

    `logo_path` is accepted for compatibility with existing callers and is ignored: the
    approved template already contains the club logo.
    """
    name = " ".join(full_name.split())
    if not name:
        raise CertificateError("Ism bo‘sh")

    image = _template().copy()
    _draw_name(ImageDraw.Draw(image), name)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
