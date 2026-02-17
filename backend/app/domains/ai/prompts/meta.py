from __future__ import annotations

from typing import Any


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
