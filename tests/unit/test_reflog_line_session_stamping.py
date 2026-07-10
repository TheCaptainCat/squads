"""Reflog line-stamping with session fields — a sibling of the append_line/read_lines
primitive test (tests/unit/test_reflog_line_persistence.py), which does not exercise
session_id at all: ``append_line`` includes ``session_id``/``parent_session_id`` when set
and omits BOTH keys entirely (no null-valued keys) when ``None``; ``read_lines`` parses the
session fields back; a legacy slug-only line (pre-lineage) parses with session=``None``; and
a file mixing legacy and new-format lines parses correctly line by line.
"""

import json

import pytest

from squads._index._reflog import ReflogLine, append_line, read_lines

pytestmark = pytest.mark.anyio


async def test_append_line_includes_session_fields_when_set(tmp_path) -> None:
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
    record = json.loads(path.read_text(encoding="utf-8").strip())
    assert record["session_id"] == "sid-abc"
    assert record["parent_session_id"] == "sid-parent"
    assert record["actor"] == "python-dev"  # actor stays a flat string, unaffected


async def test_append_line_omits_both_session_keys_entirely_when_none(tmp_path) -> None:
    path = tmp_path / ".reflog.jsonl"
    await append_line(
        path, ts="2026-06-22T10:00:00Z", actor="system", op="create", target="TASK-000001", delta={}
    )
    record = json.loads(path.read_text(encoding="utf-8").strip())
    assert "session_id" not in record
    assert "parent_session_id" not in record


async def test_read_lines_parses_the_session_fields_back(tmp_path) -> None:
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
    (line,) = await read_lines(path)
    assert isinstance(line, ReflogLine)
    assert line.session_id == "sid-001"
    assert line.parent_session_id == "sid-000"


async def test_a_legacy_slug_only_line_parses_with_both_session_fields_none(tmp_path) -> None:
    path = tmp_path / ".reflog.jsonl"
    legacy = {
        "v": "0.3",
        "ts": "2026-06-01T10:00:00Z",
        "actor": "manager",
        "op": "create",
        "target": "FEAT-000001",
        "delta": {"title": "Login"},
    }
    path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
    (line,) = await read_lines(path)
    assert line.actor == "manager"
    assert line.session_id is None
    assert line.parent_session_id is None


async def test_a_file_mixing_legacy_and_new_format_lines_parses_correctly_line_by_line(
    tmp_path,
) -> None:
    path = tmp_path / ".reflog.jsonl"
    legacy = json.dumps(
        {"v": "0.3", "ts": "t1", "actor": "system", "op": "create", "target": "X", "delta": {}}
    )
    modern = json.dumps(
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
    path.write_text(legacy + "\n" + modern + "\n", encoding="utf-8")
    lines = await read_lines(path)
    assert len(lines) == 2
    assert lines[0].session_id is None and lines[0].parent_session_id is None
    assert lines[1].session_id == "sid-new" and lines[1].parent_session_id == "sid-root"
