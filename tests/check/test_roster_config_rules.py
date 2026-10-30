"""The always-on squad-wide `sq check` rules over the roster, the display and language settings in
`.squads.toml`, and the view transforms: they cannot be selected, so each has a breach case only."""

import pytest

from tests.check._arrange import (
    add_roster,
    address,
    edit_config,
    edit_item_file,
    issue,
    ok,
    repair,
    role_id,
    write_override,
)

pytestmark = pytest.mark.anyio

# roster_config_integrity


@pytest.mark.breaches("roster_config_integrity")
async def test_a_retired_skill_still_scoped_to_a_live_role_is_an_error(
    project, invoke, check_json
) -> None:
    live = await add_roster(invoke, "skill", "Release Notes")
    retired = await add_roster(invoke, "skill", "Handover Notes")
    await ok(invoke, *address(live), "link-role", "manager")
    await ok(invoke, *address(retired), "status", "Archived")
    assert await check_json() == ([], 0)

    await ok(invoke, *address(retired), "link-role", "manager")

    assert await check_json() == (
        [
            issue(
                "roster_config_integrity",
                "error",
                retired,
                "config integrity: not live but still scoped to live role(s): manager — remedy: "
                "sever the edge with `sq skill <addr> unlink-role <role>`, or reactivate the skill",
            )
        ],
        3,
    )


async def _designer(invoke) -> str:
    """A role that defines itself, filed under the slug `designer`; returns its id."""
    return await add_roster(
        invoke,
        "role",
        "designer",
        "--name",
        "Dee Signer",
        "--job-title",
        "designer",
        "--desc",
        "Shapes the interface.",
        "--mission",
        "Keep the interface coherent.",
    )


# default_designation_duplicated


@pytest.mark.breaches("default_designation_duplicated")
async def test_two_live_roles_holding_the_default_designation_are_an_error(
    project, invoke, check_json
) -> None:
    designer = await _designer(invoke)
    manager = await role_id(invoke, "manager")
    await ok(invoke, "role", "manager", "status", "Archived")
    # no command stores the designation on a role without clearing the other holders: write the
    # key (`role add --file` refuses `is_default`, `set-default` moves it) and re-index
    edit_item_file(project, designer, "origin: project", "origin: project\nis_default: true")
    await repair(invoke)
    assert await check_json() == ([], 0)

    await ok(invoke, "role", "manager", "status", "Active")

    assert await check_json() == (
        [
            issue(
                "default_designation_duplicated",
                "error",
                "",
                "more than one live role carries the default-role designation: "
                f"{manager}, {designer} — remedy: `sq role <addr> set-default`",
            )
        ],
        3,
    )


# roster_slug_valid


@pytest.mark.breaches("roster_slug_valid")
async def test_an_operator_slug_outside_the_grammar_is_an_error(
    project, invoke, check_json
) -> None:
    await add_roster(invoke, "operator", "Al Bo", "--slug", "op-al-2")
    breaching = await add_roster(invoke, "operator", "Cy Dee")
    assert await check_json() == ([], 0)

    # the add command refuses a slug outside the grammar: write it, as the author too, and re-index
    edit_item_file(project, breaching, "slug: op-cy", "slug: op-Cy")
    edit_item_file(project, breaching, "author: op-cy", "author: op-Cy")
    await repair(invoke)

    assert await check_json() == (
        [
            issue(
                "roster_slug_valid",
                "error",
                breaching,
                "operator slug 'op-Cy' is not 'op-' followed by lowercase letters, digits and "
                f"hyphens — remedy: sq operator {breaching} remove --purge, then sq operator add "
                '"Cy Dee" --slug <compliant slug>',
            )
        ],
        3,
    )


# role_base_resolves


@pytest.mark.breaches("role_base_resolves")
async def test_a_role_defining_itself_without_a_job_title_is_an_error(
    project, invoke, check_json
) -> None:
    await _designer(invoke)
    broken = await add_roster(
        invoke,
        "role",
        "writer",
        "--name",
        "Wren Writer",
        "--job-title",
        "writer",
        "--desc",
        "Writes the docs.",
        "--mission",
        "Keep the docs current.",
    )
    assert await check_json() == ([], 0)

    # `update` refuses a blank job title: remove the key from the file and re-index
    edit_item_file(project, broken, "job_title: writer\n", "")
    await repair(invoke)
    await ok(invoke, "sync")  # the pointer carries the job title: regenerate it

    assert await check_json() == (
        [
            issue(
                "role_base_resolves",
                "error",
                broken,
                "role 'writer' defines itself but stores no job_title; set "
                "`sq role writer update --job-title … --desc … --mission …`",
            )
        ],
        3,
    )


# role_definition_shadowed


@pytest.mark.breaches("role_definition_shadowed")
async def test_a_role_file_setting_a_field_the_role_stores_is_a_warning(
    project, invoke, check_json
) -> None:
    designer = await _designer(invoke)
    write_override(project, "roles/designer.toml", 'responsibilities = ["Review layouts"]\n')
    assert await check_json() == ([], 0)

    write_override(project, "roles/designer.toml", 'title = "Chief designer"\n')
    await ok(invoke, "sync")  # the file changes the pointer: regenerate it

    assert await check_json() == (
        [
            issue(
                "role_definition_shadowed",
                "warn",
                designer,
                ".overrides/roles/designer.toml sets title, which role 'designer' stores in its "
                "item: the file wins, so `sq role designer update` of those fields has no effect "
                "— delete the file or those keys",
            )
        ],
        0,
    )


# playbook_guide_role_live


@pytest.mark.breaches("playbook_guide_role_live")
async def test_a_playbook_guide_for_a_retired_role_is_a_warning(
    project, invoke, check_json
) -> None:
    await _designer(invoke)
    write_override(
        project,
        "playbook.toml",
        '[types.task]\nroles = ["$(*self)",\n'
        '  { slug = "designer", enter = ["Read the mock-up"], do = ["Review the layout"] },\n'
        '  { slug = "manager", enter = ["Read the brief"], do = ["Assign the work"] },\n]\n',
    )
    await ok(invoke, "sync")
    assert await check_json() == ([], 0)

    await ok(invoke, "role", "designer", "status", "Archived")

    assert await check_json() == (
        [
            issue(
                "playbook_guide_role_live",
                "warn",
                "",
                "playbook guide for role 'designer' on type 'task' names no live role, so its "
                "guidance is dropped from the generated `sq-task` skill — reactivate the role "
                "(`sq role designer status Active`), or remove the guide from "
                "`.overrides/playbook.toml` under `[types.task]`",
            )
        ],
        0,
    )


# display_config_valid


@pytest.mark.breaches("display_config_valid")
async def test_a_display_setting_that_is_not_a_boolean_is_a_warning(
    project, invoke, check_json
) -> None:
    # no command edits `.squads.toml`
    edit_config(
        project, 'working_language = "en"', 'working_language = "en"\n\n[display]\npronouns = false'
    )
    assert await check_json() == ([], 0)

    edit_config(project, "pronouns = false", 'pronouns = "false"')

    assert await check_json() == (
        [
            issue(
                "display_config_valid",
                "warn",
                ".squads.toml",
                "[display] pronouns must be true or false, got 'false'; the default applies",
            )
        ],
        0,
    )


# daemon_config_valid


@pytest.mark.breaches("daemon_config_valid")
async def test_a_daemon_timeout_that_is_not_a_whole_number_of_minutes_is_a_warning(
    project, invoke, check_json
) -> None:
    # no command edits `.squads.toml`
    edit_config(
        project,
        'working_language = "en"',
        'working_language = "en"\n\n[daemon]\nidle_timeout_minutes = 5',
    )
    assert await check_json() == ([], 0)

    edit_config(project, "idle_timeout_minutes = 5", "idle_timeout_minutes = -5")

    assert await check_json() == (
        [
            issue(
                "daemon_config_valid",
                "warn",
                ".squads.toml",
                "[daemon] idle_timeout_minutes must be a whole number of minutes, 0 or more, "
                "got -5; every command runs in local mode until it is fixed",
            )
        ],
        0,
    )


@pytest.mark.breaches("daemon_config_valid")
async def test_a_daemon_key_squads_does_not_know_is_a_warning(project, invoke, check_json) -> None:
    # no command edits `.squads.toml`
    edit_config(
        project, 'working_language = "en"', 'working_language = "en"\n\n[daemon]\nbrowser = true'
    )
    assert await check_json() == ([], 0)

    edit_config(project, "browser = true", "browser = true\nport = 80")

    assert await check_json() == (
        [
            issue(
                "daemon_config_valid",
                "warn",
                ".squads.toml",
                "[daemon] has an unknown key 'port'; it is ignored",
            )
        ],
        0,
    )


@pytest.mark.breaches("daemon_config_valid")
async def test_a_squads_daemon_value_that_is_not_on_or_off_is_a_warning(
    project, invoke, check_json, monkeypatch
) -> None:
    monkeypatch.setenv("SQUADS_DAEMON", "off")
    assert await check_json() == ([], 0)

    monkeypatch.setenv("SQUADS_DAEMON", "maybe")

    assert await check_json() == (
        [
            issue(
                "daemon_config_valid",
                "warn",
                "SQUADS_DAEMON",
                "SQUADS_DAEMON must be on or off, got 'maybe'; every command runs in local "
                "mode until it is fixed",
            )
        ],
        0,
    )


# working_language_valid


@pytest.mark.breaches("working_language_valid")
async def test_a_working_language_squads_does_not_recognise_is_a_warning(
    project, invoke, check_json
) -> None:
    # no command edits `.squads.toml`
    edit_config(project, 'working_language = "en"', 'working_language = "pt-BR"')
    assert await check_json() == ([], 0)

    edit_config(project, 'working_language = "pt-BR"', 'working_language = "klingon"')

    message = (
        'working_language "klingon" in .squads.toml is not a language tag squads '
        "recognises; using English (en)"
    )
    # the load prints the same notice once to stderr, besides the issue on stdout
    assert await check_json(stderr=f"warning: {message}\n") == (
        [issue("working_language_valid", "warn", ".squads.toml", message)],
        0,
    )


# view_transform_resolves

_VIEW = (
    "[views.story_progress]\n"
    'source = { kind = "subentity", name = "story" }\n'
    'transform = { path = "transforms/progress.py", function = "story_progress" }\n'
)


@pytest.mark.breaches("view_transform_resolves")
async def test_a_view_transform_file_without_its_function_is_an_error(
    project, invoke, check_json
) -> None:
    write_override(project, "workflow.toml", _VIEW)
    write_override(
        project, "transforms/progress.py", "def story_progress(source):\n    return {}\n"
    )
    assert await check_json() == ([], 0)

    write_override(project, "transforms/progress.py", "def progress(source):\n    return {}\n")

    assert await check_json() == (
        [
            issue(
                "view_transform_resolves",
                "error",
                "views.story_progress.transform",
                "view 'story_progress' (transform transforms/progress.py:story_progress): "
                "module has no attribute 'story_progress'",
            )
        ],
        3,
    )
