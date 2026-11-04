"""The `sq check` rules over items a tracker feeds: duplicate holders of one issue, a source that is
undeclared, disabled or unreadable, an issue the pull lost, operator identities and comment
attribute lines. None can be selected or deselected, so each has a breach case only.

A sourced item is arranged by editing the file of an item the CLI created, since only a pull writes
the record.
"""

import re

import pytest

from tests.check._arrange import (
    activate,
    add_roster,
    address,
    create,
    edit_item_file,
    issue,
    ok,
    repair,
    write_override,
)

pytestmark = pytest.mark.anyio

SOURCES = (
    '[sources.platform]\nconnector = "gitlab"\nfilter = "squads"\n'
    'base_url = "https://tracker.example"\n\n[sources.platform.maps.types.type]\nissue = "task"\n'
)


def _record(name: str, issue_id: str, state: str) -> str:
    return (
        f"source:\n  name: '{name}'\n  id: '{issue_id}'\n  key: 'platform/api#{issue_id}'\n"
        f"  state: '{state}'\n  updated_at: '2026-11-03T20:41:07Z'\n  author_id: '4567'\n"
        "  author_handle: 'pchat'\n"
    )


async def _mirror(
    invoke,
    project,
    title: str,
    *,
    name: str = "platform",
    issue_id: str = "12",
    state: str = "open",
) -> str:
    """A task whose file holds a source record for issue *issue_id* of source *name*."""
    task = await create(invoke, "task", title, "tech-lead", desc="d")
    edit_item_file(project, task, "\nstatus:", f"\n{_record(name, issue_id, state)}status:")
    await repair(invoke)
    return task


@pytest.fixture
async def squad(project, invoke):
    """The `minimal` squad with `tech-lead` live and the `platform` source declared."""
    await activate(invoke, "tech-lead")
    write_override(project, "sources.toml", SOURCES)
    return project


@pytest.mark.breaches("source_id_unique")
async def test_two_items_that_hold_one_issue_are_an_error(squad, invoke, check_json) -> None:
    first = await _mirror(invoke, squad, "First")
    assert await check_json() == ([], 0)

    second = await _mirror(invoke, squad, "Second")

    assert await check_json() == (
        [
            issue(
                "source_id_unique",
                "error",
                first,
                f"{first}, {second} all hold issue platform/api#12 of source 'platform'; "
                "the pull refreshes each, so keep one and run `source unlink` on the others",
            )
        ],
        3,
    )


@pytest.mark.breaches("source_declared")
async def test_an_item_whose_source_is_disabled_or_undeclared_is_a_warning(
    squad, invoke, check_json
) -> None:
    task = await _mirror(invoke, squad, "Mirror")
    assert await check_json() == ([], 0)

    write_override(squad, "sources.toml", SOURCES.replace("filter", "enabled = false\nfilter"))
    disabled = await check_json()
    write_override(squad, "sources.toml", SOURCES.replace("platform", "other"))
    undeclared = await check_json()

    assert (disabled, undeclared) == (
        (
            [
                issue(
                    "source_declared",
                    "warn",
                    task,
                    "source 'platform' is disabled (enabled = false); no pull refreshes "
                    "platform/api#12",
                )
            ],
            0,
        ),
        (
            [
                issue(
                    "source_declared",
                    "warn",
                    task,
                    "source 'platform' is not declared in sources.toml; no pull refreshes "
                    "platform/api#12",
                )
            ],
            0,
        ),
    )


@pytest.mark.breaches("source_issue_reachable")
async def test_an_item_whose_issue_the_pull_lost_is_a_warning(squad, invoke, check_json) -> None:
    kept = await _mirror(invoke, squad, "Kept", issue_id="12")
    assert await check_json() == ([], 0)

    gone = await _mirror(invoke, squad, "Gone", issue_id="13", state="gone")
    moved = await _mirror(invoke, squad, "Moved", issue_id="14", state="out-of-filter")

    assert kept not in {i["item"] for i in (await check_json())[0]}
    assert await check_json() == (
        [
            issue(
                "source_issue_reachable",
                "warn",
                gone,
                "the tracker no longer answers for platform/api#13 (gone); keep the item, or "
                f"run `sq {' '.join(address(gone))} source unlink`",
            ),
            issue(
                "source_issue_reachable",
                "warn",
                moved,
                "the tracker no longer lists platform/api#14 (out-of-filter); keep the item, or "
                f"run `sq {' '.join(address(moved))} source unlink`",
            ),
        ],
        0,
    )


@pytest.mark.breaches("sources_loads")
async def test_a_sources_document_that_does_not_load_is_an_error(squad, invoke, check_json) -> None:
    await _mirror(invoke, squad, "Mirror")
    assert await check_json() == ([], 0)

    write_override(squad, "sources.toml", SOURCES.replace('"task"', '"nowhere"'))

    path = squad.squad_dir / ".overrides" / "sources.toml"
    assert await check_json() == (
        [
            issue(
                "sources_loads",
                "error",
                "sources",
                f"sources config invalid: {path}: invalid sources after merge: source "
                "'platform': maps.types.type: 'issue' -> 'nowhere' is not an item type",
            )
        ],
        3,
    )


@pytest.mark.breaches("source_author_declared")
async def test_an_author_naming_no_declared_source_is_a_warning(squad, invoke, check_json) -> None:
    task = await create(invoke, "task", "Mirror", "tech-lead", desc="d")
    await ok(invoke, *address(task), "comment", "--as", "tech-lead", "-m", "Noted.")
    assert await check_json() == ([], 0)

    edit_item_file(squad, task, "author: tech-lead", "author: source:phantom")
    edit_item_file(squad, task, "] `tech-lead` ", "] `source:ghost` ")
    await repair(invoke)

    assert await check_json() == (
        [
            issue(
                "source_author_declared",
                "warn",
                task,
                f"an author `source:{name}` names no source declared in sources.toml",
            )
            for name in ("ghost", "phantom")
        ],
        0,
    )


@pytest.fixture
async def operators(invoke) -> tuple[str, str]:
    """Two operators, `op-alice` and `op-bob`, and the ids their rows carry."""
    return (
        await add_roster(invoke, "operator", "Alice Tester"),
        await add_roster(invoke, "operator", "Bob Tester"),
    )


@pytest.mark.breaches("identity_source_declared")
async def test_an_identity_naming_no_declared_source_is_a_warning(
    squad, invoke, check_json, operators
) -> None:
    alice, _bob = operators
    await ok(invoke, "operator", "op-alice", "update", "--identities", "platform=4567")
    assert await check_json() == ([], 0)

    await ok(invoke, "operator", "op-alice", "update", "--identities", "ghost=4567")

    assert await check_json() == (
        [
            issue(
                "identity_source_declared",
                "warn",
                alice,
                "identity 'ghost' names no source declared in sources.toml",
            )
        ],
        0,
    )


@pytest.mark.breaches("identity_id_unique")
async def test_two_operators_holding_one_tracker_user_are_an_error(
    squad, invoke, check_json, operators
) -> None:
    alice, _bob = operators
    await ok(invoke, "operator", "op-alice", "update", "--identities", "platform=4567")
    await ok(invoke, "operator", "op-bob", "update", "--identities", "platform=4568")
    assert await check_json() == ([], 0)

    await ok(invoke, "operator", "op-bob", "update", "--identities", "platform=4567")

    assert await check_json() == (
        [
            issue(
                "identity_id_unique",
                "error",
                alice,
                "operators op-alice, op-bob all hold user '4567' of source 'platform'; "
                "a tracker user is one operator",
            )
        ],
        3,
    )


@pytest.mark.breaches("comment_attributes_valid")
async def test_a_comment_whose_attribute_line_is_not_a_json_object_of_strings_is_an_error(
    squad, invoke, check_json
) -> None:
    task = await create(invoke, "task", "Mirror", "tech-lead", desc="d")
    await ok(invoke, *address(task), "comment", "--as", "tech-lead", "-m", "Noted.")
    assert await check_json() == ([], 0)

    edit_item_file(squad, task, ":\n  - Noted.", ':\n  <!-- sq:attrs {"n":1} -->\n  - Noted.')

    found, code = await check_json()
    assert (code, len(found), found[0]["rule"], found[0]["level"], found[0]["item"]) == (
        3,
        1,
        "comment_attributes_valid",
        "error",
        task,
    )
    assert re.fullmatch(
        r"the comment by `tech-lead` at \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ has an sq:attrs line "
        r"that is not one JSON object of strings; it reads as comment text",
        found[0]["message"],
    )
