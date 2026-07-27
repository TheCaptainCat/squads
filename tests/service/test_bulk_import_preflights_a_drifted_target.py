"""The bulk importer's pre-flight of the frontmatter-skew guard: the check runs BEFORE the
batch, never inside it, so one drifted pre-existing target never turns an import into a
partially applied one -- it is reported as a pre-pass issue and nothing is written.
"""

import json

import pytest

from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


def _lines(*events: dict[str, object]) -> str:
    return "\n".join(json.dumps(e) for e in events)


async def _drift_via_interrupted_index_commit(svc, monkeypatch, item_id: str) -> None:
    real_atomic_write = IndexStore._atomic_write  # pyright: ignore[reportPrivateUsage]

    async def _boom(self, db):
        raise OSError("simulated crash during the index commit")

    monkeypatch.setattr(IndexStore, "_atomic_write", _boom)
    with pytest.raises(OSError):
        await svc.update(item_id, description="interrupted description")
    monkeypatch.setattr(IndexStore, "_atomic_write", real_atomic_write)


async def test_a_drifted_pre_existing_target_is_reported_and_nothing_is_applied(svc, monkeypatch):
    task = (await svc.create("task", "Drifted import target")).item
    await _drift_via_interrupted_index_commit(svc, monkeypatch, task.id)

    before = await svc.list_items()
    text = _lines(
        {"op": "create", "type": "task", "title": "Would have worked", "handle": "ok"},
        {"op": "status", "target": task.id, "status": "InProgress"},
    )
    result = await svc.import_events(text)

    assert not result.plan.ok
    assert any(
        task.id in issue.message and "repair" in issue.message for issue in result.plan.issues
    )
    assert result.applied is None
    after = await svc.list_items()
    assert len(after) == len(before)  # nothing applied -- not even the unrelated create


async def test_a_drifted_target_issue_coexists_with_an_unrelated_validation_issue(svc, monkeypatch):
    """The skew check never stops the pre-pass at the first problem -- it collects alongside
    every other issue the plan already gathers, same as any other collectible problem."""
    task = (await svc.create("task", "Drifted alongside an unrelated bad event")).item
    await _drift_via_interrupted_index_commit(svc, monkeypatch, task.id)

    text = _lines(
        {"op": "status", "target": task.id, "status": "InProgress"},
        {"op": "status", "target": "no-such-handle-or-id", "status": "InProgress"},
    )
    result = await svc.import_events(text)

    assert not result.plan.ok
    assert len(result.plan.issues) == 2
    assert any(task.id in i.message and "repair" in i.message for i in result.plan.issues)
    assert any("no-such-handle-or-id" in i.message for i in result.plan.issues)


async def test_several_events_on_the_same_drifted_target_report_it_once_not_per_event(
    svc, monkeypatch
):
    task = (await svc.create("task", "Multiply-targeted drifted item")).item
    await _drift_via_interrupted_index_commit(svc, monkeypatch, task.id)

    text = _lines(
        {"op": "status", "target": task.id, "status": "InProgress"},
        {"op": "update", "target": task.id, "description": "second touch"},
        {"op": "assign", "target": task.id, "assignee": "manager"},
    )
    result = await svc.import_events(text)

    assert not result.plan.ok
    matching = [i for i in result.plan.issues if task.id in i.message]
    assert len(matching) == 1


async def test_an_import_that_only_creates_items_is_never_affected_by_a_drifted_item(
    svc, monkeypatch
):
    """Creates are out of scope for the guard -- there is no prior file to diverge from --
    so a drifted item elsewhere on the board never touches a create-only import, however
    many creating events it carries."""
    drifted = (await svc.create("task", "Unrelated drifted item")).item
    await _drift_via_interrupted_index_commit(svc, monkeypatch, drifted.id)

    text = _lines(
        {"op": "create", "type": "task", "title": "Fresh one"},
        {"op": "create", "type": "task", "title": "Fresh two"},
        {"op": "create", "type": "task", "title": "Fresh three"},
    )
    result = await svc.import_events(text)

    assert result.plan.ok
    assert result.applied is not None
    assert result.applied.op_counts.counts["create"] == 3


async def test_a_clean_import_against_a_clean_board_is_unaffected(svc):
    task = (await svc.create("task", "Perfectly healthy target")).item
    text = _lines({"op": "status", "target": task.id, "status": "InProgress"})

    result = await svc.import_events(text)

    assert result.plan.ok
    assert result.applied is not None
    reloaded = await svc.get(task.id)
    assert reloaded.status == "InProgress"
