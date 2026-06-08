"""Marker-safe operations on sq-managed markdown.

All section edits go through here so we only ever touch content *between* a section's open and
close markers, leaving the marker lines and surrounding agent-authored prose intact.
"""

import re
from typing import Any, cast

import yaml

from squads.models import markers

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)


# --------------------------------------------------------------------------- frontmatter


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body). Empty dict if there is no frontmatter block."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    loaded = yaml.safe_load(m.group(1))
    data: dict[str, Any] = cast("dict[str, Any]", loaded) if isinstance(loaded, dict) else {}
    return data, text[m.end() :]


def join_frontmatter(data: dict[str, Any], body: str) -> str:
    front = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
    if not body.startswith("\n"):
        body = "\n" + body
    return f"---\n{front}---{body}"


def replace_frontmatter(text: str, data: dict[str, Any]) -> str:
    """Rewrite only the frontmatter block, preserving the entire body verbatim."""
    _, body = split_frontmatter(text)
    return join_frontmatter(data, body)


# --------------------------------------------------------------------------- sections


def has_section(text: str, tag: str) -> bool:
    return markers.open_marker(tag) in text and markers.close_marker(tag) in text


def find_markers(text: str) -> list[str]:
    """All sq marker comment strings present (open and close), for lint/repair.

    Only matches well-formed tags (``sq:`` + alnum start), so documentation references like
    ``<!-- sq:* -->`` written in prose are not mistaken for real markers.
    """
    return re.findall(r"<!--\s*(sq:[a-z0-9][a-z0-9:_-]*)\s*-->", text)


def get_section(text: str, tag: str) -> str | None:
    """Return the inner content of a section, or None if the section is absent."""
    o, c = markers.open_marker(tag), markers.close_marker(tag)
    oi = text.find(o)
    if oi == -1:
        return None
    start = oi + len(o)
    ci = text.find(c, start)
    if ci == -1:
        return None
    return text[start:ci]


def replace_section(text: str, tag: str, new_inner: str) -> str:
    o, c = markers.open_marker(tag), markers.close_marker(tag)
    oi = text.find(o)
    ci = text.find(c, oi + len(o)) if oi != -1 else -1
    if oi == -1 or ci == -1:
        raise KeyError(f"section {tag!r} not found")
    if not new_inner.startswith("\n"):
        new_inner = "\n" + new_inner
    if not new_inner.endswith("\n"):
        new_inner = new_inner + "\n"
    return text[: oi + len(o)] + new_inner + text[ci:]


def region_lines(text: str, tag: str) -> tuple[int, int] | None:
    """1-based line numbers of a section's open and close marker lines, or None."""
    o, c = markers.open_marker(tag), markers.close_marker(tag)
    start = end = None
    for i, line in enumerate(text.splitlines(), 1):
        if start is None and o in line:
            start = i
        elif start is not None and c in line:
            end = i
            break
    return (start, end) if start and end else None


def append_to_section(text: str, tag: str, snippet: str) -> str:
    """Insert ``snippet`` just before the section's close marker."""
    c = markers.close_marker(tag)
    ci = text.find(c)
    if ci == -1:
        raise KeyError(f"section {tag!r} not found")
    if not snippet.endswith("\n"):
        snippet = snippet + "\n"
    return text[:ci] + snippet + text[ci:]
