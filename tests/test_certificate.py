import io
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageDraw

import app.services.certificate as certificate
from app.services.certificate import (
    NAME_FIELD,
    TEMPLATE_SIZE,
    CertificateError,
    name_box,
    render_certificate,
    wrap_text,
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TEMPLATE_PIXEL_SHA256 = "cc926c8b101efc2b17eee22dd232838f4ca8273ccbefbf5a9b39682655ac3239"
SAMPLE_NAMES = [
    "Murod Karabekov",
    "Muhammadali Abdurahmonov",
    "Abdulazizbek Muhammadyusufov",
    "Абдулазизбек Муҳаммадюсуфов Ўғли Қўчқоров",
]


def _render(name: str) -> Image.Image:
    data = render_certificate(name)
    assert data[:8] == PNG_SIGNATURE
    return Image.open(io.BytesIO(data)).convert("RGB")


def _ink_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    """Bounding box of pixels that differ from the blank template inside the name field."""
    template = certificate._template()
    diff = ImageChops.difference(img.crop(NAME_FIELD), template.crop(NAME_FIELD))
    mask = diff.convert("L").point(lambda v: 255 if v > 40 else 0)
    box = mask.getbbox()
    if box is None:
        return None
    left, top, _, _ = NAME_FIELD
    return (box[0] + left, box[1] + top, box[2] + left, box[3] + top)


def test_template_pixels_are_the_approved_design():
    """Compares decoded pixels, not file bytes: metadata chunks do not change the design."""
    import hashlib

    pixels = Image.open(certificate.TEMPLATE_PATH).convert("RGB").tobytes()
    assert hashlib.sha256(pixels).hexdigest() == TEMPLATE_PIXEL_SHA256


def test_rendered_certificate_has_template_dimensions():
    assert _render("Murod Karabekov").size == TEMPLATE_SIZE


@pytest.mark.parametrize("name", SAMPLE_NAMES)
def test_name_is_centered_in_the_field(name):
    img = _render(name)
    box = _ink_bbox(img)
    assert box is not None
    left, top, right, bottom = name_box()
    ink_cx, ink_cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    assert abs(ink_cx - (left + right) / 2) <= 2
    assert abs(ink_cy - (top + bottom) / 2) <= 2


@pytest.mark.parametrize("name", SAMPLE_NAMES)
def test_name_never_touches_the_gold_border(name):
    box = _ink_bbox(_render(name))
    f_left, f_top, f_right, f_bottom = NAME_FIELD
    assert box[0] > f_left and box[2] < f_right
    assert box[1] > f_top and box[3] < f_bottom


@pytest.mark.parametrize("name", SAMPLE_NAMES)
def test_only_the_name_field_is_modified(name):
    img = _render(name)
    template = certificate._template()
    changed = ImageChops.difference(img, template).convert("L")
    outside = Image.new("L", img.size, 255)
    ImageDraw.Draw(outside).rectangle(NAME_FIELD, fill=0)
    assert ImageChops.multiply(changed, outside).getbbox() is None


def test_long_cyrillic_name_is_smaller_but_inside_the_field():
    short = _ink_bbox(_render("Murod Karabekov"))
    long_box = _ink_bbox(_render(SAMPLE_NAMES[3]))
    assert long_box is not None
    assert (long_box[3] - long_box[1]) <= (short[3] - short[1]) + 40
    assert long_box[2] - long_box[0] <= name_box()[2] - name_box()[0]


def test_logo_argument_is_ignored_because_template_has_the_logo(tmp_path: Path):
    logo = tmp_path / "logo.png"
    Image.new("RGBA", (50, 50), (255, 0, 0, 255)).save(logo)
    assert render_certificate("Ali Vali") == render_certificate("Ali Vali", logo_path=logo)


def test_empty_name_is_rejected():
    with pytest.raises(CertificateError):
        render_certificate("   ")


def test_missing_template_gives_clear_error(monkeypatch, tmp_path):
    monkeypatch.setattr(certificate, "TEMPLATE_PATH", tmp_path / "missing.png")
    certificate._template.cache_clear()
    try:
        with pytest.raises(CertificateError):
            render_certificate("Ali Vali")
    finally:
        certificate._template.cache_clear()


def test_wrap_text_never_drops_characters():
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    font = certificate._font(40)
    word = "W" * 60
    lines = wrap_text(draw, word, font, 300)
    assert "".join(lines) == word
