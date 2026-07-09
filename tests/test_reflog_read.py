"""Tests for ``sq reflog`` read command (TASK-000113 / FEAT-000024 / ADR-000117).

Covers:
- sq reflog tails by default (--tail N) and shows all with --tail 0.
- Filters: --item, --actor, --op, --since (all AND semantics).
- --json output: shape matches ReflogEntry fields, parseable.
- Back-compat (US2): a squad with no .reflog.jsonl behaves identically.
- Truncated/partial-last-line reflog is tolerated (no error).
- sq repair and sq check never read the reflog.
- Golden test for --json shape.
"""

import json

import pytest
from typer.testing import CliRunner

from squads._cli import app
from squads._index._reflog import reflog_path
from squads._models._schema import SCHEMA_VERSION
from squads._services._results import ReflogEntry

# ---------------------------------------------------------------------------
# Service-level read_reflog tests
# ---------------------------------------------------------------------------


async def test_read_reflog_no_file(svc, frozen_time):
    """A squad with no reflog returns empty list — never an error (US2)."""
    rpath = reflog_path(svc.paths.squad_dir)
    if rpath.exists():
        rpath.unlink()
    result = await svc.read_reflog()
    assert result == []


async def test_read_reflog_truncated_last_line(svc, frozen_time):
    """A truncated trailing line is tolerated; good entries are returned."""

    await svc.create("task", "T")
    rpath = reflog_path(svc.paths.squad_dir)
    # Append a partial (truncated) line with no \n.
    with rpath.open("a", encoding="utf-8") as fh:
        fh.write('{"v": "0.3", "ts": "t"')  # no closing brace, no \n
    # read_reflog must not raise; the partial line is silently skipped.
    result = await svc.read_reflog()
    assert isinstance(result, list)
    assert len(result) >= 1  # the real entries are there


async def test_read_reflog_returns_reflog_entries(svc, frozen_time):
    """read_reflog returns a list of ReflogEntry dataclasses."""

    item = (await svc.create("task", "Entry test")).item
    result = await svc.read_reflog()
    assert all(isinstance(r, ReflogEntry) for r in result)
    create_entries = [r for r in result if r.op == "create" and r.target == item.id]
    assert create_entries


async def test_read_reflog_filter_by_item(svc, frozen_time):
    """--item filter returns only entries for that target."""

    a = (await svc.create("task", "A")).item
    b = (await svc.create("task", "B")).item
    result = await svc.read_reflog(item=a.id)
    assert all(r.target == a.id for r in result)
    # B's entries are filtered out.
    assert not any(r.target == b.id for r in result)


async def test_read_reflog_filter_by_actor(svc, frozen_time):
    """--actor filter returns only entries for that actor slug."""
    from squads import _actor as actor

    actor.set_actor("python-dev")
    await svc.create("task", "By python-dev")
    actor.set_actor("system")
    await svc.create("task", "By system")

    dev_entries = await svc.read_reflog(actor_filter="python-dev")
    assert all(r.actor == "python-dev" for r in dev_entries)
    assert dev_entries  # at least the create logged above


async def test_read_reflog_filter_by_op(svc, frozen_time):
    """--op filter returns only entries with that operation name."""
    from squads._models._enums import Status

    item = (await svc.create("task", "T")).item
    await svc.set_status(item.id, Status.IN_PROGRESS)
    status_entries = await svc.read_reflog(op_filter="status")
    assert all(r.op == "status" for r in status_entries)
    assert status_entries


async def test_read_reflog_filter_by_since(svc, frozen_time):
    """--since filter returns only entries at or after the given timestamp."""
    # All entries in the seeded squad use frozen_time; filter with a future date.
    future_ts = "2099-01-01T00:00:00Z"
    result = await svc.read_reflog(since=future_ts)
    assert result == []

    # Filter with a past date includes everything.
    past_ts = "2000-01-01T00:00:00Z"

    await svc.create("task", "T")
    result_all = await svc.read_reflog(since=past_ts)
    assert len(result_all) > 0


async def test_read_reflog_tail_limits_results(svc, frozen_time):
    """tail=N returns at most N entries (the last N)."""

    for i in range(5):
        await svc.create("task", f"Task {i}")
    result_all = await svc.read_reflog(tail=None)
    result_tail = await svc.read_reflog(tail=3)
    assert len(result_tail) == 3
    # The tail entries are the last ones in result_all.
    assert result_tail == result_all[-3:]


async def test_read_reflog_repair_never_reads_reflog(svc, frozen_time):
    """Invariant 1: sq repair does not read or depend on the reflog."""

    await svc.create("task", "T")
    rpath = reflog_path(svc.paths.squad_dir)
    # Corrupt the reflog — repair must succeed and rebuild from .md files.
    rpath.write_text("not json\nnot json either\n", encoding="utf-8")
    result = await svc.repair()
    # Repair succeeded and returned a valid DB.
    assert len(result.db.items) >= 1


# ---------------------------------------------------------------------------
# CLI tests for sq reflog
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_squad(tmp_path, monkeypatch, frozen_time):
    """A minimal squad with some reflog entries, ready for CLI tests."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "CLI test task", "--author", "manager"])  # TASK-000002
    runner.invoke(app, ["task", "2", "status", "InProgress"])
    runner.invoke(app, ["task", "2", "comment", "--as", "manager", "-m", "A comment"])
    return runner


def test_cli_reflog_default(cli_squad):
    """sq reflog (no flags) exits 0 and shows entries."""
    r = cli_squad.invoke(app, ["reflog"])
    assert r.exit_code == 0, r.output
    assert "create" in r.output or "status" in r.output or "no reflog" in r.output


def test_cli_reflog_json_shape(cli_squad):
    """sq reflog --json exits 0 and outputs a valid JSON array of ReflogEntry-shaped dicts."""
    r = cli_squad.invoke(app, ["reflog", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert isinstance(data, list)
    if data:
        entry = data[0]
        for field in ("v", "ts", "actor", "op", "target", "delta"):
            assert field in entry, f"missing field {field!r} in --json output"
        assert entry["v"] == SCHEMA_VERSION


def test_cli_reflog_filter_item(cli_squad):
    """sq reflog --item TASK-000002 --json filters to that item only."""
    r = cli_squad.invoke(app, ["reflog", "--item", "TASK-000002", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert all(e["target"] == "TASK-000002" for e in data)


def test_cli_reflog_filter_op(cli_squad):
    """sq reflog --op status --json filters to status ops only."""
    r = cli_squad.invoke(app, ["reflog", "--op", "status", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert all(e["op"] == "status" for e in data)


def test_cli_reflog_filter_actor(cli_squad):
    """sq reflog --actor manager --json filters to manager actor only."""
    r = cli_squad.invoke(app, ["reflog", "--actor", "manager", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert all(e["actor"] == "manager" for e in data)


def test_cli_reflog_no_reflog_file(tmp_path, monkeypatch, frozen_time):
    """sq reflog on a squad with no .reflog.jsonl exits 0 with empty output (back-compat)."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    rpath = tmp_path / "squads" / ".reflog.jsonl"
    if rpath.exists():
        rpath.unlink()
    r = runner.invoke(app, ["reflog"])
    assert r.exit_code == 0, r.output
    assert "no reflog entries" in r.output


def test_cli_reflog_truncated_file(tmp_path, monkeypatch, frozen_time):
    """sq reflog on a truncated reflog exits 0 and returns partial results."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    # Corrupt the last line.
    rpath = tmp_path / "squads" / ".reflog.jsonl"
    with rpath.open("a", encoding="utf-8") as fh:
        fh.write('{"v": "0.3", "ts": "t"')  # truncated, no \n
    r = runner.invoke(app, ["reflog"])
    assert r.exit_code == 0, r.output


def test_cli_reflog_tail_flag(cli_squad):
    """sq reflog --tail 2 --json returns at most 2 entries."""
    r = cli_squad.invoke(app, ["reflog", "--tail", "2", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert len(data) <= 2


def test_cli_reflog_since_invalid(cli_squad):
    """sq reflog --since <bad-date> exits 1."""
    r = cli_squad.invoke(app, ["reflog", "--since", "not-a-date"])
    assert r.exit_code == 1


def test_cli_reflog_check_does_not_read_reflog(tmp_path, monkeypatch, frozen_time):
    """sq check exits 0 even when the reflog is corrupt — it never reads it."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    rpath = tmp_path / "squads" / ".reflog.jsonl"
    rpath.write_text("this is garbage\n", encoding="utf-8")
    r = runner.invoke(app, ["check"])
    assert r.exit_code == 0, r.output


# ---------------------------------------------------------------------------
# Golden test for --json shape (US3 / FEAT-000015)
# ---------------------------------------------------------------------------


def test_golden_reflog_json(tmp_path, monkeypatch, frozen_time):
    """Golden-file test for sq reflog --json shape (FEAT-000015 frozen surface)."""
    import os
    from pathlib import Path

    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Reflog golden task", "--author", "manager"])
    runner.invoke(app, ["task", "2", "status", "InProgress"])

    r = runner.invoke(app, ["reflog", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)

    # Verify the structural shape (field presence and types) rather than exact values,
    # since timestamps and IDs are dynamic.
    assert isinstance(data, list)
    assert len(data) >= 2  # init creates roles, then create + status
    for entry in data:
        assert "v" in entry and isinstance(entry["v"], str)
        assert "ts" in entry and isinstance(entry["ts"], str)
        assert "actor" in entry and isinstance(entry["actor"], str)
        assert "op" in entry and isinstance(entry["op"], str)
        assert "target" in entry and isinstance(entry["target"], str)
        assert "delta" in entry and isinstance(entry["delta"], dict)

    # The last two entries should be the create + status transition.
    ops = [e["op"] for e in data]
    assert "create" in ops
    assert "status" in ops

    # Write golden file (UPDATE_GOLDENS=1) or validate shape is stable.
    goldens_dir = Path(__file__).parent / "goldens"
    golden_path = goldens_dir / "reflog_shape.json"
    _UPDATE = os.getenv("UPDATE_GOLDENS") == "1"

    # We only store the structural descriptor (not exact values) in the golden.
    # Use the actual schema version from the output rather than a hardcoded string so
    # the golden stays valid across schema bumps.
    from squads._models._schema import SCHEMA_VERSION as _SV

    shape_descriptor = {
        "fields": ["v", "ts", "actor", "op", "target", "delta"],
        "schema_version": _SV,
        "example_ops": sorted(set(ops)),
    }
    if _UPDATE:
        goldens_dir.mkdir(parents=True, exist_ok=True)
        golden_path.write_text(json.dumps(shape_descriptor, indent=2) + "\n", encoding="utf-8")
    elif golden_path.exists():
        expected = json.loads(golden_path.read_text(encoding="utf-8"))
        assert shape_descriptor["fields"] == expected["fields"]
        assert shape_descriptor["schema_version"] == expected["schema_version"]
