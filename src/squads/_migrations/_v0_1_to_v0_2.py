"""Schema 0.1 → 0.2 runner, per item file: fold the legacy ``extra.ref_kinds`` ``{ID: kind}`` map
into inline ``ID:kind`` refs; upgrade sub-entity headings (subtask ``[ ]``/``[x]`` checkboxes, bare
story headings) into the sq-owned ``:meta`` regions and rebuild the parent's ``:summary`` table; and
give legacy reviews an empty ``:findings`` container plus ``:summary`` region so the finding
commands work, their free-form prose findings left unstructured (the manual, LLM-assisted step in
``docs/migration.md``). It is deterministic, marker-safe (agent bodies untouched) and idempotent,
and runs only through ``sq migrate`` via ``_migrations._registry``.
"""

from pathlib import Path
from typing import Any, cast

from squads import _discussion as discussion
from squads import _sections as sections
from squads._migrations import _meta_compat
from squads._models import _markers as markers
from squads._paths import SquadPaths

#: Frozen: the declared-default ref kind at schema 0.1/0.2, the retired
#: ``_models._item.DEFAULT_KIND`` literal. Never re-derive it from
#: ``WorkflowSpec.default_ref_kind()``: a migration is a snapshot of the schema it transforms, and a
#: project's spec can rename the default.
_DEFAULT_KIND = "related"


def _split_ref(ref: str) -> tuple[str, str]:
    """Frozen, private copy of ``squads._models._item.split_ref``: ``"ID"`` -> ``(ID, "")``,
    ``"ID:kind"`` -> ``(ID, kind)``. It is never imported live (see
    ``tests/meta/test_migrations_never_import_a_vocabulary_folded_primitive.py``), since a live
    primitive's collapse behaviour can change out from under a frozen runner even when its signature
    looks mechanical, as it did to ``_v0_5_to_v0_7``.
    """
    rid, _, kind = ref.partition(":")
    return rid, kind


def _make_ref(item_id: str, kind: str) -> str:
    """Frozen, private copy of the pre-0.14 ``squads._models._item.make_ref`` collapse: an edge
    whose kind is unspelled or is :data:`_DEFAULT_KIND` is written bare and any other kind spelled
    out. Never imported live (see :func:`_split_ref`).
    """
    return item_id if kind in ("", _DEFAULT_KIND) else f"{item_id}:{kind}"


def _fold_legacy_kinds(refs: list[str], legacy: dict[str, str]) -> list[str]:
    """Runner-owned, frozen copy of the legacy ``extra.ref_kinds`` fold: merge the map into inline
    ``ID:kind`` refs, collapsing an edge whose kind is :data:`_DEFAULT_KIND` to the bare form. It
    duplicates rather than imports ``squads._models._item.normalise_ref_kinds``, which takes the
    active spec's default kind and would make this runner's output track an adopter's spec instead
    of the schema 0.1/0.2 vocabulary; ``split_ref``/``make_ref`` are not imported either (see
    :func:`_split_ref`).
    """
    result: list[str] = []
    for rid, kind in (_split_ref(r) for r in refs):
        resolved = legacy.get(rid, kind)
        result.append(_make_ref(rid, resolved))
    return result


#: The non-deterministic step `sq migrate up` can't do — surfaced by `sq migrate chlog`.
MANUAL = """\
**Restructure each review's free-form findings into tracked findings.** `sq migrate up` gives every
legacy review an empty findings container, but a pre-2 review's findings are free-form prose (a
`## Findings` section and/or a Summary table) that can't be parsed automatically. For each review
review `<n>`, drive an agent with:

1. For every prose finding, run
   `sq review <n> add-finding "<one-line title>" --severity critical|high|medium|low|info`,
   set its detail with `sq review <n> finding <k> body -m "…"`, and its state if known
   (`sq review <n> finding <k> update --status Fixed|Verified|WontFix`).
2. Map severities from the old legend (🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info);
   default to `medium` when a finding had none.
3. One finding per real prose entry — do **not** invent; leave a missing detail as `TODO`.
4. Once all are recreated, delete the old `## Findings` prose / Summary table from the body.
5. Verify: `sq review <n> findings` shows them all and `sq check` is clean.
"""

# Frozen v0.1/v0.2 type vocabulary (type-name, prefix and folder literals at this schema). Never
# derive it from the live spec: a migration is a point-in-time snapshot.
_TYPES: tuple[tuple[str, str, str], ...] = (
    ("epic", "EPIC", "epics"),
    ("feature", "FEAT", "features"),
    ("task", "TASK", "tasks"),
    ("bug", "BUG", "bugs"),
    ("decision", "ADR", "adrs"),
    ("review", "REV", "reviews"),
    ("guide", "GUIDE", "guides"),
    ("role", "ROLE", "agents/roles"),
    ("skill", "SKILL", "agents/skills"),
    ("operator", "OP", "operators"),
)

# The frozen container tags of the three sub-entity kinds this schema knew.
_STORIES = "stories"
_SUBTASKS = "subtasks"
_FINDINGS = "findings"

# Item types whose body holds sub-entities, and the (kind, container) to upgrade + summarise.
_BODY_KIND: dict[str, tuple[str, str]] = {
    "task": ("subtask", _SUBTASKS),
    "feature": ("story", _STORIES),
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
    folded = _fold_legacy_kinds(list(fm.get("refs", []) or []), legacy)
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
    container = f"{markers.open_marker(_FINDINGS)}\n{markers.close_marker(_FINDINGS)}\n\n"
    disc = markers.open_marker(markers.DISCUSSION)
    return text.replace(disc, container + disc, 1) if disc in text else f"{text}\n{container}"


def _migrate_file(md: Path, item_type: str, *, from_squad: Path) -> bool:
    """Apply all 1→2 transforms to one file; return whether it changed."""
    original = md.read_text(encoding="utf-8")
    text = _fold_ref_kinds(original)
    body = _BODY_KIND.get(item_type)
    if body:
        kind, container = body
        for lid in _meta_compat.local_ids(text, kind):
            text = _meta_compat.upgrade_legacy_block(text, kind, lid)
        if sections.has_section(text, container):
            subs = [_meta_compat.to_subentity(b) for b in _meta_compat.list_blocks(text, kind)]
            text = discussion.ensure_summary(
                text, kind, container, subs, _meta_compat.legacy_spec(), from_squad=from_squad
            )
    elif item_type == "review" and not sections.has_section(text, _FINDINGS):
        text = _insert_findings_skeleton(text)
        text = discussion.ensure_summary(
            text, "finding", _FINDINGS, [], _meta_compat.legacy_spec(), from_squad=from_squad
        )
    if text == original:
        return False
    md.write_text(text, encoding="utf-8", newline="")
    return True


def migrate(paths: SquadPaths) -> int:
    """Migrate every item file under the squad to schema 0.2; return the count changed."""
    changed = 0
    for item_type, prefix, folder_name in _TYPES:
        folder = paths.squad_dir / folder_name
        if not folder.is_dir():
            continue
        for md in sorted(folder.glob(f"{prefix}-*.md")):
            if _migrate_file(md, item_type, from_squad=paths.squad_dir):
                changed += 1
    return changed
