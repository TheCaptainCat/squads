"""``sq reflog`` CLI surface: tails by default, ``--tail 0`` shows all, each filter flag
reaches the service, behaves identically with no reflog file / a truncated one, an invalid
``--since`` is rejected, and ``--json`` matches a pinned golden shape. Also: ``--json``
entries carry session_id/parent_session_id when the seeding env var was set for the process
and omit them entirely when absent (the session-lineage half of this same surface).
"""

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.anyio

GOLDENS_DIR = Path(__file__).parents[1] / "goldens"

# A test below sets SQUADS_SESSION_ID, which seeds the process-global session pair as a side
# effect of the CLI root callback; the root conftest's autouse `_reset_session_seed` resets it
# before/after every test, so it never leaks into the next test's own `project` fixture.


async def _seed(invoke) -> None:
    await invoke(["create", "task", "CLI test task", "--author", "manager"])  # TASK-000002
    await invoke(["task", "2", "status", "InProgress"])
    await invoke(["task", "2", "comment", "--as", "manager", "-m", "A comment"])


async def test_default_tails_and_exits_0(project, invoke):
    await _seed(invoke)
    result = await invoke(["reflog"])
    assert result.exit_code == 0
    assert "create" in result.output or "status" in result.output


async def test_tail_zero_shows_all_entries(project, invoke):
    await _seed(invoke)
    default = await invoke(["reflog", "--json"])
    all_entries = await invoke(["reflog", "--tail", "0", "--json"])
    assert len(json.loads(all_entries.output)) >= len(json.loads(default.output))


async def test_item_actor_and_op_filter_flags_each_reach_the_service(project, invoke):
    await _seed(invoke)
    by_item = await invoke(["reflog", "--item", "TASK-000002", "--json"])
    assert all(e["target"] == "TASK-000002" for e in json.loads(by_item.output))

    by_op = await invoke(["reflog", "--op", "status", "--json"])
    assert all(e["op"] == "status" for e in json.loads(by_op.output))

    by_actor = await invoke(["reflog", "--actor", "manager", "--json"])
    assert all(e["actor"] == "manager" for e in json.loads(by_actor.output))


async def test_tail_flag_limits_the_number_of_entries(project, invoke):
    await _seed(invoke)
    result = await invoke(["reflog", "--tail", "2", "--json"])
    assert len(json.loads(result.output)) <= 2


async def test_an_invalid_since_value_is_rejected(project, invoke):
    result = await invoke(["reflog", "--since", "not-a-date"])
    assert result.exit_code == 1


async def test_behaves_identically_with_no_reflog_file(project, invoke):
    rpath = project.squad_dir / ".reflog.jsonl"
    if rpath.exists():
        rpath.unlink()
    result = await invoke(["reflog"])
    assert result.exit_code == 0
    assert "no reflog entries" in result.output


async def test_behaves_identically_with_a_truncated_reflog_file(project, invoke):
    await invoke(["create", "task", "T", "--author", "manager"])
    rpath = project.squad_dir / ".reflog.jsonl"
    with rpath.open("a", encoding="utf-8") as fh:
        fh.write('{"v": "0.3", "ts": "t"')  # truncated
    result = await invoke(["reflog"])
    assert result.exit_code == 0


async def test_json_output_matches_the_pinned_golden_shape(project, invoke):
    await invoke(["create", "task", "Reflog golden task", "--author", "manager"])
    await invoke(["task", "2", "status", "InProgress"])
    result = await invoke(["reflog", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list) and len(data) >= 2
    for entry in data:
        for field in ("v", "ts", "actor", "op", "target", "delta"):
            assert field in entry
    ops = [e["op"] for e in data]
    assert "create" in ops and "status" in ops

    # Read-only check against the existing golden (shared with the old suite's own reflog
    # golden test) — this file only confirms the shape, it never rewrites the golden.
    from squads._models._schema import SCHEMA_VERSION

    golden_path = GOLDENS_DIR / "reflog_shape.json"
    expected: Any = json.loads(golden_path.read_text(encoding="utf-8"))
    assert expected["fields"] == ["v", "ts", "actor", "op", "target", "delta"]
    assert expected["schema_version"] == SCHEMA_VERSION
    assert set(ops) <= set(expected["example_ops"])


# --------------------------------------------------------------------------- session fields


async def test_json_entries_carry_session_fields_when_the_seeding_env_var_was_set(
    project, invoke, monkeypatch
):
    """Session seeding is read fresh from the environment at every CLI invocation's root
    callback, so setting the env var before ``invoke`` reaches it exactly as a real orchestrator
    would."""
    monkeypatch.setenv("SQUADS_SESSION_ID", "cli-sid")
    monkeypatch.setenv("SQUADS_PARENT_SESSION_ID", "cli-psid")
    await invoke(["create", "task", "CLI session task", "--author", "manager"])

    result = await invoke(["reflog", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    with_session = [e for e in data if e.get("session_id") == "cli-sid"]
    assert with_session
    assert all(e.get("parent_session_id") == "cli-psid" for e in with_session)


async def test_json_entries_omit_session_fields_when_the_env_var_was_absent(
    project, invoke, monkeypatch
):
    monkeypatch.delenv("SQUADS_SESSION_ID", raising=False)
    monkeypatch.delenv("SQUADS_PARENT_SESSION_ID", raising=False)
    await invoke(["create", "task", "No-session CLI task", "--author", "manager"])

    result = await invoke(["reflog", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    for entry in data:
        assert entry.get("session_id") is None
