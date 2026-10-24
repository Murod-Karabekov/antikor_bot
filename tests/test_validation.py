import pytest

from app.utils.validation import NameValidationError, normalize_name, validate_name


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Ali", "Ali"),
        ("  Abdulla   Karimov ", "Abdulla Karimov"),
        ("O‘tkir", "O‘tkir"),
        ("G'ulom", "G'ulom"),
        ("Mo’minova", "Mo’minova"),
        ("Anna-Maria", "Anna-Maria"),
    ],
)
def test_valid_latin_names(raw, expected):
    assert validate_name(raw) == expected


@pytest.mark.parametrize("raw", ["Ўлмас", "Ғаффор", "Ҳакимжон", "Қодиров", "Йўлдош", "Иброҳим"])
def test_valid_uzbek_cyrillic_names(raw):
    assert validate_name(raw) == raw


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "A", "1Ali", "Ali2", "Ali!", "Ali@", "😀😀", "<b>Ali</b>", "Ali  Vali" * 10],
)
def test_invalid_names_are_rejected(raw):
    with pytest.raises(NameValidationError):
        validate_name(raw)


def test_none_is_rejected():
    with pytest.raises(NameValidationError):
        validate_name(None)


def test_double_apostrophe_and_leading_hyphen_are_rejected():
    with pytest.raises(NameValidationError):
        validate_name("O‘‘tkir")
    with pytest.raises(NameValidationError):
        validate_name("-Ali")


def test_normalize_collapses_whitespace():
    assert normalize_name("\tA   B\n") == "A B"
