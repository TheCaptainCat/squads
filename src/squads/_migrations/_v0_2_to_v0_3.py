"""Schema 0.2 → 0.3 runner. Per item file:

  - backfill the integer ``sequence_id`` into frontmatter (derived once from the id),
  - **lift each sub-entity's machine state out of its body ``:meta`` region into a typed
    ``subentities`` frontmatter list**, then delete the now-redundant ``:meta`` markers, and
  - (re)render the human-readable ``:head`` region under every story / subtask / finding — status /
    assignee / severity / story badges — resolving the assignee's full name (from role files) and a
    subtask's story title (from its parent feature).

Sub-entity state thus becomes single-sourced in frontmatter (visible to the index); the prose
(``:body`` / ``:discussion``) and the rolled-up ``:summary`` stay in the body. Deterministic,
marker-safe, idempotent (a file whose blocks carry no ``:meta`` is already at 0.3). Invoked by
``sq migrate`` via ``_migrations._registry`` — never run directly (module is private).
"""

from pathlib import Path
from typing import Any, cast

from squads import _discussion as discussion
from squads import _sections as sections
from squads._itemfile import read_frontmatter
from squads._migrations import _meta_compat
from squads._models._enums import ItemType
from squads._paths import SquadPaths

MANUAL = ""  # fully automatic — nothing for `sq migrate chlog` to surface

# Parent item type → its sub-entity kind.
_KIND_BY_TYPE: dict[ItemType, str] = {
    ItemType.FEATURE: "story",
    ItemType.TASK: "subtask",
    ItemType.REVIEW: "finding",
}


def _name_map(paths: SquadPaths) -> dict[str, str]:
    """Agent slug → full name, scanned from the squad's role files (for the assignee badge)."""
    out: dict[str, str] = {}
    folder = paths.folder_for(ItemType.ROLE)
    if not folder.is_dir():
        return out
    for md in folder.glob(f"{ItemType.ROLE.prefix}-*.md"):
        fm = read_frontmatter(md)
        raw = fm.get("extra")
        extra = cast("dict[str, Any]", raw) if isinstance(raw, dict) else {}
        slug = extra.get("slug")
        if slug:
            out[str(slug)] = str(extra.get("full_name") or fm.get("title") or slug)
    return out


def _story_titles(paths: SquadPaths) -> dict[str, dict[str, str]]:
    """Feature id → {story local id: title}, to resolve a subtask's ``Implements: USn — …`` link."""
    out: dict[str, dict[str, str]] = {}
    folder = paths.folder_for(ItemType.FEATURE)
    if not folder.is_dir():
        return out
    for md in folder.glob(f"{ItemType.FEATURE.prefix}-*.md"):
        fid = read_frontmatter(md).get("id")
        if fid:
            blocks = _meta_compat.list_blocks(md.read_text(encoding="utf-8"), "story")
            out[fid] = {b.local_id: b.title for b in blocks}
    return out


def _story_label(
    stories: dict[str, dict[str, str]], feature_id: str | None, us_id: str | None
) -> str | None:
    if not us_id:
        return None
    title = stories.get(feature_id or "", {}).get(us_id, "")
    return f"{us_id} — {title}" if title else us_id


def _migrate_subentities(
    md: Path, kind: str, names: dict[str, str], stories: dict[str, dict[str, str]]
) -> bool:
    """Lift body ``:meta`` → frontmatter ``subentities``, render ``:head``, drop ``:meta``."""
    text = md.read_text(encoding="utf-8")
    if not _meta_compat.has_meta(text, kind):
        return False  # already at 0.3 (no legacy meta to lift)
    parent = sections.split_frontmatter(text)[0].get("parent") if kind == "subtask" else None
    subs = _meta_compat.list_blocks(text, kind)
    for b in subs:
        text = discussion.set_head(
            text,
            kind,
            b.local_id,
            status=b.status,
            severity=b.severity,
            story=_story_label(stories, parent, b.story),
            assignee_name=names.get(b.assignee, b.assignee) if b.assignee else None,
        )
        text = _meta_compat.drop_meta(text, kind, b.local_id)
    fm, _ = sections.split_frontmatter(text)
    fm["subentities"] = [_meta_compat.to_subentity(b).to_frontmatter_dict() for b in subs]
    md.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    return True


def _backfill_sequence_id(md: Path) -> bool:
    """Add a ``sequence_id`` (derived once from the id) to an item's frontmatter if it lacks one."""
    text = md.read_text(encoding="utf-8")
    fm, _ = sections.split_frontmatter(text)
    if "sequence_id" in fm or "id" not in fm:
        return False
    rebuilt: dict[str, Any] = {}
    for key, value in fm.items():
        rebuilt[key] = value
        if key == "id":  # place sequence_id right after the id
            rebuilt["sequence_id"] = int(str(value).rsplit("-", 1)[-1])
    md.write_text(sections.replace_frontmatter(text, rebuilt), encoding="utf-8")
    return True


def migrate(paths: SquadPaths) -> int:
    """Backfill ``sequence_id``, lift sub-entity state to frontmatter, render ``:head``.

    Returns the count of files changed.
    """
    names = _name_map(paths)
    stories = _story_titles(paths)
    changed = 0
    for item_type in ItemType:
        folder = paths.folder_for(item_type)
        if not folder.is_dir():
            continue
        kind = _KIND_BY_TYPE.get(item_type)
        for md in sorted(folder.glob(f"{item_type.prefix}-*.md")):
            touched = _backfill_sequence_id(md)
            if kind is not None and _migrate_subentities(md, kind, names, stories):
                touched = True
            if touched:
                changed += 1
    return changed
