"""Small shared helpers."""

import re

_slug_strip = re.compile(r"[^a-z0-9]+")


def slugify(text: str, *, max_len: int = 60) -> str:
    """Lowercase, hyphenated, ASCII-ish slug suitable for filenames and Claude agent names."""
    s = text.strip().lower()
    s = _slug_strip.sub("-", s).strip("-")
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s or "untitled"
