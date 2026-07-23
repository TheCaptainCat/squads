"""``sq <type> <n> comments`` — the dedicated read-back verb for an item's top-level discussion,
generic over every work-item type. ``show --comments`` renders the same discussion inline; this
is the focused, machine-readable entry point.
"""

import json

import pytest

pytestmark = pytest.mark.anyio


async def test_plain_output_lists_comments_and_empty_discussion_prints_a_clean_line(
    project, invoke
) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])

    empty = await invoke(["feature", "2", "comments"])
    assert empty.exit_code == 0, empty.output
    assert "no comments" in empty.output

    await invoke(["feature", "2", "comment", "--as", "manager", "-m", "hello there"])
    r = await invoke(["feature", "2", "comments"])
    assert r.exit_code == 0, r.output
    assert "hello there" in r.output
    assert "Catherine Manager" in r.output


async def test_json_output_field_names_match_show_jsons_discussion_entries(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "comment", "--as", "manager", "-m", "please review"])

    comments = json.loads((await invoke(["task", "2", "comments", "--json"])).output)
    assert len(comments) == 1
    assert set(comments[0]) == {"author", "ts", "body"}

    shown = json.loads((await invoke(["task", "2", "show", "--json"])).output)
    assert comments == shown["discussion"]


async def test_json_output_is_an_empty_list_when_there_are_no_comments(project, invoke) -> None:
    await invoke(["create", "bug", "B", "--author", "manager"])
    r = await invoke(["bug", "2", "comments", "--json"])
    assert r.exit_code == 0, r.output
    assert json.loads(r.output) == []
