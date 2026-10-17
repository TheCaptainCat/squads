"""Pronouns on a role or operator: the one shape rule and the accessor over a stored value."""

import unicodedata

from rich.text import Text

from squads import _sections as sections
from squads._errors import SquadsError
from squads._models._attributes import AttributeKey
from squads._models._item import Item

#: The longest pronouns value, in characters, after trimming.
PRONOUNS_MAX_LENGTH = 40

#: Unicode categories refused anywhere in the text: control characters, format characters (bidi
#: overrides, zero-width marks) and the line/paragraph separators.
_REFUSED_CATEGORIES = frozenset({"Cc", "Cf", "Zl", "Zp"})


def pronouns_problem(raw: str) -> str | None:
    """Why *raw* is not a pronouns value, or ``None`` when it is.

    The one shape rule every entry point shares: judged after trimming, one line, 1 to
    :data:`PRONOUNS_MAX_LENGTH` characters counted after NFC normalisation, no control or
    invisible formatting character, no sq marker tag.
    """
    text = raw.strip()
    if not text:
        return "is blank"
    length = len(unicodedata.normalize("NFC", text))
    if length > PRONOUNS_MAX_LENGTH:
        return f"is {length} characters long; the limit is {PRONOUNS_MAX_LENGTH}"
    if any(unicodedata.category(c) in _REFUSED_CATEGORIES for c in text):
        return "must be one line with no control or invisible formatting characters"
    if sections.find_markers(text):
        return "must not contain an sq marker tag"
    return None


def pronouns(item: Item) -> str | None:
    """The stored pronouns, trimmed, when they pass :func:`pronouns_problem`, else ``None``."""
    value = item.attribute(AttributeKey.PRONOUNS)
    if not isinstance(value, str) or pronouns_problem(value) is not None:
        return None
    return value.strip()


def checked_pronouns(raw: str | None) -> str | None:
    """*raw* as the value to store: trimmed, or ``None`` when it is absent or blank.

    Raises :class:`~squads._errors.SquadsError` naming the rule when *raw* is not blank and fails
    :func:`pronouns_problem`.
    """
    if raw is None or not raw.strip():
        return None
    problem = pronouns_problem(raw)
    if problem is not None:
        raise SquadsError(f"pronouns {problem}")
    return raw.strip()


def named(name: str, pronouns: str | None, *, enabled: bool, style: str = "") -> Text:
    """*name* for a human renderer: ``Name (pronouns)`` with the parenthesis dimmed when the
    display setting is *enabled* and there are pronouns, else the bare name. The pronouns are
    content, never markup, so brackets in them print as written."""
    text = Text(name, style=style)
    if enabled and pronouns:
        text.append(" ")
        text.append(f"({pronouns})", style="dim")
    return text
