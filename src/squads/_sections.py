"""Marker-safe operations on sq-managed markdown.

All section edits go through here so we only ever touch content *between* a section's open and
close markers, leaving the marker lines and surrounding agent-authored prose intact.
"""

import bisect
import difflib
import re
from collections.abc import Callable
from typing import Any, cast

from squads._errors import SquadsError
from squads._models import _markers as markers

_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---(?:\r?\n)?", re.DOTALL)

#: A well-formed sq marker comment, capturing its tag. ``\w`` is case-blind on purpose: a
#: sub-entity tag embeds its ``local_id`` (``story:US<n>``), whose prefix may be mixed-case.
#: Prose placeholders (``<!-- sq:* -->``) hold characters no real tag can, so never match.
MARKER_RE = re.compile(r"<!--\s*(sq:\w[\w:-]*)\s*-->")


# --------------------------------------------------------------------------- frontmatter


def split_frontmatter(text: str, *, source: str | None = None) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body); an empty dict if there is no frontmatter block.

    Raises :class:`SquadsError` when the block between intact ``---`` delimiters is not valid YAML
    (a hand-edit, an unresolved merge conflict). *source* names the file in the message; a caller
    holding only text leaves it unset and the message is the parse failure alone.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    import yaml

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
    import yaml

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

    Matches every well-formed tag (:data:`MARKER_RE`) wherever it appears, including mixed-case
    sub-entity tags (``sq:finding:F<n>:body``). Position is irrelevant: a tag in prose, wrapped in
    backticks or inside a fenced code block is still matched, since backticks and fences sit
    outside ``MARKER_RE``. The documented ``sq:*`` form is safe in prose only because ``*`` is not
    in the tag's character class (word characters, ``:`` and ``-``); quoting a real tag
    neutralises nothing.

    What keeps authored content free of live markers is
    :func:`~squads._services._base.reject_markers`, which every prose input entering a marker
    region passes through before a write (item and sub-entity bodies, titles, comment messages and
    the importer's equivalents); it refuses marker-shaped text and says backticks do not help. A
    corpus is safe because that guard refused live markers at the door, not because authors
    quoted them: a quoted tag is still matched here. The two diverge for a corpus adopted from
    outside squads, whose files never passed through a write path, so anyone widening the sweep's
    frozen region-tag list (:func:`~squads._services._maintenance._retired_region_tags`) must not
    reason from "a quoted tag is not matched".
    """
    return MARKER_RE.findall(text)


def iter_marker_spans(text: str) -> list[tuple[str, int, int]]:
    """Every well-formed marker tag in *text*, in file order, as ``(tag, start, end)``.

    The positional counterpart to :func:`find_markers`, for a caller that substitutes matches (such
    as read-time view-tag expansion): the spans are computed once against *text* as given, so a
    substitution is never scanned a second time.
    """
    return [(m.group(1), m.start(), m.end()) for m in MARKER_RE.finditer(text)]


def retag_markers(text: str, retag: Callable[[str], str | None]) -> str:
    """*text* with the tag of each marker *retag* answers for replaced, and every other byte
    kept: the marker line's own spacing and the content between markers are untouched. *retag*
    receives a tag as :func:`iter_marker_spans` reports it and answers its replacement, or ``None``
    to keep it."""
    parts: list[str] = []
    last = 0
    for tag, start, end in iter_marker_spans(text):
        renamed = retag(tag)
        if renamed is None or renamed == tag:
            continue
        parts += [text[last:start], text[start:end].replace(tag, renamed, 1)]
        last = end
    return "".join(parts) + text[last:]


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
    """Excise a whole section, its open marker through the matching close marker inclusive.

    The complement to :func:`replace_section`: it drops a scaffolded region wholesale (such as a
    removed sub-entity block with its nested ``:head``/``:body``/``:discussion``). It also absorbs
    the single blank separator line above the block, since every scaffolded block owns the blank
    line before it (``templates/subentities/block.md.j2``), so a removed middle block leaves no
    doubled blank. Raises ``KeyError`` if the section is absent, like :func:`get_section`.
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


def dominant_eol(text: str) -> str:
    """The line ending most of *text*'s lines use: CRLF when strictly more lines end in CRLF
    than in a bare LF, else LF."""
    crlf = text.count("\r\n")
    return "\r\n" if crlf > text.count("\n") - crlf else "\n"


#: Largest old x new middle (in lines) :func:`conform_line_endings` aligns with a full diff; a
#: larger edit span is aligned greedily, in linear time.
_FULL_DIFF_CELLS = 4_000_000


_RUN_FIELDS = 5


def _unique_anchors(
    old: list[str], new: list[str], o1: int, o2: int, n1: int, n2: int
) -> list[tuple[int, int]]:
    """Index pairs of lines that occur exactly once in ``old[o1:o2]`` and in ``new[n1:n2]``,
    reduced to the longest run that keeps both indices increasing."""
    seen_old: dict[str, int | None] = {}
    for i in range(o1, o2):
        seen_old[old[i]] = None if old[i] in seen_old else i
    seen_new: dict[str, int | None] = {}
    for j in range(n1, n2):
        seen_new[new[j]] = None if new[j] in seen_new else j
    pairs = [
        (i, j)
        for line, j in seen_new.items()
        if j is not None and (i := seen_old.get(line)) is not None
    ]
    pairs.sort(key=lambda pair: pair[1])
    tails: list[int] = []  # smallest tail old-index of an increasing run of each length
    link: list[int] = []  # index of the previous pair in the run ending at each pair
    ends: list[int] = []  # pair index ending the run of each length
    for k, (i, _j) in enumerate(pairs):
        at = bisect.bisect_left(tails, i)
        if at == len(tails):
            tails.append(i)
            ends.append(k)
        else:
            tails[at] = i
            ends[at] = k
        link.append(ends[at - 1] if at else -1)
    run: list[tuple[int, int]] = []
    k = ends[-1] if ends else -1
    while k != -1:
        run.append(pairs[k])
        k = link[k]
    return run[::-1]


def _align(old: list[str], new: list[str]) -> list[tuple[bool, int, int, int, int]]:
    """``(same, i1, i2, j1, j2)`` runs that cover *old* and *new* in order, where a ``same`` run
    holds equal lines. Equal head and tail lines of a span are matched first; the rest is diffed
    in full when small, and otherwise split at the lines unique to both sides (the longest
    in-order run of them) and each part aligned in turn. A part with no such line is left
    unmatched."""
    runs: list[tuple[bool, int, int, int, int]] = []
    # Spans still to align, and runs already settled, popped in file order.
    todo: list[tuple[int, int, int, int] | tuple[bool, int, int, int, int]] = [
        (0, len(old), 0, len(new))
    ]
    while todo:
        task = todo.pop()
        if len(task) == _RUN_FIELDS:
            runs.append(task)
            continue
        o1, o2, n1, n2 = task
        head = 0
        while o1 + head < o2 and n1 + head < n2 and old[o1 + head] == new[n1 + head]:
            head += 1
        tail = 0
        while (
            o2 - tail > o1 + head
            and n2 - tail > n1 + head
            and old[o2 - 1 - tail] == new[n2 - 1 - tail]
        ):
            tail += 1
        mo1, mo2, mn1, mn2 = o1 + head, o2 - tail, n1 + head, n2 - tail
        ahead: list[tuple[int, int, int, int] | tuple[bool, int, int, int, int]] = []
        if head:
            ahead.append((True, o1, mo1, n1, mn1))
        if mo2 > mo1 or mn2 > mn1:
            if (mo2 - mo1) * (mn2 - mn1) <= _FULL_DIFF_CELLS:
                matcher = difflib.SequenceMatcher(None, old[mo1:mo2], new[mn1:mn2], autojunk=False)
                ahead += [
                    (tag == "equal", mo1 + i1, mo1 + i2, mn1 + j1, mn1 + j2)
                    for tag, i1, i2, j1, j2 in matcher.get_opcodes()
                ]
            else:
                i_at, j_at = mo1, mn1
                anchors = _unique_anchors(old, new, mo1, mo2, mn1, mn2)
                for i, j in [*anchors, (mo2, mn2)]:
                    if i > i_at or j > j_at:
                        ahead.append((i_at, i, j_at, j) if anchors else (False, i_at, i, j_at, j))
                    if i < mo2:
                        ahead.append((True, i, i + 1, j, j + 1))
                    i_at, j_at = i + 1, j + 1
        if tail:
            ahead.append((True, mo2, o2, mn2, n2))
        todo.extend(reversed(ahead))
    return runs


def conform_line_endings(old: str, new: str) -> str:
    """*new* with every line it shares with *old*, or edits in place, keeping *old*'s ending, and
    every line it inserts or reflows ending in *old*'s dominant ending.

    A write that edits one region then leaves the rest of the file byte for byte, and what it
    adds matches the file. An *old* with no CR comes back with *new* unchanged.
    """
    if "\r" not in old:
        return new
    dominant = dominant_eol(old)
    old_lines, new_lines = split_lines(old, keepends=True), split_lines(new, keepends=True)

    def content(line: str) -> str:
        return line.rstrip("\r\n")

    out: list[str] = []
    for _same, i1, i2, j1, j2 in _align(
        [content(ln) for ln in old_lines], [content(ln) for ln in new_lines]
    ):
        # Lines the write left alone, and lines it edited in place, keep their own ending.
        paired = i2 - i1 == j2 - j1
        for k, new_line in enumerate(new_lines[j1:j2]):
            body, has_ending = content(new_line), new_line != content(new_line)
            old_line = old_lines[i1 + k] if paired else ""
            kept = old_line[len(content(old_line)) :] or dominant
            out.append(body + (kept if has_ending else ""))
    return "".join(out)


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
