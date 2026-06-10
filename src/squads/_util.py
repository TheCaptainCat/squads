"""Small shared helpers and reusable typed fields."""

import re
from typing import Annotated

from pydantic import Field

#: A string field constrained to be non-empty (for pydantic models).
type NonEmpty = Annotated[str, Field(min_length=1)]

_slug_strip = re.compile(r"[^a-z0-9]+")


def slugify(text: str, *, max_len: int = 60) -> str:
    """Lowercase, hyphenated, ASCII-ish slug suitable for filenames and Claude agent names."""
    s = text.strip().lower()
    s = _slug_strip.sub("-", s).strip("-")
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s or "untitled"


def operator_slug(name: str) -> str:
    """Operator (human) slug: ``op-`` + the slugified first name ("Pierre Chat" → ``op-pierre``)."""
    first = name.strip().split()[0] if name.strip() else name
    return f"op-{slugify(first)}"
