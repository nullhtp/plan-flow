"""Tests for the user meta prompt formatting utility."""

from app.domains.ai.prompts.meta import format_user_meta_block


def test_full_meta_produces_complete_block() -> None:
    """Full user_meta dict produces all five context lines."""
    meta = {
        "timezone": "Europe/Berlin",
        "locale": "de-DE",
        "current_datetime": "2026-02-17T14:30:00Z",
        "location": {"city": "Berlin", "country": "Germany"},
        "device_type": "desktop",
    }
    result = format_user_meta_block(meta)

    assert "User context:" in result
    assert "- Timezone: Europe/Berlin" in result
    assert "- Locale: de-DE" in result
    assert "- Current date: 2026-02-17" in result
    assert "- Location: Berlin, Germany" in result
    assert "- Device: desktop" in result


def test_meta_without_location_omits_location_line() -> None:
    """When location is None, the Location line is omitted."""
    meta = {
        "timezone": "America/New_York",
        "locale": "en-US",
        "current_datetime": "2026-02-17T10:00:00Z",
        "location": None,
        "device_type": "mobile",
    }
    result = format_user_meta_block(meta)

    assert "User context:" in result
    assert "- Timezone: America/New_York" in result
    assert "Location" not in result
    assert "- Device: mobile" in result


def test_none_meta_returns_empty_string() -> None:
    """None input returns empty string."""
    assert format_user_meta_block(None) == ""


def test_empty_dict_returns_empty_string() -> None:
    """Empty dict returns empty string."""
    assert format_user_meta_block({}) == ""


def test_location_with_only_country() -> None:
    """Location with only country (no city) still renders."""
    meta = {
        "timezone": "Asia/Tokyo",
        "locale": "ja-JP",
        "current_datetime": "2026-02-17T23:00:00Z",
        "location": {"city": None, "country": "Japan"},
        "device_type": "tablet",
    }
    result = format_user_meta_block(meta)

    assert "- Location: Japan" in result


def test_location_with_only_city() -> None:
    """Location with only city (no country) still renders."""
    meta = {
        "timezone": "Europe/London",
        "locale": "en-GB",
        "current_datetime": "2026-02-17T12:00:00Z",
        "location": {"city": "London", "country": None},
        "device_type": "desktop",
    }
    result = format_user_meta_block(meta)

    assert "- Location: London" in result


def test_location_empty_dict_omits_location_line() -> None:
    """Location with empty city and country omits the line."""
    meta = {
        "timezone": "UTC",
        "locale": "en",
        "current_datetime": "2026-02-17T00:00:00Z",
        "location": {"city": None, "country": None},
        "device_type": "desktop",
    }
    result = format_user_meta_block(meta)

    assert "Location" not in result
