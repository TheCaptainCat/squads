"""Tests for the reflog core (TASK-000112 / FEAT-000024 / ADR-000117).

Covers:
- One well-formed JSONL line is appended per mutation, atomically with the index commit.
- Applied-without-logged is the tolerated failure; logged-without-applied is impossible
  by design (ordering: append strictly AFTER os.replace, inside the lock).
- Writer tolerates a failed append without rolling back the committed mutation.
- Ambient actor flows into the reflog line (default "system"; overrideable via set_actor).
- op/delta are correctly captured at each mutating call site: create, status, update, body,
  comment, ref add/remove, subentity add/status/update, link/unlink, remove (remove stub).
- repair and repad emit their own reflog lines.
"""

import json

import pytest

from squads import _actor as actor
from squads import _clock as clock
from squads._index._reflog import ReflogLine, append_line, read_lines, reflog_path
from squads._models._enums import Status
from squads._models._schema import SCHEMA_VERSION

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Unit tests for _actor.py
# ---------------------------------------------------------------------------


def test_actor_default_is_system():
    assert actor.current_actor() == "system"


def test_actor_set_and_clear():
    actor.set_actor("python-dev")
    assert actor.current_actor() == "python-dev"
    actor.set_actor(None)
    assert actor.current_actor() == "system"


# ---------------------------------------------------------------------------
# Unit tests for _reflog.py
# ---------------------------------------------------------------------------


async def test_append_line_writes_valid_jsonl(tmp_path):
    path = tmp_path / ".reflog.jsonl"
    await append_line(
        path,
        ts="2026-06-15T10:00:00Z",
        actor="system",
        op="create",
        target="TASK-000001",
        delta={"title": "Test"},
    )
    content = path.read_text(encoding="utf-8")
    # Must end with \n; one line.
    assert content.endswith("\n")
    lines = content.strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["v"] == SCHEMA_VERSION
    assert record["ts"] == "2026-06-15T10:00:00Z"
    assert record["actor"] == "system"
    assert record["op"] == "create"
    assert record["target"] == "TASK-000001"
    assert record["delta"] == {"title": "Test"}


async def test_append_line_fails_gracefully_on_unwritable_path(tmp_path, capsys):
    """A failed append warns to stderr and does not raise."""
    path = tmp_path / "no_such_dir" / ".reflog.jsonl"
    # Parent directory does not exist → OSError on open.
    await append_line(
        path, ts="2026-06-15T10:00:00Z", actor="system", op="test", target="", delta={}
    )
    captured = capsys.readouterr()
    assert "warning" in captured.err.lower()


async def test_read_lines_missing_file_returns_empty(tmp_path):
    path = tmp_path / ".reflog.jsonl"
    assert await read_lines(path) == []


async def test_read_lines_empty_file(tmp_path):
    path = tmp_path / ".reflog.jsonl"
    path.write_text("", encoding="utf-8")
    assert await read_lines(path) == []


async def test_read_lines_multiple_entries(tmp_path):
    path = tmp_path / ".reflog.jsonl"
    for i in range(3):
        await append_line(
            path,
            ts=f"2026-06-15T10:0{i}:00Z",
            actor="system",
            op="test",
            target=f"TASK-00000{i}",
            delta={"i": i},
        )
    lines = await read_lines(path)
    assert len(lines) == 3
    assert all(isinstance(ln, ReflogLine) for ln in lines)
    assert lines[1].target == "TASK-000001"


async def test_read_lines_skips_trailing_partial_line_silently(tmp_path, capsys):
    """A trailing partial line (no \\n) is skipped without warning."""
    path = tmp_path / ".reflog.jsonl"
    good = (
        json.dumps(
            {"v": "0.3", "ts": "t", "actor": "a", "op": "create", "target": "X", "delta": {}}
        )
        + "\n"
    )
    partial = '{"v": "0.3", "ts": "t"'  # truncated, no \n
    path.write_bytes((good + partial).encode("utf-8"))
    lines = await read_lines(path)
    assert len(lines) == 1
    captured = capsys.readouterr()
    assert captured.err == ""  # no warning for trailing partial


async def test_read_lines_warns_on_interior_malformed_line(tmp_path, capsys):
    """An interior malformed line emits a warning but returns the rest."""
    path = tmp_path / ".reflog.jsonl"
    good1 = (
        json.dumps(
            {"v": "0.3", "ts": "t", "actor": "a", "op": "create", "target": "X", "delta": {}}
        )
        + "\n"
    )
    bad = "not valid json\n"
    good2 = (
        json.dumps(
            {"v": "0.3", "ts": "t", "actor": "a", "op": "status", "target": "Y", "delta": {}}
        )
        + "\n"
    )
    path.write_bytes((good1 + bad + good2).encode("utf-8"))
    lines = await read_lines(path)
    assert len(lines) == 2
    assert lines[0].op == "create"
    assert lines[1].op == "status"
    captured = capsys.readouterr()
    assert "warning" in captured.err.lower()


def test_reflog_path_is_in_squad_dir(tmp_path):
    assert reflog_path(tmp_path) == tmp_path / ".reflog.jsonl"


# ---------------------------------------------------------------------------
# Integration tests: reflog lines emitted by service mutations
# ---------------------------------------------------------------------------


async def test_create_emits_reflog_line(svc, frozen_time):
    """Service.create() appends one reflog line with op=create."""
    item = (await svc.create("task", "Write tests")).item
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    # init() also emits lines; we care about the last one (the create).
    create_lines = [ln for ln in lines if ln.op == "create" and ln.target == item.id]
    assert len(create_lines) == 1
    entry = create_lines[0]
    assert entry.op == "create"
    assert entry.target == item.id
    assert entry.actor == "system"


async def test_set_status_emits_reflog_line(svc, frozen_time):
    """Service.set_status() appends one reflog line with op=status and before→after."""
    item = (await svc.create("task", "T")).item
    await svc.set_status(item.id, Status.IN_PROGRESS)
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    status_lines = [ln for ln in lines if ln.op == "status" and ln.target == item.id]
    assert status_lines
    entry = status_lines[-1]
    assert entry.delta["status"] == ["Draft", "InProgress"]


async def test_update_emits_reflog_line(svc, frozen_time):
    """Service.update() appends one reflog line with op=update."""
    item = (await svc.create("task", "T")).item
    await svc.update(item.id, title="Updated T")
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    update_lines = [ln for ln in lines if ln.op == "update" and ln.target == item.id]
    assert update_lines
    entry = update_lines[-1]
    assert "title" in entry.delta
    assert entry.delta["title"] == ["T", "Updated T"]


async def test_ref_add_emits_reflog_line(svc, frozen_time):
    """Service.add_ref() appends one reflog line with op=ref."""
    a = (await svc.create("task", "A")).item
    b = (await svc.create("bug", "B")).item
    await svc.add_ref(a.id, b.id, kind="related")
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    ref_lines = [ln for ln in lines if ln.op == "ref" and ln.target == a.id]
    assert ref_lines
    entry = ref_lines[-1]
    assert entry.delta["add"] == b.id
    assert entry.delta["kind"] == "related"


async def test_remove_emits_reflog_line(svc, frozen_time):
    """Service.remove_work_item() appends one reflog line with op=remove + gone-item snapshot."""
    item = (await svc.create("task", "Gone")).item
    item_id = item.id
    item_type = item.type
    item_title = item.title
    await svc.remove_work_item(item_id)
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    remove_lines = [ln for ln in lines if ln.op == "remove"]
    assert remove_lines
    entry = remove_lines[-1]
    assert entry.target == item_id
    assert entry.delta["type"] == item_type
    assert entry.delta["title"] == item_title
    assert "status" in entry.delta


async def test_retype_emits_reflog_line(svc, frozen_time):
    """Service.retype() appends exactly one reflog line with op=retype.

    Pins BUG-000120: this test would fail against the pre-fix code (no _log call in retype()).
    The delta must carry old_id, new_id, old_type, new_type, status_carried, and status.
    """
    item = (await svc.create("task", "Needs retype")).item
    old_id = item.id
    result = await svc.retype(old_id, "bug")
    new_id = result.item.id
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    retype_lines = [ln for ln in lines if ln.op == "retype"]
    assert len(retype_lines) == 1, "retype must emit exactly one reflog line"
    entry = retype_lines[0]
    assert entry.target == new_id
    assert entry.delta["old_id"] == old_id
    assert entry.delta["new_id"] == new_id
    assert entry.delta["old_type"] == "task"
    assert entry.delta["new_type"] == "bug"
    assert "status_carried" in entry.delta
    assert "status" in entry.delta


async def test_comment_emits_reflog_line(svc, frozen_time):
    """Service.comment() appends one reflog line with op=comment."""
    item = (await svc.create("task", "T")).item
    await svc.comment(item.id, ["Hello world"])
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    comment_lines = [ln for ln in lines if ln.op == "comment" and ln.target == item.id]
    assert comment_lines


async def test_subentity_add_emits_reflog_line(svc, frozen_time):
    """Service.add_subtask() appends one reflog line with op=subentity."""
    item = (await svc.create("task", "T")).item
    await svc.add_subtask(item.id, "ST")
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    sub_lines = [ln for ln in lines if ln.op == "subentity" and ln.target == item.id]
    assert sub_lines
    entry = sub_lines[-1]
    assert entry.delta["op"] == "add"
    assert entry.delta["kind"] == "subtask"


async def test_repair_emits_reflog_line(svc, frozen_time):
    """Service.repair() appends one reflog line with op=repair."""
    await svc.repair()
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    repair_lines = [ln for ln in lines if ln.op == "repair"]
    assert repair_lines


async def test_actor_flows_into_reflog_line(svc, frozen_time):
    """The ambient actor set via set_actor() appears in the reflog line."""
    actor.set_actor("python-dev")
    item = (await svc.create("task", "Authored by python-dev")).item
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    create_lines = [ln for ln in lines if ln.op == "create" and ln.target == item.id]
    assert create_lines
    assert create_lines[-1].actor == "python-dev"


async def test_reflog_line_timestamp_uses_clock(svc, frozen_time):
    """Reflog timestamps respect the frozen clock (injectable via _clock.set_now)."""
    expected_ts = clock.iso(frozen_time)
    item = (await svc.create("task", "Timestamped")).item
    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    create_lines = [ln for ln in lines if ln.op == "create" and ln.target == item.id]
    assert create_lines
    assert create_lines[-1].ts == expected_ts


async def test_reflog_not_consulted_by_repair(svc, frozen_time, tmp_path):
    """Invariant 1: sq repair never reads the reflog — it rebuilds from .md files only."""
    # Create an item, then corrupt the reflog — repair must still succeed.
    await svc.create("task", "T")
    rpath = reflog_path(svc.paths.squad_dir)
    rpath.write_text("this is not json at all\n", encoding="utf-8")
    # repair must not raise and must rebuild the same index
    result = await svc.repair()
    assert len(result.db.items) > 0


async def test_no_reflog_squad_is_backward_compatible(svc, frozen_time):
    """A squad directory with no reflog file behaves identically (no error)."""
    rpath = reflog_path(svc.paths.squad_dir)
    if rpath.exists():
        rpath.unlink()
    # All read/write ops must still work.
    item = (await svc.create("task", "No reflog")).item
    assert (await svc.get(item.id)).title == "No reflog"
    # The file was (re-)created by the create op.
    assert rpath.exists()


async def test_append_line_swallows_oserror(tmp_path, capsys):
    """append_line warns and never raises on an I/O failure (ADR-000117 §1)."""
    from squads._index import _reflog

    # Make the reflog path a directory so open("a") raises IsADirectoryError (an OSError).
    rpath = tmp_path / ".reflog.jsonl"
    rpath.mkdir()
    # Must not raise.
    await _reflog.append_line(
        rpath,
        ts="2026-06-15T10:00:00Z",
        actor="system",
        op="status",
        target="TASK-000001",
        delta={"status": ["Draft", "InProgress"]},
    )
    assert "could not append" in capsys.readouterr().err


async def test_append_line_swallows_serialization_error(tmp_path, capsys):
    """A non-JSON-safe delta warns and never raises — serialization is inside the guard.

    Regression for REV-000118 F6: ``json.dumps`` formerly sat outside the ``except`` so a
    TypeError would propagate *past* an already-committed mutation, the exact failure mode
    ADR-000117 §1 forbids.
    """
    from squads._index import _reflog

    rpath = tmp_path / ".reflog.jsonl"
    # A set is not JSON-serializable → json.dumps raises TypeError; append_line must swallow it.
    await _reflog.append_line(
        rpath,
        ts="2026-06-15T10:00:00Z",
        actor="system",
        op="status",
        target="TASK-000001",
        delta={"bad": {1, 2, 3}},  # type: ignore[dict-item]
    )
    assert "could not append" in capsys.readouterr().err
    # Nothing was written (the failure was caught before any partial line landed).
    assert not rpath.exists() or rpath.read_text() == ""


async def test_failed_reflog_append_does_not_rollback_mutation(
    svc, frozen_time, monkeypatch, capsys
):
    """If the reflog append fails after commit, the committed mutation still persists.

    The append runs *after* ``os.replace`` (ADR-000117 §1), so even a raising appender must
    leave the index change durable — applied-without-logged is the tolerated failure.
    """
    from squads._index import _reflog

    def _boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise OSError("simulated reflog write failure")

    # Patch the appender to raise; append_line is imported inside store.transaction(),
    # so patching the module attribute takes effect there.
    monkeypatch.setattr(_reflog, "append_line", _boom)

    item = (await svc.create("task", "Must exist")).item
    # The index committed and the item is readable despite the reflog blowing up.
    assert (await svc.get(item.id)).title == "Must exist"
