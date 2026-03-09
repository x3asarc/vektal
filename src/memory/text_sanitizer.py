"""Text sanitization utilities to ensure UTF-8 compliance in memory files."""

from __future__ import annotations

import re
from typing import Any


# Map Windows-1252 characters to ASCII equivalents
WINDOWS_1252_TO_ASCII = {
    "\u2013": "-",  # en-dash
    "\u2014": "-",  # em-dash
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201C": '"',  # left double quote
    "\u201D": '"',  # right double quote
    "\u2026": "...",  # ellipsis
    "\u2022": "*",  # bullet
    "\u00A0": " ",  # non-breaking space
}


def sanitize_text(text: str) -> str:
    """
    Sanitize text to ensure UTF-8 compliance by replacing common Windows-1252 characters.

    This prevents encoding issues that can occur when text is pasted from Word documents,
    rich text editors, or other sources that use Windows-1252 encoding.

    Args:
        text: Input text that may contain problematic characters

    Returns:
        Sanitized text with Windows-1252 characters replaced by ASCII equivalents
    """
    if not isinstance(text, str):
        return text

    sanitized = text
    for win_char, ascii_char in WINDOWS_1252_TO_ASCII.items():
        sanitized = sanitized.replace(win_char, ascii_char)

    # Remove any remaining non-ASCII, non-printable characters (but keep valid Unicode)
    # This is a safety net - only removes truly problematic bytes
    sanitized = sanitized.encode("utf-8", errors="replace").decode("utf-8")

    return sanitized


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively sanitize all string values in a dictionary.

    Args:
        data: Dictionary that may contain string values with encoding issues

    Returns:
        Dictionary with all string values sanitized
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = sanitize_text(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_text(item) if isinstance(item, str)
                else sanitize_dict(item) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def is_utf8_safe(text: str) -> bool:
    """
    Check if text can be safely encoded as UTF-8.

    Args:
        text: Text to check

    Returns:
        True if text is UTF-8 safe, False otherwise
    """
    try:
        text.encode("utf-8")
        return True
    except UnicodeEncodeError:
        return False
