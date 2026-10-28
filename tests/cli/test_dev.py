"""`sq dev …`: adding developer roles for a technology and listing the live ones."""

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


@pytest.mark.covers("dev list")
async def test_list_says_there_are_no_developers_and_how_to_add_one(project, invoke) -> None:
    result = await invoke(["dev", "list"])
    assert (result.exit_code, result.output) == (
        0,
        "no developers (try `sq dev add --tech <t>`)\n",
    )


@pytest.mark.covers("dev list")
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


@pytest.mark.covers("dev list")
async def test_list_leaves_out_a_developer_that_was_archived(project, invoke) -> None:
    await invoke(["dev", "add", "--tech", "python"])
    await invoke(["role", "python-dev", "status", "Archived"])
    result = await invoke(["dev", "list"])
    assert (result.exit_code, result.output) == (
        0,
        "no developers (try `sq dev add --tech <t>`)\n",
    )
