"""Build collaboration content: comments, and the presentation of sub-entity blocks.

Each sub-entity's **machine state** (status / assignee / severity / mapped story) lives in the
parent item's frontmatter — see :class:`squads._models._subentity.SubEntity`. This module owns its
**prose and presentation**, scaffolded as marker-scoped regions in the parent's body:
  - a heading line (``### US<n> — title``), rendered from the stored title,
  - an sq-owned ``…:head`` region — a human-readable badge mirror of the state,
  - a ``…:body`` region the **agent** writes freely, and
  - a ``…:discussion`` region ``sq`` appends comments to.
The parent's sq-managed ``:summary`` table rolls up its children's state.

The legacy body-stored ``:meta`` regions are gone from the live path; only the migrations still
touch them, via the frozen ``_migrations._meta_compat`` helpers.
"""

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from squads import _badges as badges
from squads._errors import SquadsError
from squads._models import _markers as markers
from squads._models._participants import SLUG_PATTERN, require_valid_slug
from squads._models._subentity import SubEntity
from squads._rendering._engine import render
from squads._sections import get_section, replace_section, split_lines
from squads._workflow import WorkflowSpec

_MENTION_RE = re.compile(r"(?<![A-Za-z0-9_])@([a-z0-9][a-z0-9-]*)")

_TS = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"

# The one comment-header pattern, anchored at column 0 and never applied to a stripped line. The
# optional ``, edited <ts>`` records the last edit and is not part of the comment's hash:
#   - [2026-06-07T10:00:00Z] `architect` Robert Architect:
#   - [2026-06-07T10:00:00Z, edited 2026-06-08T09:00:00Z] `architect` Robert Architect:
_COMMENT_HEADER_RE = re.compile(rf"^- \[({_TS})(?:, edited ({_TS}))?\] `({SLUG_PATTERN})` (.+):$")

_HASH_DOMAIN = "sq-comment-1"
SHORT_HASH_LENGTH = 7
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
    """Parse a discussion region (the content between sq:discussion markers) into Comment objects.

    Each comment starts with ``- [TIMESTAMP] `slug` Author:`` (``- [TIMESTAMP, edited TIMESTAMP]
    ...`` once edited) and is followed by indented bullet lines (``  - text`` or continuation
    lines ``    text``).  The body field preserves the bullets
    as-is (including any fenced code blocks), stripping only the leading 2-space indent level so
    it reads as standalone markdown.

    ``sequence_id`` is the owning item's sequence number and ``scope`` the discussion's (``""``
    for the item's own, ``<kind>:<local_id>`` for a sub-entity's); with the header and the text
    they give each comment its ``hash``.

    Empty or whitespace-only regions return an empty list.  Lines that do not start a new header
    are accumulated as the current comment's body.  This is the inverse of :func:`format_comment`.
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
    for other in elsewhere:
        if any(c.hash.startswith(prefix) for c in other.comments):
            raise SquadsError(
                f"no comment {token} in {where}; it is in {other.label} "
                f"({other.address} {token} ...)"
            )
    raise SquadsError(f"no comment {token} in {where} (edited or removed since it was read?)")


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

    This recomputes from the **live** set's max, not a persisted high-water mark (unlike the
    item-level global counter, which is stored and never rewinds). Practically: removing a
    sub-entity that is *not* the highest-numbered one leaves its id a genuinely sanctioned gap
    (the max is unaffected, so it's never reissued). Removing the *highest*-numbered one does
    free its number back up for reissue to the next one added — a sub-entity local id is a
    within-parent label, not a durable cross-repo identity like an item id, so this is accepted
    as-is rather than adding persisted state to close it (see ``remove_block``).
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

    State (status/assignee/severity/story) lives in the parent's frontmatter, not here. The skeleton
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
    severity: str | None = None,
    story: str | None = None,
    assignee_name: str | None = None,
    spec: WorkflowSpec,
    from_squad: Path | None,
) -> str:
    """(Re)render the human-readable ``:head`` region under a block's heading.

    A presentation mirror of the frontmatter state: status/severity as colored badges, the
    implemented story as ``USn — title``, the assignee's full name. The layout lives in
    ``templates/subentities/head.md.j2`` — add an attribute by passing a value here + a line there.
    New blocks ship the region empty (from ``block.md.j2``); on a legacy block that lacks it (the
    migration path) it's created lazily, just before the block's ``:body`` marker.

    ``spec`` is the active workflow spec, used to resolve the status badge and the severity
    axis's declared label (see :func:`squads._badges.status_badge` /
    :func:`squads._badges.field_label`).
    """
    head_tag = _head_tag(kind, local_id)
    inner = render(
        "subentities/head.md.j2",
        from_squad=from_squad,
        status=badges.status_badge(status, spec) if status else None,
        severity=(
            badges.badge_render(
                badges.resolve_collection(kind, "severity", spec), severity, spec, as_label=True
            )
            if severity
            else None
        ),
        severity_label=badges.field_label(kind, "severity", spec) if severity else None,
        story=story,
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

    Fixed base (local-id column headed by the kind name, then Status/Assignee/Title) + one
    column per declared ``Field`` (headed by its ``label`` — e.g. Severity — inserted right
    after the local-id column) + a trailing Story column iff the kind declares
    ``maps_parent_story``. This is the single column-derivation shared by the body summary
    table and the CLI list/show tables — never re-rolled per caller.
    """
    field_labels = [f.label for f in spec.fields_for(kind)]
    cols = [kind.title(), *field_labels, "Status", "Assignee", "Title"]
    ks = spec.subentity_kinds.get(kind)
    if ks is not None and ks.maps_parent_story:
        cols.append("Story")
    return cols


def _field_value(sub: SubEntity, code: str) -> str | None:
    """The stored badge code for a declared field — ``severity``'s typed attribute or any
    other declared field's generic store (:meth:`SubEntity.badge_value`)."""
    return sub.badge_value(code)


def summary_row(kind: str, sub: SubEntity, spec: WorkflowSpec) -> list[str]:
    """One row aligned to :func:`summary_columns`: local id, field badges, base, then story.

    A field cell renders through :func:`~squads._badges.badge_render`'s default
    (``as_label=False``) — emoji + raw code (``"🔴 critical"``), the list/panel/summary
    convention that badge function's own docstring names. A project's own derived view over
    this same sub-entity data reads the badge value directly off the resolved ``SubEntity``
    (``sub.badge_value(code)``) and renders it however its own template chooses — the
    emoji + label form the registered ``badge`` filter gives a *status* value included — so a
    roll-up template is free to render the identical badge differently from this summary row,
    on purpose."""
    field_cells = [
        badges.badge_render(badges.resolve_collection(kind, f.code, spec), value, spec)
        if (value := _field_value(sub, f.code))
        else ""
        for f in spec.fields_for(kind)
    ]
    row = [sub.local_id, *field_cells, sub.status, sub.assignee or "", sub.title]
    ks = spec.subentity_kinds.get(kind)
    if ks is not None and ks.maps_parent_story:
        row.append(sub.story or "")
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
