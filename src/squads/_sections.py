"""Marker-safe operations on sq-managed markdown.

All section edits go through here so we only ever touch content *between* a section's open and
close markers, leaving the marker lines and surrounding agent-authored prose intact.
"""

import re
from collections.abc import Callable
from typing import Any, cast

import yaml

from squads._errors import SquadsError
from squads._models import _markers as markers

_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---(?:\r?\n)?", re.DOTALL)

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


def frontmatter_block_end(text: str) -> int | None:
    """Where the leading frontmatter block ends, or ``None`` when *text* does not open with one."""
    m = _FRONTMATTER_RE.match(text)
    return m.end() if m else None


def strip_frontmatter(text: str) -> str:
    """*text* without its leading frontmatter block, whether or not that block is valid YAML."""
    m = _FRONTMATTER_RE.match(text)
    return text[m.end() :] if m else text


def join_frontmatter(data: dict[str, Any], body: str, *, eol: str = "\n") -> str:
    """The frontmatter block of *data* followed by *body*, with *eol* as the line terminator of
    the block (and of the separator added when *body* does not open with one)."""
    front = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
    if eol != "\n":
        front = front.replace("\n", eol)
    if not body.startswith(("\n", "\r\n")):
        body = eol + body
    return f"---{eol}{front}---{body}"


def replace_frontmatter(text: str, data: dict[str, Any], *, source: str | None = None) -> str:
    """Rewrite only the frontmatter block, preserving the entire body verbatim and the line
    terminator the block was written with."""
    _, body = split_frontmatter(text, source=source)
    return join_frontmatter(data, body, eol="\r\n" if text.startswith("---\r\n") else "\n")


# --------------------------------------------------------------------------- sections


def has_section(text: str, tag: str) -> bool:
    return markers.open_marker(tag) in text and markers.close_marker(tag) in text


def with_discussion_region(text: str) -> str:
    """*text* with an empty top-level ``## Discussion`` region after its body region.

    The region goes on the line after the body region's end marker, in the file's own line
    ending, and nothing else changes. A text that already has the region, or has no body
    region to follow, comes back as it was.
    """
    if has_section(text, markers.DISCUSSION):
        return text
    close = markers.close_marker(markers.BODY)
    at = text.find(close)
    if at == -1:
        return text
    end = at + len(close)
    if text.startswith("\r\n", end):
        eol = "\r\n"
    elif text.startswith("\n", end):
        eol = "\n"
    else:
        eol = "\r\n" if "\r\n" in text else "\n"
    region = (
        f"{eol}## Discussion{eol}{eol}"
        f"{markers.open_marker(markers.DISCUSSION)}{eol}"
        f"{markers.close_marker(markers.DISCUSSION)}{eol}"
    )
    if text.startswith(eol, end):
        end += len(eol)
        return text[:end] + region + text[end:]
    return text[:end] + eol + region + text[end:]


def find_markers(text: str) -> list[str]:
    """All sq marker tags present (open and close), in file order, for lint/repair.

    Matches *every* well-formed tag (:data:`MARKER_RE`) **wherever it appears**, including the
    mixed-case sub-entity region tags (``sq:finding:F<n>:body``) that make up the bulk of the
    markers in a real item file.

    **Position is irrelevant.** A reference "written in prose" is still matched as a real
    marker: a bare well-formed tag matches, the identical tag wrapped in backticks matches, and
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


def iter_marker_spans(text: str) -> list[tuple[str, int, int]]:
    """Every well-formed marker tag in *text*, in file order, as ``(tag, start, end)`` —
    the positional counterpart to :func:`find_markers`.

    For a caller that must substitute matches without re-scanning the substituted text (e.g.
    read-time view-tag expansion): the spans are computed once, against *text* exactly as
    given, so building the result from these positions — rather than re-matching after each
    replacement — is what keeps a substitution from ever being scanned a second time.
    """
    return [(m.group(1), m.start(), m.end()) for m in MARKER_RE.finditer(text)]


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


def _terminator_at(text: str, pos: int) -> str:
    """The line terminator at *pos*, else the first one in *text*, else LF."""
    for eol in ("\r\n", "\n", "\r"):
        if text.startswith(eol, pos):
            return eol
    m = re.search(r"\r\n|\n|\r", text)
    return m.group(0) if m else "\n"


def replace_section(text: str, tag: str, new_inner: str) -> str:
    """*text* with the section's inner content replaced, padded by the file's own terminator
    (the one after the open marker) when *new_inner* does not already start and end on one."""
    o, c = markers.open_marker(tag), markers.close_marker(tag)
    oi = text.find(o)
    ci = text.find(c, oi + len(o)) if oi != -1 else -1
    if oi == -1 or ci == -1:
        raise KeyError(f"section {tag!r} not found")
    eol = _terminator_at(text, oi + len(o))
    if not new_inner.startswith(("\n", "\r")):
        new_inner = eol + new_inner
    if not new_inner.endswith(("\n", "\r")):
        new_inner = new_inner + eol
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


_LINE_RE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+")


def split_lines(text: str, *, keepends: bool = False) -> list[str]:
    """*text*'s lines, broken at CR, LF and CRLF only: the one line rule for every reader of an
    item file (``str.splitlines`` also breaks at U+2028, form feeds and others)."""
    lines = _LINE_RE.findall(text)
    return lines if keepends else [ln.rstrip("\r\n") for ln in lines]


def region_lines(text: str, tag: str) -> tuple[int, int] | None:
    """1-based line numbers of a section's open and close marker lines, or None."""
    o, c = markers.open_marker(tag), markers.close_marker(tag)
    start = end = None
    for i, line in enumerate(split_lines(text), 1):
        if start is None and o in line:
            start = i
        elif start is not None and c in line:
            end = i
            break
    return (start, end) if start and end else None


def append_to_section(text: str, tag: str, snippet: str) -> str:
    """Insert ``snippet`` just before the section's close marker, in the section's own line
    terminator (the one after the open marker)."""
    o, c = markers.open_marker(tag), markers.close_marker(tag)
    ci = text.find(c)
    if ci == -1:
        raise KeyError(f"section {tag!r} not found")
    oi = text.find(o)
    eol = _terminator_at(text, oi + len(o)) if oi != -1 else _terminator_at(text, ci)
    if not snippet.endswith("\n"):
        snippet = snippet + "\n"
    if eol != "\n":
        snippet = snippet.replace("\r\n", "\n").replace("\n", eol)
    return text[:ci] + snippet + text[ci:]


# ------------------------------------------------------------------- unpaired markers


def strip_marker_lines(text: str, keep: Callable[[str], bool]) -> tuple[str, list[str]]:
    """*text* with every well-formed marker whose raw tag fails *keep* removed, never rewriting
    a prose character. A marker alone on its own line takes the whole line, collapsing its
    flanking newlines the way a deleted line would; one sharing a line with prose loses only
    itself and the whitespace touching it. Several lone-line markers in a row are removed
    together, against only the true outer flank, so collapsing one never leaks into the next."""
    removed: list[str] = []
    result = text
    while True:
        spans = iter_marker_spans(result)
        idx = next((i for i, span in enumerate(spans) if not keep(span[0])), None)
        if idx is None:
            break
        raw, start, end = spans[idx]
        line_start = result.rfind("\n", 0, start) + 1
        next_nl = result.find("\n", end)
        line_end = next_nl if next_nl != -1 else len(result)
        alone = not result[line_start:start].strip() and not result[end:line_end].strip()
        if not alone:
            result = _strip_shared_line_marker(result, start, end)
            removed.append(raw)
            continue
        run_raw = [raw]
        run_line_end = line_end
        for nraw, nstart, nend in spans[idx + 1 :]:
            if keep(nraw) or result[run_line_end:nstart].strip("\n"):
                break
            n_line_start = result.rfind("\n", 0, nstart) + 1
            n_next_nl = result.find("\n", nend)
            n_line_end = n_next_nl if n_next_nl != -1 else len(result)
            if result[n_line_start:nstart].strip() or result[nend:n_line_end].strip():
                break
            run_raw.append(nraw)
            run_line_end = n_line_end
        result = _strip_lone_line(result, line_start, run_line_end)
        removed.extend(run_raw)
    if not removed:
        return text, []
    return result, removed


def _strip_lone_line(result: str, start: int, end: int) -> str:
    """Remove *result*'s ``[start, end)`` span — one lone-line marker, or a whole chain's first
    and last line together — collapsing its flanking newlines the way a plain deleted line
    would, with no padding at *result*'s own edges."""
    lead = 0
    while lead < 2 and start - lead - 1 >= 0 and result[start - lead - 1] == "\n":
        lead += 1
    trail = 0
    while trail < 2 and result[end + trail : end + trail + 1] == "\n":
        trail += 1
    if lead == 0 or trail == 0:
        keep_n = 0
    elif lead == 2 or trail == 2:
        keep_n = 2
    else:
        keep_n = 1
    return result[: start - lead] + ("\n" * keep_n) + result[end + trail :]


def _strip_shared_line_marker(result: str, start: int, end: int) -> str:
    """Remove *result*'s ``[start, end)`` marker — sharing its line with prose, per
    :func:`strip_marker_lines` — together with the one contiguous run of spaces/tabs directly
    touching it on whichever side has one (trailing preferred), never a newline and never the
    other side's whitespace."""
    trailing_ws = 0
    while result[end + trailing_ws : end + trailing_ws + 1] in (" ", "\t"):
        trailing_ws += 1
    if trailing_ws:
        end += trailing_ws
    else:
        while start > 0 and result[start - 1] in (" ", "\t"):
            start -= 1
    return result[:start] + result[end:]
