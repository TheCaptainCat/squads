"""`sq operator …`: registering people, listing them, and the addressed verbs (show, update,
status, remove, body and the comment listing)."""

import json
from typing import Any

import pytest

from tests import _tracker_harness as harness
from tests._profile import selected
from tests.cli import _source_checks as source_checks
from tests.cli import _source_connectors as source_connectors
from tests.cli._output import alice_document, entry_text, printed, read_json
from tests.cli._roster import (
    actors_of,
    body_of,
    raw_forms,
    usage_error,
)

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


@pytest.mark.covers("operator add", "name")
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
            "identities": {},
        }
    ]
    assert _roster_lines(project) == ["- **Alice Tester** (`op-alice`)"]


@pytest.mark.covers("operator add", "name")
async def test_add_refuses_a_slug_an_operator_already_has(project, invoke) -> None:
    await _add_alice(invoke)
    result = await invoke(["operator", "add", "Alice Tester"])
    assert (result.exit_code, result.output) == (
        1,
        "error: an operator with slug 'op-alice' already exists\n",
    )


@pytest.mark.covers("operator add", "name")
async def test_add_needs_a_name(project, invoke) -> None:
    result = await invoke(["operator", "add"])
    assert (result.exit_code, result.output) == (
        2,
        usage_error(
            "Usage: sq operator add [OPTIONS] {name}",
            "sq operator add --help",
            "Missing argument 'name'.",
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
            "identities": {},
        },
        {
            "id": "OP-3",
            "slug": "op-bob",
            "full_name": "Bob Builder",
            "pronouns": "he/him",
            "status": "Archived",
            "display": {"name": "Bob Builder (he/him)", "pronouns": "he/him"},
            "identities": {},
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
        "identities": {},
    }


@pytest.mark.covers("operator show", "--raw")
@pytest.mark.covers("operator show", "--no-header")
async def test_show_raw_lists_the_panel_rows_then_the_body_and_no_header_prints_the_body_alone(
    project, invoke, monkeypatch
) -> None:
    await _add_alice(invoke)
    body = (await _operator(invoke))["display"]["body"]
    rows, raw, bare = await raw_forms(invoke, monkeypatch, ["operator", "op-alice", "show"])
    assert raw == f"{rows}\n\n{body}\n"
    assert bare == body + "\n"
    assert "\x1b" not in raw


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
        "error: nothing to update (pass at least one of --title, --pronouns, --identities)\n",
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
            "identities": {},
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
            "identities": {},
        }
    )


SECRET = "glpat-not-a-real-token"


def _declare(project, profile, base_url: str, extra: str = "") -> None:
    """Declare the `platform` source on *base_url*, with the keys of *extra* in its table."""
    path = project.squad_dir / ".overrides" / "sources.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'[sources.platform]\nconnector = "gitlab"\nproject = "platform/api"\n'
        f'base_url = "{base_url}"\n{extra}'
        f'\n[sources.platform.maps.types.labels]\nbug = "{profile.ref}"\n',
        encoding="utf-8",
    )


async def _alice(invoke) -> object:
    return await read_json(invoke, ["operator", "op-alice", "show", "--json"])


@pytest.fixture
async def alice(invoke) -> None:
    result = await invoke(["operator", "add", "Alice Tester"])
    assert result.exit_code == 0, result.output


@pytest.mark.covers("operator update", "--identities")
async def test_resolving_a_handle_on_a_source_failing_access_stops_and_stores_nothing(
    project, invoke, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        await source_checks.declare(invoke, project, profile, tracker.base_url)
        assert (await invoke(["operator", "add", "Alice Tester"])).exit_code == 0
        source_checks.failing_token(tracker)
        stopped, asked = await source_checks.stopped(
            invoke, tracker, ["operator", "op-alice", "update", "--identities", "platform=@pchat"]
        )
        shown = await invoke(["operator", "op-alice", "show", "--json"])

    assert stopped == source_checks.TOKEN_REFUSED
    assert (json.loads(shown.output), asked) == (
        alice_document({}),
        ["/api/v4/version", "/api/v4/user"],
    )


@pytest.mark.covers("operator update", "--identities")
async def test_a_jira_cloud_handle_binds_only_on_an_exact_match_or_an_account_id(
    project, invoke, credentials_home, profile
) -> None:
    jira = source_connectors.jira(profile, "cloud-v3")
    pierre = "712020:0a1b2c3d-2222-4444-8888-bbbbbbbbbbbb"
    with harness.serve(harness.load_routes("jira-cloud/routes.json")) as tracker:
        await source_connectors.declare(
            invoke, project, jira.format(base=tracker.base_url), source_connectors.USER_FIELD
        )
        assert (await invoke(["operator", "add", "Alice Tester"])).exit_code == 0
        update = ["operator", "op-alice", "update", "--identities"]
        prefix = await invoke([*update, "platform=@Pierre"])
        exact = await invoke([*update, "platform=@Pierre Chat"])
        shown = await invoke(["operator", "op-alice", "show", "--json"])
        by_id = await invoke([*update, f"platform=@{pierre}"])

    assert (prefix.exit_code, prefix.output) == (
        1,
        "error: no one user has the display name or email 'Pierre' exactly; Jira found Pierre "
        f"Martin ({pierre}). Name the account as @<accountId>\n",
    )
    assert (exact.exit_code, by_id.exit_code) == (0, 0)
    assert json.loads(shown.output) == alice_document({"platform": pierre})


@pytest.mark.covers("operator update", "--identities")
async def test_identities_set_a_key_as_given_and_remove_it_with_an_empty_value(
    project, invoke, alice
) -> None:
    first = await invoke(["operator", "op-alice", "update", "--identities", "src=4567"])
    set_value = await _alice(invoke)
    second = await invoke(["operator", "op-alice", "update", "--identities", "src="])

    assert (first.exit_code, second.exit_code) == (0, 0)
    assert set_value == alice_document({"src": "4567"})
    assert await _alice(invoke) == alice_document({})


@pytest.mark.covers("operator update", "--identities")
async def test_identities_resolve_a_handle_to_the_trackers_immutable_user_id(
    project, invoke, alice, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _declare(project, profile, tracker.base_url)
        stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
        assert stored.exit_code == 0, stored.output
        result = await invoke(["operator", "op-alice", "update", "--identities", "platform=@pchat"])
        assert result.exit_code == 0, result.output
        assert await _alice(invoke) == alice_document({"platform": "4567"})

        missing = await invoke(
            ["operator", "op-alice", "update", "--identities", "platform=@nobody"]
        )
    assert (missing.exit_code, missing.output) == (
        1,
        "error: source 'platform' has no user '@nobody'\n",
    )
    assert await _alice(invoke) == alice_document({"platform": "4567"})


@pytest.mark.covers("operator update", "--identities")
async def test_a_handle_on_a_source_without_a_credential_is_refused_naming_the_remedy(
    project, invoke, alice, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _declare(project, profile, tracker.base_url)
        result = await invoke(["operator", "op-alice", "update", "--identities", "platform=@pchat"])
    assert (result.exit_code, result.output) == (
        1,
        "error: source 'platform' has no stored credential\n"
        "  fix: run `sq source credential set platform`\n",
    )
    assert await _alice(invoke) == alice_document({})
    assert tracker.requests == []


@pytest.mark.covers("operator update", "--identities")
async def test_a_handle_on_a_disabled_or_an_undeclared_source_is_refused(
    project, invoke, alice, credentials_home, profile
) -> None:
    with harness.serve(harness.load_routes("gitlab/routes.json")) as tracker:
        _declare(project, profile, tracker.base_url, "enabled = false\n")
        stored = await invoke(["source", "credential", "set", "platform"], input=f"{SECRET}\n")
        assert stored.exit_code == 0, stored.output
        disabled = await invoke(
            ["operator", "op-alice", "update", "--identities", "platform=@pchat"]
        )
        undeclared = await invoke(["operator", "op-alice", "update", "--identities", "x=@pchat"])
    assert (disabled.exit_code, disabled.output) == (
        1,
        "error: source 'platform' is disabled (`enabled = false` in its sources.toml table); "
        "enable it to fetch from it\n",
    )
    assert (undeclared.exit_code, undeclared.output) == (
        1,
        "error: no source 'x' is declared (declared: platform)\n",
    )
    assert tracker.requests == []


@pytest.mark.covers("operator update", "--identities")
async def test_a_pair_without_an_equals_sign_is_refused(project, invoke, alice) -> None:
    result = await invoke(["operator", "op-alice", "update", "--identities", "novalue"])
    assert (result.exit_code, result.output) == (
        1,
        "error: --identities expects key=value, got 'novalue'\n",
    )
