"""Frozen helpers for the legacy body-stored sub-entity ``:meta`` regions.

Sub-entity state used to live in an sq-owned ``…:meta`` marker region inside the parent's body.
Only the migrations touch it now — ``_v0_1_to_v0_2`` builds it from pre-2 headings, and
``_v0_2_to_v0_3`` reads it to lift the state into frontmatter (then deletes the region). These
helpers are kept here, decoupled from the live ``_discussion`` module, so historical migration
chains stay self-contained as the live format moves on.
"""

import re
from dataclasses import dataclass

from squads._models import _markers as markers
from squads._models._enums import Severity, Status
from squads._models._subentity import SubEntity
from squads._sections import get_section, replace_section
from squads._workflow import subentity_initial

_LOCAL_ID_PREFIX = {"story": "US", "subtask": "ST", "finding": "F"}
# the meta keys, in render order; assignee/severity/story are optional per kind
_META_ORDER = ("status", "assignee", "severity", "story")


@dataclass
class BlockInfo:
    """A parsed legacy ``:meta`` block: its local id, title, status, and kind-specific extras."""

    local_id: str
    title: str
    status: str  # a Status value string
    severity: str | None = None  # Severity value, findings only
    story: str | None = None  # mapped user story, subtasks only
    assignee: str | None = None  # registered agent slug owning this sub-entity


def meta_tag(kind: str, local_id: str) -> str:
    return f"{kind}:{local_id}:meta"


def render_meta(meta: dict[str, str | None]) -> str:
    return "\n".join(f"{key}: {meta[key]}" for key in _META_ORDER if meta.get(key))


def parse_meta(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in raw.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


# --------------------------------------------------------------------------- block parsing


def _iter_blocks(text: str, kind: str):
    prefix = _LOCAL_ID_PREFIX[kind]
    open_pat = re.compile(rf"<!--\s*sq:{kind}:({prefix}\d+)\s*-->")
    for m in open_pat.finditer(text):
        lid = m.group(1)
        end = text.find(markers.close_marker(f"{kind}:{lid}"), m.end())
        yield lid, text[m.end() : end if end != -1 else len(text)]


def _existing_ids(text: str, kind: str) -> list[int]:
    pat = re.compile(rf"<!--\s*sq:{kind}:{_LOCAL_ID_PREFIX[kind]}(\d+)\s*-->")
    return [int(n) for n in pat.findall(text)]


def local_ids(text: str, kind: str) -> list[str]:
    """All sub-entity local ids of ``kind`` present in ``text`` (sorted)."""
    return [f"{_LOCAL_ID_PREFIX[kind]}{n}" for n in sorted(_existing_ids(text, kind))]


def _heading_title(block: str, local_id: str) -> str:
    m = re.search(rf"###[ \t]*{re.escape(local_id)}[ \t]*(?:—[ \t]*)?([^\n]*)", block)
    return m.group(1).strip() if m else ""


def _body_first_line(block: str, kind: str, local_id: str) -> str:
    inner = get_section(block, f"{kind}:{local_id}:body") or ""
    for line in inner.splitlines():
        s = line.strip()
        if not s or (s.startswith("_") and s.endswith("_")):
            continue  # blank or placeholder italics
        return re.sub(r"^[-*#>\s]+", "", s)
    return ""


def _parse_block(block: str, kind: str, local_id: str) -> BlockInfo:
    meta = parse_meta(get_section(block, meta_tag(kind, local_id)) or "")
    title = _heading_title(block, local_id) or _body_first_line(block, kind, local_id)
    return BlockInfo(
        local_id=local_id,
        title=title,
        status=meta.get("status") or subentity_initial(kind),
        severity=meta.get("severity"),
        story=meta.get("story"),
        assignee=meta.get("assignee"),
    )


def list_blocks(text: str, kind: str) -> list[BlockInfo]:
    """Parsed legacy ``:meta`` blocks of ``kind`` in document order."""
    return [_parse_block(block, kind, lid) for lid, block in _iter_blocks(text, kind)]


def to_subentity(b: BlockInfo) -> SubEntity:
    """A parsed legacy block → the typed :class:`SubEntity` now stored in frontmatter."""
    return SubEntity(
        local_id=b.local_id,
        title=b.title,
        status=Status(b.status),
        assignee=b.assignee,
        severity=Severity(b.severity) if b.severity else None,
        story=b.story,
    )


def has_meta(text: str, kind: str) -> bool:
    """Whether any ``kind`` block in ``text`` still carries a legacy ``:meta`` region."""
    return any(
        get_section(text, meta_tag(kind, lid)) is not None for lid, _ in _iter_blocks(text, kind)
    )


def drop_meta(text: str, kind: str, local_id: str) -> str:
    """Remove a block's ``:meta`` region entirely (markers + content + trailing blank line)."""
    tag = meta_tag(kind, local_id)
    inner = get_section(text, tag)
    if inner is None:
        return text
    region = f"{markers.open_marker(tag)}{inner}{markers.close_marker(tag)}\n\n"
    if region in text:
        return text.replace(region, "", 1)
    # fall back to collapsing the region without assuming the trailing blank line
    return replace_section(text, tag, "").replace(
        f"{markers.open_marker(tag)}\n{markers.close_marker(tag)}", "", 1
    )


# --------------------------------------------------------------------------- pre-2 upgrade


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
    if get_section(text, meta_tag(kind, local_id)) is not None:
        return text  # already migrated
    status, story, title = _parse_legacy_heading(text, local_id)
    clean = f"### {local_id} — {title}".rstrip()
    meta_block = (
        f"{markers.open_marker(meta_tag(kind, local_id))}\n"
        f"{render_meta({'status': status, 'story': story})}\n"
        f"{markers.close_marker(meta_tag(kind, local_id))}"
    )
    pat = re.compile(rf"###[ \t]*{re.escape(local_id)}[ \t]*(?:—[ \t]*)?[^\n]*")
    return pat.sub(lambda _m: f"{clean}\n\n{meta_block}", text, count=1)
