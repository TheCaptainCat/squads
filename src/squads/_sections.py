"""Marker-safe operations on sq-managed markdown.

All section edits go through here so we only ever touch content *between* a section's open and
close markers, leaving the marker lines and surrounding agent-authored prose intact.
"""

import re
from typing import Any, cast

import yaml

from squads._errors import SquadsError
from squads._models import _markers as markers

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)

#: A well-formed sq marker comment, capturing its tag.
#:
#: The tag grammar is ``sq:`` + a word-character-initial run of word characters, ``:``
#: separators and hyphens. ``\w`` is Unicode-aware and therefore case-blind, which is the whole
#: point: a sub-entity region's tag embeds its ``local_id`` (``story:US<n>``, ``subtask:ST<n>``,
#: ``finding:F<n>``), and every declared ``local_prefix`` — bundled or adopter-declared — is
#: free to be uppercase or mixed-case. A lowercase-only class silently matched none of them, so
#: every consumer of :func:`find_markers` went blind to every sub-entity marker in the corpus.
#:
#: It stays strict about *well-formedness*, which is the other half of the contract: the
#: documentation placeholders that appear in agent-facing prose — ``<!-- sq:* -->`` in a role
#: file, ``<!-- sq:… -->`` in this project's own marker-rejection error message — carry
#: characters no real tag can contain and still do not lint as markers.
MARKER_RE = re.compile(r"<!--\s*(sq:\w[\w:-]*)\s*-->")


# --------------------------------------------------------------------------- frontmatter


def split_frontmatter(text: str, *, source: str | None = None) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body). Empty dict if there is no frontmatter block.

    Raises :class:`SquadsError` when the block between intact ``---`` delimiters is not
    valid YAML — a hand-edit, an unresolved merge conflict, a file restored from a partial
    patch. ``source`` names the offending file in that message when the caller has a path;
    callers that only hold text (no path in scope) leave it unset and the message degrades
    to the parse failure alone.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        where = f" in {source}" if source else ""
        raise SquadsError(f"malformed frontmatter{where}: {exc}") from exc
    data: dict[str, Any] = cast("dict[str, Any]", loaded) if isinstance(loaded, dict) else {}
    return data, text[m.end() :]


def join_frontmatter(data: dict[str, Any], body: str) -> str:
    front = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
    if not body.startswith("\n"):
        body = "\n" + body
    return f"---\n{front}---{body}"


def replace_frontmatter(text: str, data: dict[str, Any], *, source: str | None = None) -> str:
    """Rewrite only the frontmatter block, preserving the entire body verbatim."""
    _, body = split_frontmatter(text, source=source)
    return join_frontmatter(data, body)


# --------------------------------------------------------------------------- sections


def has_section(text: str, tag: str) -> bool:
    return markers.open_marker(tag) in text and markers.close_marker(tag) in text


def find_markers(text: str) -> list[str]:
    """All sq marker tags present (open and close), in file order, for lint/repair.

    Matches *every* well-formed tag (:data:`MARKER_RE`) **wherever it appears**, including the
    mixed-case sub-entity region tags (``sq:finding:F<n>:body``) that make up the bulk of the
    markers in a real item file.

    **Position is irrelevant, and an earlier version of this docstring said otherwise.** It
    claimed a reference "written in prose" was not mistaken for a real marker. Driven with a
    control: a bare well-formed tag matches, the identical tag wrapped in backticks matches, and
    so does one inside a fenced code block — backticks and fences sit outside ``MARKER_RE`` in
    both directions and neutralise nothing. What makes the documented ``sq:*`` form safe to write
    in prose is the ``*`` alone, which is not in the tag's character class (word characters, ``:``
    and ``-``); quoting a *real* tag leaves it fully matched.

    **What keeps authored content free of live markers is a different mechanism**:
    :func:`~squads._services._base.reject_markers`, which every prose input entering a marker
    region passes through before any write (ten call sites — item and sub-entity bodies, titles,
    comment messages, and the importer's equivalents). It refuses marker-shaped text at the door,
    and its own message says backtick-wrapping does not help.

    The distinction is load-bearing rather than pedantic, and it is why this paragraph is here at
    all: someone widening the sweep's frozen region-tag list
    (:func:`~squads._services._maintenance._retired_region_tags`) reasons from the recorded
    argument. "A quoted tag is not matched" invites the belief that a corpus is safe because its
    authors quoted; it is safe because a guard refused it at the door. Those two readings agree
    everywhere the guard runs and diverge exactly where it does not — a corpus adopted from
    outside squads, whose files never passed through any write path.
    """
    return MARKER_RE.findall(text)


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


def remove_section(text: str, tag: str) -> str:
    """Excise a whole section: its open marker through the matching close marker, inclusive.

    The complement to :func:`replace_section` — drops a scaffolded region wholesale (e.g. a
    removed sub-entity block, whose nested ``:head``/``:body``/``:discussion`` sub-regions live
    between the same open/close pair) rather than editing its inner content. Also absorbs a
    single blank separator line immediately above the block, if present — every scaffolded block
    owns the blank line *before* it (see ``templates/subentities/block.md.j2``), so without this
    a removed middle block would leave a doubled blank line behind. Raises ``KeyError`` if the
    section isn't present (mirrors :func:`get_section`/:func:`replace_section`).
    """
    o, c = markers.open_marker(tag), markers.close_marker(tag)
    oi = text.find(o)
    ci = text.find(c, oi + len(o)) if oi != -1 else -1
    if oi == -1 or ci == -1:
        raise KeyError(f"section {tag!r} not found")
    start = text.rfind("\n", 0, oi) + 1
    if text[:start].endswith("\n\n"):
        start -= 1  # absorb the blank line this block owns
    end = ci + len(c)
    if text[end : end + 1] == "\n":
        end += 1
    return text[:start] + text[end:]


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
