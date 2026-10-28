"""The work policy rules of `sq check`: the squad-wide members a squad selects and the per-item
members a type opts into. Each reports the one change that breaks it, a sibling at the boundary
stays unreported, and a selection can move a rule to the other level.

A state the create and update gate refuses is arranged by editing the item file and re-indexing the
squad; every other breach goes through the CLI.
"""

from datetime import timedelta

import pytest

from tests._squads import FROZEN
from tests.check._arrange import (
    activate,
    add_ref,
    address,
    at,
    create,
    edit_item_file,
    issue,
    ok,
    repair,
    set_status,
    update,
)

pytestmark = pytest.mark.anyio


async def _live_and_retired_authors(invoke) -> tuple[str, str]:
    """A task authored by the live tech-lead and a cancelled bug whose author role is retired;
    returns the task and the bug."""
    await activate(invoke, "tech-lead", "qa")
    task = await create(invoke, "task", "Index", "tech-lead")
    bug = await create(invoke, "bug", "Crash", "qa")
    await set_status(invoke, bug, "Cancelled")
    await ok(invoke, "role", "qa", "status", "Archived")
    return task, bug


def _no_live_author(level: str) -> dict[str, str]:
    return issue(
        "type_has_live_author",
        level,
        "",
        "type 'bug' has 1 open item but no live role authors it"
        " — reactivate `qa` (`sq role qa status Active`)",
    )


@pytest.mark.breaches("type_has_live_author")
async def test_an_open_item_of_a_type_no_live_role_authors_is_a_warning(invoke, check_json) -> None:
    _task, bug = await _live_and_retired_authors(invoke)
    assert await check_json() == ([], 0)

    await set_status(invoke, bug, "Open")

    assert await check_json() == ([_no_live_author("warn")], 0)


@pytest.mark.breaches("type_has_live_author@error")
async def test_type_has_live_author_selected_at_error_fails_the_check(
    invoke, check_json, select_validators
) -> None:
    _task, bug = await _live_and_retired_authors(invoke)
    select_validators("type_has_live_author@error")
    assert await check_json() == ([], 0)

    await set_status(invoke, bug, "Open")

    assert await check_json() == ([_no_live_author("error")], 3)


async def _features_with_one_open_task(invoke) -> tuple[str, str, str]:
    """A feature in progress with an open task, beside a done feature whose task is done; returns
    the first feature, its task and the done feature."""
    await activate(invoke, "product-owner", "tech-lead")
    feature = await create(invoke, "feature", "Search", "product-owner")
    task = await create(invoke, "task", "Index", "tech-lead", parent=feature)
    await set_status(invoke, feature, "InProgress")
    done = await create(invoke, "feature", "Export", "product-owner")
    done_task = await create(invoke, "task", "Write", "tech-lead", parent=done)
    await set_status(invoke, done_task, "InProgress", "Done")
    await set_status(invoke, done, "InProgress", "Done")
    return feature, task, done


def _open_child(parent: str, child: str, level: str) -> dict[str, str]:
    return issue(
        "children_settled_with_parent",
        level,
        parent,
        f"{parent} is Done with 1 open child: {child}",
    )


@pytest.mark.breaches("children_settled_with_parent")
async def test_a_settled_parent_with_an_open_child_is_a_warning(
    invoke, check_json, select_validators
) -> None:
    feature, task, _done = await _features_with_one_open_task(invoke)
    select_validators("children_settled_with_parent")
    assert await check_json() == ([], 0)

    await set_status(invoke, feature, "Done")

    assert await check_json() == ([_open_child(feature, task, "warn")], 0)


@pytest.mark.breaches("children_settled_with_parent@error")
async def test_children_settled_with_parent_selected_at_error_fails_the_check(
    invoke, check_json, select_validators
) -> None:
    feature, task, _done = await _features_with_one_open_task(invoke)
    select_validators("children_settled_with_parent@error")
    assert await check_json() == ([], 0)

    await set_status(invoke, feature, "Done")

    assert await check_json() == ([_open_child(feature, task, "error")], 3)


async def _chain_of_dependencies(invoke) -> tuple[str, str, str]:
    """Three tasks where the first depends on the second and the second on the third; returns
    them in that order."""
    await activate(invoke, "tech-lead")
    first, second, third = [await create(invoke, "task", n, "tech-lead") for n in "ABC"]
    await add_ref(invoke, first, second, "depends-on")
    await add_ref(invoke, second, third, "depends-on")
    return first, second, third


def _cycle(first: str, second: str, third: str, level: str) -> dict[str, str]:
    return issue(
        "dependency_acyclic",
        level,
        "",
        f"dependency cycle: {first} -> {second} -> {third} -> {first}",
    )


@pytest.mark.breaches("dependency_acyclic")
async def test_a_dependency_cycle_is_a_warning(invoke, check_json, select_validators) -> None:
    first, second, third = await _chain_of_dependencies(invoke)
    select_validators("dependency_acyclic")
    assert await check_json() == ([], 0)

    await add_ref(invoke, third, first, "depends-on")

    assert await check_json() == ([_cycle(first, second, third, "warn")], 0)


@pytest.mark.breaches("dependency_acyclic@error")
async def test_dependency_acyclic_selected_at_error_fails_the_check(
    invoke, check_json, select_validators
) -> None:
    first, second, third = await _chain_of_dependencies(invoke)
    select_validators("dependency_acyclic@error")
    assert await check_json() == ([], 0)

    await add_ref(invoke, third, first, "depends-on")

    assert await check_json() == ([_cycle(first, second, third, "error")], 3)


async def _two_assignees_at_the_wip_limit(invoke) -> tuple[str, str]:
    """The tech-lead and the qa each holding one active task; returns a second, unstarted task of
    the tech-lead and the tech-lead's active one."""
    await activate(invoke, "tech-lead", "qa")
    held = await create(invoke, "task", "Index", "tech-lead")
    other = await create(invoke, "task", "Crawl", "tech-lead")
    waiting = await create(invoke, "task", "Rank", "tech-lead")
    for task, who in ((held, "tech-lead"), (other, "qa")):
        await update(invoke, task, "--assignee", who)
        await set_status(invoke, task, "InProgress")
    await update(invoke, waiting, "--assignee", "tech-lead")
    return waiting, held


def _over_wip(waiting: str, held: str, level: str) -> dict[str, str]:
    return issue(
        "wip_limit", level, "", f"tech-lead holds 2 active items (limit 1): {held}, {waiting}"
    )


@pytest.mark.breaches("wip_limit", "wip_limit:param")
async def test_an_assignee_holding_more_active_items_than_the_limit_is_reported(
    invoke, check_json, select_validators
) -> None:
    waiting, held = await _two_assignees_at_the_wip_limit(invoke)
    select_validators("wip_limit:1")
    assert await check_json() == ([], 0)

    await set_status(invoke, waiting, "InProgress")

    assert await check_json() == ([_over_wip(waiting, held, "warn")], 0)


@pytest.mark.breaches("wip_limit@error")
async def test_wip_limit_selected_at_error_fails_the_check(
    invoke, check_json, select_validators
) -> None:
    waiting, held = await _two_assignees_at_the_wip_limit(invoke)
    select_validators("wip_limit:1@error")
    assert await check_json() == ([], 0)

    await set_status(invoke, waiting, "InProgress")

    assert await check_json() == ([_over_wip(waiting, held, "error")], 3)


async def _one_unassigned_active_task(invoke) -> tuple[str, str]:
    """An unassigned task in progress and an unassigned one not started; returns the started one
    and the other."""
    await activate(invoke, "tech-lead")
    started = await create(invoke, "task", "Index", "tech-lead")
    waiting = await create(invoke, "task", "Crawl", "tech-lead")
    await set_status(invoke, started, "InProgress")
    return started, waiting


def _unassigned(first: str, second: str, level: str) -> dict[str, str]:
    return issue(
        "unassigned_active",
        level,
        "",
        f"2 active items have no assignee (limit 1): {first}, {second}",
    )


@pytest.mark.breaches("unassigned_active", "unassigned_active:param")
async def test_more_unassigned_active_items_than_the_limit_is_reported(
    invoke, check_json, select_validators
) -> None:
    started, waiting = await _one_unassigned_active_task(invoke)
    select_validators("unassigned_active:1")
    assert await check_json() == ([], 0)

    await set_status(invoke, waiting, "InProgress")

    assert await check_json() == ([_unassigned(started, waiting, "warn")], 0)


@pytest.mark.breaches("unassigned_active@error")
async def test_unassigned_active_selected_at_error_fails_the_check(
    invoke, check_json, select_validators
) -> None:
    started, waiting = await _one_unassigned_active_task(invoke)
    select_validators("unassigned_active:1@error")
    assert await check_json() == ([], 0)

    await set_status(invoke, waiting, "InProgress")

    assert await check_json() == ([_unassigned(started, waiting, "error")], 3)


STALE_DAYS = 30


async def _two_tasks_idle_for_the_limit(invoke) -> tuple[str, str]:
    """Two tasks in progress, each last touched exactly the limit before the frozen clock;
    returns them."""
    await activate(invoke, "tech-lead")
    tasks = [await create(invoke, "task", n, "tech-lead") for n in ("Index", "Crawl")]
    for task in tasks:
        await at(
            invoke,
            FROZEN - timedelta(days=STALE_DAYS),
            *address(task),
            "update",
            "--status",
            "InProgress",
        )
    return tasks[0], tasks[1]


async def _touch_before_the_limit(invoke, task: str) -> None:
    """Touch *task* one day further back than the limit."""
    await at(
        invoke,
        FROZEN - timedelta(days=STALE_DAYS + 1),
        *address(task),
        "update",
        "--status",
        "InReview",
    )


def _stale(task: str, level: str) -> dict[str, str]:
    return issue(
        "stale_active",
        level,
        task,
        f"{task} is InReview and untouched since 2026-05-07T10:00:00Z (more than 30 days)",
    )


@pytest.mark.breaches("stale_active", "stale_active:param")
async def test_an_active_item_untouched_for_longer_than_the_limit_is_reported(
    invoke, check_json, select_validators
) -> None:
    stale, _at_the_limit = await _two_tasks_idle_for_the_limit(invoke)
    select_validators(f"stale_active:{STALE_DAYS}")
    assert await check_json() == ([], 0)

    await _touch_before_the_limit(invoke, stale)

    assert await check_json() == ([_stale(stale, "warn")], 0)


@pytest.mark.breaches("stale_active@error")
async def test_stale_active_selected_at_error_fails_the_check(
    invoke, check_json, select_validators
) -> None:
    stale, _at_the_limit = await _two_tasks_idle_for_the_limit(invoke)
    select_validators(f"stale_active:{STALE_DAYS}@error")
    assert await check_json() == ([], 0)

    await _touch_before_the_limit(invoke, stale)

    assert await check_json() == ([_stale(stale, "error")], 3)


async def _task_in_progress_and_one_ready(invoke) -> tuple[str, str]:
    """A task in progress with an assignee and an unassigned one not started; returns the second
    and the first."""
    await activate(invoke, "tech-lead")
    active = await create(invoke, "task", "Index", "tech-lead")
    await update(invoke, active, "--assignee", "tech-lead")
    await set_status(invoke, active, "InProgress")
    waiting = await create(invoke, "task", "Crawl", "tech-lead")
    await set_status(invoke, waiting, "Ready")
    return waiting, active


def _unassigned_item(task: str, level: str) -> dict[str, str]:
    return issue("assignee_present", level, task, "status is InProgress but nobody is assigned")


@pytest.mark.breaches("assignee_present")
async def test_an_active_item_nobody_is_assigned_is_a_warning(
    invoke, check_json, select_validators
) -> None:
    waiting, _active = await _task_in_progress_and_one_ready(invoke)
    select_validators("assignee_present", on="task")
    assert await check_json() == ([], 0)

    await set_status(invoke, waiting, "InProgress")

    assert await check_json() == ([_unassigned_item(waiting, "warn")], 0)


@pytest.mark.breaches("assignee_present@error")
async def test_assignee_present_selected_at_error_fails_the_check(
    project, invoke, check_json, select_validators
) -> None:
    waiting, _active = await _task_in_progress_and_one_ready(invoke)
    select_validators("assignee_present@error", on="task")
    assert await check_json() == ([], 0)

    # the gate refuses an error-level finding on update
    edit_item_file(project, waiting, "status: Ready", "status: InProgress")
    await repair(invoke)

    assert await check_json() == ([_unassigned_item(waiting, "error")], 3)


async def _blocked_task_with_a_blocker_and_a_ready_one(invoke) -> tuple[str, str]:
    """A task blocked behind a dependency and a ready one with no dependency; returns the ready
    one and the blocked one."""
    await activate(invoke, "tech-lead")
    blocked = await create(invoke, "task", "Index", "tech-lead")
    blocker = await create(invoke, "task", "Crawl", "tech-lead")
    await add_ref(invoke, blocked, blocker, "depends-on")
    await set_status(invoke, blocked, "Ready", "Blocked")
    waiting = await create(invoke, "task", "Rank", "tech-lead")
    await set_status(invoke, waiting, "Ready")
    return waiting, blocked


def _no_blocker(task: str, level: str) -> dict[str, str]:
    return issue(
        "blocked_has_blocker",
        level,
        task,
        "status is Blocked but no dependency edge is recorded (kinds: blocks, depends-on)"
        " — record a dependency edge (`--ref <id>:<kind>` on create, `ref add` after)",
    )


@pytest.mark.breaches("blocked_has_blocker")
async def test_a_blocked_item_with_no_dependency_edge_is_a_warning(
    invoke, check_json, select_validators
) -> None:
    waiting, _blocked = await _blocked_task_with_a_blocker_and_a_ready_one(invoke)
    select_validators("blocked_has_blocker", on="task")
    assert await check_json() == ([], 0)

    await set_status(invoke, waiting, "Blocked")

    assert await check_json() == ([_no_blocker(waiting, "warn")], 0)


@pytest.mark.breaches("blocked_has_blocker@error")
async def test_blocked_has_blocker_selected_at_error_fails_the_check(
    project, invoke, check_json, select_validators
) -> None:
    waiting, _blocked = await _blocked_task_with_a_blocker_and_a_ready_one(invoke)
    select_validators("blocked_has_blocker@error", on="task")
    assert await check_json() == ([], 0)

    # the gate refuses an error-level finding on update
    edit_item_file(project, waiting, "status: Ready", "status: Blocked")
    await repair(invoke)

    assert await check_json() == ([_no_blocker(waiting, "error")], 3)


async def _done_task_with_a_comment_and_one_in_progress(invoke) -> tuple[str, str]:
    """A done task whose discussion holds a comment and a task in progress with none; returns the
    task in progress and the done one."""
    await activate(invoke, "tech-lead")
    done = await create(invoke, "task", "Index", "tech-lead")
    await set_status(invoke, done, "InProgress")
    await ok(invoke, *address(done), "comment", "--as", "tech-lead", "-m", "Shipped")
    await set_status(invoke, done, "Done")
    working = await create(invoke, "task", "Crawl", "tech-lead")
    await set_status(invoke, working, "InProgress")
    return working, done


def _no_discussion(task: str, level: str) -> dict[str, str]:
    return issue(
        "settled_requires_discussion",
        level,
        task,
        "status is Done but its discussion holds no comment",
    )


@pytest.mark.breaches("settled_requires_discussion")
async def test_a_settled_item_with_no_comment_is_a_warning(
    invoke, check_json, select_validators
) -> None:
    working, _done = await _done_task_with_a_comment_and_one_in_progress(invoke)
    select_validators("settled_requires_discussion", on="task")
    assert await check_json() == ([], 0)

    await set_status(invoke, working, "Done")

    assert await check_json() == ([_no_discussion(working, "warn")], 0)


@pytest.mark.breaches("settled_requires_discussion@error")
async def test_settled_requires_discussion_selected_at_error_fails_the_check(
    invoke, check_json, select_validators
) -> None:
    working, _done = await _done_task_with_a_comment_and_one_in_progress(invoke)
    select_validators("settled_requires_discussion@error", on="task")
    assert await check_json() == ([], 0)

    await set_status(invoke, working, "Done")

    assert await check_json() == ([_no_discussion(working, "error")], 3)
