"""`sq operator …`: registering people, listing them, and the addressed verbs (show, update,
status, remove, body and the comment listing)."""

from typing import Any

import pytest

from tests._profile import selected
from tests.cli._output import entry_text, printed, read_json
from tests.cli._roster import actors_of, body_of, forced_terminal, usage_error

P = selected()

pytestmark = pytest.mark.anyio

NAME_PROBLEM = (
    "error: operator slug '{slug}' must start with 'op-' and be lowercase letters, digits and "
    "hyphens (e.g. '{hint}')\n"
)


async def _add_alice(invoke, *extra: str) -> None:
    result = await invoke(["operator", "add", "Alice Tester", *extra])
    assert result.exit_code == 0, result.output


async def _operator(invoke, address: str = "op-alice") -> dict[str, Any]:
    return await read_json(invoke, ["operator", address, "show", "--json"])


def _roster_lines(project) -> list[str]:
    """The operator lines of the managed CLAUDE.md section."""
    text = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    return [line for line in text.splitlines() if line.startswith("- **") and "(`op-" in line]


# ------------------------------------------------------------------------------------- add


@pytest.mark.covers("operator add", "NAME")
async def test_add_registers_a_person_under_a_slug_made_from_the_first_name(
    project, invoke
) -> None:
    result = await invoke(["operator", "add", "Alice Tester"])
    assert (result.exit_code, result.output) == (0, "registered Alice Tester (`op-alice`) OP-2\n")
    assert await read_json(invoke, ["operator", "list", "--json"]) == [
        {
            "id": "OP-2",
            "slug": "op-alice",
            "full_name": "Alice Tester",
            "pronouns": None,
            "status": "Active",
            "display": {"name": "Alice Tester", "pronouns": None},
        }
    ]
    assert _roster_lines(project) == ["- **Alice Tester** (`op-alice`)"]


@pytest.mark.covers("operator add", "NAME")
async def test_add_refuses_a_slug_an_operator_already_has(project, invoke) -> None:
    await _add_alice(invoke)
    result = await invoke(["operator", "add", "Alice Tester"])
    assert (result.exit_code, result.output) == (
        1,
        "error: an operator with slug 'op-alice' already exists\n",
    )


@pytest.mark.covers("operator add", "NAME")
async def test_add_needs_a_name(project, invoke) -> None:
    result = await invoke(["operator", "add"])
    assert (result.exit_code, result.output) == (
        2,
        usage_error(
            "Usage: sq operator add [OPTIONS] NAME",
            "sq operator add --help",
            "Missing argument 'NAME'.",
        ),
    )


@pytest.mark.covers("operator add", "--slug")
async def test_add_slug_files_the_operator_under_the_given_slug(project, invoke) -> None:
    result = await invoke(["operator", "add", "Alice Tester", "--slug", "op-at"])
    assert (result.exit_code, result.output) == (0, "registered Alice Tester (`op-at`) OP-2\n")
    assert (await _operator(invoke, "op-at"))["full_name"] == "Alice Tester"


@pytest.mark.covers("operator add", "--slug")
async def test_add_slug_refuses_a_slug_that_is_not_op_prefixed_lowercase(project, invoke) -> None:
    result = await invoke(["operator", "add", "Alice Tester", "--slug", "Alice_T"])
    assert (result.exit_code, result.output) == (
        1,
        NAME_PROBLEM.format(slug="Alice_T", hint="op-alice-t"),
    )


@pytest.mark.covers("operator add", "--pronouns")
async def test_add_pronouns_are_stored_and_shown_beside_the_name(project, invoke) -> None:
    result = await invoke(["operator", "add", "Alice Tester", "--pronouns", "she/her"])
    assert (result.exit_code, result.output) == (
        0,
        "registered Alice Tester (she/her) (`op-alice`) OP-2\n",
    )
    assert (await _operator(invoke))["pronouns"] == "she/her"


@pytest.mark.covers("operator add", "--as")
async def test_add_as_attributes_the_registration_to_the_actor(project, invoke) -> None:
    await _add_alice(invoke, "--as", "manager")
    assert await actors_of(invoke, "OP-2", "create") == ["manager"]


@pytest.mark.covers("operator add", "--as")
async def test_add_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    result = await invoke(["operator", "add", "Alice Tester", "--as", "nobody"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager\n",
    )


# ------------------------------------------------------------------------------------ list


@pytest.mark.covers("operator list", "--json")
async def test_list_json_describes_each_operator_with_its_status(project, invoke) -> None:
    assert await read_json(invoke, ["operator", "list", "--json"]) == []
    await _add_alice(invoke)
    await invoke(["operator", "add", "Bob Builder", "--pronouns", "he/him"])
    await invoke(["operator", "op-bob", "status", "Archived"])
    assert await read_json(invoke, ["operator", "list", "--json"]) == [
        {
            "id": "OP-2",
            "slug": "op-alice",
            "full_name": "Alice Tester",
            "pronouns": None,
            "status": "Active",
            "display": {"name": "Alice Tester", "pronouns": None},
        },
        {
            "id": "OP-3",
            "slug": "op-bob",
            "full_name": "Bob Builder",
            "pronouns": "he/him",
            "status": "Archived",
            "display": {"name": "Bob Builder (he/him)", "pronouns": "he/him"},
        },
    ]


# --------------------------------------------------------------------------------- address


@pytest.mark.covers("operator", "<slug|id|n>")
async def test_address_resolves_a_slug_an_id_and_a_number_to_the_same_operator(
    project, invoke
) -> None:
    await _add_alice(invoke)
    by_slug = await _operator(invoke, "op-alice")
    assert by_slug["id"] == "OP-2"
    assert await _operator(invoke, "OP-2") == by_slug
    assert await _operator(invoke, "2") == by_slug


@pytest.mark.covers("operator", "<slug|id|n>")
async def test_address_refuses_a_slug_no_operator_has(project, invoke) -> None:
    result = await invoke(["operator", "op-nobody", "show"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no operator with slug, ID, or number 'op-nobody'\n",
    )


@pytest.mark.covers("operator", "<slug|id|n>")
async def test_address_refuses_the_number_of_an_item_that_is_not_an_operator(
    populated_project, invoke
) -> None:
    result = await invoke(["operator", "3", "show"])
    assert (result.exit_code, result.output) == (
        1,
        f"error: 3 is {P.ref_prefix}-3 ({P.ref}), not of type operator\n",
    )


# ------------------------------------------------------------------------------------ show


PANEL = (
    "╭───────────────────────────────────────╮\n"
    "│ Alice Tester                          │\n"
    "│ slug: op-alice                        │\n"
    "│ id: OP-2                              │\n"
    "│ status: Active                        │\n"
    "│ file: operators/OP-000002-op-alice.md │\n"
    "╰───────────────────────────────────────╯\n"
)
PROFILE = (
    "\n# Alice Tester\n\n**Operator (human)**  ·  **Slug:** `op-alice`\n\n"
    f"A human who works on this project — authors items and {P.third} points, and can be \n"
    "assigned work (including manual steps).\n\n"
    'Attribute their words with `sq <type> <n> comment --as op-alice -m "…"`,\n'
    "correct or withdraw their comment with `comment <hash> edit|remove --as \n"
    "op-alice`,\n"
    "and assign work to them with `--assignee op-alice`.\n"
)


@pytest.mark.covers("operator show", "--json")
@pytest.mark.bundled_only("the operator text names the bundled review points")
async def test_show_json_describes_the_operator(project, invoke) -> None:
    await _add_alice(invoke, "--pronouns", "she/her")
    assert await _operator(invoke) == {
        "id": "OP-2",
        "slug": "op-alice",
        "full_name": "Alice Tester",
        "pronouns": "she/her",
        "status": "Active",
        "path": "operators/OP-000002-op-alice.md",
        "display": {
            "name": "Alice Tester (she/her)",
            "pronouns": "she/her",
            "body": (
                "# Alice Tester\n\n**Operator (human)**  ·  **Slug:** `op-alice`\n\nA human who "
                f"works on this project — authors items and {P.third} points, and can be assigned "
                "work (including manual steps).\n\nAttribute their words with `sq <type> <n> "
                'comment --as op-alice -m "…"`,\ncorrect or withdraw their comment with `comment '
                "<hash> edit|remove --as op-alice`,\nand assign work to them with `--assignee "
                "op-alice`."
            ),
            "discussion": [],
        },
    }


@pytest.mark.covers("operator show", "--raw")
@pytest.mark.bundled_only("the operator text names the bundled review points")
async def test_show_raw_prints_the_body_unrendered_where_a_terminal_would_render_it(
    project, invoke, monkeypatch
) -> None:
    await _add_alice(invoke)
    piped = await invoke(["operator", "op-alice", "show"])
    assert (piped.exit_code, piped.output) == (0, PANEL + PROFILE)
    forced_terminal(monkeypatch)
    raw = await invoke(["operator", "op-alice", "show", "--raw"])
    rendered = await invoke(["operator", "op-alice", "show"])
    assert (raw.exit_code, raw.output) == (0, piped.output)
    assert rendered.output != piped.output


@pytest.mark.covers("operator show", "--comments")
@pytest.mark.bundled_only("the operator text names the bundled review points")
async def test_show_comments_appends_the_discussion(project, invoke) -> None:
    await _add_alice(invoke)
    await invoke(["operator", "op-alice", "comment", "-m", "Welcome.", "--as", "manager"])
    listed = (await read_json(invoke, ["operator", "op-alice", "comments", "--json"]))[0]
    result = await invoke(["operator", "op-alice", "show", "--comments"])
    assert (result.exit_code, result.output) == (
        0,
        PANEL
        + PROFILE
        + f"--- {listed['short_hash']} [{listed['ts']}] Catherine Manager (manager) ---\n"
        "- Welcome.\n\n",
    )


@pytest.mark.covers("operator show", "--json")
async def test_show_refuses_an_unknown_operator(project, invoke) -> None:
    result = await invoke(["operator", "op-nobody", "show", "--json"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no operator with slug, ID, or number 'op-nobody'\n",
    )


# ---------------------------------------------------------------------------------- update


@pytest.mark.covers("operator update", "--title")
async def test_update_title_renames_the_operator_and_the_managed_roster(project, invoke) -> None:
    await _add_alice(invoke)
    result = await invoke(["operator", "op-alice", "update", "--title", "Alice T"])
    assert (result.exit_code, result.output) == (0, "updated OP-2\n")
    assert (await _operator(invoke))["full_name"] == "Alice T"
    assert _roster_lines(project) == ["- **Alice T** (`op-alice`)"]


@pytest.mark.covers("operator update", "--pronouns")
async def test_update_pronouns_sets_them_and_a_blank_value_clears_them(project, invoke) -> None:
    await _add_alice(invoke)
    await invoke(["operator", "op-alice", "update", "--pronouns", "she/her"])
    assert (await _operator(invoke))["pronouns"] == "she/her"
    await invoke(["operator", "op-alice", "update", "--pronouns", ""])
    assert (await _operator(invoke))["pronouns"] is None


@pytest.mark.covers("operator update")
async def test_update_needs_a_field_to_change(project, invoke) -> None:
    await _add_alice(invoke)
    result = await invoke(["operator", "op-alice", "update"])
    assert (result.exit_code, result.output) == (
        1,
        "error: nothing to update (pass at least one of --title, --pronouns)\n",
    )


@pytest.mark.covers("operator update", "--as")
async def test_update_as_attributes_the_edit_to_the_actor(project, invoke) -> None:
    await _add_alice(invoke)
    await invoke(["operator", "op-alice", "update", "--title", "Alice T", "--as", "manager"])
    assert await actors_of(invoke, "OP-2", "update") == ["manager"]


@pytest.mark.covers("operator update", "--as")
async def test_update_as_refuses_a_slug_that_is_not_registered(project, invoke) -> None:
    await _add_alice(invoke)
    result = await invoke(
        ["operator", "op-alice", "update", "--title", "Alice T", "--as", "nobody"]
    )
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown slug 'nobody'; valid slugs: manager, op-alice\n",
    )


# ------------------------------------------------------------------------------------ body


# ---------------------------------------------------------------------------------- status


# ---------------------------------------------------------------------------------- remove


@pytest.mark.covers("role remove", "--purge")
async def test_remove_purge_deletes_the_operator_and_drops_them_from_the_roster(
    project, invoke
) -> None:
    await _add_alice(invoke)
    result = await invoke(["operator", "op-alice", "remove", "--purge"])
    assert (result.exit_code, result.output) == (0, "removed OP-2\n")
    assert await read_json(invoke, ["operator", "list", "--json"]) == []
    assert _roster_lines(project) == []


# ------------------------------------------------------------------------------- comments


@pytest.mark.covers("operator", "<slug|id|n>")
async def test_comments_refuses_an_unknown_operator(project, invoke) -> None:
    result = await invoke(["operator", "op-nobody", "comments", "--json"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no operator with slug, ID, or number 'op-nobody'\n",
    )


# --------------------------------------------------------------------- shared verbs' address


@pytest.mark.covers("operator", "<slug|id|n>")
async def test_body_status_and_remove_act_on_the_operator_they_address(project, invoke) -> None:
    """The shared roster verbs resolve the address of an operator, never another roster entry."""
    await _add_alice(invoke)
    body = await invoke(["operator", "op-alice", "body", "-m", "Likes tea."])
    assert (body.exit_code, body.output) == (0, "OP-2: body set\n")
    assert await body_of(invoke, 2) == "Likes tea."
    assert await body_of(invoke, 1) != "Likes tea."
    moved = await invoke(["operator", "op-alice", "status", "Archived"])
    assert (moved.exit_code, moved.output) == (0, "OP-2 → Archived\n")
    assert (await _operator(invoke))["status"] == "Archived"
    roles = await read_json(invoke, ["role", "list", "--json"])
    assert [r["status"] for r in roles] == ["Active"]
    removed = await invoke(["operator", "op-alice", "remove", "--purge"])
    assert (removed.exit_code, removed.output) == (0, "removed OP-2\n")
    assert [r["slug"] for r in await read_json(invoke, ["role", "list", "--json"])] == ["manager"]


# ---------------------------------------------------------------------------- JSON of the writes


@pytest.mark.covers("operator add", "--json")
async def test_add_json_prints_the_operator_it_registered(project, invoke) -> None:
    output = await printed(
        invoke, ["operator", "add", "Alice Tester", "--pronouns", "she/her", "--json"]
    )
    assert output == entry_text(
        {
            "id": "OP-2",
            "slug": "op-alice",
            "full_name": "Alice Tester",
            "pronouns": "she/her",
            "status": "Active",
            "display": {"name": "Alice Tester (she/her)", "pronouns": "she/her"},
        }
    )


@pytest.mark.covers("operator update", "--json")
async def test_update_json_prints_the_operator_after_the_update(project, invoke) -> None:
    await _add_alice(invoke)
    output = await printed(
        invoke, ["operator", "op-alice", "update", "--title", "Alice T", "--json"]
    )
    assert output == entry_text(
        {
            "id": "OP-2",
            "slug": "op-alice",
            "full_name": "Alice T",
            "pronouns": None,
            "status": "Active",
            "display": {"name": "Alice T", "pronouns": None},
        }
    )
