"""The `sq check` rules over sub-entities: the story a subtask maps to, a sub-entity's status,
container marker, body, title length and deferral, and a parent settled over unsettled ones.

A state the update gate or the vocabulary check refuses is arranged by editing the item file and
re-indexing the squad; every other breach goes through the CLI.
"""

from typing import NamedTuple

import pytest

from tests.check._arrange import (
    activate,
    address,
    create,
    edit_item_file,
    issue,
    ok,
    repair,
    update,
)

pytestmark = pytest.mark.anyio


class Squad(NamedTuple):
    """The ids the `squad` fixture created."""

    feature: str
    task: str


@pytest.fixture
async def squad(project, invoke) -> Squad:
    """Every author role live, a feature with one story and a task under it whose subtask maps to
    that story, with a written body."""
    await activate(invoke, "tech-lead", "product-owner", "reviewer")
    feature = await create(invoke, "feature", "Plan", "product-owner", desc="d")
    await ok(invoke, *address(feature), "add-story", "Index", "-m", "As a user")
    task = await create(invoke, "task", "Build", "tech-lead", parent=feature, desc="d")
    await ok(invoke, *address(task), "add-subtask", "Parse", "-m", "Do it", "--story", "US1")
    return Squad(feature, task)


async def _review(invoke, title: str) -> str:
    """Create a review with one written finding that is still open."""
    review = await create(invoke, "review", title, "reviewer", desc="d")
    await ok(invoke, *address(review), "add-finding", "Leak", "-m", "It leaks")
    return review


# subtask_story_mapping


def _unmapped(squad: Squad, level: str) -> dict[str, str]:
    message = f"subtask ST2 → US9 missing from {squad.feature}"
    return issue("subtask_story_mapping", level, squad.task, message)


STORY_US1 = "title: Lex\n  status: Todo\n  story: US1"
STORY_US9 = "title: Lex\n  status: Todo\n  story: US9"


@pytest.mark.breaches("subtask_story_mapping")
async def test_a_subtask_mapped_to_a_story_its_parent_lacks_is_reported(
    squad, project, invoke, check_json
) -> None:
    await ok(invoke, *address(squad.task), "add-subtask", "Lex", "-m", "Do it", "--story", "US1")
    assert await check_json() == ([], 0)

    # the update gate refuses an error-level story that is missing: edit the file and re-index
    edit_item_file(project, squad.task, STORY_US1, STORY_US9)
    await repair(invoke)

    assert await check_json() == ([_unmapped(squad, "error")], 3)


@pytest.mark.breaches("subtask_story_mapping@warn")
async def test_a_story_mapping_selected_at_warn_leaves_the_exit_code_alone(
    squad, project, invoke, check_json, select_validators
) -> None:
    await ok(invoke, *address(squad.task), "add-subtask", "Lex", "-m", "Do it", "--story", "US1")
    select_validators("subtask_story_mapping@warn", on="task")
    assert await check_json() == ([], 0)

    # the CLI refuses a story the parent lacks: edit the file and re-index
    edit_item_file(project, squad.task, STORY_US1, STORY_US9)
    await repair(invoke)

    assert await check_json() == ([_unmapped(squad, "warn")], 0)


# subentity_status_valid


def _bad_status(squad: Squad, level: str) -> dict[str, str]:
    return issue(
        "subentity_status_valid", level, squad.task, "subtask ST2 has invalid status 'Approved'"
    )


async def _start_a_second_subtask(squad: Squad, invoke) -> None:
    await ok(invoke, *address(squad.task), "add-subtask", "Lex", "-m", "Do it")
    await ok(invoke, *address(squad.task), "subtask", "ST2", "update", "--status", "InProgress")


@pytest.mark.breaches("subentity_status_valid")
async def test_a_subtask_in_a_status_its_lifecycle_lacks_is_reported(
    squad, project, invoke, check_json
) -> None:
    await _start_a_second_subtask(squad, invoke)
    assert await check_json() == ([], 0)

    # the CLI refuses a status outside the vocabulary: edit the file and re-index
    edit_item_file(project, squad.task, "status: InProgress", "status: Approved")
    await repair(invoke)

    assert await check_json() == ([_bad_status(squad, "error")], 3)


@pytest.mark.breaches("subentity_status_valid@warn")
async def test_a_subtask_status_selected_at_warn_leaves_the_exit_code_alone(
    squad, project, invoke, check_json, select_validators
) -> None:
    await _start_a_second_subtask(squad, invoke)
    select_validators("subentity_status_valid@warn", on="task")
    assert await check_json() == ([], 0)

    # the CLI refuses a status outside the vocabulary: edit the file and re-index
    edit_item_file(project, squad.task, "status: InProgress", "status: Approved")
    await repair(invoke)

    assert await check_json() == ([_bad_status(squad, "warn")], 0)


# subentity_container_marker


@pytest.mark.breaches("subentity_container_marker")
async def test_a_container_marker_that_is_not_the_declared_plural_is_reported(
    squad, project, invoke, check_json
) -> None:
    carry = await create(invoke, "task", "Carry", "tech-lead", desc="d")
    spare = await create(invoke, "task", "Spare", "tech-lead", desc="d")
    edit_item_file(project, spare, "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n", "")
    await repair(invoke)
    assert await check_json() == ([], 0)

    # no command renames a container marker: edit the file and re-index
    edit_item_file(project, carry, "<!-- sq:subtasks -->", "<!-- sq:chores -->")
    edit_item_file(project, carry, "<!-- sq:subtasks:end -->", "<!-- sq:chores:end -->")
    await repair(invoke)

    noun = " ".join(address(carry))
    message = (
        "no 'subtasks' container section; the file carries 'chores' — 'subtask' declares "
        f"plural 'subtasks', so `sq {noun} add-subtask` cannot write here. Revert "
        "subentity_kinds.subtask.plural in the workflow override, or change it only while "
        "no task items exist"
    )
    assert await check_json() == ([issue("subentity_container_marker", "error", carry, message)], 3)


# subentity_body_written

UNWRITTEN = "ST2 body is unwritten (still the placeholder stub)"


@pytest.mark.breaches("subentity_body_written")
async def test_a_subtask_left_at_its_placeholder_body_is_reported(
    squad, invoke, check_json
) -> None:
    assert await check_json() == ([], 0)

    await ok(invoke, *address(squad.task), "add-subtask", "Lex")

    assert await check_json() == (
        [issue("subentity_body_written", "warn", squad.task, UNWRITTEN)],
        0,
    )


@pytest.mark.breaches("subentity_body_written@error")
async def test_an_unwritten_subtask_body_selected_at_error_fails_the_check(
    squad, invoke, check_json, select_validators
) -> None:
    select_validators("subentity_body_written@error", on="task")
    assert await check_json() == ([], 0)

    await ok(invoke, *address(squad.task), "add-subtask", "Lex")

    assert await check_json() == (
        [issue("subentity_body_written", "error", squad.task, UNWRITTEN)],
        3,
    )


# subentity_title_max


def _long_title(length: int) -> str:
    return "x" * length


def _too_long(title_length: int, threshold: int) -> str:
    return (
        f"advisory: subtask ST3 title is {title_length} chars (threshold: {threshold})"
        " — a sub-entity title is a one-line handle; put the detail in the body"
    )


async def _add_subtask(invoke, task: str, title: str) -> None:
    await ok(invoke, *address(task), "add-subtask", title, "-m", "Do it")


@pytest.mark.breaches("subentity_title_max")
async def test_a_subtask_title_over_the_default_length_is_reported(
    squad, invoke, check_json, select_validators
) -> None:
    await _add_subtask(invoke, squad.task, _long_title(120))
    select_validators("subentity_title_max", on="task")
    assert await check_json() == ([], 0)

    await _add_subtask(invoke, squad.task, _long_title(121))

    assert await check_json() == (
        [issue("subentity_title_max", "warn", squad.task, _too_long(121, 120))],
        0,
    )


@pytest.mark.breaches("subentity_title_max:param")
async def test_a_subtask_title_over_the_selected_length_is_reported(
    squad, invoke, check_json, select_validators
) -> None:
    await _add_subtask(invoke, squad.task, _long_title(30))
    select_validators("subentity_title_max:30", on="task")
    assert await check_json() == ([], 0)

    await _add_subtask(invoke, squad.task, _long_title(50))

    assert await check_json() == (
        [issue("subentity_title_max", "warn", squad.task, _too_long(50, 30))],
        0,
    )


@pytest.mark.breaches("subentity_title_max@error")
async def test_a_subtask_title_selected_at_error_fails_the_check(
    squad, invoke, check_json, select_validators
) -> None:
    await _add_subtask(invoke, squad.task, _long_title(120))
    select_validators("subentity_title_max@error", on="task")
    assert await check_json() == ([], 0)

    await _add_subtask(invoke, squad.task, _long_title(121))

    assert await check_json() == (
        [issue("subentity_title_max", "error", squad.task, _too_long(121, 120))],
        3,
    )


# subentity_deferral_resolved


async def _defer_two_findings(squad: Squad, invoke) -> str:
    """A review with one finding deferred to the task under test and one to a live task; returns
    the review."""
    review = await _review(invoke, "Audit")
    await ok(invoke, *address(review), "add-finding", "Drift", "-m", "It drifts")
    carrier = await create(invoke, "task", "Carry", "tech-lead", desc="d")
    for finding, to in (("1", squad.task), ("2", carrier)):
        await ok(
            invoke,
            *address(review),
            *("finding", finding, "update", "--status", "Deferred"),
            *("--deferred-to", to),
        )
    return review


def _retired_carrier(squad: Squad) -> str:
    return f"finding F1 is Deferred to {squad.task}, which is Cancelled and will not carry the work"


@pytest.mark.breaches("subentity_deferral_resolved")
async def test_a_finding_deferred_to_a_cancelled_task_is_reported(
    squad, invoke, check_json
) -> None:
    review = await _defer_two_findings(squad, invoke)
    assert await check_json() == ([], 0)

    await update(invoke, squad.task, "--status", "Cancelled")

    assert await check_json() == (
        [issue("subentity_deferral_resolved", "warn", review, _retired_carrier(squad))],
        0,
    )


@pytest.mark.breaches("subentity_deferral_resolved@error")
async def test_a_deferral_selected_at_error_fails_the_check(
    squad, invoke, check_json, select_validators
) -> None:
    review = await _defer_two_findings(squad, invoke)
    select_validators("subentity_deferral_resolved@error", on="review")
    assert await check_json() == ([], 0)

    await update(invoke, squad.task, "--status", "Cancelled")

    assert await check_json() == (
        [issue("subentity_deferral_resolved", "error", review, _retired_carrier(squad))],
        3,
    )


# subentities_settled_with_parent


async def _two_reviews(invoke) -> tuple[str, str]:
    """One review in progress over an open finding, one approved over a noted one; returns them."""
    open_review = await _review(invoke, "Audit")
    await update(invoke, open_review, "--status", "InReview")
    noted = await _review(invoke, "Sweep")
    await ok(invoke, *address(noted), "finding", "1", "update", "--status", "Noted")
    await update(invoke, noted, "--status", "InReview")
    await update(invoke, noted, "--status", "Approved")
    return open_review, noted


def _unsettled(review: str, level: str) -> dict[str, str]:
    return issue(
        "subentities_settled_with_parent",
        level,
        review,
        "status is Approved with 1 unsettled finding: F1",
    )


@pytest.mark.breaches("subentities_settled_with_parent")
async def test_a_review_approved_over_an_open_finding_is_reported(
    squad, invoke, check_json
) -> None:
    open_review, _noted = await _two_reviews(invoke)
    assert await check_json() == ([], 0)

    await update(invoke, open_review, "--status", "Approved")

    assert await check_json() == ([_unsettled(open_review, "warn")], 0)


@pytest.mark.breaches("subentities_settled_with_parent@error")
async def test_a_review_approved_over_an_open_finding_selected_at_error_fails_the_check(
    squad, project, invoke, check_json, select_validators
) -> None:
    open_review, _noted = await _two_reviews(invoke)
    select_validators("subentities_settled_with_parent@error", on="review")
    assert await check_json() == ([], 0)

    # the update gate refuses an error-level approval: edit the file and re-index
    edit_item_file(project, open_review, "status: InReview", "status: Approved")
    await repair(invoke)

    assert await check_json() == ([_unsettled(open_review, "error")], 3)
