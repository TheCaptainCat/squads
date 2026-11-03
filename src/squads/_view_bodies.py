"""Stored view bodies: the paired view tag, the escape that keeps a body from forging a marker, and
the text between the two tags.

A view declared ``stored`` keeps its body between ``sq:view:<name>`` and ``sq:view:<name>:end``.
The escape makes the stored text contain no HTML-comment opener, so no marker of any spelling can
open, close or be forged inside it.
"""

import re
from dataclasses import dataclass

from squads._models import _markers as markers
from squads._sections import iter_marker_spans

_OPENER_RUN_RE = re.compile(r"<(!+)--")
_ESCAPED_RUN_RE = re.compile(r"<(!{2,})--")


def escape_body(text: str) -> str:
    """*text* with one ``!`` added to every run of ``!`` between ``<`` and ``--``."""
    return _OPENER_RUN_RE.sub(lambda m: f"<{m.group(1)}!--", text)


def unescape_body(text: str) -> str:
    """The inverse of :func:`escape_body`: one ``!`` off every such run of two or more."""
    return _ESCAPED_RUN_RE.sub(lambda m: f"<{m.group(1)[1:]}--", text)


def encode_inner(text: str) -> str:
    """The text between a pair's tags for the stored body *text*: escaped, on lines of its own.
    An empty body is the empty pair."""
    escaped = escape_body(text)
    return f"\n{escaped}\n" if escaped else "\n"


def decode_inner(inner: str) -> str:
    """The stored body held by *inner*, the text between a pair's tags, unescaped."""
    body = inner.replace("\r\n", "\n")
    body = body.removeprefix("\n").removesuffix("\n")
    return unescape_body(body)


@dataclass(frozen=True, slots=True)
class ViewPair:
    """One view's opening tag, end tag and the text between them, with their offsets in the
    text they were found in."""

    parts: markers.ViewTagParts
    start: int
    open_end: int
    close_start: int
    end: int
    inner: str

    @property
    def body(self) -> str:
        """The stored body, unescaped."""
        return decode_inner(self.inner)


def find_view_pairs(text: str) -> list[ViewPair]:
    """Every view tag directly followed by its own end tag, in file order. The escape leaves no
    marker inside a stored body, so a pair never has another marker between its tags."""
    spans = iter_marker_spans(text)
    pairs: list[ViewPair] = []
    i = 0
    while i < len(spans) - 1:
        raw, start, open_end = spans[i]
        parts = markers.view_tag_parts(raw)
        close_raw, close_start, end = spans[i + 1]
        if parts is not None and markers.view_close_name(close_raw) == parts.name:
            pairs.append(
                ViewPair(parts, start, open_end, close_start, end, text[open_end:close_start])
            )
            i += 2
        else:
            i += 1
    return pairs


def collapse_pairs(text: str) -> tuple[str, dict[str, str]]:
    """*text* with each pair reduced to its opening tag, and the text between the tags of the
    first pair of each view, by view name."""
    inners: dict[str, str] = {}
    out: list[str] = []
    last = 0
    for pair in find_view_pairs(text):
        out += [text[last : pair.open_end]]
        last = pair.end
        inners.setdefault(pair.parts.name, pair.inner)
    out.append(text[last:])
    return "".join(out), inners
