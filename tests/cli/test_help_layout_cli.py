"""Help screens keep to one layout at 80 columns: nothing cut by an ellipsis, example lines each
on a line of their own, and one placeholder for each thing a usage line asks the reader to type.
"""

import re

import pytest

from squads._index._reflog import REFLOG_OPS

pytestmark = pytest.mark.anyio


def _flat(text: str) -> str:
    return " ".join(text.replace("│", " ").split())


def _lines(text: str) -> set[str]:
    return {line.strip().strip("│").strip() for line in text.splitlines()}


async def _task_number(invoke) -> str:
    created = await invoke(["create", "task", "T", "--author", "manager"])
    match = re.search(r"TASK-0*(\d+)", created.output)
    assert match, created.output
    return match.group(1)


async def test_retype_names_the_type_list_instead_of_enumerating_it(project, invoke) -> None:
    num = await _task_number(invoke)
    result = await invoke(["task", num, "retype", "--help"])
    assert "…" not in result.output
    assert "sq workflow types" in _flat(result.output)
    assert "epic|feature|task" not in result.output


async def test_reflog_op_help_shows_every_operation(project, invoke) -> None:
    result = await invoke(["reflog", "--help"])
    assert "…" not in result.output
    flat = _flat(result.output)
    assert all(op in flat for op in REFLOG_OPS)


@pytest.mark.parametrize(
    ("group", "examples"),
    [
        ("role", ["sq role manager show", "sq role 1 regen", "sq role qa set-default"]),
        ("operator", ["sq operator op-alice show", "sq operator 2 remove --purge"]),
        ("skill", ["sq skill squads show", "sq skill 2 regen"]),
    ],
)
async def test_each_example_of_a_roster_group_sits_on_its_own_line(
    project, invoke, group: str, examples: list[str]
) -> None:
    result = await invoke([group, "--help"])
    assert result.exit_code == 0, result.output
    assert set(examples) <= _lines(result.output)


async def test_the_comment_group_examples_sit_on_their_own_lines(project, invoke) -> None:
    num = await _task_number(invoke)
    result = await invoke(["task", num, "comment", "--help"])
    lines = _lines(result.output)
    assert "comment -m TEXT [-m TEXT ...] --as SLUG" in lines
    assert "comment --file PATH --as SLUG" in lines
    assert "comment HASH show|edit|remove" in lines
    assert max(len(line) for line in result.output.splitlines()) <= 80


async def test_the_renumber_command_line_sits_on_its_own_line(project, invoke) -> None:
    result = await invoke(["renumber", "--help"])
    assert "git show <mainref>:squads/.squads.json | jq .counter" in _lines(result.output)


async def test_an_addressed_roster_verb_asks_for_the_address_once(project, invoke) -> None:
    result = await invoke(["role", "manager", "show", "--help"])
    assert "Usage: sq role <slug|id|n> show [OPTIONS]" in result.output


async def test_a_sub_entity_verb_names_the_item_and_the_sub_entity_apart(project, invoke) -> None:
    num = await _task_number(invoke)
    await invoke(["task", num, "add-subtask", "A"])
    result = await invoke(["task", num, "subtask", "1", "show", "--help"])
    assert result.exit_code == 0, result.output
    assert "Usage: sq task N subtask LOCAL-ID show [OPTIONS]" in result.output
