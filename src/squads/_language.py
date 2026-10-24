"""The squad's working language: a language tag validated with Babel, English when unusable."""

import json
from dataclasses import dataclass

from babel import Locale, UnknownLocaleError

DEFAULT_WORKING_LANGUAGE = "en"


@dataclass(frozen=True)
class WorkingLanguage:
    """A working language: the *tag* as written and its English display *name*."""

    tag: str
    name: str


def _parse(tag: str) -> WorkingLanguage:
    """The language *tag* names, exactly as Babel knows it (no likely-subtag expansion)."""
    locale = Locale.parse(tag, sep="-", resolve_likely_subtags=False)
    name = locale.get_display_name("en")
    if name is None:  # the root locale is data, not a language
        raise ValueError(tag)
    return WorkingLanguage(tag=tag, name=name)


def _written(raw: object) -> str:
    """*raw* as it reads in TOML: a string quoted, a number, boolean, array or date bare."""
    try:
        return json.dumps(raw, ensure_ascii=False)
    except (TypeError, ValueError):  # fmt: skip
        return str(raw)  # a TOML date or time, which JSON cannot spell


def resolve_working_language(raw: object) -> tuple[WorkingLanguage, str | None]:
    """The language *raw* (the ``working_language`` value as read) names, plus a problem.

    Never raises: an absent value is English with no problem; a value that is not a language tag
    Babel recognises is English with a problem naming the value.
    """
    if raw is None:
        return _parse(DEFAULT_WORKING_LANGUAGE), None
    if isinstance(raw, str):
        try:
            return _parse(raw), None
        except (ValueError, UnknownLocaleError):  # fmt: skip
            pass
    problem = (
        f"working_language {_written(raw)} in .squads.toml is not a language tag squads "
        f"recognises; using English ({DEFAULT_WORKING_LANGUAGE})"
    )
    return _parse(DEFAULT_WORKING_LANGUAGE), problem
