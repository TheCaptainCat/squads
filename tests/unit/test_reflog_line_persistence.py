"""The reflog append/read primitive itself (`_index/_reflog.py`), against a bare path with no
service involved: one well-formed JSONL line per append, a failed append warns to stderr rather
than raising (including when the failure is a serialization error, not just an OSError), and
reading tolerates a truncated trailing line silently while still warning on an interior one.
"""

import json

import pytest

from squads import _actor as actor
from squads._index._reflog import ReflogLine, append_line, read_lines, reflog_path
from squads._models._schema import SCHEMA_VERSION

pytestmark = pytest.mark.anyio


def test_actor_defaults_to_system_and_set_actor_overrides_until_cleared():
    assert actor.current_actor() == "system"
    actor.set_actor("python-dev")
    assert actor.current_actor() == "python-dev"
    actor.set_actor(None)
    assert actor.current_actor() == "system"


async def test_append_line_writes_one_well_formed_jsonl_record(tmp_path):
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
    assert content.endswith("\n")
    lines = content.strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record == {
        "v": SCHEMA_VERSION,
        "ts": "2026-06-15T10:00:00Z",
        "actor": "system",
        "op": "create",
        "target": "TASK-000001",
        "delta": {"title": "Test"},
    }


async def test_append_line_swallows_an_oserror_and_warns(tmp_path, capsys):
    rpath = tmp_path / ".reflog.jsonl"
    rpath.mkdir()  # open("a") on a directory raises IsADirectoryError, an OSError
    await append_line(
        rpath, ts="t", actor="system", op="status", target="TASK-000001", delta={"a": 1}
    )
    assert "could not append" in capsys.readouterr().err


async def test_append_line_swallows_a_serialization_error_and_writes_nothing(tmp_path, capsys):
    rpath = tmp_path / ".reflog.jsonl"
    # A set is not JSON-serializable — json.dumps must be inside the guard, not outside it.
    await append_line(
        rpath, ts="t", actor="system", op="status", target="TASK-000001", delta={"bad": {1, 2}}
    )
    assert "could not append" in capsys.readouterr().err
    assert not rpath.exists() or rpath.read_text() == ""


async def test_read_lines_missing_or_empty_file_returns_empty(tmp_path):
    path = tmp_path / ".reflog.jsonl"
    assert await read_lines(path) == []
    path.write_text("", encoding="utf-8")
    assert await read_lines(path) == []


async def test_read_lines_parses_every_well_formed_record(tmp_path):
    path = tmp_path / ".reflog.jsonl"
    for i in range(3):
        await append_line(
            path, ts=f"t{i}", actor="system", op="test", target=f"TASK-00000{i}", delta={"i": i}
        )
    lines = await read_lines(path)
    assert len(lines) == 3
    assert all(isinstance(ln, ReflogLine) for ln in lines)
    assert lines[1].target == "TASK-000001"


def _line(op: str, target: str) -> str:
    rec = {"v": "0.3", "ts": "t", "actor": "a", "op": op, "target": target, "delta": {}}
    return json.dumps(rec) + "\n"


async def test_read_lines_skips_a_truncated_trailing_line_without_warning(tmp_path, capsys):
    path = tmp_path / ".reflog.jsonl"
    partial = '{"v": "0.3", "ts": "t"'  # truncated, no trailing newline
    path.write_bytes((_line("create", "X") + partial).encode("utf-8"))
    lines = await read_lines(path)
    assert len(lines) == 1
    assert capsys.readouterr().err == ""


async def test_read_lines_warns_on_an_interior_malformed_line_but_returns_the_rest(
    tmp_path, capsys
):
    path = tmp_path / ".reflog.jsonl"
    bad = "not valid json\n"
    path.write_bytes((_line("create", "X") + bad + _line("status", "Y")).encode("utf-8"))
    lines = await read_lines(path)
    assert [ln.op for ln in lines] == ["create", "status"]
    assert "warning" in capsys.readouterr().err.lower()


def test_reflog_path_lives_directly_under_the_squad_dir(tmp_path):
    assert reflog_path(tmp_path) == tmp_path / ".reflog.jsonl"
