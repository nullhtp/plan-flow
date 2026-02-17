"""Language utility functions for the AI pipeline."""

from __future__ import annotations

# Common ISO 639-1 codes to language names (in the language itself for prompt clarity)
_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "ru": "Russian",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
    "pt": "Portuguese",
    "it": "Italian",
    "nl": "Dutch",
    "pl": "Polish",
    "uk": "Ukrainian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "cs": "Czech",
    "ro": "Romanian",
    "hu": "Hungarian",
    "el": "Greek",
    "he": "Hebrew",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
}


def get_language_name(code: str) -> str:
    """Return the English name of a language given its ISO 639-1 code.

    Falls back to the code itself if not found.
    """
    return _LANGUAGE_NAMES.get(code.lower(), code)
