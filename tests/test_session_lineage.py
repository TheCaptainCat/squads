"""Tests for session lineage (TASK-000159 / ADR-000158).

Covers:
- _actor.py: seed_session() reads from env or explicit args; current_session() returns
  the pair; session fields are NOT settable by set_actor() / --as / --author.
- Reflog: when session env vars are present, the reflog line carries session_id /
  parent_session_id; when absent the entry is slug-only, exactly as before.
- Legacy slug-only reflog lines parse with both session fields as None (back-compat).
- Item frontmatter: created_session / modified_session populated when session is set;
  absent when not set; existing item files load without error.
- sq repair on legacy items (no session fields) succeeds — Invariant 1 holds.
- schema 0.3 → 0.4 migration: sq migrate up runs clean, stamps 0.4, sq check passes.
- CLI smoke: sq reflog --json shows session fields when env set; absent otherwise.
"""

import json

import pytest
from typer.testing import CliRunner

from squads import _actor as actor
from squads._cli import app
from squads._index._reflog import ReflogLine, append_line, read_lines, reflog_path
from squads._models._enums import ItemType, Status
from squads._models._schema import SCHEMA_VERSION

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Unit tests for _actor.py session pair
# ---------------------------------------------------------------------------


def test_seed_session_explicit_sets_pair():
    actor.seed_session("sess-abc", "parent-xyz")
    assert actor.current_session() == ("sess-abc", "parent-xyz")
    actor.seed_session(None, None)  # clear
    assert actor.current_session() == (None, None)


def test_seed_session_from_env(monkeypatch):
    monkeypatch.setenv("SQUADS_SESSION_ID", "env-sid")
    monkeypatch.setenv("SQUADS_PARENT_SESSION_ID", "env-psid")
    actor.seed_session(from_env=True)
    assert actor.current_session() == ("env-sid", "env-psid")
    # cleanup
    actor.seed_session(None, None)


def test_seed_session_from_env_absent(monkeypatch):
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    actor.seed_session(from_env=True)
    assert actor.current_session() == (None, None)


def test_seed_session_empty_string_treated_as_none(monkeypatch):
    """An empty-string env var is treated as None (env not meaningfully set)."""
    monkeypatch.setenv("SQUADS_SESSION_ID", "")
    monkeypatch.setenv("SQUADS_PARENT_SESSION_ID", "")
    actor.seed_session(from_env=True)
    assert actor.current_session() == (None, None)
    actor.seed_session(None, None)


def test_set_actor_does_not_change_session():
    """set_actor (the --as/--author path) must NOT touch session fields."""
    actor.seed_session("locked-sid", "locked-psid")
    actor.set_actor("python-dev")
    # actor slug changed, session must be unchanged
    assert actor.current_actor() == "python-dev"
    assert actor.current_session() == ("locked-sid", "locked-psid")
    # cleanup
    actor.set_actor(None)
    actor.seed_session(None, None)


def test_session_defaults_to_none():
    """After a fresh seed_session(None, None) call, current_session returns (None, None)."""
    actor.seed_session(None, None)
    assert actor.current_session() == (None, None)


# ---------------------------------------------------------------------------
# Unit tests for reflog append_line / read_lines with session fields
# ---------------------------------------------------------------------------


async def test_append_line_includes_session_fields_when_set(tmp_path):
    path = tmp_path / ".reflog.jsonl"
    await append_line(
        path,
        ts="2026-06-22T10:00:00Z",
        actor="python-dev",
        op="create",
        target="TASK-000001",
        delta={"title": "Test"},
        session_id="sid-abc",
        parent_session_id="sid-parent",
    )
    content = path.read_text(encoding="utf-8")
    record = json.loads(content.strip())
    assert record["actor"] == "python-dev"  # actor stays a flat string
    assert record["session_id"] == "sid-abc"
    assert record["parent_session_id"] == "sid-parent"
    # actor is still the top-level key (back-compat)
    assert "actor" in record


async def test_append_line_omits_session_fields_when_none(tmp_path):
    """When session_id and parent_session_id are None, neither key appears in the JSON."""
    path = tmp_path / ".reflog.jsonl"
    await append_line(
        path,
        ts="2026-06-22T10:00:00Z",
        actor="system",
        op="create",
        target="TASK-000001",
        delta={},
    )
    content = path.read_text(encoding="utf-8")
    record = json.loads(content.strip())
    assert "session_id" not in record
    assert "parent_session_id" not in record


async def test_read_lines_parses_session_fields(tmp_path):
    path = tmp_path / ".reflog.jsonl"
    await append_line(
        path,
        ts="2026-06-22T10:00:00Z",
        actor="python-dev",
        op="create",
        target="TASK-000001",
        delta={},
        session_id="sid-001",
        parent_session_id="sid-000",
    )
    lines = await read_lines(path)
    assert len(lines) == 1
    line = lines[0]
    assert isinstance(line, ReflogLine)
    assert line.actor == "python-dev"
    assert line.session_id == "sid-001"
    assert line.parent_session_id == "sid-000"


async def test_legacy_slug_only_lines_parse_with_none_session(tmp_path):
    """A reflog line written before schema 0.4 (no session fields) parses with both None."""
    path = tmp_path / ".reflog.jsonl"
    # Write a legacy-style line (no session_id / parent_session_id fields).
    legacy_line = (
        json.dumps(
            {
                "v": "0.3",
                "ts": "2026-06-01T10:00:00Z",
                "actor": "manager",
                "op": "create",
                "target": "FEAT-000001",
                "delta": {"title": "Login", "type": "feature", "status": "Draft"},
            }
        )
        + "\n"
    )
    path.write_text(legacy_line, encoding="utf-8")

    lines = await read_lines(path)
    assert len(lines) == 1
    line = lines[0]
    assert line.actor == "manager"
    assert line.session_id is None
    assert line.parent_session_id is None


async def test_mixed_legacy_and_new_lines_parse_correctly(tmp_path):
    """A file containing both old (no session) and new (with session) lines parses cleanly."""
    path = tmp_path / ".reflog.jsonl"
    legacy = (
        json.dumps(
            {
                "v": "0.3",
                "ts": "t1",
                "actor": "system",
                "op": "create",
                "target": "X",
                "delta": {},
            }
        )
        + "\n"
    )
    modern = (
        json.dumps(
            {
                "v": "0.4",
                "ts": "t2",
                "actor": "python-dev",
                "session_id": "sid-new",
                "parent_session_id": "sid-root",
                "op": "status",
                "target": "X",
                "delta": {},
            }
        )
        + "\n"
    )
    path.write_text(legacy + modern, encoding="utf-8")

    lines = await read_lines(path)
    assert len(lines) == 2
    assert lines[0].session_id is None
    assert lines[0].parent_session_id is None
    assert lines[1].session_id == "sid-new"
    assert lines[1].parent_session_id == "sid-root"


# ---------------------------------------------------------------------------
# Service-level tests: session flows into reflog + item frontmatter
# ---------------------------------------------------------------------------


async def test_service_create_records_session_on_reflog(svc, frozen_time):
    """When session env vars are set, the create reflog entry carries session_id."""
    actor.seed_session("sid-create", "sid-parent")
    item = (await svc.create(ItemType.TASK, "Session task")).item
    actor.seed_session(None, None)

    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    create_lines = [ln for ln in lines if ln.op == "create" and ln.target == item.id]
    assert create_lines
    entry = create_lines[-1]
    assert entry.session_id == "sid-create"
    assert entry.parent_session_id == "sid-parent"
    assert entry.actor == "system"  # actor slug unchanged


async def test_service_create_no_session_slug_only(svc, frozen_time):
    """When no session is set, the create reflog entry has no session fields."""
    actor.seed_session(None, None)
    item = (await svc.create(ItemType.TASK, "No-session task")).item

    lines = await read_lines(reflog_path(svc.paths.squad_dir))
    create_lines = [ln for ln in lines if ln.op == "create" and ln.target == item.id]
    assert create_lines
    entry = create_lines[-1]
    assert entry.session_id is None
    assert entry.parent_session_id is None


async def test_service_create_records_session_on_item_frontmatter(svc, frozen_time):
    """When session is set, the created item has created_session / modified_session."""
    actor.seed_session("sid-fm", "sid-pm")
    item = (await svc.create(ItemType.TASK, "Frontmatter session")).item
    actor.seed_session(None, None)

    loaded = await svc.get(item.id)
    assert loaded.created_session == "sid-fm"
    assert loaded.modified_session == "sid-fm"


async def test_service_create_no_session_frontmatter_absent(svc, frozen_time):
    """When no session, created_session and modified_session are None on the item."""
    actor.seed_session(None, None)
    item = (await svc.create(ItemType.TASK, "No-session frontmatter")).item

    loaded = await svc.get(item.id)
    assert loaded.created_session is None
    assert loaded.modified_session is None


async def test_service_set_status_updates_modified_session(svc, frozen_time):
    """Status mutation updates modified_session; created_session is unchanged."""
    actor.seed_session("sid-create", None)
    item = (await svc.create(ItemType.TASK, "Session update test")).item
    actor.seed_session("sid-modify", None)
    await svc.set_status(item.id, Status.IN_PROGRESS)
    actor.seed_session(None, None)

    loaded = await svc.get(item.id)
    assert loaded.created_session == "sid-create"
    assert loaded.modified_session == "sid-modify"


async def test_service_read_reflog_returns_session_fields(svc, frozen_time):
    """read_reflog() surfaces session_id / parent_session_id on ReflogEntry."""
    from squads._services._results import ReflogEntry

    actor.seed_session("sid-svc", "sid-par")
    item = (await svc.create(ItemType.TASK, "Reflog entry session")).item
    actor.seed_session(None, None)

    entries = await svc.read_reflog(item=item.id)
    assert entries
    create_entries = [e for e in entries if e.op == "create"]
    assert create_entries
    entry = create_entries[-1]
    assert isinstance(entry, ReflogEntry)
    assert entry.session_id == "sid-svc"
    assert entry.parent_session_id == "sid-par"
    assert entry.actor == "system"


async def test_legacy_items_load_without_session_fields(svc, frozen_time):
    """Items written without session fields (legacy) load cleanly with both None."""
    from squads import _sections as sections
    from squads._index._resolver import item_file

    item = (await svc.create(ItemType.TASK, "Legacy item")).item
    path = item_file(svc.paths, item)

    # Manually strip the session fields from the frontmatter to simulate a legacy file.
    from squads import _aio

    text = await _aio.read_text(path)
    fm, body = sections.split_frontmatter(text)
    fm.pop("created_session", None)
    fm.pop("modified_session", None)
    await _aio.write_text(path, sections.join_frontmatter(fm, body))

    # Repair and reload — should succeed without error.
    await svc.repair()
    loaded = await svc.get(item.id)
    assert loaded.created_session is None
    assert loaded.modified_session is None


async def test_repair_on_legacy_items_invariant_1(svc, frozen_time):
    """sq repair of items without session fields rebuilds index cleanly (Invariant 1)."""
    from squads import _aio
    from squads import _sections as sections
    from squads._index._resolver import item_file

    item = (await svc.create(ItemType.TASK, "Repair legacy")).item
    path = item_file(svc.paths, item)

    # Strip session fields.
    text = await _aio.read_text(path)
    fm, body = sections.split_frontmatter(text)
    fm.pop("created_session", None)
    fm.pop("modified_session", None)
    await _aio.write_text(path, sections.join_frontmatter(fm, body))

    result = await svc.repair()
    assert len(result.db.items) >= 1
    issues = await svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors


# ---------------------------------------------------------------------------
# Session fields are NOT settable via set_actor / --as / --author CLI flags
# ---------------------------------------------------------------------------


def test_session_not_settable_via_set_actor_only_explicit_seed():
    """Only seed_session() changes the session pair; set_actor changes only the slug."""
    actor.seed_session("fixed-sid", "fixed-psid")
    actor.set_actor("reviewer")
    # slug changed, session unchanged
    assert actor.current_actor() == "reviewer"
    assert actor.current_session() == ("fixed-sid", "fixed-psid")
    # cleanup
    actor.set_actor(None)
    actor.seed_session(None, None)


def test_session_not_set_by_cli_as_flag(tmp_path, monkeypatch):
    """sq <cmd> --as <slug> does not set or modify session fields."""
    monkeypatch.chdir(tmp_path)
    # Ensure no session env is set.
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)

    runner = CliRunner()
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Test", "--author", "manager"])
    result = runner.invoke(app, ["task", "2", "comment", "--as", "manager", "-m", "A note"])
    assert result.exit_code == 0

    # Read the reflog: the comment entry should have no session_id.
    import asyncio

    from squads._index._reflog import read_lines
    from squads._index._reflog import reflog_path as _reflog_path

    lines = asyncio.run(read_lines(_reflog_path(tmp_path / "squads")))
    comment_lines = [ln for ln in lines if ln.op == "comment"]
    assert comment_lines
    assert all(ln.session_id is None for ln in comment_lines)


# ---------------------------------------------------------------------------
# CLI smoke test: sq reflog --json shows session fields when env set, absent otherwise
# ---------------------------------------------------------------------------


def test_cli_reflog_json_has_session_fields_when_env_set(tmp_path, monkeypatch):
    """sq reflog --json entries include session_id / parent_session_id when env vars were set."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SQUADS_SESSION_ID", "cli-sid")
    monkeypatch.setenv("SQUADS_PARENT_SESSION_ID", "cli-psid")

    runner = CliRunner()
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "CLI session task", "--author", "manager"])

    r = runner.invoke(app, ["reflog", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert isinstance(data, list)
    # At least one entry should carry the session fields.
    entries_with_session = [e for e in data if e.get("session_id") == "cli-sid"]
    assert entries_with_session, f"No entries with session_id=cli-sid in: {data}"
    for e in entries_with_session:
        assert e.get("parent_session_id") == "cli-psid"


def test_cli_reflog_json_no_session_when_env_absent(tmp_path, monkeypatch):
    """sq reflog --json entries omit session fields when env vars were absent."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)

    runner = CliRunner()
    runner.invoke(app, ["init", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "No-session CLI task", "--author", "manager"])

    r = runner.invoke(app, ["reflog", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert isinstance(data, list)
    # No entry should have a session_id set.
    for entry in data:
        assert "session_id" not in entry or entry["session_id"] is None, (
            f"Unexpected session_id in entry: {entry}"
        )


# ---------------------------------------------------------------------------
# Migration: v0_3 corpus migrates to schema 0.4 cleanly
# ---------------------------------------------------------------------------


async def test_v0_3_to_v0_4_migration_is_noop_runner():
    """The 0.3→0.4 migration runner is a no-op that returns 0."""
    from squads._migrations._v0_3_to_v0_4 import migrate

    # Pass a non-existent path — the no-op runner never touches files.
    count = migrate(None)  # type: ignore[arg-type]
    assert count == 0


async def test_schema_version_is_0_4():
    """SCHEMA_VERSION is now 0.4 after the bump."""
    assert SCHEMA_VERSION == "0.4"


async def test_v0_3_migration_stamps_0_4(project, frozen_time):
    """run_pending_migrations() on a 0.3 squad stamps the schema to 0.4."""
    import tomllib

    from squads import _aio
    from squads._services._service import Service

    # The `project` fixture initialises a fresh squad at SCHEMA_VERSION (0.4); forcibly
    # downgrade the on-disk config to 0.3 to simulate a pre-migration squad.
    cfg_path = project.config_path
    cfg_text = await _aio.read_text(cfg_path)
    cfg_text_03 = cfg_text.replace('schema_version = "0.4"', 'schema_version = "0.3"')
    await _aio.write_text(cfg_path, cfg_text_03)

    # Re-load paths from disk so in-memory config reflects the downgrade.
    with cfg_path.open("rb") as fh:
        from squads._models._config import SquadsConfig

        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    from squads._paths import SquadPaths

    paths_03 = SquadPaths(root=project.root, squad_dir=project.squad_dir, config=cfg)
    svc_03 = Service(paths_03)

    applied = await svc_03.run_pending_migrations()
    assert len(applied) == 1, f"Expected 1 migration, got {len(applied)}: {applied}"
    assert applied[0].from_schema == "0.3"
    assert applied[0].to_schema == "0.4"

    # Verify on-disk stamp.
    with cfg_path.open("rb") as fh:
        stamped = tomllib.load(fh)
    assert stamped["schema_version"] == "0.4"

    issues = await svc_03.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors
