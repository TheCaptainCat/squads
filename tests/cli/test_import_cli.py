"""``sq import`` CLI surface: a clean file applies and reports counts, ``--dry-run`` writes
nothing and prints the projected plan, a file with seeded problems exits non-zero (nothing
written, every problem line-numbered), stdin (``-``) works, ``--json`` shape is asserted, and
the global ``--at``/local ``--as`` defaults reach the engine.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_clean_file_applies_and_reports_counts(project, invoke, tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        '{"op":"create","type":"feature","title":"Imported feature","handle":"f1"}\n'
        '{"op":"status","target":"f1","status":"InProgress"}\n',
        encoding="utf-8",
    )
    result = await invoke(["import", str(events)])
    assert result.exit_code == 0, result.output
    assert "create: 1" in result.output
    assert "status: 1" in result.output
    assert "imported" in result.output

    listed = await invoke(["list", "--type", "feature", "--json"])
    items = json.loads(listed.output)
    assert len(items) == 1
    assert items[0]["title"] == "Imported feature"
    assert items[0]["status"] == "InProgress"


async def test_dry_run_writes_nothing_and_prints_the_plan(project, invoke, tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text('{"op":"create","type":"feature","title":"Not written","handle":"f1"}\n')
    result = await invoke(["import", "--dry-run", str(events)])
    assert result.exit_code == 0, result.output
    assert "f1" in result.output
    assert "dry run" in result.output

    listed = await invoke(["list", "--type", "feature", "--json"])
    assert json.loads(listed.output) == []


async def test_a_bad_file_exits_nonzero_writes_nothing_and_lists_every_line_numbered_issue(
    project, invoke, tmp_path
):
    events = tmp_path / "bad.jsonl"
    events.write_text(
        '{"op":"create","type":"not-a-real-type","title":"x"}\n'
        "not json at all\n"
        '{"op":"status","target":"does-not-exist","status":"InProgress"}\n',
        encoding="utf-8",
    )
    result = await invoke(["import", str(events)])
    assert result.exit_code == 1
    assert "line 1:" in result.output
    assert "line 2:" in result.output
    assert "line 3:" in result.output
    assert "3 issue(s) found" in result.output

    listed = await invoke(["list", "--json"])
    # Nothing beyond the seeded roster item was written.
    assert all(i["type"] != "feature" for i in json.loads(listed.output))


async def test_stdin_dash_reads_the_event_stream(project, invoke):
    result = await invoke(
        ["import", "-"],
        input='{"op":"create","type":"task","title":"From stdin"}\n',
    )
    assert result.exit_code == 0, result.output
    listed = await invoke(["list", "--type", "task", "--json"])
    assert json.loads(listed.output)[0]["title"] == "From stdin"


async def test_json_shape_on_success(project, invoke, tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        '{"op":"create","type":"feature","title":"JSON shape","handle":"f1"}\n'
        '{"op":"add-story","target":"f1","title":"a story","handle":"s1"}\n',
        encoding="utf-8",
    )
    result = await invoke(["import", "--json", str(events)])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["applied"] is True
    assert payload["dry_run"] is False
    assert payload["op_counts"] == {"create": 1, "add-story": 1}
    assert set(payload["handle_to_id"]) == {"f1"}
    assert payload["handle_to_sub"]["s1"][0] == payload["handle_to_id"]["f1"]
    assert payload["created_ids"] == [payload["handle_to_id"]["f1"]]
    assert payload["issues"] == []
    assert isinstance(payload["warnings"], list)


async def test_json_shape_on_failure_no_ansi_and_exit_1(project, invoke, tmp_path):
    events = tmp_path / "bad.jsonl"
    events.write_text('{"op":"status","target":"NOPE","status":"weird"}\n', encoding="utf-8")
    result = await invoke(["import", "--json", str(events)])
    assert result.exit_code == 1
    payload = json.loads(result.output)  # raises if any ANSI/non-JSON leaked in
    assert payload["ok"] is False
    assert payload["applied"] is False
    assert len(payload["issues"]) == 1
    assert payload["issues"][0]["line"] == 1


async def test_global_at_and_local_as_flow_through_to_the_created_item(project, invoke, tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text('{"op":"create","type":"task","title":"Backdated"}\n', encoding="utf-8")
    result = await invoke(
        ["--at", "2020-01-01T00:00:00Z", "import", str(events), "--as", "manager"]
    )
    assert result.exit_code == 0, result.output
    listed = await invoke(["list", "--type", "task", "--json"])
    item = json.loads(listed.output)[0]
    assert item["created_at"] == "2020-01-01T00:00:00Z"
    assert item["author"] == "manager"


async def test_an_event_at_overrides_the_file_level_default(project, invoke, tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(
        '{"op":"create","type":"task","title":"Own timestamp","at":"2021-06-01T00:00:00Z",'
        '"as":"manager"}\n',
        encoding="utf-8",
    )
    result = await invoke(["--at", "2020-01-01T00:00:00Z", "import", str(events)])
    assert result.exit_code == 0, result.output
    listed = await invoke(["list", "--type", "task", "--json"])
    assert json.loads(listed.output)[0]["created_at"] == "2021-06-01T00:00:00Z"


async def test_unreadable_file_is_a_clean_error_not_a_traceback(project, invoke, tmp_path):
    missing = tmp_path / "does-not-exist.jsonl"
    result = await invoke(["import", str(missing)])
    assert result.exit_code == 1
    assert "cannot read import file" in result.output
