"""``sq <type> <n> update``: sets the author (validated against the roster) and the parent
(a valid id or cleared with ``--no-parent``) in the same call, and rejects the two
mutually-exclusive flag pairs (``--parent``/``--no-parent``, ``--priority``/``--no-priority``)
when both are given at once.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_update_sets_the_author_and_the_parent_then_clears_the_parent(
    project, invoke
) -> None:
    await invoke(["role", "activate", "reviewer"])  # ROLE-2
    await invoke(["create", "feature", "F", "--author", "manager"])  # FEAT-3
    await invoke(["create", "task", "T", "--author", "manager"])  # TASK-4

    bad_author = await invoke(["task", "4", "update", "--author", "ghost"])
    assert bad_author.exit_code == 1

    set_both = await invoke(["task", "4", "update", "--author", "reviewer", "--parent", "FEAT-3"])
    assert set_both.exit_code == 0, set_both.output
    shown = await invoke(["task", "4", "show", "--json"])
    import json

    data = json.loads(shown.output)
    assert data["author"] == "reviewer"
    assert data["parent"] == "FEAT-3"

    cleared = await invoke(["task", "4", "update", "--no-parent"])
    assert cleared.exit_code == 0, cleared.output
    data_after = json.loads((await invoke(["task", "4", "show", "--json"])).output)
    assert data_after["parent"] is None


async def test_update_rejects_parent_and_no_parent_together(project, invoke) -> None:
    await invoke(["create", "feature", "F", "--author", "manager"])  # FEAT-2
    await invoke(["create", "task", "T", "--author", "manager"])  # TASK-3

    clash = await invoke(["task", "3", "update", "--parent", "FEAT-2", "--no-parent"])
    assert clash.exit_code == 1
    assert "not both" in clash.output


async def test_update_rejects_priority_and_no_priority_together(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager", "--priority", "high"])

    clash = await invoke(["task", "2", "update", "--priority", "low", "--no-priority"])
    assert clash.exit_code == 1
    assert "not both" in clash.output


async def test_no_priority_clears_a_previously_set_priority(project, invoke) -> None:
    await invoke(["create", "task", "T", "--author", "manager", "--priority", "high"])

    r = await invoke(["task", "2", "update", "--no-priority"])
    assert r.exit_code == 0, r.output

    import json

    data = json.loads((await invoke(["task", "2", "show", "--json"])).output)
    assert data["priority"] is None


async def test_an_unknown_priority_code_is_rejected_and_lists_the_valid_ones(
    project, invoke
) -> None:
    r = await invoke(["create", "task", "T", "--author", "manager", "--priority", "stratospheric"])
    assert r.exit_code == 1
    assert "stratospheric" in r.output
    for code in ("urgent", "high", "medium", "low"):
        assert code in r.output
