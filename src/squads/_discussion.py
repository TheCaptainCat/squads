"""Build collaboration content: comments, and the presentation of sub-entity blocks.

A sub-entity's machine state (status, assignee, field values, mapping) lives in the parent
item's frontmatter, see :class:`squads._models._subentity.SubEntity`. This module owns its
prose and presentation, scaffolded as marker-scoped regions in the parent's body:
  - a heading line (``### US<n> — title``), rendered from the stored title,
  - an sq-owned ``…:head`` region, a human-readable badge mirror of the state,
  - a ``…:body`` region the agent writes freely, and
  - a ``…:discussion`` region ``sq`` appends comments to.
The parent's sq-managed ``:summary`` table rolls up its children's state. Only the migrations
touch the legacy body-stored ``:meta`` regions, via ``_migrations._meta_compat``.
"""

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import NamedTuple

from squads import _badges as badges
from squads._errors import CommentNotFoundError, SquadsError
from squads._models import _markers as markers
from squads._models._item import Item
from squads._models._participants import SLUG_PATTERN, require_valid_slug
from squads._models._subentity import SubEntity
from squads._rendering._engine import render
from squads._sections import (
    append_to_section,
    find_markers,
    get_section,
    iter_marker_spans,
    replace_section,
    split_lines,
)
from squads._workflow import WorkflowSpec

_MENTION_RE = re.compile(r"(?<![A-Za-z0-9_])@([a-z0-9][a-z0-9-]*)")

_TS = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"

# The one comment-header pattern, anchored at column 0 and never applied to a stripped line.
# The optional ``, edited <ts>`` is not part of the comment's hash:
#   - [2026-06-07T10:00:00Z] `architect` Robert Architect:
#   - [2026-06-07T10:00:00Z, edited 2026-06-08T09:00:00Z] `architect` Robert Architect:
_COMMENT_HEADER_RE = re.compile(rf"^- \[({_TS})(?:, edited ({_TS}))?\] `({SLUG_PATTERN})` (.+):$")

_HASH_DOMAIN = "sq-comment-1"
SHORT_HASH_LENGTH = 7
#: The length of a comment's full hash, a SHA-256 in hex.
FULL_HASH_LENGTH = 64
MIN_HASH_PREFIX = 4

_HEX_RE = re.compile(r"[0-9a-fA-F]+")


# --------------------------------------------------------------------------- comments


def format_comment(
    timestamp_iso: str,
    slug: str,
    name: str,
    messages: list[str],
    *,
    edited_ts: str | None = None,
) -> str:
    """One discussion entry: a header naming the author's slug and display name, then one bullet
    per message.

    The name is a display snapshot: line breaks collapse to spaces and an empty name falls back to
    the slug. A multi-line message keeps its first line on the bullet and indents continuation
    lines so they stay nested under it. ``edited_ts`` adds the edit mark to the header.
    """
    require_valid_slug(slug, action="write a comment")
    shown = " ".join(part.strip() for part in name.splitlines() if part.strip()) or slug
    mark = f", edited {edited_ts}" if edited_ts else ""
    lines = [f"- [{timestamp_iso}{mark}] `{slug}` {shown}:"]
    for msg in messages:
        # split on every break str.splitlines knows, so no author line can land at column 0
        first, *rest = msg.splitlines() or [""]
        lines.append(f"  - {first}")
        # indent *every* continuation line (blanks included) to the bullet's content column, so a
        # nested fenced code block — and its internal blank lines — stays inside the list item.
        lines += [f"    {ln}" for ln in rest]
    return "\n".join(lines)


@dataclass
class Comment:
    """A single parsed comment from a discussion region."""

    timestamp: str
    author: str  # the display name written in the header
    author_slug: str
    body: str  # the raw bullet lines for this comment, stripped of their outer indentation
    hash: str = ""  # derived on load, never written
    edited_ts: str | None = None
    span: tuple[int, int] = (0, 0)  # the region's lines [start, end): header to the next header


def _region_lines(region: str) -> list[str]:
    """*region*'s lines with their terminators (CRLF, CR and LF alike), none merged or lost."""
    return split_lines(region, keepends=True)


def _content(line: str) -> str:
    return line.rstrip("\r\n")


def canonical_text(lines: Sequence[str]) -> str:
    """A comment's stored lines as the hash reads them.

    Trailing spaces and tabs are stripped per line, leading and trailing blank lines are dropped,
    and the rest is kept byte for byte, joined with LF. Line terminators are ignored, so CRLF, CR
    and LF checkouts hash alike.
    """
    stripped = [_content(ln).rstrip(" \t") for ln in lines]
    filled = [i for i, ln in enumerate(stripped) if ln]
    if not filled:
        return ""
    return "\n".join(stripped[filled[0] : filled[-1] + 1])


def comment_hash(sequence_id: int, scope: str, slug: str, timestamp: str, text: str) -> str:
    """The comment's address: SHA-256 hex over its item's sequence number, discussion scope,
    author slug, header timestamp and canonical text."""
    payload = "\0".join((_HASH_DOMAIN, str(sequence_id), scope, slug, timestamp, text))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def split_discussion(region: str, *, sequence_id: int, scope: str = "") -> list[Comment]:
    """Parse a discussion region (the content between sq:discussion markers) into Comments.

    Each comment starts with ``- [TIMESTAMP] `slug` Author:`` (``- [TIMESTAMP, edited TIMESTAMP]
    ...`` once edited) and is followed by indented bullet lines (``  - text``) or continuation
    lines (``    text``). The body keeps the bullets as-is, fenced code blocks included, stripping
    only the leading 2-space indent so it reads as standalone markdown. Lines that do not start
    a new header join the current comment; an empty or whitespace-only region gives an empty
    list. This is the inverse of :func:`format_comment`.

    ``sequence_id`` is the owning item's sequence number and ``scope`` the discussion's (``""`` for
    the item's own, ``<kind>:<local_id>`` for a sub-entity's); with the header and text they give
    each comment its ``hash``.
    """
    lines = _region_lines(region)
    heads = [(i, m) for i, ln in enumerate(lines) if (m := _COMMENT_HEADER_RE.match(_content(ln)))]
    comments: list[Comment] = []
    for n, (start, m) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        ts, edited, slug, name = m.group(1), m.group(2), m.group(3), m.group(4)
        # Strip the 2-space indent that format_comment adds at the message level. Continuation
        # lines have 4 spaces; after stripping 2 they become "  text", which renders correctly
        # under the bullet. Blank lines are not collapsed: fenced code blocks depend on them.
        body = [
            _content(ln)[2:] if ln.startswith("  ") else _content(ln)
            for ln in lines[start + 1 : end]
        ]
        comments.append(
            Comment(
                timestamp=ts,
                author=name,
                author_slug=slug,
                body="\n".join(body).strip(),
                hash=comment_hash(
                    sequence_id, scope, slug, ts, canonical_text(lines[start + 1 : end])
                ),
                edited_ts=edited,
                span=(start, end),
            )
        )
    return comments


def short_hashes(comments: Sequence[Comment]) -> list[str]:
    """Each comment's displayed hash: 7 characters, widened for the whole scope to the shortest
    length at which its distinct hashes tell apart."""
    distinct = {c.hash for c in comments}
    width = SHORT_HASH_LENGTH
    while len({h[:width] for h in distinct}) < len(distinct):
        width += 1
    return [c.hash[:width] for c in comments]


class OtherScope(NamedTuple):
    """Another discussion of the same item, consulted to name where a hash lives instead."""

    label: str  # "subtask 2"
    address: str  # "sq task 5 subtask 2 comment"
    comments: Sequence[Comment]


def is_hash_token(token: str) -> bool:
    """Whether *token* can address a comment: at least 4 hexadecimal characters."""
    return len(token) >= MIN_HASH_PREFIX and _HEX_RE.fullmatch(token) is not None


def resolve_hash(
    comments: Sequence[Comment],
    token: str,
    *,
    where: str,
    elsewhere: Sequence[OtherScope] = (),
) -> list[Comment]:
    """The comments a hash prefix addresses within one scope: the members of one duplicate group.

    ``where`` names the scope in messages (``the item's discussion``). A prefix matching two or more
    distinct hashes is refused with its candidates; one matching nothing here but something in
    ``elsewhere`` is refused naming that address. Nothing outside the scope is ever returned.
    """
    if not is_hash_token(token):
        raise SquadsError(
            f"{token!r} is not a comment hash (4 or more hex characters); "
            "a new comment takes -m or --file"
        )
    prefix = token.lower()
    hits = [c for c in comments if c.hash.startswith(prefix)]
    distinct = list(dict.fromkeys(c.hash for c in hits))
    if len(distinct) > 1:
        shown = dict(zip((c.hash for c in comments), short_hashes(comments), strict=True))
        firsts = [next(c for c in hits if c.hash == h) for h in distinct]
        listed = "; ".join(f"{shown[c.hash]} ({c.author_slug}, {c.timestamp})" for c in firsts)
        raise SquadsError(f"{token} is ambiguous in {where}: {listed}")
    if hits:
        return hits
    # A full hash is what a removal sends after its preview; name it as the preview showed it.
    named = token[:SHORT_HASH_LENGTH] if len(token) == FULL_HASH_LENGTH else token
    for other in elsewhere:
        if any(c.hash.startswith(prefix) for c in other.comments):
            raise CommentNotFoundError(
                f"no comment {named} in {where}; it is in {other.label} "
                f"({other.address} {named} ...)"
            )
    raise CommentNotFoundError(
        f"no comment {named} in {where} (edited or removed since it was read?)"
    )


def author_label(cmt: Comment) -> str:
    """The author as a person reads it: ``Name (slug)``, or the slug once when the name is it."""
    return cmt.author if cmt.author == cmt.author_slug else f"{cmt.author} ({cmt.author_slug})"


def comment_json(cmt: Comment, short_hash: str) -> dict[str, str | None]:
    """One discussion entry for ``--json``: the display name, the permanent slug, time, edit
    time, full and displayed hash, and body."""
    return {
        "author": cmt.author,
        "author_slug": cmt.author_slug,
        "ts": cmt.timestamp,
        "edited_ts": cmt.edited_ts,
        "hash": cmt.hash,
        "short_hash": short_hash,
        "body": cmt.body,
    }


def comments_json(comments: Sequence[Comment]) -> list[dict[str, str | None]]:
    """:func:`comment_json` for a whole discussion, with hashes shown at the scope's length."""
    return [
        comment_json(c, short) for c, short in zip(comments, short_hashes(comments), strict=True)
    ]


def edited_suffix(cmt: Comment) -> str:
    """``" (edited <ts>)"`` for an edited comment, else nothing."""
    return f" (edited {cmt.edited_ts})" if cmt.edited_ts else ""


def match_comment_header(line: str) -> tuple[str, str, str] | None:
    """If ``line`` is a comment header, return ``(timestamp, slug, name)``.

    Exposed for callers that need to attribute a line to *which* comment (e.g. search result
    region attribution) without re-parsing a whole discussion region via :func:`split_discussion`.
    """
    m = _COMMENT_HEADER_RE.match(line)
    return (m.group(1), m.group(3), m.group(4)) if m else None


def legacy_header_lines(region: str) -> list[tuple[int, str]]:
    """Column-0 lines that open like a header (``- [``) but are not in the grammar, as 1-based
    ``(line, text)`` within *region*: a header from before the slug, or stray prose. Such a line
    is folded into the comment above it, so a splice must not run over it."""
    return [
        (i, _content(ln))
        for i, ln in enumerate(_region_lines(region), 1)
        if ln.startswith("- [") and _COMMENT_HEADER_RE.match(_content(ln)) is None
    ]


def replace_comments(
    region: str,
    changes: Sequence[tuple[Comment, str | None]],
    *,
    sequence_id: int,
    scope: str = "",
) -> str:
    """*region* with the given comments replaced by an entry or, for ``None``, removed.

    Each comment is edited by its line span (header to the next header); every other line, the
    preamble included, stays byte-identical. A replacement keeps the blank lines that followed the
    comment and takes the line terminator of the header it replaces. A removal takes the comment
    and the blank lines after it; the last comment, when nothing followed it, takes the blank
    lines before it instead (unless it is the first comment, whose predecessor is the preamble).

    A span is valid only against the exact string it was parsed from. *region* is parsed again
    here, and a change whose comment is not the one now at its span (same hash) is refused.
    """
    current = {c.span: c for c in split_discussion(region, sequence_id=sequence_id, scope=scope)}
    for cmt, _ in changes:
        found = current.get(cmt.span)
        if found is None or found.hash != cmt.hash:
            raise SquadsError("the discussion changed since the comment was read; read it again")
    lines = _region_lines(region)
    first_head = next(
        (i for i, ln in enumerate(lines) if _COMMENT_HEADER_RE.match(_content(ln))), len(lines)
    )
    gone: set[int] = set()
    swapped: dict[int, list[str]] = {}
    for cmt, entry in changes:
        start, end = cmt.span
        content_end = end
        while content_end > start + 1 and not _content(lines[content_end - 1]).strip():
            content_end -= 1
        if entry is None:
            gone.update(range(start, end))
            if end == content_end and end == len(lines) and start > first_head:
                back = start
                while back > 0 and not _content(lines[back - 1]).strip():
                    back -= 1
                    gone.add(back)
            continue
        eol = lines[start][len(_content(lines[start])) :] or "\n"
        new = [ln + eol for ln in entry.split("\n")]
        if content_end == len(lines) and not lines[-1].endswith(("\n", "\r")):
            new[-1] = new[-1][: -len(eol)]
        swapped[start] = new
        gone.update(range(start + 1, content_end))
    out: list[str] = []
    for i, ln in enumerate(lines):
        if i in swapped:
            out.extend(swapped[i])
        elif i not in gone:
            out.append(ln)
    return "".join(out)


def extract_mentions(text: str) -> set[str]:
    """All ``@slug`` mentions in a blob of text (lowercased slugs)."""
    return {m.lower() for m in _MENTION_RE.findall(text)}


# --------------------------------------------------------------------------- ids / tags


def local_id_for(kind: str, token: str, spec: WorkflowSpec) -> str:
    """Normalize a CLI local-id token to its canonical form: ``2`` → ``STn``/``USn``/``Fn``.

    The prefix resolves from *kind*'s ``SubentityKindSpec.local_prefix`` in the given (or
    bundled) spec.
    """
    prefix = spec.subentity_kinds[kind].local_prefix
    t = token.strip()
    return f"{prefix}{int(t)}" if t.isdigit() else t.upper()


def next_local_id(subentities: list[SubEntity], kind: str, spec: WorkflowSpec) -> str:
    """The next free local id for ``kind``, computed from the parent's stored sub-entities.

    It uses the live set's max, not a persisted high-water mark (unlike the item-level counter).
    Removing a sub-entity that is not the highest leaves a gap that is never reissued; removing the
    highest frees its number for the next one added. That is accepted: a local id is a
    within-parent label, not a durable cross-repo identity, so no persisted state closes it (see
    ``remove_block``).
    """
    prefix = spec.subentity_kinds[kind].local_prefix
    nums = [
        int(s.local_id[len(prefix) :])
        for s in subentities
        if s.local_id.startswith(prefix) and s.local_id[len(prefix) :].isdigit()
    ]
    return f"{prefix}{(max(nums) + 1) if nums else 1}"


def body_tag(kind: str, local_id: str) -> str:
    return f"{kind}:{local_id}:body"


def _head_tag(kind: str, local_id: str) -> str:
    return f"{kind}:{local_id}:head"


# --------------------------------------------------------------------------- block scaffold


def _generic_placeholder(kind: str) -> str:
    """Scaffold prose for a kind that declares no explicit ``placeholder``."""
    return f"_Describe this {kind} here — free-form paragraphs or bullet lists._"


def body_placeholder(kind: str, spec: WorkflowSpec) -> str:
    """The italic placeholder a freshly-scaffolded ``:body`` region holds until content is set.

    Resolves ``SubentityKindSpec.placeholder``; a kind that declares none (``None``) falls
    back to a generic kind-name-derived scaffold line.
    """
    ks = spec.subentity_kinds[kind]
    return ks.placeholder or _generic_placeholder(kind)


def build_block(
    kind: str,
    local_id: str,
    title: str = "",
    *,
    body: str | None = None,
    spec: WorkflowSpec,
    from_squad: Path | None,
) -> str:
    """A sub-entity block: heading + empty ``:head`` + ``:body`` + ``:discussion``.

    State (status, assignee, field values, mapping) lives in the parent's frontmatter, not here.
    The skeleton
    lives in ``templates/subentities/block.md.j2`` (sub-tags derive from ``tag``); the ``:head`` is
    filled by :func:`set_head` right after.
    """
    heading = f"### {local_id} — {title}".rstrip()
    return render(
        "subentities/block.md.j2",
        from_squad=from_squad,
        tag=f"{kind}:{local_id}",
        heading=heading,
        body=body or body_placeholder(kind, spec),
    )


def set_heading(text: str, kind: str, local_id: str, title: str) -> str:
    """Re-render a block's ``### {local_id} — {title}`` heading from the stored title (idempotent).

    The heading is a derived projection of the frontmatter title (like ``:head``); scoped to the
    first heading line after the block's opener marker so sibling blocks are untouched.
    """
    opener = markers.open_marker(f"{kind}:{local_id}")
    oi = text.find(opener)
    if oi == -1:
        return text
    heading = f"### {local_id} — {title}".rstrip()
    pat = re.compile(rf"###[ \t]*{re.escape(local_id)}[ \t]*(?:—[ \t]*)?[^\n]*")
    m = pat.search(text, oi + len(opener))
    if m is None:
        return text
    return text[: m.start()] + heading + text[m.end() :]


# --------------------------------------------------------------------------- head region


def set_head(  # noqa: PLR0913 — the head's whole state, passed by keyword
    text: str,
    kind: str,
    local_id: str,
    *,
    status: str | None = None,
    field_values: Mapping[str, str] | None = None,
    mapping: str | None = None,
    assignee_name: str | None = None,
    spec: WorkflowSpec,
    from_squad: Path | None,
) -> str:
    """(Re)render the human-readable ``:head`` region under a block's heading.

    A presentation mirror of the frontmatter state: status and each field with a value as coloured
    badges, the mapped sub-entity, the assignee's full name. The layout is
    ``templates/subentities/head.md.j2``, which receives ``status``, ``assignee``, ``fields`` (a
    list of ``code``, ``label`` and ``badge``, in declared order) and ``mapping`` (``label`` and
    ``value``, or ``None``). New blocks ship the region empty (from ``block.md.j2``); a legacy
    block that lacks it gets it created just before the block's ``:body`` marker.
    """
    head_tag = _head_tag(kind, local_id)
    held = field_values or {}
    target = spec.mapping_target_kind(kind)
    inner = render(
        "subentities/head.md.j2",
        from_squad=from_squad,
        status=badges.status_badge(status, spec) if status else None,
        fields=[
            {
                "code": f.code,
                "label": f.label,
                "badge": badges.badge_render(
                    badges.resolve_collection(kind, f.code, spec),
                    held[f.code],
                    spec,
                    as_label=True,
                ),
            }
            for f in spec.fields_for(kind)
            if held.get(f.code)
        ],
        mapping={"label": target.title(), "value": mapping} if mapping and target else None,
        assignee=assignee_name,
    )
    if get_section(text, head_tag) is None:
        if not inner.strip():
            return text  # nothing to show and no region yet — keep the block clean
        body_open = markers.open_marker(body_tag(kind, local_id))
        region = f"{markers.open_marker(head_tag)}\n{markers.close_marker(head_tag)}\n\n"
        text = text.replace(body_open, region + body_open, 1)
    return replace_section(text, head_tag, inner)


# --------------------------------------------------------------------------- summary table


def summary_columns(kind: str, spec: WorkflowSpec) -> list[str]:
    """The header row for *kind*'s summary/list table.

    A fixed base (local-id column headed by the kind name, then Status/Assignee/Title), one column
    per declared ``Field`` headed by its ``label`` and inserted right after the local-id column, and
    a trailing column headed by the target kind iff the kind declares ``maps_to_parent``. The body
    summary table and
    the CLI list/show tables share this derivation.
    """
    field_labels = [f.label for f in spec.fields_for(kind)]
    cols = [kind.title(), *field_labels, "Status", "Assignee", "Title"]
    target = spec.mapping_target_kind(kind)
    if target is not None:
        cols.append(target.title())
    return cols


def _field_value(sub: SubEntity, code: str) -> str | None:
    """The stored badge code for a declared field (:meth:`SubEntity.badge_value`)."""
    return sub.badge_value(code)


def summary_row(kind: str, sub: SubEntity, spec: WorkflowSpec) -> list[str]:
    """One row aligned to :func:`summary_columns`: local id, field badges, base, then the mapping.

    A field cell renders through :func:`~squads._badges.badge_render`'s default
    (``as_label=False``), emoji plus raw code (``"🔴 critical"``). A project's own view over the
    same data may render the badge differently, so a roll-up template is free to differ from this
    row.
    """
    field_cells = [
        badges.badge_render(badges.resolve_collection(kind, f.code, spec), value, spec)
        if (value := _field_value(sub, f.code))
        else ""
        for f in spec.fields_for(kind)
    ]
    row = [sub.local_id, *field_cells, sub.status, sub.assignee or "", sub.title]
    ks = spec.subentity_kinds.get(kind)
    if ks is not None and ks.maps_to_parent:
        row.append(sub.maps_to or "")
    return row


def render_summary(
    kind: str, subentities: list[SubEntity], spec: WorkflowSpec, *, from_squad: Path | None
) -> str:
    """The sq-managed roll-up table for a parent's sub-entities (empty until there are any).

    The table layout lives in ``templates/subentities/summary.md.j2``.
    """
    if not subentities:
        return ""
    cols = summary_columns(kind, spec)
    return render(
        "subentities/summary.md.j2",
        from_squad=from_squad,
        cols=cols,
        seps=["---"] * len(cols),
        rows=[summary_row(kind, s, spec) for s in subentities],
    )


def ensure_container(text: str, heading: str, container: str) -> str:
    """Append ``## <heading>`` + an empty marker pair for ``container`` if the section is missing.

    Used by retype to scaffold a container block (e.g. ``sq:subtasks``) when an item gains a type
    that hosts sub-entities.  Idempotent: returns the text unchanged if the section is present.
    """
    open_tag = markers.open_marker(container)
    if open_tag in text:
        return text  # already present
    block = (
        f"\n\n## {heading}\n\n{markers.open_marker(container)}\n{markers.close_marker(container)}\n"
    )
    return text + block


def _pair_absent(text: str, tag: str) -> bool:
    return markers.open_marker(tag) not in text and markers.close_marker(tag) not in text


def stale_container_tags(text: str, plural: str) -> list[str]:
    """The top-level container-like tags *text* carries other than the declared *plural* and the
    fixed structural ones: the container a renamed plural left behind."""
    structural = {markers.BODY, markers.SUMMARY, markers.DISCUSSION, plural}
    tags = {tag.removeprefix(markers.PREFIX).removesuffix(":end") for tag in find_markers(text)}
    return sorted(tag for tag in tags if ":" not in tag and tag not in structural)


def _pair(tag: str, inner: str = "") -> str:
    body = f"{inner}\n" if inner else ""
    return f"{markers.open_marker(tag)}\n{body}{markers.close_marker(tag)}\n"


def _insert_at_line_start(text: str, at: int, chunk: str) -> str:
    """*text* with *chunk* (its own lines) inserted at line start *at*, set off by blank lines."""
    lead = "" if at == 0 or text[:at].endswith("\n\n") else "\n"
    tail = "" if text[at : at + 1] in ("", "\n") else "\n"
    return text[:at] + lead + chunk + tail + text[at:]


def _before_region(text: str, tag: str, heading: str) -> int:
    """The line start to insert before the *tag* region: its open marker, or the *heading* line
    that sits directly above it when the template put one there."""
    at = text.find(markers.open_marker(tag))
    above = text[:at].rstrip("\n")
    line_start = above.rfind("\n") + 1
    return line_start if above[line_start:].strip() == heading else at


def _local_number(local_id: str) -> int:
    digits = re.search(r"\d+$", local_id)
    return int(digits.group()) if digits else 0


def restore_regions(
    text: str, item: Item, kind: str | None, spec: WorkflowSpec, *, from_squad: Path | None
) -> str:
    """*text* with every missing region a write may need added empty.

    That is a non-roster item's discussion (with its heading, at the end of the file) and, for each
    declared sub-entity of *kind*, its container (before the discussion), its block in id order, and
    the block's body and discussion. A region goes only between existing regions, never inside one;
    a surviving heading is not looked for, and a half-present pair is left to the marker check.
    """
    if not spec.item_is_roster(item.type) and _pair_absent(text, markers.DISCUSSION):
        text = text.rstrip("\n") + f"\n\n## Discussion\n\n{_pair(markers.DISCUSSION)}"
    if kind is None or not item.subentities:
        return text
    container = spec.subentity_plural(kind)
    if _pair_absent(text, container):
        if stale_container_tags(text, container):
            return text
        text = restore_container(text, item, kind, spec)
    for sub in item.subentities:
        tag = f"{kind}:{sub.local_id}"
        if _pair_absent(text, tag):
            text = _restore_block(text, item, kind, sub.local_id, sub.title, spec, from_squad)
        else:
            text = _restore_block_regions(text, kind, sub.local_id, spec)
    return text


def restore_container(text: str, item: Item, kind: str, spec: WorkflowSpec) -> str:
    """*text* with the missing container added around the item's surviving blocks of *kind*, so
    each sits inside it in id order; with none, an empty one before the item discussion.

    A heading already above the first block is reused, never written twice. Refuses, naming the
    item and the container, when prose sits between the surviving blocks: enclosing them would
    move it.
    """
    heading, container = spec.subentity_container_heading(kind), spec.subentity_plural(kind)
    spans = _surviving_block_spans(text, item, kind)
    if not spans:
        if (own := re.search(rf"^## {re.escape(heading)}[ \t]*$", text, re.MULTILINE)) is not None:
            following = re.compile(r"^## ", re.MULTILINE).search(text, own.end())
            return _insert_at_line_start(
                text, following.start() if following else len(text), _pair(container)
            )
        if markers.open_marker(markers.DISCUSSION) not in text:
            return ensure_container(text, heading, container)
        at = _before_region(text, markers.DISCUSSION, "## Discussion")
        return _insert_at_line_start(text, at, f"## {heading}\n\n{_pair(container)}")
    first, last = spans[0][1], max(end for _, _, end in spans)
    if any(text[end:start].strip() for (_, _, end), (_, start, _) in pairwise(spans)):
        raise SquadsError(
            f"{item.id}: cannot restore the {container} container, prose sits between its blocks"
            f" -- restore the {markers.open_marker(container)} and "
            f"{markers.close_marker(container)} lines by hand"
        )
    _refuse_inside_a_region(text, item, container, first, last)
    inner = text[first:last]
    ordered = sorted(spans, key=lambda span: _local_number(span[0]))
    if [span[0] for span in ordered] != [span[0] for span in spans]:
        inner = "\n".join(text[start:end] for _, start, end in ordered)
    after_region = max(
        (end for tag, _, end in iter_marker_spans(text) if end <= first and _closes_a_region(tag)),
        default=0,
    )
    own = re.search(rf"^## {re.escape(heading)}[ \t]*$", text[after_region:first], re.MULTILINE)
    lead = "" if own else f"## {heading}\n\n"
    opened = f"{lead}{markers.open_marker(container)}\n\n"
    return f"{text[:first]}{opened}{inner}{markers.close_marker(container)}\n{text[last:]}"


def _closes_a_region(tag: str) -> bool:
    """Whether *tag* closes a top-level region (``sq:body:end``), not a block or a sub-region."""
    return tag.endswith(":end") and tag.count(":") == 2


def _refuse_inside_a_region(text: str, item: Item, container: str, first: int, last: int) -> None:
    """Raise when the blocks to enclose sit inside another top-level region (the body, the
    discussion): the container would nest in it."""
    for tag in find_markers(text):
        name = tag.removeprefix(markers.PREFIX)
        if ":" in name or name == container:
            continue
        start = text.find(markers.open_marker(name))
        end = text.find(markers.close_marker(name), start)
        if start != -1 and end != -1 and start < first and last <= end:
            raise SquadsError(
                f"{item.id}: cannot restore the {container} container, its blocks sit inside the "
                f"{name} region -- move them out of it, or restore the {container} marker lines "
                "by hand"
            )


def _surviving_block_spans(text: str, item: Item, kind: str) -> list[tuple[str, int, int]]:
    """``(local_id, start, end)`` of each of the item's *kind* blocks whose pair is in *text*, in
    file order: *start* at the opening marker line, *end* just past the closing marker line."""
    spans: list[tuple[str, int, int]] = []
    for sub in item.subentities:
        tag = f"{kind}:{sub.local_id}"
        start = text.find(markers.open_marker(tag))
        close = text.find(markers.close_marker(tag), start) if start != -1 else -1
        if close == -1:
            continue
        line = text.rfind("\n", 0, start) + 1
        newline = text.find("\n", close)
        spans.append((sub.local_id, line, len(text) if newline == -1 else newline + 1))
    return sorted(spans, key=lambda span: span[1])


def _restore_block(
    text: str,
    item: Item,
    kind: str,
    local_id: str,
    title: str,
    spec: WorkflowSpec,
    from_squad: Path | None,
) -> str:
    """*text* with the absent block for *local_id* added inside its container, before the first
    present block with a higher number, else at the end."""
    block = build_block(kind, local_id, title, spec=spec, from_squad=from_squad)
    number = _local_number(local_id)
    for other in item.subentities:
        if _local_number(other.local_id) > number:
            marker = markers.open_marker(f"{kind}:{other.local_id}")
            if (at := text.find(marker)) != -1:
                return text[:at] + block.rstrip("\n") + "\n\n" + text[at:]
    return append_to_section(text, spec.subentity_plural(kind), block)


def _restore_block_regions(text: str, kind: str, local_id: str, spec: WorkflowSpec) -> str:
    """*text* with the block's absent body and discussion regions added empty: the body before
    the block's discussion (or at its end), the discussion, under a heading of its own, right
    after the body."""
    tag = f"{kind}:{local_id}"
    open_at = text.find(markers.open_marker(tag))
    if open_at == -1 or text.find(markers.close_marker(tag), open_at) == -1:
        return text
    body_name, disc_tag = body_tag(kind, local_id), markers.discussion_tag(tag)

    def span() -> tuple[int, int]:
        start = text.find(markers.open_marker(tag))
        return start, text.find(markers.close_marker(tag), start)

    start, end = span()
    if _pair_absent(text[start:end], body_name):
        pair = _pair(body_name, body_placeholder(kind, spec))
        if markers.open_marker(disc_tag) in text[start:end]:
            at = _before_region(text, disc_tag, "#### Discussion")
        else:
            at = end
        text = _insert_at_line_start(text, at, pair)
        start, end = span()
    if _pair_absent(text[start:end], disc_tag):
        close = text.find(markers.close_marker(body_name), start)
        at = text.find("\n", close) + 1 if close != -1 and close < end else end
        text = _insert_at_line_start(text, at, f"#### Discussion\n\n{_pair(disc_tag)}")
    return text


def ensure_summary(
    text: str,
    kind: str,
    container: str,
    subentities: list[SubEntity],
    spec: WorkflowSpec,
    *,
    from_squad: Path | None,
) -> str:
    """Insert an empty ``sq:summary`` region before ``container`` if missing, then (re)render it."""
    if get_section(text, markers.SUMMARY) is None:
        region = (
            f"{markers.open_marker(markers.SUMMARY)}\n{markers.close_marker(markers.SUMMARY)}\n\n"
        )
        text = text.replace(
            markers.open_marker(container), region + markers.open_marker(container), 1
        )
    return replace_section(
        text, markers.SUMMARY, render_summary(kind, subentities, spec, from_squad=from_squad)
    )
