"""Build and parse marker-delimited collaboration content: comments, stories, subtasks, findings.

Each sub-entity (story / subtask / finding) is scaffolded as marker-scoped regions — its
sq-tracked state lives in markers, never in the heading prose:
  - a heading line (``### US1 — title``, agent-editable),
  - an sq-owned ``…:meta`` region (status, plus severity/story where they apply),
  - a ``…:body`` region the **agent** writes freely, and
  - a ``…:discussion`` region ``sq`` appends comments to.
The parent's sq-managed summary table renders the meta of all its children.
"""

import re
from dataclasses import dataclass

from squads._models import _markers as markers
from squads._models._enums import SEVERITY_EMOJI, Severity, Status
from squads._sections import get_section, replace_section
from squads._workflow import subentity_initial

_MENTION_RE = re.compile(r"(?<![A-Za-z0-9_])@([a-z0-9][a-z0-9-]*)")
_LOCAL_ID_PREFIX = {"story": "US", "subtask": "ST", "finding": "F"}

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


@dataclass
class BlockInfo:
    """A parsed sub-entity block: its local id, title, status, and kind-specific extras."""

    local_id: str
    title: str
    status: str  # a Status value string
    severity: str | None = None  # Severity value, findings only
    story: str | None = None  # mapped user story, subtasks only


# --------------------------------------------------------------------------- comments


def format_comment(timestamp_iso: str, author: str, messages: list[str]) -> str:
    """One discussion entry: a timestamped author line with one sub-item per message."""
    lines = [f"- [{timestamp_iso}] {author}:", *(f"  - {msg}" for msg in messages)]
    return "\n".join(lines)


def extract_mentions(text: str) -> set[str]:
    """All ``@slug`` mentions in a blob of text (lowercased slugs)."""
    return {m.lower() for m in _MENTION_RE.findall(text)}


# --------------------------------------------------------------------------- ids / tags


def _existing_ids(text: str, kind: str) -> list[int]:
    # only the bare block opener (e.g. sq:story:US1), not :meta / :body / :discussion
    pat = re.compile(rf"<!--\s*sq:{kind}:{_LOCAL_ID_PREFIX[kind]}(\d+)\s*-->")
    return [int(n) for n in pat.findall(text)]


def next_local_id(text: str, kind: str) -> str:
    nums = _existing_ids(text, kind)
    return f"{_LOCAL_ID_PREFIX[kind]}{(max(nums) + 1) if nums else 1}"


def local_ids(text: str, kind: str) -> list[str]:
    """All sub-entity local ids of ``kind`` present in ``text`` (sorted)."""
    return [f"{_LOCAL_ID_PREFIX[kind]}{n}" for n in sorted(_existing_ids(text, kind))]


def body_tag(kind: str, local_id: str) -> str:
    return f"{kind}:{local_id}:body"


def _meta_tag(kind: str, local_id: str) -> str:
    return f"{kind}:{local_id}:meta"


# --------------------------------------------------------------------------- meta region


def _render_meta(status: str, severity: str | None = None, story: str | None = None) -> str:
    lines = [f"status: {status}"]
    if severity:
        lines.append(f"severity: {severity}")
    if story:
        lines.append(f"story: {story}")
    return "\n".join(lines)


def _parse_meta(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in raw.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


# --------------------------------------------------------------------------- block builders


def build_block(
    kind: str,
    local_id: str,
    title: str = "",
    *,
    status: Status,
    severity: Severity | None = None,
    story: str | None = None,
) -> str:
    """A sub-entity block: heading + sq-owned ``:meta`` + agent ``:body`` + ``:discussion``."""
    tag = f"{kind}:{local_id}"
    mtag, btag, dtag = (
        _meta_tag(kind, local_id),
        body_tag(kind, local_id),
        markers.discussion_tag(tag),
    )
    heading = f"### {local_id} — {title}".rstrip()
    meta = _render_meta(status.value, severity.value if severity else None, story)
    return (
        f"\n{markers.open_marker(tag)}\n"
        f"{heading}\n\n"
        f"{markers.open_marker(mtag)}\n{meta}\n{markers.close_marker(mtag)}\n\n"
        f"{markers.open_marker(btag)}\n{_PLACEHOLDER[kind]}\n{markers.close_marker(btag)}\n\n"
        f"#### Discussion\n\n"
        f"{markers.open_marker(dtag)}\n{markers.close_marker(dtag)}\n"
        f"{markers.close_marker(tag)}\n"
    )


def build_story_block(local_id: str, title: str = "", *, status: Status = Status.TODO) -> str:
    return build_block("story", local_id, title, status=status)


def build_subtask_block(
    local_id: str, title: str = "", *, status: Status = Status.TODO, story: str | None = None
) -> str:
    return build_block("subtask", local_id, title, status=status, story=story)


def build_finding_block(
    local_id: str, title: str = "", *, status: Status = Status.OPEN, severity: Severity
) -> str:
    return build_block("finding", local_id, title, status=status, severity=severity)


# --------------------------------------------------------------------------- parsing


def _iter_blocks(text: str, kind: str):
    prefix = _LOCAL_ID_PREFIX[kind]
    open_pat = re.compile(rf"<!--\s*sq:{kind}:({prefix}\d+)\s*-->")
    for m in open_pat.finditer(text):
        lid = m.group(1)
        end = text.find(markers.close_marker(f"{kind}:{lid}"), m.end())
        yield lid, text[m.end() : end if end != -1 else len(text)]


def _heading_title(block: str, local_id: str) -> str:
    # title is the rest of the heading line after the local id (no sq state lives here)
    m = re.search(rf"###[ \t]*{re.escape(local_id)}[ \t]*(?:—[ \t]*)?([^\n]*)", block)
    return m.group(1).strip() if m else ""


def _body_first_line(block: str, kind: str, local_id: str) -> str:
    inner = get_section(block, body_tag(kind, local_id)) or ""
    for line in inner.splitlines():
        s = line.strip()
        if not s or (s.startswith("_") and s.endswith("_")):
            continue  # blank or placeholder italics
        return re.sub(r"^[-*#>\s]+", "", s)
    return ""


def _parse_block(block: str, kind: str, local_id: str) -> BlockInfo:
    meta = _parse_meta(get_section(block, _meta_tag(kind, local_id)) or "")
    title = _heading_title(block, local_id) or _body_first_line(block, kind, local_id)
    return BlockInfo(
        local_id=local_id,
        title=title,
        status=meta.get("status") or subentity_initial(kind).value,
        severity=meta.get("severity"),
        story=meta.get("story"),
    )


def list_blocks(text: str, kind: str) -> list[BlockInfo]:
    """Parsed sub-entity blocks of ``kind`` in document order."""
    return [_parse_block(block, kind, lid) for lid, block in _iter_blocks(text, kind)]


def subtask_stories(text: str) -> list[tuple[str, str | None]]:
    """[(subtask local id, referenced US id or None), …] across a task file."""
    return [(b.local_id, b.story) for b in list_blocks(text, "subtask")]


def set_block_status(text: str, kind: str, local_id: str, status_value: str) -> str:
    """Rewrite the ``status:`` line in a block's sq-owned ``:meta`` region."""
    tag = _meta_tag(kind, local_id)
    current = get_section(text, tag)
    if current is None:
        raise KeyError(local_id)
    meta = _parse_meta(current)
    meta["status"] = status_value
    return replace_section(
        text, tag, _render_meta(status_value, meta.get("severity"), meta.get("story"))
    )


# --------------------------------------------------------------------------- pre-2 migration


_LEGACY_STORY_REF_RE = re.compile(r"\(→[ \t]*(US\d+)\)")


def _parse_legacy_heading(text: str, local_id: str) -> tuple[str, str | None, str]:
    """A pre-2 ``### id — [ ]/[x] title (→ USn)`` heading → (status, story, clean title)."""
    m = re.search(
        rf"###[ \t]*{re.escape(local_id)}[ \t]*(?:—[ \t]*)?(?:\[([ xX])\][ \t]*)?([^\n]*)", text
    )
    token, raw = (m.group(1), m.group(2) or "") if m else (None, "")
    story = _LEGACY_STORY_REF_RE.search(raw)
    title = _LEGACY_STORY_REF_RE.sub("", raw).strip()
    status = Status.DONE.value if (token or "").lower() == "x" else Status.TODO.value
    return status, (story.group(1) if story else None), title


def upgrade_legacy_block(text: str, kind: str, local_id: str) -> str:
    """Pre-2 → 2: clean the heading and insert the sq-owned ``:meta`` region. Idempotent."""
    if get_section(text, _meta_tag(kind, local_id)) is not None:
        return text  # already migrated
    status, story, title = _parse_legacy_heading(text, local_id)
    clean = f"### {local_id} — {title}".rstrip()
    meta_block = (
        f"{markers.open_marker(_meta_tag(kind, local_id))}\n"
        f"{_render_meta(status, None, story)}\n"
        f"{markers.close_marker(_meta_tag(kind, local_id))}"
    )
    pat = re.compile(rf"###[ \t]*{re.escape(local_id)}[ \t]*(?:—[ \t]*)?[^\n]*")
    return pat.sub(lambda _m: f"{clean}\n\n{meta_block}", text, count=1)


# --------------------------------------------------------------------------- summary table


_SUMMARY_COLS: dict[str, tuple[str, ...]] = {
    "subtask": ("Subtask", "Status", "Title", "Story"),
    "story": ("Story", "Status", "Title"),
    "finding": ("Finding", "Severity", "Status", "Title"),
}


def _summary_cells(kind: str, b: BlockInfo) -> list[str]:
    if kind == "finding":
        sev = f"{SEVERITY_EMOJI[Severity(b.severity)]} {b.severity}" if b.severity else ""
        return [b.local_id, sev, b.status, b.title]
    if kind == "subtask":
        return [b.local_id, b.status, b.title, b.story or ""]
    return [b.local_id, b.status, b.title]


def render_summary(kind: str, blocks: list[BlockInfo]) -> str:
    """The sq-managed roll-up table for a parent's sub-entities (empty until there are any)."""
    if not blocks:
        return ""
    cols = _SUMMARY_COLS[kind]
    return "\n".join(
        [
            "| " + " | ".join(cols) + " |",
            "| " + " | ".join("---" for _ in cols) + " |",
            *("| " + " | ".join(_summary_cells(kind, b)) + " |" for b in blocks),
        ]
    )


def ensure_summary(text: str, kind: str, container: str) -> str:
    """Insert an empty ``sq:summary`` region before ``container`` if missing, then (re)render it."""
    if get_section(text, markers.SUMMARY) is None:
        region = (
            f"{markers.open_marker(markers.SUMMARY)}\n{markers.close_marker(markers.SUMMARY)}\n\n"
        )
        text = text.replace(
            markers.open_marker(container), region + markers.open_marker(container), 1
        )
    return replace_section(text, markers.SUMMARY, render_summary(kind, list_blocks(text, kind)))
