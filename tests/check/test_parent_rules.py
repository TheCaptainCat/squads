"""The parent rules of `sq check`: each reports the one parent edge that breaks it, a sibling at the
boundary stays unreported, and a selection can move a rule to the other level.

The error-level rules cannot be breached through the CLI, because the create and update gate
refuses the write: the item file is edited and the squad re-indexed instead.
"""

import pytest

from tests.check._arrange import activate, create, edit_item_file, issue, repair, update

pytestmark = pytest.mark.anyio

PARENT_HINT = (
    "a task's parent must be of type feature; link a bug or review with "
    "`sq task <n> ref add <id> --kind fixes|addresses`"
)


async def _tasks_under_a_feature(invoke) -> tuple[str, str, str, str]:
    """An epic, a feature under it and two tasks under the feature; returns their ids."""
    await activate(invoke, "tech-lead", "product-owner")
    epic = await create(invoke, "epic", "Roadmap", "product-owner")
    feature = await create(invoke, "feature", "Search", "product-owner", parent=epic)
    first = await create(invoke, "task", "Index", "tech-lead", parent=feature)
    second = await create(invoke, "task", "Query", "tech-lead", parent=feature)
    return epic, feature, first, second


async def _three_parentless(invoke, item_type: str, author: str) -> tuple[str, str, str]:
    await activate(invoke, author)
    return (
        await create(invoke, item_type, "Roadmap", author),
        await create(invoke, item_type, "Backlog", author),
        await create(invoke, item_type, "Ideas", author),
    )


def _wrong_parent(task: str, level: str) -> dict[str, str]:
    return issue("parent_in", level, task, f"{PARENT_HINT} (got epic)")


@pytest.mark.breaches("parent_in")
async def test_a_parent_of_a_type_the_child_does_not_accept_is_an_error(
    project, invoke, check_json
) -> None:
    epic, feature, task, _sibling = await _tasks_under_a_feature(invoke)
    assert await check_json() == ([], 0)

    # the gate refuses an error-level parent: edit the file and re-index
    edit_item_file(project, task, f"parent: {feature}", f"parent: {epic}")
    await repair(invoke)

    assert await check_json() == ([_wrong_parent(task, "error")], 3)


@pytest.mark.breaches("parent_in@warn")
async def test_parent_in_selected_at_warn_reports_a_warning_and_passes(
    project, invoke, check_json, select_validators
) -> None:
    epic, _feature, task, _sibling = await _tasks_under_a_feature(invoke)
    select_validators("parent_in@warn", on="task")
    assert await check_json() == ([], 0)

    await update(invoke, task, "--parent", epic)

    assert await check_json() == ([_wrong_parent(task, "warn")], 0)


def _with_a_parent(item: str, item_type: str, parent: str, level: str) -> dict[str, str]:
    return issue("no_parent", level, item, f"{item_type} takes no parent (got {parent})")


@pytest.mark.breaches("no_parent")
async def test_a_parent_on_a_type_that_takes_none_is_an_error(project, invoke, check_json) -> None:
    root, child, _loose = await _three_parentless(invoke, "epic", "product-owner")
    assert await check_json() == ([], 0)

    edit_item_file(
        project, child, "author: product-owner\n", f"author: product-owner\nparent: {root}\n"
    )
    await repair(invoke)

    assert await check_json() == ([_with_a_parent(child, "epic", root, "error")], 3)


@pytest.mark.breaches("no_parent@warn")
async def test_no_parent_selected_at_warn_reports_a_warning_and_passes(
    project, invoke, check_json, select_validators
) -> None:
    root, child, _loose = await _three_parentless(invoke, "epic", "product-owner")
    select_validators("no_parent@warn", on="epic")
    assert await check_json() == ([], 0)

    await update(invoke, child, "--parent", root)

    assert await check_json() == ([_with_a_parent(child, "epic", root, "warn")], 0)


def _missing_parent(task: str, level: str) -> dict[str, str]:
    return issue("parent_present", level, task, "task requires a parent of type feature")


@pytest.mark.breaches("parent_present")
async def test_a_parentless_item_of_a_type_that_requires_one_is_an_error(
    project, invoke, check_json, select_validators
) -> None:
    _epic, feature, task, _sibling = await _tasks_under_a_feature(invoke)
    select_validators("parent_present", on="task")
    assert await check_json() == ([], 0)

    edit_item_file(project, task, f"parent: {feature}\n", "")
    await repair(invoke)

    assert await check_json() == ([_missing_parent(task, "error")], 3)


@pytest.mark.breaches("parent_present@warn")
async def test_parent_present_selected_at_warn_reports_a_warning_and_passes(
    project, invoke, check_json, select_validators
) -> None:
    _epic, _feature, _task, _sibling = await _tasks_under_a_feature(invoke)
    select_validators("parent_present@warn", on="task")
    assert await check_json() == ([], 0)

    orphan = await create(invoke, "task", "Orphan", "tech-lead")

    assert await check_json() == ([_missing_parent(orphan, "warn")], 0)


@pytest.mark.breaches("parent_acyclic")
async def test_a_parent_chain_that_closes_on_itself_is_reported_for_each_member(
    project, invoke, check_json
) -> None:
    await activate(invoke, "qa")
    first = await create(invoke, "bug", "Crash", "qa")
    second = await create(invoke, "bug", "Hang", "qa", parent=first)
    slow = await create(invoke, "bug", "Slow", "qa")
    await create(invoke, "bug", "Lag", "qa", parent=slow)
    assert await check_json() == ([], 0)

    edit_item_file(project, first, "author: qa\n", f"author: qa\nparent: {second}\n")
    await repair(invoke)

    def cycle(item: str, other: str) -> dict[str, str]:
        number = other.split("-")[1]
        return issue(
            "parent_acyclic",
            "error",
            item,
            f"{item}'s parent chain forms a cycle: {item} -> {other} -> {item}; "
            f"break it with `sq bug {number} update --no-parent`",
        )

    assert await check_json() == ([cycle(first, second), cycle(second, first)], 3)
