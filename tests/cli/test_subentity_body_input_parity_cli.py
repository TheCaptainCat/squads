"""Regression lock-in: ``add-story``/``add-subtask``/``add-finding`` accept body input
identically via ``-m``, ``--file <path>``, and ``--file -`` (stdin) — all three built-in kinds
route through the same generic ``add-<kind>`` builder, so this asserts the parity holds and never
silently regresses for one kind while the others keep working.
"""

import json

import pytest

pytestmark = pytest.mark.anyio

# (parent item type, add-<kind> verb, list verb, kind name)
_KINDS = [
    ("feature", "add-story", "stories", "story"),
    ("task", "add-subtask", "subtasks", "subtask"),
    ("review", "add-finding", "findings", "finding"),
]


async def _make_parent(invoke, parent_type: str) -> str:
    r = await invoke(["create", parent_type, "Parent", "--author", "manager"])
    assert r.exit_code == 0, r.output
    # bare number: ROLE-1 (manager, from the minimal bundle) precedes every created work item.
    return "2"


@pytest.mark.parametrize(("parent_type", "add_verb", "list_verb", "kind"), _KINDS)
async def test_message_flag_sets_the_body_in_one_shot(
    project, invoke, parent_type, add_verb, list_verb, kind
) -> None:
    num = await _make_parent(invoke, parent_type)
    r = await invoke([parent_type, num, add_verb, "Title", "-m", "the body text"])
    assert r.exit_code == 0, r.output

    detail = await invoke([parent_type, num, kind, "1", "show"])
    assert "the body text" in detail.output


@pytest.mark.parametrize(("parent_type", "add_verb", "list_verb", "kind"), _KINDS)
async def test_file_flag_sets_the_body_from_a_file(
    project, invoke, tmp_path, parent_type, add_verb, list_verb, kind
) -> None:
    num = await _make_parent(invoke, parent_type)
    body_file = tmp_path / "body.md"
    body_file.write_text("body from a file\n", encoding="utf-8")
    r = await invoke([parent_type, num, add_verb, "Title", "--file", str(body_file)])
    assert r.exit_code == 0, r.output

    detail = await invoke([parent_type, num, kind, "1", "show"])
    assert "body from a file" in detail.output


@pytest.mark.parametrize(("parent_type", "add_verb", "list_verb", "kind"), _KINDS)
async def test_file_dash_sets_the_body_from_stdin(
    project, invoke, parent_type, add_verb, list_verb, kind
) -> None:
    num = await _make_parent(invoke, parent_type)
    r = await invoke(
        [parent_type, num, add_verb, "Title", "--file", "-"], input="body from stdin\n"
    )
    assert r.exit_code == 0, r.output

    detail = await invoke([parent_type, num, kind, "1", "show"])
    assert "body from stdin" in detail.output


@pytest.mark.parametrize(("parent_type", "add_verb", "list_verb", "kind"), _KINDS)
async def test_a_body_supplied_at_creation_leaves_sibling_blocks_and_markers_intact(
    project, invoke, parent_type, add_verb, list_verb, kind
) -> None:
    num = await _make_parent(invoke, parent_type)
    await invoke([parent_type, num, add_verb, "First", "-m", "first body"])
    await invoke([parent_type, num, add_verb, "Second", "-m", "second body"])

    listed = json.loads((await invoke([parent_type, num, list_verb, "--json"])).output)
    assert [b["title"] for b in listed] == ["First", "Second"]

    first = await invoke([parent_type, num, kind, "1", "show"])
    assert "first body" in first.output
    second = await invoke([parent_type, num, kind, "2", "show"])
    assert "second body" in second.output


@pytest.mark.parametrize(("parent_type", "add_verb", "list_verb", "kind"), _KINDS)
async def test_created_with_a_body_produces_no_unwritten_body_check_warning(
    project, invoke, parent_type, add_verb, list_verb, kind
) -> None:
    num = await _make_parent(invoke, parent_type)
    await invoke([parent_type, num, add_verb, "Title", "-m", "a real body"])

    issues = json.loads((await invoke(["check", "--json"])).output)
    assert not any("body is unwritten" in issue["message"] for issue in issues)


@pytest.mark.parametrize(("parent_type", "add_verb", "list_verb", "kind"), _KINDS)
async def test_created_with_no_body_produces_exactly_the_unwritten_body_warning(
    project, invoke, parent_type, add_verb, list_verb, kind
) -> None:
    num = await _make_parent(invoke, parent_type)
    await invoke([parent_type, num, add_verb, "Title"])

    issues = json.loads((await invoke(["check", "--json"])).output)
    unwritten = [i for i in issues if "body is unwritten" in i["message"]]
    assert len(unwritten) == 1
    assert unwritten[0]["level"] == "warn"
