"""Every path that materializes an Item from disk validates `type`/`status`/badge codes
against the loaded spec and fails closed with a clean `SquadsError` — never a raw `KeyError`/
`ValueError`, and never a silent index that crashes downstream. Two independent boundaries are
covered: `IndexStore.load()` (a corrupted index) and `repair()` (a corrupted frontmatter file).
"""

import json
from pathlib import Path

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


def _index_path(project) -> Path:
    return project.squad_dir / ".squads.json"


def _patch_index_item_field(index_path: Path, field: str, value: str) -> None:
    data = json.loads(index_path.read_text(encoding="utf-8"))
    items = data["items"]
    first_key = next(iter(items))
    items[first_key] = {**items[first_key], field: value}
    index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _patch_index_first_subentity_status(index_path: Path, bad_status: str) -> None:
    data = json.loads(index_path.read_text(encoding="utf-8"))
    items = data["items"]
    for key in items:
        item = dict(items[key])
        subs = item.get("subentities") or []
        if subs:
            patched = {**subs[0], "status": bad_status}
            item["subentities"] = [patched, *subs[1:]]
            items[key] = item
            break
    index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _patch_index_item_by_seq(index_path: Path, seq: int, **fields: object) -> None:
    data = json.loads(index_path.read_text(encoding="utf-8"))
    key = str(seq)
    data["items"][key] = {**data["items"][key], **fields}
    index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _patch_md_frontmatter_field(md_path: Path, field: str, value: str) -> None:
    lines = md_path.read_text(encoding="utf-8").splitlines(keepends=True)
    patched = [f"{field}: {value}\n" if line.startswith(f"{field}:") else line for line in lines]
    md_path.write_text("".join(patched), encoding="utf-8")


def _patch_md_subentity_status(md_path: Path, bad_status: str) -> None:
    lines = md_path.read_text(encoding="utf-8").splitlines(keepends=True)
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


# --------------------------------------------------------------------------- IndexStore.load()


async def test_load_rejects_an_item_with_an_unknown_type(svc, project):
    await svc.create("task", "Normal task")
    _patch_index_item_field(_index_path(project), "type", "gizmo")

    with pytest.raises(SquadsError, match="no longer declares"):
        await svc.list_items()


async def test_load_rejects_an_item_with_an_unknown_status(svc, project):
    await svc.create("task", "Normal task")
    _patch_index_item_field(_index_path(project), "status", "Frobnicated")

    with pytest.raises(SquadsError, match="no longer declares"):
        await svc.list_items()


async def test_load_rejects_an_unknown_subentity_status(svc, project):
    feat_res = await svc.create("feature", "Feature with story")
    await svc.add_story(feat_res.item.id, "User story one")
    _patch_index_first_subentity_status(_index_path(project), "Frobnicated")

    with pytest.raises(SquadsError, match="no longer declares"):
        await svc.list_items()


async def test_load_error_leads_with_the_real_cause_not_a_repair_loop(svc, project):
    """When the real cause is a spec that dropped a still-populated type, the message must
    lead with that cause, not send the user into a `sq repair` loop -- repair rebuilds from
    frontmatter, which still carries the vanished type, so it would just re-fail."""
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


async def test_load_rejects_an_unknown_badge_code_on_a_priority_field(svc, project):
    task = (await svc.create("task", "Normal task", priority="high")).item
    _patch_index_item_by_seq(_index_path(project), task.sequence_id, priority="stratospheric")

    with pytest.raises(SquadsError, match="field 'priority' has unknown code 'stratospheric'"):
        await svc.list_items()


async def test_load_rejects_an_unknown_badge_code_on_a_severity_field(svc, project):
    bug = (await svc.create("bug", "Normal bug")).item
    _patch_index_item_by_seq(_index_path(project), bug.sequence_id, severity="apocalyptic")

    with pytest.raises(SquadsError, match="field 'severity' has unknown code 'apocalyptic'"):
        await svc.list_items()


async def test_load_rejects_an_unknown_badge_code_on_a_finding_sub_entity(svc, project):
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


async def test_load_backfills_a_pre_migration_bugs_legacy_extra_severity(svc, project):
    """A bug indexed before the top-level severity field existed still resolves correctly:
    load() backfills the legacy extra copy in memory and drops it, with no dedicated migration
    needed."""
    bug = (await svc.create("bug", "Legacy-shaped bug")).item
    _patch_index_item_by_seq(
        _index_path(project), bug.sequence_id, severity=None, extra={"severity": "critical"}
    )

    got = await svc.get(bug.id)
    assert got.severity == "critical"
    assert "severity" not in got.extra


# --------------------------------------------------------------------------- repair() boundary


async def test_repair_rejects_a_frontmatter_file_with_an_unknown_type(svc):
    res = await svc.create("task", "Repair target task")
    _patch_md_frontmatter_field(res.path, "type", "gizmo")

    with pytest.raises(SquadsError, match="unknown type"):
        await svc.repair()


async def test_repair_rejects_a_frontmatter_file_with_an_unknown_status(svc):
    res = await svc.create("task", "Repair target task")
    _patch_md_frontmatter_field(res.path, "status", "Frobnicated")

    with pytest.raises(SquadsError, match="unknown status"):
        await svc.repair()


async def test_repair_rejects_a_frontmatter_sub_entity_with_an_unknown_status(svc):
    feat_res = await svc.create("feature", "Feature with story for repair test")
    await svc.add_story(feat_res.item.id, "Sub-entity with bad status")
    _patch_md_subentity_status(feat_res.path, "Frobnicated")

    with pytest.raises(SquadsError, match="unknown status"):
        await svc.repair()
