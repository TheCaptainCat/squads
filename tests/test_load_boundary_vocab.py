"""TASK-000235 F1/F5: load-boundary vocabulary validation characterization tests.

Every path that materializes an Item from disk must validate ``item.type``,
``item.status``, and every ``item.subentities[].status`` against the loaded
WorkflowSpec, raising a clean ``SquadsError`` rather than silently indexing and
crashing downstream (ADR-000232 §1).

Coverage:
- ``IndexStore.load()`` rejects an index entry with an unknown type (repro: type=gizmo)
- ``IndexStore.load()`` rejects an index entry with an unknown status (repro: status=Frobnicated)
- ``repair()`` (the from-frontmatter reconstruction path) rejects a file with an unknown type
- ``repair()`` rejects a file with an unknown status
- ``IndexStore.load()`` rejects a sub-entity with an unknown status (F5)
- ``repair()`` rejects a file whose sub-entity has an unknown status (F5)
"""

import json
from pathlib import Path

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _index_path(project) -> Path:  # type: ignore[no-untyped-def]
    """Return the path to the .squads.json index for the given project paths."""
    return project.squad_dir / ".squads.json"


def _patch_index_item_field(index_path: Path, field: str, value: str) -> None:
    """Mutate the FIRST item in .squads.json, setting ``field`` to ``value``."""
    from typing import Any

    raw = index_path.read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(raw)
    items: dict[str, Any] = data["items"]
    first_key = next(iter(items))
    first_item: dict[str, Any] = dict(items[first_key])
    first_item[field] = value
    items[first_key] = first_item
    index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _patch_index_first_subentity_status(index_path: Path, bad_status: str) -> None:
    """Set the FIRST sub-entity's status to ``bad_status`` in the first item that has one."""
    from typing import Any

    raw = index_path.read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(raw)
    items: dict[str, Any] = data["items"]
    for key in items:
        item: dict[str, Any] = dict(items[key])
        subs: list[Any] = item.get("subentities") or []
        if subs:
            patched_sub: dict[str, Any] = dict(subs[0])
            patched_sub["status"] = bad_status
            item["subentities"] = [patched_sub, *subs[1:]]
            items[key] = item
            break
    index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _patch_md_subentity_status(md_path: Path, bad_status: str) -> None:
    """Set the first ``status:`` key inside a ``subentities:`` YAML block to ``bad_status``.

    Only patches the first ``status:`` line that appears after a ``subentities:`` header,
    so the item-level status above it is not affected.
    """
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    patched: list[str] = []
    in_subentities = False
    patched_one = False
    for line in lines:
        if line.strip() == "subentities:":
            in_subentities = True
            patched.append(line)
            continue
        if in_subentities and not patched_one and line.strip().startswith("status:"):
            patched.append(f"  status: {bad_status}\n")
            patched_one = True
            continue
        patched.append(line)
    md_path.write_text("".join(patched), encoding="utf-8")


def _patch_index_item_by_seq(index_path: Path, seq: int, **fields: object) -> None:
    """Mutate the item keyed by *seq* in .squads.json, setting each of ``fields``.

    Unlike :func:`_patch_index_item_field` (which patches whichever item happens to be
    first — fine for the type/status checks above, which don't care which item is bad),
    the field/collection checks below target ONE specific item (the roster's seeded role
    items sort first and don't declare a priority/severity field at all).
    """
    from typing import Any

    raw = index_path.read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(raw)
    items: dict[str, Any] = data["items"]
    key = str(seq)
    items[key] = {**items[key], **fields}
    index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _patch_md_frontmatter_field(md_path: Path, field: str, value: str) -> None:
    """Patch one YAML frontmatter field in a markdown file (simple key: value replacement)."""
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    patched: list[str] = []
    for line in lines:
        if line.startswith(f"{field}:"):
            patched.append(f"{field}: {value}\n")
        else:
            patched.append(line)
    md_path.write_text("".join(patched), encoding="utf-8")


# ---------------------------------------------------------------------------
# IndexStore.load() — unknown type / status
# ---------------------------------------------------------------------------


async def test_load_rejects_unknown_type(svc, project) -> None:
    """IndexStore.load() raises a clean SquadsError when an item has type='gizmo'.

    Repro: hand-edit .squads.json to set the first item's type to 'gizmo', then
    trigger a load via svc.list_items() — must surface SquadsError, not KeyError.
    """
    # Create an item so the index is non-empty.
    await svc.create("task", "Normal task")

    # Corrupt the index: set type to an unknown value.
    _patch_index_item_field(_index_path(project), "type", "gizmo")

    # Any operation that calls store.load() must now raise SquadsError.
    with pytest.raises(SquadsError, match="no longer declares"):
        await svc.list_items()


async def test_load_error_leads_with_dropped_type_cause_not_sq_repair(svc, project) -> None:
    """When the *real* cause is a spec that dropped a still-populated type, the message must
    lead with that cause (migrate/re-type), not send the user in a `sq repair` loop —
    `sq repair` rebuilds from the frontmatter, which still carries the vanished type, so it
    would just re-fail.

    Repro: create a task against the normal bundled spec, then load the (unmodified,
    genuinely correct) index through a *spec* that no longer declares "task" — simulating a
    dropped-type override, as opposed to index/frontmatter corruption.
    """
    from squads._index._store import IndexStore
    from squads._workflow import bundled_spec

    await svc.create("task", "Normal task")

    base = bundled_spec()
    dropped_items = {k: v for k, v in base.items.items() if k != "task"}
    spec_without_task = base.model_copy(update={"items": dropped_items})

    store = IndexStore(project.index_path, project.lock_path, spec=spec_without_task)
    with pytest.raises(SquadsError) as exc_info:
        await store.load()

    message = str(exc_info.value)
    assert "no longer declares" in message
    assert message.index("no longer declares") < message.index("sq repair")


async def test_load_rejects_unknown_status(svc, project) -> None:
    """IndexStore.load() raises a clean SquadsError when an item has status='Frobnicated'.

    Repro: hand-edit .squads.json to set the first item's status to 'Frobnicated',
    then trigger a load — must surface SquadsError, not KeyError.
    """
    await svc.create("task", "Normal task")

    _patch_index_item_field(_index_path(project), "status", "Frobnicated")

    with pytest.raises(SquadsError, match="no longer declares"):
        await svc.list_items()


# ---------------------------------------------------------------------------
# repair() — unknown type / status in frontmatter
# ---------------------------------------------------------------------------


async def _get_first_item_md(svc) -> Path:  # type: ignore[no-untyped-def]
    """Create a task and return the Path to its markdown file."""
    res = await svc.create("task", "Repair target task")
    return res.path


async def test_repair_rejects_unknown_type(svc) -> None:
    """repair() raises a clean SquadsError when a markdown file's type is unknown.

    Repro: create a task, hand-edit its frontmatter to type=gizmo, then run sq repair —
    must surface SquadsError (not silently index and crash downstream).
    """
    md_path = await _get_first_item_md(svc)

    # Corrupt the markdown file's frontmatter type.
    _patch_md_frontmatter_field(md_path, "type", "gizmo")

    with pytest.raises(SquadsError, match="unknown type"):
        await svc.repair()


async def test_repair_rejects_unknown_status(svc) -> None:
    """repair() raises a clean SquadsError when a markdown file's status is unknown.

    Repro: create a task, hand-edit its frontmatter to status=Frobnicated, then run
    sq repair — must surface SquadsError (not silently index then crash downstream).
    """
    md_path = await _get_first_item_md(svc)

    _patch_md_frontmatter_field(md_path, "status", "Frobnicated")

    with pytest.raises(SquadsError, match="unknown status"):
        await svc.repair()


# ---------------------------------------------------------------------------
# F5: sub-entity status validation
# ---------------------------------------------------------------------------


async def test_load_rejects_unknown_subentity_status(svc, project) -> None:
    """IndexStore.load() raises a clean SquadsError when a sub-entity has an unknown status.

    Repro (F5): create a feature + story, hand-edit the story's status in .squads.json
    to 'Frobnicated', then trigger a load — must raise SquadsError, not crash with a
    raw ValueError from _discussion._status_badge downstream.
    """
    feat_res = await svc.create("feature", "Feature with story")
    await svc.add_story(feat_res.item.id, "User story one")

    # Corrupt the sub-entity status in the index.
    _patch_index_first_subentity_status(_index_path(project), "Frobnicated")

    with pytest.raises(SquadsError, match="no longer declares"):
        await svc.list_items()


async def test_repair_rejects_unknown_subentity_status(svc) -> None:
    """repair() raises a clean SquadsError when a sub-entity in the frontmatter has an unknown
    status.

    Repro (F5): create a feature + story, hand-edit the story's status in the markdown
    frontmatter to 'Frobnicated', then run sq repair — must raise SquadsError (not silently
    index and crash with a raw ValueError on show --full).
    """
    feat_res = await svc.create("feature", "Feature with story for repair test")
    await svc.add_story(feat_res.item.id, "Sub-entity with bad status")

    # Corrupt the sub-entity status in the feature's markdown frontmatter.
    _patch_md_subentity_status(feat_res.path, "Frobnicated")

    with pytest.raises(SquadsError, match="unknown status"):
        await svc.repair()


# ---------------------------------------------------------------------------
# TASK-341 (ADR-323): badge-code validation — the field/collection-axis counterpart
# to the type/status checks above.
# ---------------------------------------------------------------------------


async def test_load_rejects_unknown_priority_code(svc, project) -> None:
    """IndexStore.load() raises a clean SquadsError when an item's priority code isn't a
    badge in the bound 'priority' collection (hand-edited/stale index entry)."""
    task = (await svc.create("task", "Normal task", priority="high")).item

    _patch_index_item_by_seq(_index_path(project), task.sequence_id, priority="stratospheric")

    with pytest.raises(SquadsError, match="field 'priority' has unknown code 'stratospheric'"):
        await svc.list_items()


async def test_load_rejects_unknown_severity_code(svc, project) -> None:
    """Same check for item-level bug severity."""
    bug = (await svc.create("bug", "Normal bug")).item

    _patch_index_item_by_seq(_index_path(project), bug.sequence_id, severity="apocalyptic")

    with pytest.raises(SquadsError, match="field 'severity' has unknown code 'apocalyptic'"):
        await svc.list_items()


async def test_load_rejects_unknown_finding_severity_code(svc, project) -> None:
    """Same check for a sub-entity (finding) badge field."""
    rev = (await svc.create("review", "Review with a bad finding severity")).item
    await svc.add_finding(rev.id, "Null deref")

    (sub,) = (await svc.get(rev.id)).subentities
    _patch_index_item_by_seq(
        _index_path(project),
        rev.sequence_id,
        subentities=[{**sub.to_frontmatter_dict(), "severity": "off-the-scale"}],
    )

    with pytest.raises(SquadsError, match="field 'severity' has unknown code 'off-the-scale'"):
        await svc.list_items()


async def test_load_backfills_legacy_extra_severity_for_a_pre_adr323_bug(svc, project) -> None:
    """A bug indexed before ADR-323's storage move still has severity in extra[X.SEVERITY]
    (not top-level); IndexStore.load() backfills it onto Item.severity in memory and drops
    the stale extra copy, so the item reads correctly without a dedicated migration."""
    bug = (await svc.create("bug", "Legacy-shaped bug")).item

    _patch_index_item_by_seq(
        _index_path(project), bug.sequence_id, severity=None, extra={"severity": "critical"}
    )

    got = await svc.get(bug.id)
    assert got.severity == "critical"
    assert "severity" not in got.extra
