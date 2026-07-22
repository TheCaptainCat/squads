"""``sq list --category``/``sq tree --category`` — the roster/work/records filter, and its
clean error on an unknown value.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_list_category_narrows_to_the_matching_types(project, invoke):
    await invoke(["create", "task", "T1", "--author", "manager"])
    await invoke(["create", "decision", "D1", "--author", "manager"])

    work = await invoke(["list", "--category", "work"])
    assert "TASK-2" in work.output and "ADR-3" not in work.output

    records = await invoke(["list", "--category", "records"])
    assert "ADR-3" in records.output and "TASK-2" not in records.output


async def test_tree_category_narrows_to_the_matching_types(project, invoke):
    await invoke(["create", "task", "T1", "--author", "manager"])
    await invoke(["create", "decision", "D1", "--author", "manager"])

    records = await invoke(["tree", "--category", "records"])
    assert "ADR-3" in records.output and "TASK-2" not in records.output


async def test_list_category_composes_with_other_filters(project, invoke):
    await invoke(["create", "task", "Hi", "--author", "manager", "--priority", "high"])
    await invoke(["create", "task", "Lo", "--author", "manager", "--priority", "low"])

    result = await invoke(["list", "--category", "work", "--priority", "high"])
    assert "TASK-2" in result.output and "TASK-3" not in result.output


async def test_list_unknown_category_errors_cleanly(project, invoke):
    result = await invoke(["list", "--category", "bogus"])
    assert result.exit_code == 1
    assert "category" in result.output.lower()


async def test_tree_unknown_category_errors_cleanly(project, invoke):
    result = await invoke(["tree", "--category", "bogus"])
    assert result.exit_code == 1
    assert "category" in result.output.lower()
