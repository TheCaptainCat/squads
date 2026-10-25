"""A write that needs a region the file lacks outright adds it empty and goes through, and
`sq check` reports nothing missing: a file written by hand, or one a region was deleted from,
stays usable."""

import json
import re

import pytest

pytestmark = pytest.mark.anyio


def _drop_pair(text: str, tag: str) -> str:
    pattern = rf"<!-- sq:{re.escape(tag)} -->.*?<!-- sq:{re.escape(tag)}:end -->\n?"
    return re.sub(pattern, "", text, flags=re.S)


def _without(tag: str):
    return lambda text: _drop_pair(text, tag)


_REGIONS = {
    "discussion": _without("discussion"),
    "block": _without("subtask:ST1"),
    "body": _without("subtask:ST1:body"),
    "block-discussion": _without("subtask:ST1:discussion"),
    "container": lambda text: _drop_pair(_drop_pair(text, "subtask:ST1"), "subtasks"),
    "intact": lambda text: text,
}

_WRITES = {
    "item-comment": ["task", "2", "comment", "--as", "manager", "-m", "hi"],
    "sub-comment": ["task", "2", "subtask", "1", "comment", "--as", "manager", "-m", "hi"],
    "sub-body": ["task", "2", "subtask", "1", "body", "-m", "text"],
    "sub-body-append": ["task", "2", "subtask", "1", "body", "--append", "-m", "text"],
    "sub-update": ["task", "2", "subtask", "1", "update", "--status", "InProgress"],
    "item-body": ["task", "2", "body", "-m", "text"],
}

#: The regions each write leaves in the file.
_NEEDED = {
    "item-comment": {"discussion"},
    "sub-comment": {"subtask:ST1", "subtask:ST1:discussion"},
    "sub-body": {"subtask:ST1", "subtask:ST1:body"},
    "sub-body-append": {"subtask:ST1", "subtask:ST1:body"},
}


async def _damaged(project, invoke, region):
    await invoke(["create", "task", "t", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "st"])
    (md,) = (project.squad_dir / "tasks").glob("TASK-*.md")
    md.write_text(_REGIONS[region](md.read_text()))
    return md


@pytest.mark.parametrize("write", list(_WRITES))
@pytest.mark.parametrize("region", [r for r in _REGIONS if r != "container"])
async def test_a_write_goes_through_whichever_region_is_absent(project, invoke, region, write):
    md = await _damaged(project, invoke, region)

    result = await invoke(_WRITES[write])

    assert result.exit_code == 0, result.output
    assert "Traceback" not in result.output
    text = md.read_text()
    for tag in _NEEDED.get(write, ()):
        assert f"<!-- sq:{tag} -->" in text
    check = await invoke(["check"])
    assert check.exit_code == 0, check.output
    assert "missing" not in check.output


@pytest.mark.parametrize("region", ["block", "body"])
async def test_a_restored_body_takes_the_text_written(project, invoke, region):
    await _damaged(project, invoke, region)

    await invoke(["task", "2", "subtask", "1", "body", "-m", "kept words"])

    shown = await invoke(["task", "2", "show", "--full"])
    assert "kept words" in shown.output


async def test_add_subtask_writes_a_missing_container(project, invoke):
    md = await _damaged(project, invoke, "container")

    result = await invoke(["task", "2", "add-subtask", "again"])

    assert result.exit_code == 0, result.output
    assert "<!-- sq:subtasks -->" in md.read_text()
    assert (await invoke(["check"])).exit_code == 0


async def test_add_subtask_on_a_file_with_no_container_or_block_is_clean(project, invoke):
    await invoke(["create", "task", "t", "--author", "manager"])
    (md,) = (project.squad_dir / "tasks").glob("TASK-*.md")
    md.write_text(_drop_pair(md.read_text(), "subtasks"))
    assert (await invoke(["check"])).exit_code == 0
    assert "container" not in (await invoke(["check"])).output

    assert (await invoke(["task", "2", "add-subtask", "x"])).exit_code == 0


@pytest.mark.parametrize("region", ["discussion", "block", "body", "block-discussion"])
async def test_import_ops_restore_the_region_they_need(project, invoke, tmp_path, region):
    md = await _damaged(project, invoke, region)
    events = tmp_path / "ev.jsonl"
    lines = [
        {"op": "comment", "target": "TASK-2", "message": "hi", "as": "manager"},
        {"op": "sub-body", "target": "TASK-2", "kind": "subtask", "local": "ST1", "body": "x"},
    ]
    events.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")

    result = await invoke(["import", str(events)])

    assert result.exit_code == 0, result.output
    assert "<!-- sq:discussion -->" in md.read_text()
    assert (await invoke(["check"])).exit_code == 0
