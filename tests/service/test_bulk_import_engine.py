"""The bulk import engine: a JSONL event stream is validated (writing nothing) before it is
ever applied (one transaction), per-event ``at``/``as`` drives every mutation's timestamps and
authorship, and client handles let a create and a later event on the same new item compose
within one file. Covers both the validate-first pre-pass (error collection, dry-run) and the
apply pass (files/frontmatter/reflog/board-debt warnings/crash-safety).
"""

import json

import pytest

from _helpers import create_item
from squads import _itemfile
from squads._index._reflog import read_lines, reflog_path
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section

pytestmark = pytest.mark.anyio


def _lines(*events: dict[str, object]) -> str:
    return "\n".join(json.dumps(e) for e in events)


async def test_a_clean_multi_event_file_creates_cross_references_and_writes_everything(svc):
    await svc.activate_role("tech-lead")

    text = _lines(
        {
            "op": "create",
            "at": "2026-01-01T00:00:00Z",
            "as": "manager",
            "type": "epic",
            "title": "Epic one",
            "handle": "epic1",
        },
        {
            "op": "create",
            "type": "feature",
            "title": "Feature one",
            "parent": "epic1",
            "handle": "feat1",
        },
        {"op": "add-story", "target": "feat1", "title": "Login flow", "handle": "us1"},
        {
            "op": "create",
            "as": "tech-lead",
            "type": "task",
            "title": "Task one",
            "parent": "feat1",
            "handle": "task1",
        },
        {
            "op": "add-subtask",
            "target": "task1",
            "title": "Wire endpoint",
            "story": "us1",
            "handle": "st1",
        },
        {"op": "status", "target": "task1", "status": "InProgress"},
        {"op": "body", "target": "task1", "body": "Do the thing."},
        {"op": "comment", "target": "task1", "messages": ["hi team"]},
        {"op": "ref", "target": "task1", "to": "feat1", "kind": "implements"},
        {
            "op": "sub-status",
            "target": "task1",
            "kind": "subtask",
            "local": "st1",
            "status": "InProgress",
        },
        {
            "op": "sub-body",
            "target": "task1",
            "kind": "subtask",
            "local": "st1",
            "body": "Subtask notes.",
        },
        {"op": "assign", "target": "task1", "assignee": "tech-lead"},
        {
            "op": "update",
            "target": "feat1",
            "title": "Feature renamed",
            "add_labels": ["important"],
        },
    )

    result = await svc.import_events(text)
    assert result.plan.ok, result.plan.issues
    assert result.applied is not None
    applied = result.applied

    # Handles resolved to real ids/locals.
    assert set(applied.handle_to_id) == {"epic1", "feat1", "task1"}
    assert set(applied.handle_to_sub) == {"us1", "st1"}
    task_id = applied.handle_to_id["task1"]
    feat_id = applied.handle_to_id["feat1"]

    task = await svc.get(task_id)
    assert task.status == "InProgress"
    assert task.assignee == "tech-lead"
    assert task.parent == feat_id
    assert any(r.startswith(f"{feat_id}:implements") for r in task.refs)
    (subtask,) = task.subentities
    assert subtask.status == "InProgress"
    assert subtask.story == applied.handle_to_sub["us1"][1]

    text_on_disk = await _read(svc, task_id)
    assert (get_section(text_on_disk, markers.BODY) or "").strip() == "Do the thing."
    assert "hi team" in (get_section(text_on_disk, markers.DISCUSSION) or "")

    feat = await svc.get(feat_id)
    assert feat.title == "Feature renamed"
    assert "important" in feat.labels

    # Reflog: per-event actor recorded correctly even though every event shares ONE transaction.
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    task_create = next(ln for ln in lines if ln.op == "create" and ln.target == task_id)
    assert task_create.actor == "tech-lead"
    epic_id = applied.handle_to_id["epic1"]
    epic_create = next(ln for ln in lines if ln.op == "create" and ln.target == epic_id)
    assert epic_create.actor == "manager"

    # Op counts reflect what the file actually wrote (ergonomic fronts kept, not normalized).
    assert applied.op_counts.counts["add-story"] == 1
    assert applied.op_counts.counts["add-subtask"] == 1
    assert applied.op_counts.counts["create"] == 3


async def _read(svc, item_id: str) -> str:
    item = await svc.get(item_id)
    from squads import _aio

    return await _aio.read_text(item_file(svc.paths, item))


async def test_the_counter_advances_monotonically_across_every_created_item(svc):
    before = (await svc.store.load()).counter
    text = _lines(
        {"op": "create", "type": "task", "title": "One", "handle": "a"},
        {"op": "create", "type": "task", "title": "Two", "handle": "b"},
        {"op": "create", "type": "task", "title": "Three", "handle": "c"},
    )
    result = await svc.import_events(text, default_as="manager")
    assert result.applied is not None
    after = (await svc.store.load()).counter
    assert after == before + 3


async def test_dry_run_writes_nothing_even_when_the_file_is_fully_clean(svc):
    before = await svc.list_items()
    text = _lines({"op": "create", "type": "task", "title": "Never written"})
    result = await svc.import_events(text, dry_run=True, default_as="manager")
    assert result.plan.ok
    assert result.applied is None
    after = await svc.list_items()
    assert len(after) == len(before)


async def test_prepass_collects_every_seeded_error_with_correct_line_numbers(svc):
    existing = (await create_item(svc, "task", "Existing")).item
    other = (await create_item(svc, "task", "Other")).item

    text = _lines(
        {"op": "create", "type": "not-a-real-type", "title": "Bad type"},  # line 1
        {"op": "status", "target": existing.id, "status": "Bogus"},  # line 2: bad status
        {"op": "status", "target": existing.id, "status": "Done"},  # line 3: illegal transition
        {"op": "create", "type": "task", "title": "Dangling", "parent": "TASK-999999"},  # line 4
        {"op": "create", "type": "task", "title": "Bad actor", "as": "no-such-agent"},  # line 5
        {"op": "ref", "target": existing.id, "to": other.id, "kind": "bogus-kind"},  # line 6
        {"op": "add-sub", "target": existing.id, "kind": "no-such-kind", "title": "x"},  # line 7
    )

    result = await svc.import_events(text, dry_run=True, default_as="manager")
    assert not result.plan.ok
    assert result.applied is None
    lines_with_issues = {i.line for i in result.plan.issues}
    assert lines_with_issues == {1, 2, 3, 4, 5, 6, 7}
    # Nothing was written — the pre-existing item is untouched and no new one appeared.
    still = await svc.get(existing.id)
    assert still.status == "Draft"
    assert len([i for i in await svc.list_items() if i.type == "task"]) == 2


async def test_an_unknown_add_sub_kind_is_collected_not_a_traceback(svc):
    """A generic ``add-sub`` naming a kind the item doesn't host (or that doesn't exist at
    all) must resolve to a reported pre-pass issue at its own line, never an uncaught
    ``KeyError`` that aborts the whole validate-first pass."""
    task = (await create_item(svc, "task", "Host")).item
    text = _lines(
        {"op": "add-sub", "target": task.id, "kind": "no-such-kind", "title": "x"},
    )
    result = await svc.import_events(text, dry_run=True, default_as="manager")
    assert not result.plan.ok
    assert result.applied is None
    assert result.plan.issues[0].line == 1
    assert "no-such-kind" in result.plan.issues[0].message


async def test_a_dangling_handle_reference_is_reported_not_silently_passed_through(svc):
    text = _lines(
        {"op": "status", "target": "never-created", "status": "InProgress"},
    )
    result = await svc.import_events(text, dry_run=True, default_as="manager")
    assert not result.plan.ok
    assert result.plan.issues[0].line == 1


async def test_board_debt_from_an_import_surfaces_as_a_warning_not_silent_debt(svc):
    review = (await create_item(svc, "review", "A review")).item
    long_title = "x" * 200
    text = _lines(
        {"op": "add-finding", "target": review.id, "title": long_title, "severity": "high"},
    )
    result = await svc.import_events(text, default_as="manager")
    assert result.applied is not None
    assert any("title" in w.lower() for w in result.applied.warnings)


async def test_apply_only_runs_after_a_fully_clean_prepass(svc):
    """A file mixing one good and one bad event applies NOTHING — not even the good half."""
    text = _lines(
        {"op": "create", "type": "task", "title": "Would have worked", "handle": "ok"},
        {"op": "status", "target": "ok", "status": "Bogus"},
    )
    before = await svc.list_items()
    result = await svc.import_events(text, default_as="manager")
    assert not result.plan.ok
    assert result.applied is None
    after = await svc.list_items()
    assert len(after) == len(before)


async def test_repair_reconciles_after_a_simulated_mid_apply_failure(svc, monkeypatch):
    """A crash between two events' file writes leaves the first item's file on disk but the
    index uncommitted (the whole transaction never reaches its one ``os.replace``) — ``sq
    repair`` reconciles it back into the index, per the files-then-index safe-failure order."""
    text = _lines(
        {"op": "create", "type": "task", "title": "Survives the crash", "handle": "a"},
        {"op": "status", "target": "a", "status": "InProgress"},
    )
    parsed = await svc.import_events(text, dry_run=True, default_as="manager")
    assert parsed.plan.ok

    from squads._services import _import_model

    events, _issues = _import_model.parse_events(
        text, default_at=_import_model.utc_now_floor(), default_as="manager"
    )

    real_update_frontmatter = _itemfile.update_frontmatter
    calls = {"n": 0}

    async def _boom(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("simulated crash mid-apply")
        return await real_update_frontmatter(*args, **kwargs)

    monkeypatch.setattr("squads._services._items.update_frontmatter", _boom)

    with pytest.raises(OSError):
        await svc._apply_import(events)

    # The index was never committed with this new item...
    db = await svc.store.load()
    assert all(it.title != "Survives the crash" for it in db.items.values())

    # ...but repair reconciles it back in from the file that DID get written.
    await svc.repair()
    db2 = await svc.store.load()
    assert any(it.title == "Survives the crash" for it in db2.items.values())


async def test_a_dry_run_title_change_never_renames_the_file_on_disk(svc):
    """A title-bearing `update` reaches a real `Path.rename` only through the apply pass's
    `_update_core` -- the pre-pass simulates purely against a throwaway index copy. Pin the
    actual promise a dry run makes: the filesystem is untouched, not just the index."""
    task = (await create_item(svc, "task", "Original title")).item
    old_path = item_file(svc.paths, task)
    assert old_path.exists()

    text = _lines({"op": "update", "target": task.id, "title": "Renamed via dry run"})
    result = await svc.import_events(text, dry_run=True, default_as="manager")
    assert result.plan.ok
    assert result.applied is None

    assert old_path.exists()
    assert list(old_path.parent.glob("*renamed-via-dry-run*")) == []
    reloaded = await svc.get(task.id)
    assert reloaded.title == "Original title"


async def test_replaying_a_history_that_retires_the_last_live_role_before_a_replacement_lands(
    svc,
):
    """The importer's pre-pass is held to the same config-integrity gate as the interactive
    path, at each step it replays: a history that retires the only live role and activates a
    replacement in the very next event is refused at the retiring step, even though the final
    state would have been fine — the accepted cost of holding a replay to the same rule as the
    interactive path. The remedy is to reorder the import so the replacement lands first."""
    manager = await svc.roster_item("role", "manager")
    qa = await svc.activate_role("qa")
    await svc.set_status(qa.id, "Archived")  # pre-existing, but not yet live

    text = _lines(
        {"op": "status", "target": manager.id, "status": "Archived"},  # line 1: last live role
        {"op": "status", "target": qa.id, "status": "Active"},  # line 2: would have fixed it
    )
    result = await svc.import_events(text, dry_run=True, default_as="manager")

    assert not result.plan.ok
    assert result.applied is None
    assert result.plan.issues[0].line == 1
    assert "no role entry is live" in result.plan.issues[0].message
    # Nothing written — the pre-existing roles are untouched on disk.
    still_manager = await svc.get(manager.id)
    assert still_manager.status == "Active"


async def test_a_shrinking_pre_existing_scoped_edge_violation_replays_cleanly(svc):
    """The delta-key fix through the importer: the pre-pass calls the same delta-scoped gate as the
    interactive path, at each event it replays. A skill archived while scoped to two live
    roles is a pre-existing violation; replaying an event that retires one of those roles
    strictly shrinks it and must not be refused, the same as the interactive path."""
    live_role = await svc.activate_role("qa")
    other_role = await svc.roster_item("role", "manager")
    skill = await svc.add_skill("Custom Helper")
    await svc.link_role(skill.id, live_role.id)
    await svc.link_role(skill.id, other_role.id)
    async with svc.store.transaction() as db:
        item = db.get(skill.id)
        assert item is not None
        base = item.model_copy(deep=True)
        item.status = "Archived"  # pre-existing: scoped to qa AND manager, reached outside sq
        await _itemfile.update_frontmatter(
            item_file(svc.paths, item), item, base, default_kind=svc.spec.default_ref_kind()
        )

    text = _lines({"op": "status", "target": live_role.id, "status": "Archived"})
    result = await svc.import_events(text, default_as="manager")

    assert result.plan.ok, result.plan.issues
    assert result.applied is not None
    assert (await svc.get(live_role.id)).status == "Archived"


async def test_a_generic_update_event_cannot_change_a_roster_items_status(svc):
    """The generic ``update`` op's ``status`` field reaches ``_update_model`` directly, which
    evaluates none of the config-integrity clauses and runs no projection — the roster status
    axis has exactly one gated entry point (the ``status`` op / ``set_roster_status``), and this
    ungated one must refuse rather than silently write a status the gate never saw."""
    role = await svc.roster_item("role", "manager")

    text = _lines({"op": "update", "target": role.id, "status": "Archived"})
    result = await svc.import_events(text, dry_run=True, default_as="manager")

    assert not result.plan.ok
    assert "status cannot change through `update`" in result.plan.issues[0].message
    still_manager = await svc.get(role.id)
    assert still_manager.status == "Active"


async def test_applying_a_title_change_does_rename_the_file_on_disk(svc):
    """The other half of the same guarantee: once a dry run's own plan is clean, the real
    apply performs the physical move the pre-pass deliberately never does."""
    task = (await create_item(svc, "task", "Original title")).item
    old_path = item_file(svc.paths, task)

    text = _lines({"op": "update", "target": task.id, "title": "Renamed for real"})
    result = await svc.import_events(text, default_as="manager")
    assert result.applied is not None

    assert not old_path.exists()
    item = await svc.get(task.id)
    assert item.title == "Renamed for real"
    assert item_file(svc.paths, item).exists()
