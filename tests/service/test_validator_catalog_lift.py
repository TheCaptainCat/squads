"""Parity between each lifted ``CATALOG``/``SQUAD_GLOBAL_CATALOG`` entry and the hardcoded
``_check_*`` method it replaces: same level, item id, and message on crafted fixtures. The
engine itself is still inert (empty bundles) — these tests call each named validator directly
against a hand-built context, sourced from a real ``svc``-created scenario.
"""

from pathlib import Path

import pytest

from squads._interactions import TITLE_ADVISORY_MAX
from squads._services._validators import (
    CATALOG,
    SQUAD_GLOBAL_CATALOG,
    SquadGlobalContext,
    ValidatorContext,
    registered_slugs,
    supersedes_incoming_seqs,
)

pytestmark = pytest.mark.anyio


def _raw_text(svc, item) -> str:
    return svc.paths.abspath(item.path).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- parent_in / no_parent


async def test_parent_in_flags_a_dangling_parent(svc):
    task = (await svc.create("task", "t")).item
    db = await svc.store.load()
    db.items[task.sequence_id].parent = "FEAT-999999"  # dangling, bypassing create()'s own gate
    ctx = ValidatorContext(item=db.get(task.id), spec=svc.spec, index=db)
    issues = CATALOG["parent_in"](ctx)
    assert issues == [
        type(issues[0])("error", task.id, "dangling parent FEAT-999999"),
    ]


async def test_parent_in_flags_a_wrong_type_parent(svc):
    feat = (await svc.create("feature", "f")).item
    task = (await svc.create("task", "t", parent=feat.id)).item
    other_task = (await svc.create("task", "u")).item
    db = await svc.store.load()
    db.items[task.sequence_id].parent = other_task.id  # a task can't parent a task
    ctx = ValidatorContext(item=db.get(task.id), spec=svc.spec, index=db)
    issues = CATALOG["parent_in"](ctx)
    assert len(issues) == 1
    assert issues[0].level == "error"
    assert issues[0].item == task.id
    assert "got task" in issues[0].message


async def test_parent_in_is_lenient_when_parents_is_empty(svc):
    """`review`'s declared `parents` is empty — any parent (or none) passes, byte-identical
    with today's `parent_allowed` short-circuit."""
    task = (await svc.create("task", "t")).item
    rev = (await svc.create("review", "r", parent=task.id)).item
    db = await svc.store.load()
    ctx = ValidatorContext(item=db.get(rev.id), spec=svc.spec, index=db)
    assert CATALOG["parent_in"](ctx) == []


async def test_no_parent_flags_any_declared_parent(svc):
    feat = (await svc.create("feature", "f")).item
    task = (await svc.create("task", "t", parent=feat.id)).item
    db = await svc.store.load()
    ctx = ValidatorContext(item=db.get(task.id), spec=svc.spec, index=db)
    issues = CATALOG["no_parent"](ctx)
    assert len(issues) == 1 and issues[0].level == "error" and issues[0].item == task.id


async def test_no_parent_is_silent_with_no_parent(svc):
    feat = (await svc.create("feature", "f")).item
    db = await svc.store.load()
    ctx = ValidatorContext(item=db.get(feat.id), spec=svc.spec, index=db)
    assert CATALOG["no_parent"](ctx) == []


# --------------------------------------------------------------------------- item_status_valid


async def test_item_status_valid_flags_an_unknown_status(svc):
    task = (await svc.create("task", "t")).item
    db = await svc.store.load()
    db.items[task.sequence_id].status = "NotAStatus"
    ctx = ValidatorContext(item=db.get(task.id), spec=svc.spec)
    issues = CATALOG["item_status_valid"](ctx)
    assert issues == [type(issues[0])("error", task.id, "status 'NotAStatus' invalid for task")]


# ------------------------------------------------------------------ dangling_ref / ref_kind_valid


async def test_dangling_ref_flags_an_unresolvable_target(svc):
    task = (await svc.create("task", "t")).item
    db = await svc.store.load()
    db.items[task.sequence_id].refs = ["BUG-999999"]
    ctx = ValidatorContext(item=db.get(task.id), spec=svc.spec, index=db)
    issues = CATALOG["dangling_ref"](ctx)
    assert issues == [type(issues[0])("warn", task.id, "dangling ref BUG-999999")]


async def test_ref_kind_valid_flags_an_unknown_kind(svc):
    a = (await svc.create("task", "a")).item
    b = (await svc.create("task", "b")).item
    db = await svc.store.load()
    db.items[a.sequence_id].refs = [f"{b.id}:not-a-real-kind"]
    ctx = ValidatorContext(item=db.get(a.id), spec=svc.spec, index=db)
    issues = CATALOG["ref_kind_valid"](ctx)
    assert len(issues) == 1
    assert issues[0].level == "warn"
    assert "not-a-real-kind" in issues[0].message


# --------------------------------------------------------------------------- agent_registered


async def test_agent_registered_flags_a_deregistered_author(svc):
    task = (await svc.create("task", "t", author="manager")).item
    await svc.remove_item((await svc.get("ROLE-000001")).id)
    db = await svc.store.load()
    ctx = ValidatorContext(
        item=db.get(task.id), spec=svc.spec, registered_slugs=registered_slugs(db, svc.spec)
    )
    issues = CATALOG["agent_registered"](ctx)
    assert len(issues) == 1
    assert issues[0].level == "warn" and issues[0].item == task.id
    assert "author 'manager' is not a registered agent or operator" in issues[0].message


async def test_agent_registered_is_silent_for_a_registered_author(svc):
    task = (await svc.create("task", "t", author="manager")).item
    db = await svc.store.load()
    ctx = ValidatorContext(
        item=db.get(task.id), spec=svc.spec, registered_slugs=registered_slugs(db, svc.spec)
    )
    assert CATALOG["agent_registered"](ctx) == []


# --------------------------------------------------------------------------- subtask_story_mapping


async def test_subtask_story_mapping_flags_a_missing_story(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "a story")
    task = (await svc.create("task", "t", parent=feat.id)).item
    await svc.add_subtask(task.id, "a subtask", story="US1")

    db = await svc.store.load()
    db.items[task.sequence_id].subentities[0].story = "US99"  # bypass add_subtask's own guard
    ctx = ValidatorContext(item=db.get(task.id), spec=svc.spec, index=db)
    issues = CATALOG["subtask_story_mapping"](ctx)
    assert len(issues) == 1
    assert issues[0].level == "error" and issues[0].item == task.id
    assert "US99" in issues[0].message and feat.id in issues[0].message


async def test_subtask_story_mapping_is_silent_when_the_story_exists(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "a story")
    task = (await svc.create("task", "t", parent=feat.id)).item
    await svc.add_subtask(task.id, "a subtask", story="US1")

    db = await svc.store.load()
    ctx = ValidatorContext(item=db.get(task.id), spec=svc.spec, index=db)
    assert CATALOG["subtask_story_mapping"](ctx) == []


# --------------------------------------------------------------------------- subentity_status_valid


async def test_subentity_status_valid_flags_an_unreachable_status(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "a story")
    db = await svc.store.load()
    db.items[feat.sequence_id].subentities[0].status = "NotAStatus"
    ctx = ValidatorContext(item=db.get(feat.id), spec=svc.spec)
    issues = CATALOG["subentity_status_valid"](ctx)
    assert len(issues) == 1 and issues[0].level == "error" and "US1" in issues[0].message


# --------------------------------------------------------------------------- subentity_body_written


async def test_subentity_body_written_flags_an_unwritten_placeholder(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "a story")  # no body= → stays the placeholder
    db = await svc.store.load()
    item = db.get(feat.id)
    ctx = ValidatorContext(item=item, spec=svc.spec, raw_text=_raw_text(svc, item))
    issues = CATALOG["subentity_body_written"](ctx)
    assert len(issues) == 1 and issues[0].level == "warn" and "US1" in issues[0].message


async def test_subentity_body_written_is_silent_once_written(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "a story", body="real content")
    db = await svc.store.load()
    item = db.get(feat.id)
    ctx = ValidatorContext(item=item, spec=svc.spec, raw_text=_raw_text(svc, item))
    assert CATALOG["subentity_body_written"](ctx) == []


# --------------------------------------------------------------------------- subentity_title_max


async def test_subentity_title_max_flags_an_over_long_title(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "x" * (TITLE_ADVISORY_MAX + 1))
    db = await svc.store.load()
    ctx = ValidatorContext(item=db.get(feat.id), spec=svc.spec)
    issues = CATALOG["subentity_title_max"](ctx)
    assert len(issues) == 1 and issues[0].level == "warn"
    assert str(TITLE_ADVISORY_MAX) in issues[0].message


async def test_subentity_title_max_is_silent_at_the_threshold(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "x" * TITLE_ADVISORY_MAX)
    db = await svc.store.load()
    ctx = ValidatorContext(item=db.get(feat.id), spec=svc.spec)
    assert CATALOG["subentity_title_max"](ctx) == []


# --------------------------------------------------------------------------- no_status_banner


async def test_no_status_banner_flags_a_body_banner(svc):
    task = (await svc.create("task", "t", body="STATUS: Draft\nsome text")).item
    db = await svc.store.load()
    item = db.get(task.id)
    ctx = ValidatorContext(item=item, spec=svc.spec, raw_text=_raw_text(svc, item))
    issues = CATALOG["no_status_banner"](ctx)
    assert len(issues) == 1 and issues[0].level == "warn" and "body opens with" in issues[0].message


async def test_no_status_banner_flags_a_description_banner(svc):
    task = (await svc.create("task", "t", description="STATUS: Draft")).item
    db = await svc.store.load()
    item = db.get(task.id)
    ctx = ValidatorContext(item=item, spec=svc.spec, raw_text=_raw_text(svc, item))
    issues = CATALOG["no_status_banner"](ctx)
    assert len(issues) == 1 and "description opens with" in issues[0].message


async def test_no_status_banner_is_silent_for_ordinary_prose(svc):
    task = (await svc.create("task", "t", body="just some prose")).item
    db = await svc.store.load()
    item = db.get(task.id)
    ctx = ValidatorContext(item=item, spec=svc.spec, raw_text=_raw_text(svc, item))
    assert CATALOG["no_status_banner"](ctx) == []


# --------------------------------------------------------------------------- supersedes_incoming


async def test_supersedes_incoming_flags_a_superseded_decision_with_no_incoming_edge(svc):
    old_adr = (await svc.create("decision", "old decision")).item
    await svc.set_status(old_adr.id, "Proposed")
    await svc.set_status(old_adr.id, "Superseded", force=True)
    db = await svc.store.load()
    ctx = ValidatorContext(item=db.get(old_adr.id), spec=svc.spec)
    issues = CATALOG["supersedes_incoming"](ctx)
    assert len(issues) == 1 and issues[0].level == "warn"


async def test_supersedes_incoming_is_silent_once_superseded(svc):
    old_adr = (await svc.create("decision", "old decision")).item
    new_adr = (await svc.create("decision", "new decision")).item
    await svc.set_status(old_adr.id, "Proposed")
    await svc.set_status(old_adr.id, "Superseded", force=True)
    await svc.add_ref(new_adr.id, old_adr.id, kind="supersedes")
    db = await svc.store.load()
    ctx = ValidatorContext(
        item=db.get(old_adr.id), spec=svc.spec, supersedes_incoming=supersedes_incoming_seqs(db)
    )
    assert CATALOG["supersedes_incoming"](ctx) == []


# --------------------------------------------------------------------------- squad-global


async def test_index_reconciled_flags_an_item_with_no_markdown_file(svc):
    task = (await svc.create("task", "t")).item
    db = await svc.store.load()  # on_disk stays {} — no on-disk entry for this item's sequence
    ctx = SquadGlobalContext(index=db, on_disk={}, spec=svc.spec, paths=svc.paths)
    issues = SQUAD_GLOBAL_CATALOG["index_reconciled"](ctx)
    assert any(i.item == task.id and "no markdown file found" in i.message for i in issues)


async def test_index_reconciled_flags_a_file_absent_from_the_index(svc):
    task = (await svc.create("task", "t")).item
    db = await svc.store.load()
    on_disk = {task.sequence_id: (task.id, Path("unused"), {})}
    del db.items[task.sequence_id]  # present on disk, absent from the (in-memory) index
    ctx = SquadGlobalContext(index=db, on_disk=on_disk, spec=svc.spec, paths=svc.paths)
    issues = SQUAD_GLOBAL_CATALOG["index_reconciled"](ctx)
    assert any(i.item == task.id and "on disk but not in index" in i.message for i in issues)


async def test_backend_reconciled_flags_a_missing_managed_file(svc):
    (svc.paths.root / "CLAUDE.md").unlink(missing_ok=True)
    db = await svc.store.load()
    ctx = SquadGlobalContext(index=db, on_disk={}, spec=svc.spec, paths=svc.paths)
    issues = SQUAD_GLOBAL_CATALOG["backend_reconciled"](ctx)
    assert any("managed file missing" in i.message for i in issues)


async def test_backend_reconciled_is_silent_after_sync(svc):
    await svc.sync()
    db = await svc.store.load()
    ctx = SquadGlobalContext(index=db, on_disk={}, spec=svc.spec, paths=svc.paths)
    assert SQUAD_GLOBAL_CATALOG["backend_reconciled"](ctx) == []


# ------------------------------------------------------------------ context builders


async def test_registered_slugs_reads_the_roster(svc):
    db = await svc.store.load()
    assert "manager" in registered_slugs(db, svc.spec)


async def test_supersedes_incoming_seqs_reads_incoming_supersedes_edges(svc):
    old_adr = (await svc.create("decision", "old decision")).item
    new_adr = (await svc.create("decision", "new decision")).item
    await svc.add_ref(new_adr.id, old_adr.id, kind="supersedes")
    db = await svc.store.load()
    seqs = supersedes_incoming_seqs(db)
    assert old_adr.sequence_id in seqs
    assert new_adr.sequence_id not in seqs
