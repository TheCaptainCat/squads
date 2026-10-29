"""A renumbered item's scaffolded `sq <type> <n> add-…` hint names its new number."""

import pytest

pytestmark = pytest.mark.anyio

TASK_FILE = "tasks/TASK-000003-build-the-query-parser.md"


async def test_repair_renumber_moves_the_hint_to_the_new_number(populated, invoke) -> None:
    squad = populated.squad_dir
    original = (squad / TASK_FILE).read_text(encoding="utf-8")
    twin = (
        original.replace("id: TASK-3", "id: TASK-2")
        .replace("sequence_id: 3", "sequence_id: 2")
        .replace("sq task 3 ", "sq task 2 ")
    )
    (squad / "tasks/TASK-000002-build-the-query-parser.md").write_text(twin, encoding="utf-8")
    result = await invoke(["repair", "--renumber"])
    assert (result.exit_code, result.output) == (
        0,
        "rebuilt index: 5 items, counter=5\n"
        "  renumbered TASK-2 -> TASK-5 (tasks/TASK-000005-build-the-query-parser.md)\n",
    )
    shown = await invoke(["task", "5", "show", "--json"])
    # The hint is in the file only: no command prints it.
    text = (squad / "tasks/TASK-000005-build-the-query-parser.md").read_text(encoding="utf-8")
    assert (
        '_Add with `sq task 5 add-subtask "<title>"`; track with '
        "`sq task 5 subtask <n> update --status <Status>`._"
    ) in text
    assert "sq task 2 " not in text
    assert shown.exit_code == 0


async def test_repair_renumber_moves_the_hint_of_a_same_id_twin(populated, invoke) -> None:
    squad = populated.squad_dir
    original = (squad / TASK_FILE).read_text(encoding="utf-8")
    twin = original.replace("title: Build the query parser", "title: Twin parser")
    (squad / "tasks/TASK-000003-twin.md").write_text(twin, encoding="utf-8")
    result = await invoke(["repair", "--renumber"])
    assert (result.exit_code, result.output) == (
        0,
        "rebuilt index: 5 items, counter=5\n"
        "  renumbered TASK-3 -> TASK-5 (tasks/TASK-000005-twin.md)\n",
    )
    # The hint is in the file only: no command prints it.
    text = (squad / "tasks/TASK-000005-twin.md").read_text(encoding="utf-8")
    assert (
        '_Add with `sq task 5 add-subtask "<title>"`; track with '
        "`sq task 5 subtask <n> update --status <Status>`._"
    ) in text
    assert "sq task 3 " not in text
