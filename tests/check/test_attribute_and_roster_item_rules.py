"""The `sq check` rules over an item's frontmatter: its status, its author and assignee, the
attributes its type declares and the keys it does not, plus the two rules of the roster types: an
operator's pronouns and a skill that shadows a type's generated guidance."""

import pytest

from tests.check._arrange import (
    activate,
    add_roster,
    create,
    edit_item_file,
    issue,
    ok,
    repair,
    update,
)

pytestmark = pytest.mark.anyio


async def _task(invoke, title: str, *, assignee: str | None = None) -> str:
    task = await create(invoke, "task", title, "tech-lead", desc="d")
    if assignee:
        await update(invoke, task, "--assignee", assignee)
    return task


@pytest.fixture
async def squad(project, invoke):
    """The `minimal` squad with `tech-lead` and `manager` live."""
    await activate(invoke, "tech-lead", "manager")
    return project


# item_status_valid


def _invalid_status(status: str) -> str:
    return f"status {status!r} invalid for task"


@pytest.mark.breaches("item_status_valid")
async def test_a_status_the_workflow_does_not_have_is_an_error(squad, invoke, check_json) -> None:
    await _task(invoke, "Valid")
    stray = await _task(invoke, "Stray")
    assert await check_json() == ([], 0)

    # the update gate refuses a status outside the workflow: edit the file and re-index
    edit_item_file(squad, stray, "status: Draft", "status: Accepted")
    await repair(invoke)

    assert await check_json() == (
        [issue("item_status_valid", "error", stray, _invalid_status("Accepted"))],
        3,
    )


@pytest.mark.breaches("item_status_valid@warn")
async def test_a_status_check_selected_at_warn_reports_a_warning_and_passes(
    squad, invoke, check_json, select_validators
) -> None:
    await _task(invoke, "Valid")
    stray = await _task(invoke, "Stray")
    select_validators("item_status_valid@warn", on="task")
    assert await check_json() == ([], 0)

    edit_item_file(squad, stray, "status: Draft", "status: Accepted")
    await repair(invoke)

    assert await check_json() == (
        [issue("item_status_valid", "warn", stray, _invalid_status("Accepted"))],
        0,
    )


# agent_registered


def _unregistered(attr: str) -> str:
    return f"{attr} 'manager' is not a registered role or operator"


@pytest.mark.breaches("agent_registered")
async def test_an_assignee_that_is_no_longer_a_registered_role_is_reported(
    squad, invoke, check_json
) -> None:
    await _task(invoke, "Kept", assignee="tech-lead")
    orphan = await _task(invoke, "Orphan", assignee="manager")
    assert await check_json() == ([], 0)

    await ok(invoke, "role", "manager", "remove", "--purge")

    assert await check_json() == (
        [issue("agent_registered", "warn", orphan, _unregistered("assignee"))],
        0,
    )


@pytest.mark.breaches("agent_registered@error")
async def test_an_unregistered_assignee_selected_at_error_fails_the_check(
    squad, invoke, check_json, select_validators
) -> None:
    await _task(invoke, "Kept", assignee="tech-lead")
    orphan = await _task(invoke, "Orphan", assignee="manager")
    select_validators("agent_registered@error", on="task")
    assert await check_json() == ([], 0)

    await ok(invoke, "role", "manager", "remove", "--purge")

    assert await check_json() == (
        [issue("agent_registered", "error", orphan, _unregistered("assignee"))],
        3,
    )


# attribute_valid


async def _two_skills(invoke) -> str:
    """Two skills whose attributes are all valid; returns the second."""
    await add_roster(invoke, "skill", "Release Notes")
    return await add_roster(invoke, "skill", "Handover Notes")


def _not_a_string() -> str:
    return "attribute 'when_to_use': expected a string, got a list"


@pytest.mark.breaches("attribute_valid")
async def test_an_attribute_of_the_wrong_kind_is_an_error(squad, invoke, check_json) -> None:
    broken = await _two_skills(invoke)
    assert await check_json() == ([], 0)

    # no command writes a list where `when_to_use` takes a string: edit the file and re-index
    edit_item_file(squad, broken, "when_to_use: ''", "when_to_use: [a]")
    await repair(invoke)

    assert await check_json() == (
        [issue("attribute_valid", "error", broken, _not_a_string())],
        3,
    )


@pytest.mark.breaches("attribute_valid@warn")
async def test_an_attribute_check_selected_at_warn_reports_a_warning_and_passes(
    squad, invoke, check_json, select_validators
) -> None:
    broken = await _two_skills(invoke)
    select_validators("attribute_valid@warn", on="skill")
    assert await check_json() == ([], 0)

    edit_item_file(squad, broken, "when_to_use: ''", "when_to_use: [a]")
    await repair(invoke)

    assert await check_json() == (
        [issue("attribute_valid", "warn", broken, _not_a_string())],
        0,
    )


# frontmatter_key_undeclared


def _undeclared() -> str:
    return (
        "frontmatter key 'colour' is not declared on skill"
        "; `sq migrate rename-field colour <new> --type skill` moves its value to a declared key"
    )


@pytest.mark.breaches("frontmatter_key_undeclared")
async def test_a_frontmatter_key_the_type_does_not_declare_is_reported(
    squad, invoke, check_json, select_validators
) -> None:
    typo = await _two_skills(invoke)
    select_validators("frontmatter_key_undeclared", on="skill")
    assert await check_json() == ([], 0)

    # no command writes a key the type does not declare: edit the file and re-index
    edit_item_file(squad, typo, "allowed_tools: ''", "allowed_tools: ''\ncolour: red")
    await repair(invoke)

    assert await check_json() == (
        [issue("frontmatter_key_undeclared", "warn", typo, _undeclared())],
        0,
    )


@pytest.mark.breaches("frontmatter_key_undeclared@error")
async def test_an_undeclared_key_selected_at_error_fails_the_check(
    squad, invoke, check_json, select_validators
) -> None:
    typo = await _two_skills(invoke)
    select_validators("frontmatter_key_undeclared@error", on="skill")
    assert await check_json() == ([], 0)

    edit_item_file(squad, typo, "allowed_tools: ''", "allowed_tools: ''\ncolour: red")
    await repair(invoke)

    assert await check_json() == (
        [issue("frontmatter_key_undeclared", "error", typo, _undeclared())],
        3,
    )


# pronouns_valid

LIMIT = 40
AT_LIMIT = "p" * LIMIT
OVER_LIMIT = "p" * (LIMIT + 1)
OVER_MESSAGE = f"pronouns is {LIMIT + 1} characters long; the limit is {LIMIT}"


def _replace_with(slug: str) -> str:
    return f" — replace it with `sq operator {slug} update --pronouns <text>`"


async def _two_operators(invoke) -> str:
    """An operator whose pronouns are at the limit, and one (returned) that will cross it."""
    await add_roster(invoke, "operator", "Ada Bound", "--pronouns", AT_LIMIT)
    return await add_roster(invoke, "operator", "Pat Lee", "--pronouns", "they/them")


@pytest.mark.breaches("pronouns_valid")
async def test_pronouns_longer_than_the_limit_are_an_error(squad, invoke, check_json) -> None:
    pat = await _two_operators(invoke)
    assert await check_json() == ([], 0)

    # the command refuses pronouns over the limit: edit the file and re-index
    edit_item_file(squad, pat, "pronouns: they/them", f"pronouns: {OVER_LIMIT}")
    await repair(invoke)

    assert await check_json() == (
        [issue("pronouns_valid", "error", pat, OVER_MESSAGE + _replace_with("op-pat"))],
        3,
    )


@pytest.mark.breaches("pronouns_valid@warn")
async def test_a_pronouns_check_selected_at_warn_reports_a_warning_and_passes(
    squad, invoke, check_json, select_validators
) -> None:
    pat = await _two_operators(invoke)
    select_validators("pronouns_valid@warn", on="operator")
    assert await check_json() == ([], 0)

    edit_item_file(squad, pat, "pronouns: they/them", f"pronouns: {OVER_LIMIT}")
    await repair(invoke)

    assert await check_json() == (
        [issue("pronouns_valid", "warn", pat, OVER_MESSAGE + _replace_with("op-pat"))],
        0,
    )


# item_skill_shadowed


REMEDY = (
    "move the prose first (`sq skill add <new-slug>`); take the type out of the active spec "
    "(drop it from `[selected]`, or remove a project type's own declaration); clear sq-task with "
    '`sq skill sq-task body -m "" --force`; then restore the type'
)
SHADOWED = (
    "documents declared type 'task' and carries prose beside its item_skill tag — task's "
    "generated guidance renders through the tag, but the prose beside it has no supported way to "
    f"be removed once this slug documents a declared type; {REMEDY}"
)
SCAFFOLD = (
    "# sq-task\n\n_TODO: describe what this skill does and when to use it._\n\n## Instructions\n\n"
)


async def _task_skill_without_prose(squad, invoke) -> str:
    """The skill `sq-task`, whose body holds only its generated tag, beside a skill named after
    no type that keeps its prose."""
    await add_roster(invoke, "skill", "Release Notes")
    skill = await add_roster(invoke, "skill", "sq-task")
    # no command clears prose beside a type skill's tag: edit the file and re-index
    edit_item_file(squad, skill, SCAFFOLD, "")
    await repair(invoke)
    return skill


@pytest.mark.breaches("item_skill_shadowed")
async def test_a_skill_that_documents_a_type_and_holds_prose_of_its_own_is_reported(
    squad, invoke, check_json
) -> None:
    skill = await _task_skill_without_prose(squad, invoke)
    assert await check_json() == ([], 0)

    edit_item_file(
        squad, skill, "<!-- sq:view:item_skill -->", "A runbook.\n<!-- sq:view:item_skill -->"
    )
    await repair(invoke)

    assert await check_json() == ([issue("item_skill_shadowed", "warn", skill, SHADOWED)], 0)


@pytest.mark.breaches("item_skill_shadowed@error")
async def test_a_shadowing_skill_selected_at_error_fails_the_check(
    squad, invoke, check_json, select_validators
) -> None:
    skill = await _task_skill_without_prose(squad, invoke)
    select_validators("item_skill_shadowed@error", on="skill")
    assert await check_json() == ([], 0)

    edit_item_file(
        squad, skill, "<!-- sq:view:item_skill -->", "A runbook.\n<!-- sq:view:item_skill -->"
    )
    await repair(invoke)

    assert await check_json() == ([issue("item_skill_shadowed", "error", skill, SHADOWED)], 3)
