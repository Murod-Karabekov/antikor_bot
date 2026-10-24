import pytest

from app.config import ConfigError, load_settings

VALID = {
    "BOT_TOKEN": "123456:ABC",
    "GROUP_ID": "-1001234567890",
    "GROUP_INVITE_URL": "https://t.me/example_group",
    "ADMIN_TELEGRAM_IDS": "111, 222",
}


def test_loads_valid_settings():
    s = load_settings(VALID)
    assert s.group_id == -1001234567890
    assert s.admin_ids == frozenset({111, 222})
    assert s.club_logo_path is None


def test_token_is_hidden_from_repr():
    assert "123456:ABC" not in repr(load_settings(VALID))


@pytest.mark.parametrize(
    "key, value",
    [
        ("BOT_TOKEN", ""),
        ("GROUP_ID", "abc"),
        ("GROUP_INVITE_URL", "http://insecure"),
        ("ADMIN_TELEGRAM_IDS", "12,admin"),
    ],
)
def test_invalid_values_raise(key, value):
    with pytest.raises(ConfigError):
        load_settings({**VALID, key: value})


def test_empty_admin_list_is_allowed():
    assert load_settings({**VALID, "ADMIN_TELEGRAM_IDS": ""}).admin_ids == frozenset()
