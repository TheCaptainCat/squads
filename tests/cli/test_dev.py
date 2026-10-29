"""`sq dev …`: adding developer roles for a technology and listing the live ones."""

import json
from typing import Any

import pytest

from tests.cli._roster import actors_of, read_json

pytestmark = pytest.mark.anyio


async def _role(invoke, slug: str) -> dict[str, Any]:
    return await read_json(invoke, ["role", slug, "show", "--json"])


def _lines(output: str) -> list[str]:
    """The output's lines without the padding a table puts after its last column."""
    return [line.rstrip() for line in output.splitlines()]


# ------------------------------------------------------------------------------------- add


@pytest.mark.covers("dev add", "--tech")
async def test_add_tech_builds_a_developer_role_named_for_the_technology(project, invoke) -> None:
    result = await invoke(["dev", "add", "--tech", "python"])
    assert (result.exit_code, result.output) == (0, "added Elias Python (`python-dev`) ROLE-2\n")
    shown = await _role(invoke, "python-dev")
    assert (shown["id"], shown["full_name"], shown["title"], shown["capabilities"]) == (
        "ROLE-2",
        "Elias Python",
        "Python developer",
        ["dev"],
    )
    pointer = (project.root / ".claude" / "agents" / "python-dev.md").read_text(encoding="utf-8")
    assert "You are **Elias Python**, the Python developer on this project." in pointer.splitlines()


async def test_add_needs_a_technology(project, invoke) -> None:
    result = await invoke(["dev", "add"])
    assert (result.exit_code, result.output) == (
        1,
        "error: role template 'dev' takes a technology: pass --tech\n",
    )


@pytest.mark.covers("dev add", "--tech")
async def test_add_refuses_a_technology_whose_developer_role_already_exists(
    project, invoke
) -> None:
    await invoke(["dev", "add", "--tech", "python"])
    result = await invoke(["dev", "add", "--tech", "python"])
    assert (result.exit_code, result.output) == (
        1,
        "error: a role with slug 'python-dev' already exists\n",
    )


@pytest.mark.covers("dev add", "--name")
async def test_add_name_replaces_the_name_picked_from_the_templates_pool(project, invoke) -> None:
    result = await invoke(["dev", "add", "--tech", "go", "--name", "Gus Go"])
    assert (result.exit_code, result.output) == (0, "added Gus Go (`go-dev`) ROLE-2\n")
    assert (await _role(invoke, "go-dev"))["full_name"] == "Gus Go"


@pytest.mark.covers("dev add", "--slug")
async def test_add_slug_files_the_role_under_the_given_slug(project, invoke) -> None:
    result = await invoke(["dev", "add", "--tech", "go", "--slug", "gopher"])
    assert result.exit_code == 0, result.output
    assert (await _role(invoke, "gopher"))["id"] == "ROLE-2"


@pytest.mark.covers("dev add", "--slug")
async def test_add_slug_refuses_a_slug_a_role_already_has(project, invoke) -> None:
    await invoke(["dev", "add", "--tech", "go", "--slug", "gopher"])
    result = await invoke(["dev", "add", "--tech", "rust", "--slug", "gopher"])
    assert (result.exit_code, result.output) == (
        1,
        "error: a role with slug 'gopher' already exists\n",
    )


@pytest.mark.covers("dev add", "--slug")
async def test_add_slug_refuses_a_slug_the_catalog_declares(project, invoke) -> None:
    result = await invoke(["dev", "add", "--tech", "go", "--slug", "architect"])
    assert (result.exit_code, result.output) == (
        1,
        "error: slug 'architect' belongs to a role the catalog declares; `sq role activate "
        "architect` activates it, or pick another slug\n",
    )


@pytest.mark.covers("dev add", "--model")
async def test_add_model_is_stored_on_the_role_and_written_to_its_pointer(project, invoke) -> None:
    await invoke(["dev", "add", "--tech", "go", "--model", "haiku"])
    assert (await _role(invoke, "go-dev"))["model"] == "haiku"
    assert "model: haiku\n" in (project.root / ".claude/agents/go-dev.md").read_text(
        encoding="utf-8"
    )


@pytest.mark.covers("dev add", "--pronouns")
async def test_add_pronouns_are_stored_and_shown_beside_the_name(project, invoke) -> None:
    result = await invoke(["dev", "add", "--tech", "python", "--pronouns", "he/him"])
    assert (result.exit_code, result.output) == (
        0,
        "added Elias Python (he/him) (`python-dev`) ROLE-2\n",
    )
    assert (await _role(invoke, "python-dev"))["pronouns"] == "he/him"


@pytest.mark.covers("dev add", "--as")
async def test_add_as_attributes_the_creation_to_the_actor(project, invoke) -> None:
    await invoke(["dev", "add", "--tech", "python", "--as", "manager"])
    assert await actors_of(invoke, "ROLE-2", "create") == ["manager"]


@pytest.mark.covers("dev add", "--as")
async def test_add_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(["dev", "add", "--tech", "python", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


# ------------------------------------------------------------------------------------ list


async def test_list_says_there_are_no_developers_and_how_to_add_one(project, invoke) -> None:
    result = await invoke(["dev", "list"])
    assert (result.exit_code, result.output) == (
        0,
        "no developers (try `sq dev add --tech <t>`)\n",
    )


async def test_list_shows_each_live_developer_and_leaves_other_roles_out(project, invoke) -> None:
    await invoke(["dev", "add", "--tech", "python"])
    await invoke(["dev", "add", "--tech", "go", "--name", "Gus Go", "--pronouns", "he/him"])
    await invoke(["role", "activate", "architect"])
    result = await invoke(["dev", "list"])
    assert (result.exit_code, _lines(result.output)) == (
        0,
        [
            "ID      Slug        Name             Tech",
            "ROLE-2  python-dev  Elias Python     python",
            "ROLE-3  go-dev      Gus Go (he/him)  go",
        ],
    )


async def test_list_leaves_out_a_developer_that_was_archived(project, invoke) -> None:
    await invoke(["dev", "add", "--tech", "python"])
    await invoke(["role", "python-dev", "status", "Archived"])
    result = await invoke(["dev", "list"])
    assert (result.exit_code, result.output) == (
        0,
        "no developers (try `sq dev add --tech <t>`)\n",
    )


# ------------------------------------------------------------------------------------- JSON


async def _printed(invoke, args: list[str]) -> str:
    """What a command that succeeds prints, compared as text so the key order is held too."""
    result = await invoke(args)
    assert result.exit_code == 0, result.output
    return result.output


def _text(document: object) -> str:
    return json.dumps(document, indent=2) + "\n"


def _entry(row: object) -> str:
    """A write that reports nothing beside its entry: the entry under `entry`."""
    return _text({"entry": row})


@pytest.mark.covers("dev add", "--json")
async def test_add_json_prints_the_developer_role_it_added(project, invoke) -> None:
    printed = await _printed(invoke, ["dev", "add", "--tech", "python", "--json"])
    assert printed == _entry(
        {
            "id": "ROLE-2",
            "slug": "python-dev",
            "full_name": "Elias Python",
            "pronouns": None,
            "title": "Python developer",
            "description": "Implements Python code following the project's guides and standards.",
            "is_default": False,
            "capabilities": ["dev"],
            "status": "Active",
            "origin": "system",
            "display": {"name": "Elias Python", "pronouns": None, "live": True},
        }
    )


@pytest.mark.covers("dev list", "--json")
async def test_list_json_prints_the_developers_the_columns_and_the_template(
    project, invoke
) -> None:
    """The name drops the pronouns once `[display] pronouns` is off; the field keeps them."""
    await invoke(["dev", "add", "--tech", "python", "--pronouns", "he/him"])

    def listing(display: dict[str, Any]) -> str:
        return _text(
            {
                "items": [
                    {
                        "id": "ROLE-2",
                        "slug": "python-dev",
                        "full_name": "Elias Python",
                        "pronouns": "he/him",
                        "tech": "python",
                        "display": display,
                    }
                ],
                "columns": [
                    {"key": "id", "header": "ID"},
                    {"key": "slug", "header": "Slug"},
                    {"key": "display.name", "header": "Name"},
                    {"key": "tech", "header": "Tech"},
                ],
                "template_available": True,
            }
        )

    printed = await _printed(invoke, ["dev", "list", "--json"])
    assert printed == listing({"name": "Elias Python (he/him)", "pronouns": "he/him"})
    config = project.root / ".squads.toml"
    config.write_text(
        config.read_text(encoding="utf-8") + "\n[display]\npronouns = false\n", encoding="utf-8"
    )
    printed = await _printed(invoke, ["dev", "list", "--json"])
    assert printed == listing({"name": "Elias Python", "pronouns": None})
