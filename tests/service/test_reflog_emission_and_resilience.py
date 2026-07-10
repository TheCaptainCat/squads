"""Every mutating verb appends exactly one reflog line, using the injected clock and the ambient
actor (parametrized over the verb list rather than one near-identical body per verb) — and the
log is best-effort: a failed append never rolls back the committed mutation, a squad with no
reflog file at all is backward compatible, and neither `repair` nor `check` ever reads it back
(frontmatter, not the reflog, is the rebuildable source of truth).
"""

import pytest

from squads import _actor as actor
from squads import _clock as clock
from squads._index import _reflog
from squads._index._reflog import reflog_path

pytestmark = pytest.mark.anyio


async def _create(svc):
    return (await svc.create("task", "T")).item


async def _status(svc):
    item = await _create(svc)
    await svc.set_status(item.id, "InProgress")
    return item


async def _update(svc):
    item = await _create(svc)
    await svc.update(item.id, title="Updated T")
    return item


async def _ref_add(svc):
    a = await _create(svc)
    b = (await svc.create("bug", "B")).item
    await svc.add_ref(a.id, b.id, kind="related")
    return a


async def _comment(svc):
    item = await _create(svc)
    await svc.comment(item.id, ["Hello world"])
    return item


async def _subentity_add(svc):
    item = await _create(svc)
    await svc.add_subtask(item.id, "ST")
    return item


async def _retype(svc):
    item = await _create(svc)
    result = await svc.retype(item.id, "bug")
    return result.item


async def _remove(svc):
    item = await _create(svc)
    await svc.remove_work_item(item.id)
    return item


_VERBS = {
    "create": ("create", _create),
    "status": ("status", _status),
    "update": ("update", _update),
    "ref": ("ref", _ref_add),
    "comment": ("comment", _comment),
    "subentity": ("subentity", _subentity_add),
    "retype": ("retype", _retype),
    "remove": ("remove", _remove),
}


@pytest.mark.parametrize("verb", sorted(_VERBS))
async def test_every_mutating_verb_emits_exactly_one_reflog_line(svc, frozen_time, verb):
    op, run = _VERBS[verb]
    item = await run(svc)
    lines = await _reflog.read_lines(reflog_path(svc.paths.squad_dir))
    # retype changes the target id (new id); every other verb's line targets the item's own id.
    target = item.id
    matching = [ln for ln in lines if ln.op == op and ln.target == target]
    assert len(matching) == 1, f"expected exactly one {op!r} line for {target!r}, got {matching}"


async def test_repair_emits_its_own_reflog_line(svc, frozen_time):
    await svc.repair()
    lines = await _reflog.read_lines(reflog_path(svc.paths.squad_dir))
    assert any(ln.op == "repair" for ln in lines)


async def test_ambient_actor_and_frozen_clock_flow_into_the_reflog_line(svc, frozen_time):
    actor.set_actor("python-dev")
    item = (await svc.create("task", "Authored by python-dev")).item
    lines = await _reflog.read_lines(reflog_path(svc.paths.squad_dir))
    create_lines = [ln for ln in lines if ln.op == "create" and ln.target == item.id]
    assert create_lines[-1].actor == "python-dev"
    assert create_lines[-1].ts == clock.iso(frozen_time)


async def test_repair_and_check_never_read_the_reflog_a_corrupt_reflog_does_not_break_them(
    svc, frozen_time
):
    await svc.create("task", "T")
    rpath = reflog_path(svc.paths.squad_dir)
    rpath.write_text("this is not json at all\n", encoding="utf-8")
    result = await svc.repair()
    assert len(result.db.items) > 0
    assert await svc.check() == []  # a corrupt reflog raises no check issue either


async def test_a_squad_with_no_reflog_file_is_backward_compatible(svc, frozen_time):
    rpath = reflog_path(svc.paths.squad_dir)
    if rpath.exists():
        rpath.unlink()
    item = (await svc.create("task", "No reflog")).item
    assert (await svc.get(item.id)).title == "No reflog"
    assert rpath.exists()  # re-created by the mutation that just ran


async def test_a_failed_reflog_append_does_not_roll_back_the_committed_mutation(
    svc, frozen_time, monkeypatch
):
    """The append runs strictly after the index commit, so an append that raises must still
    leave the mutation durable — applied-without-logged is the tolerated failure mode."""

    def _boom(*args, **kwargs):
        raise OSError("simulated reflog write failure")

    monkeypatch.setattr(_reflog, "append_line", _boom)
    item = (await svc.create("task", "Must exist")).item
    assert (await svc.get(item.id)).title == "Must exist"
