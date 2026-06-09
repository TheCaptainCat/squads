"""Schema 1 → 2 runner. Per item file:

  - fold the legacy ``extra.ref_kinds`` ``{ID: kind}`` map into inline ``ID:kind`` refs,
  - upgrade sub-entity headings (subtask ``[ ]``/``[x]`` checkboxes, bare story headings) into the
    sq-owned ``:meta`` regions, then (re)build the parent's ``:summary`` table, and
  - give legacy reviews an (empty) ``:findings`` container + ``:summary`` region so the new
    finding commands work. Their **free-form prose findings are NOT auto-structured** — that's the
    manual, LLM-assisted step documented in ``docs/migration.md``.

Deterministic, marker-safe (agent bodies untouched), and **idempotent**. Invoked by the
``sq migrate`` command via ``_migrations._registry`` — never run directly (this module is private).
"""

from pathlib import Path
from typing import Any, cast

from squads import _discussion as discussion
from squads import _sections as sections
from squads._models import _markers as markers
from squads._models._enums import ItemType
from squads._models._item import fold_legacy_kinds
from squads._paths import SquadPaths

#: The non-deterministic step `sq migrate up` can't do — surfaced by `sq migrate chlog`.
MANUAL = """\
**Restructure each review's free-form findings into tracked findings.** `sq migrate up` gives every
legacy review an empty findings container, but a pre-2 review's findings are free-form prose (a
`## Findings` section and/or a Summary table) that can't be parsed automatically. For each review
`REV-<id>`, drive an agent with:

1. For every prose finding, run
   `sq finding add REV-<id> "<one-line title>" --severity critical|high|medium|low|info`,
   write its detail in the finding's `:body` region, and set its state if known
   (`sq finding status REV-<id> Fn Fixed|Verified|WontFix`).
2. Map severities from the old legend (🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info);
   default to `medium` when a finding had none.
3. One finding per real prose entry — do **not** invent; leave a missing detail as `TODO`.
4. Once all are recreated, delete the old `## Findings` prose / Summary table from the body.
5. Verify: `sq finding list REV-<id>` shows them all and `sq check` is clean.
"""

# Item types whose body holds sub-entities, and the (kind, container) to upgrade + summarise.
_BODY_KIND: dict[ItemType, tuple[str, str]] = {
    ItemType.TASK: ("subtask", markers.SUBTASKS),
    ItemType.FEATURE: ("story", markers.STORIES),
}


def _fold_ref_kinds(text: str) -> str:
    """Fold a pre-2 ``extra.ref_kinds`` map into inline refs; return (possibly unchanged) text."""
    fm, _ = sections.split_frontmatter(text)
    raw_extra = fm.get("extra")
    if not isinstance(raw_extra, dict):
        return text
    extra = cast("dict[str, Any]", raw_extra)
    raw_legacy = extra.get("ref_kinds")
    if not isinstance(raw_legacy, dict):
        return text
    legacy = {str(k): str(v) for k, v in cast("dict[Any, Any]", raw_legacy).items()}
    folded = fold_legacy_kinds(list(fm.get("refs", []) or []), legacy)
    extra.pop("ref_kinds", None)
    if folded:
        fm["refs"] = folded
    else:
        fm.pop("refs", None)
    if not extra:
        fm.pop("extra", None)
    return sections.replace_frontmatter(text, fm)


def _insert_findings_skeleton(text: str) -> str:
    """Give a legacy review an empty findings container before its discussion (markers only)."""
    container = (
        f"{markers.open_marker(markers.FINDINGS)}\n{markers.close_marker(markers.FINDINGS)}\n\n"
    )
    disc = markers.open_marker(markers.DISCUSSION)
    return text.replace(disc, container + disc, 1) if disc in text else f"{text}\n{container}"


def _migrate_file(md: Path, item_type: ItemType) -> bool:
    """Apply all 1→2 transforms to one file; return whether it changed."""
    original = md.read_text(encoding="utf-8")
    text = _fold_ref_kinds(original)
    body = _BODY_KIND.get(item_type)
    if body:
        kind, container = body
        for lid in discussion.local_ids(text, kind):
            text = discussion.upgrade_legacy_block(text, kind, lid)
        if sections.has_section(text, container):
            text = discussion.ensure_summary(text, kind, container)
    elif item_type is ItemType.REVIEW and not sections.has_section(text, markers.FINDINGS):
        text = _insert_findings_skeleton(text)
        text = discussion.ensure_summary(text, "finding", markers.FINDINGS)
    if text == original:
        return False
    md.write_text(text, encoding="utf-8")
    return True


def migrate(paths: SquadPaths) -> int:
    """Migrate every item file under the squad to schema 2; return the count changed."""
    changed = 0
    for item_type in ItemType:
        folder = paths.folder_for(item_type)
        if not folder.is_dir():
            continue
        for md in sorted(folder.glob(f"{item_type.prefix}-*.md")):
            if _migrate_file(md, item_type):
                changed += 1
    return changed
