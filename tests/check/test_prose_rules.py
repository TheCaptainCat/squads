"""The `sq check` rules over an item's prose: a status banner, the title length, an unwritten body,
a missing description and a tracker id in a title. No bundled type selects any of them, so each
test enables its member on `task`."""

import pytest

from tests.check._arrange import (
    activate,
    address,
    create,
    edit_item_file,
    issue,
    repair,
    update,
    write_body,
)

pytestmark = pytest.mark.anyio

BANNER_TAIL = " — move state to frontmatter or a dated discussion comment"
TITLE_TAIL = " — an item title is a one-line handle; put the detail in the body"


async def _task(invoke, title: str) -> str:
    return await create(invoke, "task", title, "tech-lead", desc="d")


@pytest.fixture
async def squad(project, invoke):
    """The `minimal` squad with `tech-lead` live, so open tasks have an author."""
    await activate(invoke, "tech-lead")
    return project


# no_status_banner

BODY_BANNER = "body opens with a status/lifecycle banner" + BANNER_TAIL


async def _two_written_bodies(invoke) -> tuple[str, str]:
    """Two written bodies; the second has a status line that is not the opening one."""
    plain = await _task(invoke, "Plain")
    quoted = await _task(invoke, "Quoted")
    await write_body(invoke, plain, "The plan.")
    await write_body(invoke, quoted, "The plan.\nStatus: discussed below.")
    return plain, quoted


@pytest.mark.breaches("no_status_banner")
async def test_a_body_that_opens_with_a_status_line_is_reported(
    squad, invoke, check_json, select_validators
) -> None:
    await _two_written_bodies(invoke)
    select_validators("no_status_banner", on="task")
    assert await check_json() == ([], 0)

    banner = await _task(invoke, "Banner")
    await write_body(invoke, banner, "STATUS: Proposed\nThe plan.")

    assert await check_json() == (
        [issue("no_status_banner", "warn", banner, BODY_BANNER)],
        0,
    )


@pytest.mark.breaches("no_status_banner")
async def test_a_description_that_opens_with_a_status_line_is_reported(
    squad, invoke, check_json, select_validators
) -> None:
    plain, _quoted = await _two_written_bodies(invoke)
    select_validators("no_status_banner", on="task")
    assert await check_json() == ([], 0)

    await update(invoke, plain, "--desc", "## Status")

    message = "description opens with a status/lifecycle banner" + BANNER_TAIL
    assert await check_json() == ([issue("no_status_banner", "warn", plain, message)], 0)


@pytest.mark.breaches("no_status_banner@error")
async def test_a_status_banner_selected_at_error_fails_the_check(
    squad, invoke, check_json, select_validators
) -> None:
    await _two_written_bodies(invoke)
    banner = await _task(invoke, "Banner")
    select_validators("no_status_banner@error", on="task")
    assert await check_json() == ([], 0)

    await write_body(invoke, banner, "STATUS: Proposed\nThe plan.")

    assert await check_json() == (
        [issue("no_status_banner", "error", banner, BODY_BANNER)],
        3,
    )


# item_title_max


def _title_of(length: int) -> str:
    return "t" * length


def _over(length: int) -> str:
    return f"title is {length} chars (threshold: 20)" + TITLE_TAIL


@pytest.mark.breaches("item_title_max", "item_title_max:param")
async def test_a_title_longer_than_the_selected_limit_is_reported(
    squad, invoke, check_json, select_validators
) -> None:
    await _task(invoke, _title_of(20))
    long = await _task(invoke, _title_of(20))
    select_validators("item_title_max:20", on="task")
    assert await check_json() == ([], 0)

    await update(invoke, long, "--title", _title_of(21))

    assert await check_json() == ([issue("item_title_max", "warn", long, _over(21))], 0)


@pytest.mark.breaches("item_title_max@error")
async def test_a_title_limit_selected_at_error_fails_the_check(
    squad, invoke, check_json, select_validators
) -> None:
    await _task(invoke, _title_of(20))
    long = await _task(invoke, _title_of(20))
    select_validators("item_title_max:20@error", on="task")
    assert await check_json() == ([], 0)

    # the update gate refuses an error-level change: edit the file and re-index
    edit_item_file(squad, long, f"title: {_title_of(20)}", f"title: {_title_of(21)}")
    await repair(invoke)

    assert await check_json() == ([issue("item_title_max", "error", long, _over(21))], 3)


# body_written


def _unwritten_body(task: str) -> str:
    return (
        "body is unwritten (still the template scaffold) — write it with "
        f'`sq {" ".join(address(task))} body -m "..."`'
    )


@pytest.mark.breaches("body_written")
async def test_a_body_left_at_its_template_scaffold_is_reported(
    squad, invoke, check_json, select_validators
) -> None:
    written = await _task(invoke, "Written")
    await write_body(invoke, written, "The plan.")
    select_validators("body_written", on="task")
    assert await check_json() == ([], 0)

    blank = await _task(invoke, "Blank")

    assert await check_json() == (
        [issue("body_written", "warn", blank, _unwritten_body(blank))],
        0,
    )


@pytest.mark.breaches("body_written@error")
async def test_an_unwritten_body_selected_at_error_fails_the_check(
    squad, invoke, check_json, select_validators
) -> None:
    written = await _task(invoke, "Written")
    await write_body(invoke, written, "The plan.")
    select_validators("body_written@error", on="task")
    assert await check_json() == ([], 0)

    blank = await _task(invoke, "Blank")

    assert await check_json() == (
        [issue("body_written", "error", blank, _unwritten_body(blank))],
        3,
    )


# description_present


NO_DESCRIPTION = "description is empty — set a summary: `--desc` on create, `update --desc` after"


@pytest.mark.breaches("description_present")
async def test_an_empty_description_is_reported(
    squad, invoke, check_json, select_validators
) -> None:
    await _task(invoke, "Described")
    blank = await _task(invoke, "Blank")
    select_validators("description_present", on="task")
    assert await check_json() == ([], 0)

    await update(invoke, blank, "--desc", "")

    assert await check_json() == (
        [issue("description_present", "warn", blank, NO_DESCRIPTION)],
        0,
    )


@pytest.mark.breaches("description_present@error")
async def test_an_empty_description_selected_at_error_fails_the_check(
    squad, invoke, check_json, select_validators
) -> None:
    await _task(invoke, "Described")
    blank = await _task(invoke, "Blank")
    select_validators("description_present@error", on="task")
    assert await check_json() == ([], 0)

    # the update gate refuses an error-level change: edit the file and re-index
    edit_item_file(squad, blank, "description: d", "description: ''")
    await repair(invoke)

    assert await check_json() == (
        [issue("description_present", "error", blank, NO_DESCRIPTION)],
        3,
    )


# external_id_not_in_title

TRACKER_ID = "[A-Z]+-[0-9]+"


def _holds(task: str, level: str) -> list[dict[str, str]]:
    message = (
        f"title holds `JIRA-123` (matches the external-id pattern `{TRACKER_ID}`)"
        " — keep tracker ids out of the title"
    )
    return [issue("external_id_not_in_title", level, task, message)]


@pytest.mark.breaches("external_id_not_in_title", "external_id_not_in_title:param")
async def test_a_title_holding_a_tracker_id_is_reported(
    squad, invoke, check_json, select_validators
) -> None:
    await _task(invoke, "Fix JIRA-abc")
    tagged = await _task(invoke, "Fix JIRA-abc")
    select_validators(f"external_id_not_in_title:{TRACKER_ID}", on="task")
    assert await check_json() == ([], 0)

    await update(invoke, tagged, "--title", "Fix JIRA-123")

    assert await check_json() == (_holds(tagged, "warn"), 0)


@pytest.mark.breaches("external_id_not_in_title@error")
async def test_a_tracker_id_selected_at_error_fails_the_check(
    squad, invoke, check_json, select_validators
) -> None:
    await _task(invoke, "Fix JIRA-abc")
    tagged = await _task(invoke, "Fix JIRA-abc")
    select_validators(f"external_id_not_in_title:{TRACKER_ID}@error", on="task")
    assert await check_json() == ([], 0)

    # the update gate refuses an error-level change: edit the file and re-index
    edit_item_file(squad, tagged, "title: Fix JIRA-abc", "title: Fix JIRA-123")
    await repair(invoke)

    assert await check_json() == (_holds(tagged, "error"), 3)
