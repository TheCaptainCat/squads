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
    with pytest.raises(SquadsError, match="unknown type"):
        await svc.list_items()


async def test_load_rejects_unknown_status(svc, project) -> None:
    """IndexStore.load() raises a clean SquadsError when an item has status='Frobnicated'.

    Repro: hand-edit .squads.json to set the first item's status to 'Frobnicated',
    then trigger a load — must surface SquadsError, not KeyError.
    """
    await svc.create("task", "Normal task")

    _patch_index_item_field(_index_path(project), "status", "Frobnicated")

    with pytest.raises(SquadsError, match="unknown status"):
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

    with pytest.raises(SquadsError, match="unknown status"):
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
