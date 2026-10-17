"""``comment`` appends with ``-m``/``--file`` and routes a leading hash to ``show``, ``edit`` and
``remove``: how each argument shape parses at the item and the sub-entity level."""

import hashlib

import pytest

pytestmark = pytest.mark.anyio

ITEM = ["task", "2"]
SUB = ["task", "2", "subtask", "1"]


@pytest.fixture
async def board(project, invoke):
    for argv in (
        ["create", "task", "T", "--author", "manager"],
        ["task", "2", "add-subtask", "Child"],
    ):
        r = await invoke(argv)
        assert r.exit_code == 0, r.output


def _file_hash(project) -> str:
    path = next(project.squad_dir.glob("tasks/TASK-*.md"))
    return hashlib.sha256(path.read_bytes()).hexdigest()


# (id, args after `comment`, stdin, exit code, text in the output, whether the file changes)
ROWS = [
    pytest.param(["-m", "a", "--as", "manager"], None, 0, "commented on", True, id="one-message"),
    pytest.param(
        ["-m", "a", "-m", "b", "--as", "manager"], None, 0, "commented on", True, id="two-messages"
    ),
    pytest.param(
        ["-m", "a1b2", "-m", "edit", "--as", "manager"],
        None,
        0,
        "commented on",
        True,
        id="hex-looking-and-verb-looking-messages",
    ),
    pytest.param(
        ["--file", "-", "--as", "manager"], "from stdin", 0, "commented on", True, id="stdin"
    ),
    pytest.param(
        ["--as", "manager"], None, 1, "provide the comment via -m", False, id="no-message"
    ),
    pytest.param([], None, 1, "--as is required", False, id="no-arguments"),
    pytest.param(
        ["a1b2c3d"], None, 2, "missing verb after a1b2c3d: show|edit|remove", False, id="bare-hash"
    ),
    pytest.param(
        ["a1b2c3d", "frob"], None, 2, "missing verb after a1b2c3d", False, id="unknown-verb"
    ),
    pytest.param(["some text"], None, 2, "not a comment hash", False, id="bare-text"),
    pytest.param(["abc"], None, 2, "a new comment takes -m or --file", False, id="short-token"),
    pytest.param(["zzzzzz"], None, 2, "not a comment hash", False, id="non-hex-token"),
    pytest.param(
        ["-m", "x", "a1b2c3d", "edit", "--as", "manager"],
        None,
        2,
        "-m, --file and --as go after the verb",
        False,
        id="options-before-the-verb",
    ),
    pytest.param(
        ["--as", "manager", "a1b2c3d", "remove"],
        None,
        2,
        "go after the verb",
        False,
        id="as-before-the-verb",
    ),
]


@pytest.mark.parametrize("level", [ITEM, SUB], ids=["item", "subentity"])
@pytest.mark.parametrize(("args", "stdin", "code", "text", "changes"), ROWS)
async def test_each_argument_shape_parses_as_the_grammar_says(
    board, project, invoke, level, args, stdin, code, text, changes
) -> None:
    before = _file_hash(project)

    r = await invoke([*level, "comment", *args], input=stdin)

    assert r.exit_code == code, r.output
    assert text in " ".join(r.output.split()), r.output
    assert (_file_hash(project) != before) is changes


async def test_a_message_that_looks_like_a_hash_is_stored_as_text(board, invoke, project) -> None:
    r = await invoke([*ITEM, "comment", "--as", "manager", "-m", "deadbeef"])
    assert r.exit_code == 0, r.output

    shown = await invoke([*ITEM, "comments"])

    assert "deadbeef" in shown.output


async def test_a_hex_file_is_stored_as_one_comment(board, invoke, tmp_path) -> None:
    note = tmp_path / "note.txt"
    note.write_text("a1b2c3d4", encoding="utf-8")

    r = await invoke([*ITEM, "comment", "--as", "manager", "--file", str(note)])

    assert r.exit_code == 0, r.output
    assert "a1b2c3d4" in (await invoke([*ITEM, "comments"])).output


@pytest.mark.parametrize("level", [ITEM, SUB], ids=["item", "subentity"])
async def test_comment_help_describes_both_forms(board, invoke, level) -> None:
    r = await invoke([*level, "comment", "--help"])

    out = " ".join(r.output.split())
    assert r.exit_code == 0
    assert "comment -m TEXT" in out
    assert "comment HASH show|edit|remove" in out
    assert "_addr" not in out
