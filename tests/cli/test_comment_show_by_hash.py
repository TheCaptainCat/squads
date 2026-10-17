"""``comment <hash> show``: one comment with its context line, or one JSON record."""

import json

import pytest

pytestmark = pytest.mark.anyio

ITEM = ["task", "2"]
SUB = ["task", "2", "subtask", "1"]
COMMENT_KEYS = ["author", "author_slug", "ts", "edited_ts", "hash", "short_hash", "body"]


@pytest.fixture
async def board(project, invoke):
    for argv in (
        ["create", "task", "T", "--author", "manager"],
        ["task", "2", "add-subtask", "Child"],
        [*ITEM, "comment", "--as", "manager", "-m", "on the item"],
        [*SUB, "comment", "--as", "manager", "-m", "on the subtask"],
    ):
        r = await invoke(argv)
        assert r.exit_code == 0, r.output


async def _hash(invoke, level) -> str:
    argv = [*level, "show", "--json"]
    return json.loads((await invoke(argv)).output)["discussion"][0]["hash"]


@pytest.mark.parametrize(
    ("level", "scope", "context"),
    [
        pytest.param(ITEM, None, "TASK-2", id="item"),
        pytest.param(SUB, "subtask:ST1", "TASK-2 · subtask ST1", id="subentity"),
    ],
)
async def test_show_json_is_one_comment_entry_plus_item_scope_and_copies(
    board, invoke, level, scope, context
) -> None:
    full = await _hash(invoke, level)

    r = await invoke([*level, "comment", full[:7], "show", "--json"])

    record = json.loads(r.output)
    assert r.exit_code == 0, r.output
    assert list(record) == [*COMMENT_KEYS, "item", "scope", "copies"]
    assert (record["item"], record["scope"], record["copies"]) == ("TASK-2", scope, 1)
    assert record["hash"] == full
    assert record["short_hash"] == full[:7]
    assert record["edited_ts"] is None


@pytest.mark.parametrize("level", [ITEM, SUB], ids=["item", "subentity"])
@pytest.mark.parametrize("flags", [[], ["--raw"]], ids=["piped", "raw"])
async def test_show_renders_the_context_line_and_the_header(board, invoke, level, flags) -> None:
    full = await _hash(invoke, level)

    r = await invoke([*level, "comment", full[:7], "show", *flags])

    first, header, *rest = r.output.splitlines()
    assert r.exit_code == 0, r.output
    assert first == ("TASK-2" if level is ITEM else "TASK-2 · subtask ST1")
    assert header.startswith(f"--- {full[:7]} [")
    assert "Catherine Manager (manager)" in header
    assert "(edited" not in header
    assert any("on the" in line for line in rest)


async def test_an_edited_comment_shows_its_edit_mark(board, invoke) -> None:
    full = await _hash(invoke, ITEM)
    r = await invoke([*ITEM, "comment", full[:7], "edit", "--as", "manager", "-m", "changed"])
    assert r.exit_code == 0, r.output
    new = r.output.rsplit("now ", 1)[1].strip()

    shown = await invoke([*ITEM, "comment", new, "show"])
    as_json = json.loads((await invoke([*ITEM, "comment", new, "show", "--json"])).output)

    assert "(edited " in shown.output
    assert as_json["edited_ts"] is not None


@pytest.mark.parametrize("level", [ITEM, SUB], ids=["item", "subentity"])
async def test_show_json_stays_valid_when_color_is_forced(
    board, invoke, monkeypatch, level
) -> None:
    full = await _hash(invoke, level)
    monkeypatch.setenv("FORCE_COLOR", "3")

    r = await invoke([*level, "comment", full[:7], "show", "--json"])

    assert json.loads(r.output)["hash"] == full


async def test_a_hash_of_the_other_discussion_is_refused_naming_its_address(board, invoke) -> None:
    sub_hash = await _hash(invoke, SUB)

    r = await invoke([*ITEM, "comment", sub_hash[:7], "show"])

    out = " ".join(r.output.split())
    assert r.exit_code == 1
    assert f"it is in subtask ST1 (sq task 2 subtask 1 comment {sub_hash[:7]} ...)" in out


@pytest.mark.parametrize("token", ["deadbeef", "ffff"])
async def test_an_unknown_hash_is_refused(board, invoke, token) -> None:
    r = await invoke([*ITEM, "comment", token, "show"])

    assert r.exit_code == 1
    assert "edited or removed since it was read" in " ".join(r.output.split())
