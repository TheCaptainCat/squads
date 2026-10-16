"""`sq workflow roles` carries the `blocked` flag as the sixth key and a Blocked column; `sq
workflow lint` refuses a non-boolean value; an override keeps or changes the flag per role; and
nothing outside the role catalog reads it (`sq blocked` and `sq tree` are computed from edges).
"""

import json

import pytest

from _helpers import create_item
from _selection_table import service_with, write_override

pytestmark = pytest.mark.anyio

_SIX_KEYS = ["role", "settled", "hidden", "color", "live", "blocked"]


async def _roles(invoke) -> list[dict[str, object]]:
    result = await invoke(["workflow", "roles", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


async def test_every_row_carries_the_six_keys_in_order_and_only_the_blocked_role_is_flagged(
    project, invoke
) -> None:
    rows = await _roles(invoke)
    assert len(rows) == 8
    assert all(list(row) == _SIX_KEYS for row in rows)
    assert {row["role"]: row["blocked"] for row in rows} == {
        "active": False,
        "attention": False,
        "blocked": True,
        "done": False,
        "in_force": False,
        "pending": False,
        "retired": False,
        "superseded": False,
    }


async def test_the_text_table_shows_the_column(project, invoke) -> None:
    result = await invoke(["workflow", "roles"])
    assert result.exit_code == 0, result.output
    header, *lines = result.output.splitlines()
    assert header.split()[-1] == "Blocked"
    blocked_line = next(line for line in lines if line.split()[0] == "blocked")
    assert blocked_line.split()[-1] == "yes"
    pending_line = next(line for line in lines if line.split()[0] == "pending")
    assert "yes" not in pending_line.split()


@pytest.mark.parametrize(
    ("override", "flagged"),
    [
        ('[roles.blocked]\ncolor = "warning"\n', {"blocked"}),
        ("[roles.blocked]\nblocked = false\n", set()),
        (
            '[roles.waiting]\nsettled = false\ncolor = "danger"\nblocked = true\n',
            {"blocked", "waiting"},
        ),
        ('[roles.waiting]\nsettled = false\ncolor = "danger"\n', {"blocked"}),
        ("", {"blocked"}),
    ],
    ids=["other-key-changed", "flag-cleared", "own-role-flagged", "own-role-unflagged", "none"],
)
async def test_an_override_keeps_changes_or_adds_the_flag_per_role(
    project, invoke, override: str, flagged: set[str]
) -> None:
    write_override(project.squad_dir, override)
    rows = await _roles(invoke)
    assert {row["role"] for row in rows if row["blocked"]} == flagged


async def test_a_project_declared_flagged_role_shows_in_both_outputs(project, invoke) -> None:
    write_override(
        project.squad_dir,
        '[roles.waiting]\nsettled = false\ncolor = "danger"\nblocked = true\n',
    )
    assert {r["role"] for r in await _roles(invoke) if r["blocked"]} == {"blocked", "waiting"}
    text = await invoke(["workflow", "roles"])
    waiting = next(line for line in text.output.splitlines() if line.split()[:1] == ["waiting"])
    assert waiting.split()[-1] == "yes"


@pytest.mark.parametrize(
    ("written", "exit_code"),
    [("true", 0), ("false", 0), ('"yes"', 1), ("1", 1), ("[true]", 1)],
)
async def test_lint_refuses_a_non_boolean_value_naming_the_role(
    project, invoke, written: str, exit_code: int
) -> None:
    write_override(project.squad_dir, f"[roles.blocked]\nblocked = {written}\n")
    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == exit_code, linted.output
    if exit_code:
        assert "blocked" in linted.output


async def test_an_override_that_predates_the_flag_loads_and_checks_as_before(
    project, invoke
) -> None:
    await create_item(service_with(project.squad_dir, ""), "task", "t")
    before = await invoke(["check", "--json"])
    write_override(project.squad_dir, '[roles.blocked]\ncolor = "warning"\n')
    assert (await invoke(["workflow", "lint"])).exit_code == 0
    after = await invoke(["check", "--json"])
    assert (after.exit_code, after.output) == (before.exit_code, before.output)


@pytest.mark.parametrize("override", ["", "[roles.blocked]\nblocked = false\n"], ids=["on", "off"])
async def test_the_blocked_listing_and_the_tree_do_not_read_the_flag(
    project, invoke, override: str
) -> None:
    svc = service_with(project.squad_dir, override)
    waiting = (await create_item(svc, "task", "waiting")).item
    blocker = (await create_item(svc, "task", "blocker")).item
    await svc.add_ref(waiting.id, blocker.id, kind="depends-on")
    await svc.update(waiting.id, status="Blocked", force=True)

    listed = await invoke(["blocked", "--json"])
    tree = await invoke(["tree", str(waiting.sequence_id), "--json"])
    assert (listed.exit_code, tree.exit_code) == (0, 0), (listed.output, tree.output)
    assert [row["id"] for row in json.loads(listed.output)] == [waiting.id]
    nodes = {node["id"]: node["blocked"] for node in json.loads(tree.output)}
    assert nodes[waiting.id] is True
