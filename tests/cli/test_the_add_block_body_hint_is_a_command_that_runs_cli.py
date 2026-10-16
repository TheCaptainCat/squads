"""The body hint printed after `add-<kind>` is a command that exists and sets that block's body."""

import re

import pytest

pytestmark = pytest.mark.anyio

# (parent type, add verb, local id the verb allocates)
SHAPES = [
    ("feature", "add-story", "US1"),
    ("task", "add-subtask", "ST1"),
    ("review", "add-finding", "F1"),
]


@pytest.mark.parametrize(("parent_type", "verb", "local_id"), SHAPES)
async def test_hinted_body_command_runs(project, invoke, parent_type, verb, local_id):
    created = await invoke(["create", parent_type, "Parent", "--author", "manager"])
    assert created.exit_code == 0, created.output
    match = re.search(r"-0*(\d+)", created.output)
    assert match is not None, created.output
    number = match.group(1)

    added = await invoke([parent_type, number, verb, "A block"])
    assert added.exit_code == 0, added.output
    hint = re.search(r"set its body:\s+(sq .+?)\s+\(or", added.output.replace("\n", " "))
    assert hint is not None, added.output
    hinted = hint.group(1)
    assert hinted == f'sq {parent_type} {number} {verb[4:]} {local_id} body -m "…"'

    argv = [*hinted.split()[1:-2], "-m", "hinted body"]
    ran = await invoke(argv)
    assert ran.exit_code == 0, ran.output
