import struct
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from app.services.certificate import (
    CONTENT_WIDTH,
    FONT_SANS_BOLD,
    CertificateError,
    fit_text,
    render_certificate,
    wrap_text,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == PNG_SIGNATURE
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _draw():
    return ImageDraw.Draw(Image.new("RGB", (10, 10)))


def test_renders_1600x900_png_in_memory():
    data = render_certificate("Ali Valiyev")
    assert _png_size(data) == (1600, 900)


@pytest.mark.parametrize(
    "name",
    [
        "Ўлмас Ғаффоров",
        "Ҳакимжон Йўлдошев",
        "Abdurahmonxo‘ja Muhammadjonovich-Qo‘chqorov Ўлмасбеков",
        "A" * 80,
    ],
)
def test_uzbek_latin_cyrillic_and_long_names_render(name):
    data = render_certificate(name)
    assert _png_size(data) == (1600, 900)


def test_fit_text_keeps_long_names_inside_content_width():
    font, lines = fit_text(
        _draw(),
        "Abdurahmonxo‘ja Muhammadjonovich-Qo‘chqorov Ўлмасбеков",
        FONT_SANS_BOLD,
        CONTENT_WIDTH,
        max_height=150,
        max_size=100,
        min_size=40,
        max_lines=2,
    )
    draw = _draw()
    assert len(lines) <= 2
    assert all(draw.textlength(line, font=font) <= CONTENT_WIDTH for line in lines)


def test_fit_text_uses_large_font_for_short_names():
    font, lines = fit_text(
        _draw(),
        "Ali",
        FONT_SANS_BOLD,
        CONTENT_WIDTH,
        max_height=150,
        max_size=100,
        min_size=40,
        max_lines=2,
    )
    assert lines == ["Ali"]
    assert font.size == 100


def test_wrap_text_never_drops_characters():
    draw = _draw()
    font = fit_text(draw, "x", FONT_SANS_BOLD, 500, 500, 60, 60, 2)[0]
    word = "W" * 60
    lines = wrap_text(draw, word, font, 300)
    assert "".join(lines) == word
    assert all(draw.textlength(line, font=font) <= 300 for line in lines)


def test_empty_name_is_rejected():
    with pytest.raises(CertificateError):
        render_certificate("   ")


def test_missing_logo_does_not_break_rendering(tmp_path: Path):
    data = render_certificate("Ali", logo_path=tmp_path / "missing.png")
    assert _png_size(data) == (1600, 900)


def test_logo_is_pasted_when_provided(tmp_path: Path):
    logo = tmp_path / "logo.png"
    Image.new("RGBA", (300, 300), (255, 0, 0, 255)).save(logo)
    data = render_certificate("Ali", logo_path=logo)
    assert _png_size(data) == (1600, 900)
