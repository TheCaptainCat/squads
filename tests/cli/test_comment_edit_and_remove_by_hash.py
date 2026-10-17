"""``comment <hash> edit`` and ``remove`` through the CLI: output, input shapes, the prompt,
refusals and the files they leave untouched."""

import hashlib
import json

import pytest

pytestmark = pytest.mark.anyio

ITEM = ["task", "2"]
SUB = ["task", "2", "subtask", "1"]


@pytest.fixture
async def board(project, svc, invoke):
    assert (await invoke(["create", "task", "T", "--author", "manager"])).exit_code == 0
    await svc.add_operator("Pierre Chat")
    for argv in (
        ["task", "2", "add-subtask", "Child"],
        [*ITEM, "comment", "--as", "manager", "-m", "on the item"],
        [*SUB, "comment", "--as", "manager", "-m", "on the subtask"],
    ):
        r = await invoke(argv)
        assert r.exit_code == 0, r.output


def _tree(project) -> str:
    h = hashlib.sha256()
    for p in sorted(project.squad_dir.rglob("*")):
        if p.is_file() and p.name.startswith(("TASK-", ".reflog")):
            h.update(p.read_bytes())
    return h.hexdigest()


async def _hash(invoke, level) -> str:
    return json.loads((await invoke([*level, "show", "--json"])).output)["discussion"][0]["hash"]


@pytest.mark.parametrize("level", [ITEM, SUB], ids=["item", "subentity"])
async def test_edit_prints_the_old_and_the_new_hash_and_the_new_one_resolves(
    board, invoke, level
) -> None:
    old = await _hash(invoke, level)

    r = await invoke([*level, "comment", old[:7], "edit", "--as", "manager", "-m", "reworded"])

    assert r.exit_code == 0, r.output
    assert r.output.startswith(f"edited {old[:7]} on TASK-2")
    new = r.output.rsplit("now ", 1)[1].strip()
    shown = json.loads((await invoke([*level, "comment", new, "show", "--json"])).output)
    assert shown["hash"].startswith(new)
    assert shown["body"] == "- reworded"
    assert (await invoke([*level, "comment", old[:7], "show"])).exit_code == 1


async def test_edit_json_is_the_new_entry(board, invoke) -> None:
    old = await _hash(invoke, ITEM)

    r = await invoke([*ITEM, "comment", old[:7], "edit", "--as", "manager", "-m", "x", "--json"])

    entry = json.loads(r.output)
    assert list(entry) == [
        "author", "author_slug", "ts", "edited_ts", "hash", "short_hash", "body"
    ]  # fmt: skip
    assert entry["hash"] != old
    assert entry["edited_ts"] is not None


async def test_edit_reads_one_bullet_from_a_file_and_stdin(board, invoke, tmp_path) -> None:
    old = await _hash(invoke, ITEM)
    note = tmp_path / "n.md"
    note.write_text("from a file\nsecond line", encoding="utf-8")

    r = await invoke([*ITEM, "comment", old[:7], "edit", "--as", "manager", "--file", str(note)])
    assert r.exit_code == 0, r.output
    new = r.output.rsplit("now ", 1)[1].strip()
    r = await invoke(
        [*ITEM, "comment", new, "edit", "--as", "manager", "--file", "-"], input="piped"
    )

    assert r.exit_code == 0, r.output
    assert "- piped" in (await invoke([*ITEM, "comments"])).output


@pytest.mark.parametrize(
    ("extra", "message"),
    [
        pytest.param([], "provide the comment via -m", id="neither"),
        pytest.param(["-m", "a", "--file", "x"], "not both", id="both"),
    ],
)
async def test_edit_input_follows_the_comment_contract(
    board, project, invoke, extra, message
) -> None:
    old = await _hash(invoke, ITEM)
    before = _tree(project)

    r = await invoke([*ITEM, "comment", old[:7], "edit", "--as", "manager", *extra])

    assert r.exit_code == 1
    assert message in " ".join(r.output.split())
    assert _tree(project) == before


async def test_an_edit_to_the_same_text_says_so_and_writes_nothing(board, project, invoke) -> None:
    old = await _hash(invoke, ITEM)
    before = _tree(project)

    r = await invoke([*ITEM, "comment", old[:7], "edit", "--as", "manager", "-m", "on the item"])

    assert r.exit_code == 0, r.output
    assert "unchanged; nothing written" in r.output
    assert _tree(project) == before


@pytest.mark.parametrize("verb", ["edit", "remove"])
async def test_another_authors_comment_is_refused_and_nothing_changes(
    board, project, invoke, verb
) -> None:
    old = await _hash(invoke, ITEM)
    before = _tree(project)
    extra = ["-m", "x"] if verb == "edit" else ["--yes"]

    r = await invoke([*ITEM, "comment", old[:7], verb, "--as", "op-pierre", *extra])

    assert r.exit_code == 1
    assert "written by manager; --as op-pierre cannot change it" in " ".join(r.output.split())
    assert _tree(project) == before


@pytest.mark.parametrize("verb", ["edit", "remove"])
async def test_a_retired_author_is_refused_until_reactivated(board, project, invoke, verb) -> None:
    await invoke(["role", "activate", "qa"])
    await invoke([*ITEM, "comment", "--as", "qa", "-m", "from qa"])
    qa = json.loads((await invoke([*ITEM, "comments", "--json"])).output)[-1]["hash"]
    await invoke(["role", "qa", "status", "Archived"])
    before = _tree(project)
    extra = ["-m", "x"] if verb == "edit" else ["--yes"]

    r = await invoke([*ITEM, "comment", qa[:7], verb, "--as", "qa", *extra])

    assert r.exit_code == 1
    assert "is retired" in r.output
    assert _tree(project) == before


async def test_remove_asks_first_and_declining_writes_nothing(board, project, invoke) -> None:
    old = await _hash(invoke, ITEM)
    before = _tree(project)

    r = await invoke([*ITEM, "comment", old[:7], "remove", "--as", "manager"], input="n\n")

    assert r.exit_code != 0
    assert "manager: - on the item" in r.output
    assert "Remove this comment?" in r.output
    assert _tree(project) == before


async def test_remove_with_yes_deletes_and_a_second_remove_finds_nothing(board, invoke) -> None:
    old = await _hash(invoke, SUB)

    r = await invoke([*SUB, "comment", old[:7], "remove", "--as", "manager", "--yes"])
    again = await invoke([*SUB, "comment", old[:7], "remove", "--as", "manager", "--yes"])

    assert r.exit_code == 0, r.output
    assert r.output.strip() == f"removed {old[:7]} from TASK-2 ST1"
    assert again.exit_code == 1
    assert "edited or removed since it was read" in " ".join(again.output.split())
    assert json.loads((await invoke([*SUB, "show", "--json"])).output)["discussion"] == []


async def test_remove_json_lists_the_removed_entries(board, invoke) -> None:
    old = await _hash(invoke, ITEM)

    r = await invoke([*ITEM, "comment", old[:7], "remove", "--as", "manager", "--yes", "--json"])

    (entry,) = json.loads(r.output)
    assert entry["hash"] == old
    assert entry["body"] == "- on the item"


async def test_the_files_stay_valid_for_check_after_an_edit_and_a_removal(board, invoke) -> None:
    old = await _hash(invoke, ITEM)
    r = await invoke([*ITEM, "comment", old[:7], "edit", "--as", "manager", "-m", "again"])
    new = r.output.rsplit("now ", 1)[1].strip()
    await invoke(
        [*SUB, "comment", (await _hash(invoke, SUB))[:7], "remove", "--as", "manager", "--yes"]
    )

    check = await invoke(["check"])
    repaired = await invoke(["repair"])

    assert "comment" not in check.output.lower().replace("comments", "")
    assert repaired.exit_code == 0, repaired.output
    assert (await invoke([*ITEM, "comment", new, "show"])).exit_code == 0
