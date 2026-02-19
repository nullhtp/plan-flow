"""Tests for the user meta prompt formatting utility."""

from datetime import UTC
from unittest.mock import patch

from app.domains.ai.prompts.meta import (
    _compute_day_of_week,
    format_user_meta_block,
    resolve_user_context,
)


def test_full_meta_produces_complete_block() -> None:
    """Full user_meta dict produces all six context lines (including day of week)."""
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
    assert "- Day of week: Tuesday" in result
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


# ── Day of week tests ────────────────────────────────────


def test_day_of_week_computed_correctly() -> None:
    """Day of week is computed correctly from the date string."""
    # 2026-02-19 is a Thursday
    assert _compute_day_of_week("2026-02-19") == "Thursday"
    # 2026-02-20 is a Friday
    assert _compute_day_of_week("2026-02-20") == "Friday"
    # 2026-02-21 is a Saturday
    assert _compute_day_of_week("2026-02-21") == "Saturday"


def test_day_of_week_invalid_date_returns_none() -> None:
    """Invalid date strings return None."""
    assert _compute_day_of_week("invalid") is None
    assert _compute_day_of_week("") is None


def test_day_of_week_included_in_meta_block() -> None:
    """Day of week is included when current_datetime is present."""
    meta = {
        "timezone": "UTC",
        "current_datetime": "2026-02-19T12:00:00Z",  # Thursday
    }
    result = format_user_meta_block(meta)
    assert "- Day of week: Thursday" in result


def test_day_of_week_not_included_without_datetime() -> None:
    """Day of week is NOT included when current_datetime is missing."""
    meta = {
        "timezone": "UTC",
        "locale": "en",
    }
    result = format_user_meta_block(meta)
    assert "Day of week" not in result


# ── resolve_user_context tests ───────────────────────────


def test_resolve_user_context_returns_empty_for_none() -> None:
    """resolve_user_context returns empty string for None input."""
    assert resolve_user_context(None) == ""


def test_resolve_user_context_returns_empty_for_empty_dict() -> None:
    """resolve_user_context returns empty string for empty dict."""
    assert resolve_user_context({}) == ""


def test_resolve_user_context_computes_server_date() -> None:
    """resolve_user_context computes the current date server-side."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    meta = {
        "timezone": "Europe/Berlin",
        "locale": "de-DE",
        "current_datetime": "",  # Will be overridden
        "location": {"city": "Berlin", "country": "Germany"},
        "device_type": "desktop",
    }
    result = resolve_user_context(meta)

    # The result should contain today's date in the Berlin timezone
    now_berlin = datetime.now(ZoneInfo("Europe/Berlin"))
    expected_date = now_berlin.strftime("%Y-%m-%d")
    expected_day = now_berlin.strftime("%A")

    assert f"- Current date: {expected_date}" in result
    assert f"- Day of week: {expected_day}" in result
    assert "- Timezone: Europe/Berlin" in result
    assert "- Locale: de-DE" in result


def test_resolve_user_context_cross_timezone() -> None:
    """resolve_user_context handles timezones where the date differs from UTC."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    # Mock datetime.now to return a specific UTC time where Auckland is a day ahead
    # 2026-02-19 23:00 UTC = 2026-02-20 12:00 NZST (UTC+13)
    import app.domains.ai.prompts.meta as meta_module

    mock_utc_time = datetime(2026, 2, 19, 23, 0, 0, tzinfo=UTC)

    meta = {
        "timezone": "Pacific/Auckland",
        "locale": "en-NZ",
        "device_type": "desktop",
    }

    original_now = datetime.now

    def mock_now(tz: ZoneInfo | None = None) -> datetime:  # type: ignore[assignment]
        if tz is not None:
            return mock_utc_time.astimezone(tz)
        return original_now(tz)

    with patch.object(meta_module, "datetime") as mock_dt:
        mock_dt.now = mock_now
        mock_dt.strptime = datetime.strptime
        result = resolve_user_context(meta)

    # Auckland is UTC+13, so 2026-02-19 23:00 UTC = 2026-02-20 12:00 NZST
    assert "- Current date: 2026-02-20" in result
    assert "- Day of week: Friday" in result


def test_resolve_user_context_without_timezone_fallback() -> None:
    """resolve_user_context works even without a timezone field."""
    meta = {
        "locale": "en-US",
        "device_type": "mobile",
    }
    result = resolve_user_context(meta)

    # Should still produce output with current date
    assert "User context:" in result
    assert "- Locale: en-US" in result
    assert "- Current date:" in result
    assert "- Day of week:" in result


def test_resolve_user_context_invalid_timezone_falls_back_to_utc() -> None:
    """resolve_user_context handles invalid timezone gracefully."""
    meta = {
        "timezone": "Invalid/Timezone",
        "locale": "en",
    }
    result = resolve_user_context(meta)

    # Should still produce output (falls back to UTC)
    assert "User context:" in result
    assert "- Current date:" in result
