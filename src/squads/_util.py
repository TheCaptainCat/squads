"""Small shared helpers and reusable typed fields."""

import re
import unicodedata
from typing import Annotated

from pydantic import Field

#: A string field constrained to be non-empty (for pydantic models).
type NonEmpty = Annotated[str, Field(min_length=1)]

_slug_strip = re.compile(r"[^a-z0-9]+")

#: Lowercase letters NFKD does not decompose, with their ASCII spelling.
_TRANSLITERATIONS: tuple[tuple[str, str], ...] = (
    ("ß", "ss"),
    ("æ", "ae"),
    ("ø", "o"),
    ("œ", "oe"),
    ("ł", "l"),
    ("đ", "d"),
    ("þ", "th"),
    ("ð", "d"),
    ("ħ", "h"),
    ("ŧ", "t"),
    ("\u0131", "i"),
)


def _ascii_units(text: str) -> list[str]:
    """*text* lowercased, decomposed and stripped of combining marks, as one string per source
    letter with the transliteration applied, so an expansion stays whole."""
    decomposed = unicodedata.normalize("NFKD", text.strip().lower())
    table = dict(_TRANSLITERATIONS)
    return [table.get(c, c) for c in decomposed if not unicodedata.combining(c)]


def slugify(text: str, *, max_len: int = 60) -> str:
    """Lowercase, hyphenated ASCII slug suitable for filenames and Claude agent names; accented
    Latin letters are transliterated (``Élodie`` -> ``elodie``), other scripts are dropped. The
    length cut never splits a transliterated letter."""
    out = ""
    pending_hyphen = False
    for unit in _ascii_units(text):
        if _slug_strip.fullmatch(unit):
            pending_hyphen = bool(out)
            continue
        addition = ("-" if pending_hyphen else "") + unit
        if len(out) + len(addition) > max_len:
            return out.rstrip("-") or "untitled"
        out += addition
        pending_hyphen = False
    return out or "untitled"


def legacy_slugify(text: str, *, max_len: int = 60) -> str:
    """The slug rule that dropped accented letters (``Élodie`` -> ``lodie``). Kept verbatim and
    self-contained so a duplicate check can recognise a slug stored under it; never used to
    propose a slug."""
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > max_len:
        s = s[:max_len].rstrip("-")
    return s or "untitled"


def operator_slug(name: str) -> str:
    """Operator (human) slug: ``op-`` + the slugified first name ("Alice Tester" → ``op-alice``)."""
    first = name.strip().split()[0] if name.strip() else name
    return f"op-{slugify(first)}"


def legacy_operator_slug(name: str) -> str:
    """:func:`operator_slug` under :func:`legacy_slugify`, for duplicate checks only."""
    first = name.strip().split()[0] if name.strip() else name
    return f"op-{legacy_slugify(first)}"


_VERSION_RE = re.compile(
    r"^v?(?P<rel>\d+(?:\.\d+)*)"
    r"(?:[.\-_]?(?P<pre>alpha|beta|preview|pre|rc|a|b|c)[.\-_]?(?P<pre_n>\d*))?"
    r"(?:[.\-_]?(?:post|rev|r)[.\-_]?(?P<post_n>\d*))?"
    r"(?:[.\-_]?dev[.\-_]?(?P<dev_n>\d*))?"
    r"(?:\+.*)?$",
    re.IGNORECASE,
)
_PRE_RANKS: tuple[tuple[str, int], ...] = (
    ("alpha", 0),
    ("a", 0),
    ("beta", 1),
    ("b", 1),
    ("rc", 2),
    ("c", 2),
    ("pre", 2),
    ("preview", 2),
)

#: Comparison key: release numbers, pre-release ``(rank, n)``, post-release, dev-release.
type VersionKey = tuple[tuple[int, ...], tuple[int, int], int, int]

_NO_DEV = 1 << 60


def _trim_release(nums: list[int]) -> tuple[int, ...]:
    while nums and nums[-1] == 0:
        nums.pop()
    return tuple(nums)


def version_tuple(version: str) -> VersionKey:
    """A comparable key ordered by PEP 440: ``X.devN < X.aN < X.bN < X.rcN < X < X.postN``, with
    the release numbers compared as their own tuple (any length, trailing zeros ignored). Text that
    is not a version falls back to each dotted segment's leading digits (0 when it has none),
    never joining digits across a suffix."""
    text = version.strip()
    m = _VERSION_RE.match(text)
    if m is None:
        nums = [
            int(d.group()) if (d := re.match(r"\d+", p.strip())) else 0 for p in text.split(".")
        ]
        return (_trim_release(nums), (3, 0), -1, _NO_DEV)
    release = _trim_release([int(p) for p in m["rel"].split(".")])
    pre_tag = m["pre"]
    has_post = m["post_n"] is not None
    has_dev = m["dev_n"] is not None
    if pre_tag:
        pre = (dict(_PRE_RANKS)[pre_tag.lower()], int(m["pre_n"] or 0))
    elif has_dev and not has_post:
        pre = (-1, 0)
    else:
        pre = (3, 0)
    post = int(m["post_n"] or 0) if has_post else -1
    dev = int(m["dev_n"] or 0) if has_dev else _NO_DEV
    return (release, pre, post, dev)


_SILENT_H = ("hour", "honest", "honor", "heir")
_CONSONANT_SOUND = ("uni", "use", "usu", "uti", "ubi", "eu", "one")


def article(word: str) -> str:
    """``"an"`` before a vowel sound, ``"a"`` before a consonant sound: ``an epic``, ``a unit``,
    ``a user_story``, ``an hour``."""
    w = word.lower()
    if w.startswith(_SILENT_H):
        return "an"
    if w.startswith(_CONSONANT_SOUND):
        return "a"
    return "an" if w[:1] in ("a", "e", "i", "o", "u") else "a"
