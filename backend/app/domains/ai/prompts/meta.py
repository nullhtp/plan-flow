from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


def _compute_day_of_week(date_str: str, timezone_str: str | None = None) -> str | None:
    """Compute English day-of-week name from a YYYY-MM-DD date string.

    If timezone_str is provided and the date_str is ambiguous, uses the timezone
    for context. Returns None on parse failure.
    """
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%A")  # e.g., "Thursday"
    except (ValueError, IndexError):
        return None


def format_user_meta_block(user_meta: dict[str, Any] | None) -> str:
    """Format user meta context into a text block for AI prompt injection.

    Returns a formatted "User context:" block with available fields,
    or an empty string if user_meta is None or empty.
    Null/missing fields are omitted from the output.
    """
    if not user_meta:
        return ""

    lines: list[str] = []

    timezone = user_meta.get("timezone")
    if timezone:
        lines.append(f"- Timezone: {timezone}")

    locale = user_meta.get("locale")
    if locale:
        lines.append(f"- Locale: {locale}")

    current_datetime = user_meta.get("current_datetime")
    if current_datetime:
        # Extract just the date portion (YYYY-MM-DD) from ISO 8601
        current_date = (
            current_datetime[:10] if len(current_datetime) >= 10 else current_datetime
        )
        lines.append(f"- Current date: {current_date}")

        # Compute and add day of week
        day_name = _compute_day_of_week(current_date, timezone)
        if day_name:
            lines.append(f"- Day of week: {day_name}")

    location = user_meta.get("location")
    if location:
        city = location.get("city")
        country = location.get("country")
        parts = [p for p in [city, country] if p]
        if parts:
            lines.append(f"- Location: {', '.join(parts)}")

    device_type = user_meta.get("device_type")
    if device_type:
        lines.append(f"- Device: {device_type}")

    if not lines:
        return ""

    return "\nUser context:\n" + "\n".join(lines)


def resolve_user_context(user_meta: dict[str, Any] | None) -> str:
    """Resolve user context with server-computed current date.

    Takes a stored user_meta dict (from goal.ai_context["user_meta"]),
    computes the current date and day-of-week server-side using the
    stored timezone, and returns the formatted context string.

    This is used by chat endpoints and classification where we need
    fresh temporal context without requiring the frontend to send it.

    Returns an empty string if user_meta is None or empty.
    """
    if not user_meta:
        return ""

    timezone_str = user_meta.get("timezone")

    # Compute current datetime in the user's timezone
    try:
        if timezone_str:
            tz = ZoneInfo(timezone_str)
            now = datetime.now(tz)
        else:
            now = datetime.now()
        current_datetime_iso = now.isoformat()
    except Exception:
        logger.warning("Failed to resolve timezone '%s', using UTC", timezone_str)
        from datetime import UTC

        now = datetime.now(UTC)
        current_datetime_iso = now.isoformat()

    # Build a copy of user_meta with the server-computed current_datetime
    resolved_meta = dict(user_meta)
    resolved_meta["current_datetime"] = current_datetime_iso

    return format_user_meta_block(resolved_meta)
