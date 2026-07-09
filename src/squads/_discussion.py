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

import re
from dataclasses import dataclass

from squads import _badges as badges
from squads._models import _markers as markers
from squads._models._subentity import SubEntity
from squads._rendering._engine import render
from squads._sections import get_section, replace_section
from squads._workflow import WorkflowSpec

_MENTION_RE = re.compile(r"(?<![A-Za-z0-9_])@([a-z0-9][a-z0-9-]*)")
_LOCAL_ID_PREFIX = {"story": "US", "subtask": "ST", "finding": "F"}

# Matches the header line of a formatted comment, e.g.:
#   - [2026-06-07T10:00:00Z] Author Name:
_COMMENT_HEADER_RE = re.compile(r"^- \[([^\]]+)\] (.+?):$")

_STORY_PLACEHOLDER = (
    "_Write the user story (e.g. “As an <role>, I want … so that …”) and its acceptance "
    "criteria here — free-form paragraphs or bullet lists._"
)
_SUBTASK_PLACEHOLDER = "_Describe this subtask here — free-form paragraphs or bullet lists._"
_FINDING_PLACEHOLDER = "_Describe the finding, its impact, and a recommendation — free-form._"
_PLACEHOLDER = {
    "story": _STORY_PLACEHOLDER,
    "subtask": _SUBTASK_PLACEHOLDER,
    "finding": _FINDING_PLACEHOLDER,
}


# --------------------------------------------------------------------------- comments


def format_comment(timestamp_iso: str, author: str, messages: list[str]) -> str:
    """One discussion entry: a timestamped author line + one bullet per message.

    A multi-line message keeps its first line on the bullet and indents continuation lines so they
    stay nested under it.
    """
    lines = [f"- [{timestamp_iso}] {author}:"]
    for msg in messages:
        first, *rest = msg.split("\n")
        lines.append(f"  - {first}")
        # indent *every* continuation line (blanks included) to the bullet's content column, so a
        # nested fenced code block — and its internal blank lines — stays inside the list item.
        lines += [f"    {ln}" for ln in rest]
    return "\n".join(lines)


@dataclass
class Comment:
    """A single parsed comment from a discussion region."""

    timestamp: str
    author: str
    body: str  # the raw bullet lines for this comment, stripped of their outer indentation


def split_discussion(region: str) -> list[Comment]:
    """Parse a discussion region (the content between sq:discussion markers) into Comment objects.

    Each comment starts with ``- [TIMESTAMP] Author:`` and is followed by indented bullet lines
    (``  - text`` or continuation lines ``    text``).  The body field preserves the bullets as-is
    (including any fenced code blocks), stripping only the leading 2-space indent level so it reads
    as standalone markdown.

    Empty or whitespace-only regions return an empty list.  Lines that do not start a new header
    are accumulated as the current comment's body.  This is the inverse of :func:`format_comment`.
    """
    comments: list[Comment] = []
    current_ts: str | None = None
    current_author: str | None = None
    body_lines: list[str] = []

    for raw_line in region.splitlines():
        m = _COMMENT_HEADER_RE.match(raw_line)
        if m:
            # Flush any previous comment
            if current_ts is not None and current_author is not None:
                comments.append(
                    Comment(
                        timestamp=current_ts,
                        author=current_author,
                        body="\n".join(body_lines).strip(),
                    )
                )
            current_ts = m.group(1)
            current_author = m.group(2)
            body_lines = []
        elif current_ts is not None:
            # Strip the 2-space indent that format_comment adds at the message level.
            # Continuation lines have 4 spaces; after stripping 2 they become "  text", which
            # renders correctly under the bullet.  We do NOT collapse blank lines — fenced code
            # blocks depend on them staying in place.
            if raw_line.startswith("  "):
                body_lines.append(raw_line[2:])
            else:
                body_lines.append(raw_line)

    # Flush the last comment
    if current_ts is not None and current_author is not None:
        comments.append(
            Comment(
                timestamp=current_ts,
                author=current_author,
                body="\n".join(body_lines).strip(),
            )
        )

    return comments


def extract_mentions(text: str) -> set[str]:
    """All ``@slug`` mentions in a blob of text (lowercased slugs)."""
    return {m.lower() for m in _MENTION_RE.findall(text)}


# --------------------------------------------------------------------------- ids / tags


def local_id_for(kind: str, token: str) -> str:
    """Normalize a CLI local-id token to its canonical form: ``2`` → ``STn``/``USn``/``Fn``."""
    prefix = _LOCAL_ID_PREFIX[kind]
    t = token.strip()
    return f"{prefix}{int(t)}" if t.isdigit() else t.upper()


def next_local_id(subentities: list[SubEntity], kind: str) -> str:
    """The next free local id for ``kind``, computed from the parent's stored sub-entities."""
    prefix = _LOCAL_ID_PREFIX[kind]
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


def body_placeholder(kind: str) -> str:
    """The italic placeholder a freshly-scaffolded ``:body`` region holds until content is set."""
    return _PLACEHOLDER[kind]


def build_block(kind: str, local_id: str, title: str = "", *, body: str | None = None) -> str:
    """A sub-entity block: heading + empty ``:head`` + ``:body`` + ``:discussion``.

    State (status/assignee/severity/story) lives in the parent's frontmatter, not here. The skeleton
    lives in ``templates/subentities/block.md.j2`` (sub-tags derive from ``tag``); the ``:head`` is
    filled by :func:`set_head` right after.
    """
    heading = f"### {local_id} — {title}".rstrip()
    return render(
        "subentities/block.md.j2",
        tag=f"{kind}:{local_id}",
        heading=heading,
        body=body or _PLACEHOLDER[kind],
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


def set_head(
    text: str,
    kind: str,
    local_id: str,
    *,
    status: str | None = None,
    severity: str | None = None,
    story: str | None = None,
    assignee_name: str | None = None,
    spec: WorkflowSpec | None = None,
) -> str:
    """(Re)render the human-readable ``:head`` region under a block's heading.

    A presentation mirror of the frontmatter state: status/severity as colored badges, the
    implemented story as ``USn — title``, the assignee's full name. The layout lives in
    ``templates/subentities/head.md.j2`` — add an attribute by passing a value here + a line there.
    New blocks ship the region empty (from ``block.md.j2``); on a legacy block that lacks it (the
    migration path) it's created lazily, just before the block's ``:body`` marker.

    ``spec`` is the active workflow spec, used to resolve the status badge (falls back to the
    bundled spec when not passed — see :func:`squads._badges.status_badge`).
    """
    head_tag = _head_tag(kind, local_id)
    inner = render(
        "subentities/head.md.j2",
        status=badges.status_badge(status, spec) if status else None,
        severity=(
            badges.badge_render(
                badges.resolve_collection(kind, "severity", spec), severity, spec, as_label=True
            )
            if severity
            else None
        ),
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


_SUMMARY_COLS: dict[str, tuple[str, ...]] = {
    "subtask": ("Subtask", "Status", "Assignee", "Title", "Story"),
    "story": ("Story", "Status", "Assignee", "Title"),
    "finding": ("Finding", "Severity", "Status", "Assignee", "Title"),
}


def _summary_cells(kind: str, s: SubEntity, spec: WorkflowSpec | None = None) -> list[str]:
    if kind == "finding":
        sev = (
            badges.badge_render(badges.resolve_collection(kind, "severity", spec), s.severity, spec)
            if s.severity
            else ""
        )
        return [s.local_id, sev, s.status, s.assignee or "", s.title]
    if kind == "subtask":
        return [s.local_id, s.status, s.assignee or "", s.title, s.story or ""]
    return [s.local_id, s.status, s.assignee or "", s.title]


def render_summary(
    kind: str, subentities: list[SubEntity], spec: WorkflowSpec | None = None
) -> str:
    """The sq-managed roll-up table for a parent's sub-entities (empty until there are any).

    The table layout lives in ``templates/subentities/summary.md.j2``. ``spec`` defaults to
    the bundled spec (frozen migration runners call this with no spec on purpose).
    """
    if not subentities:
        return ""
    cols = _SUMMARY_COLS[kind]
    return render(
        "subentities/summary.md.j2",
        cols=list(cols),
        seps=["---"] * len(cols),
        rows=[_summary_cells(kind, s, spec) for s in subentities],
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
    spec: WorkflowSpec | None = None,
) -> str:
    """Insert an empty ``sq:summary`` region before ``container`` if missing, then (re)render it."""
    if get_section(text, markers.SUMMARY) is None:
        region = (
            f"{markers.open_marker(markers.SUMMARY)}\n{markers.close_marker(markers.SUMMARY)}\n\n"
        )
        text = text.replace(
            markers.open_marker(container), region + markers.open_marker(container), 1
        )
    return replace_section(text, markers.SUMMARY, render_summary(kind, subentities, spec))
