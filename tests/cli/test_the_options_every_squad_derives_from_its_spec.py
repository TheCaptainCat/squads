"""The options a squad derives from its own declarations, and the verbs every squad has, run on
whichever squad the run is on: a field option on a sub-entity kind, the generic JSON of the
sub-entity verbs, the reference and discussion views of an item, and the squads skill.
"""

import json
from typing import Any

import pytest

from tests._populated import REVIEW, TASK
from tests._profile import selected

pytestmark = pytest.mark.anyio

P = selected()
FIELD_FLAG = f"--{P.third_field.replace('_', '-')}"
THIRD_ID = f"{P.third_prefix}-{REVIEW}"


async def _ran(invoke, args: list[str]) -> tuple[int, str]:
    result = await invoke(args)
    return result.exit_code, result.output


async def _ok(invoke, args: list[str]) -> str:
    code, output = await _ran(invoke, args)
    assert code == 0, output
    return output


async def _entry(invoke, local: int) -> dict[str, Any]:
    shown = await _ok(invoke, [P.third, str(REVIEW), P.third_kind, str(local), "show", "--json"])
    return json.loads(shown)


@pytest.mark.covers("<type> add-<kind>", "--<field>")
async def test_add_takes_the_kinds_field_and_stores_it(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [P.third, str(REVIEW), f"add-{P.third_kind}", "Dead branch", FIELD_FLAG, P.third_value],
    )
    assert out[0] == 0
    assert (await _entry(invoke, 3))["badges"][P.third_field].lower() == P.third_value.lower()


@pytest.mark.covers("<type> add-<kind>", "--<field>")
async def test_add_refuses_a_value_the_field_does_not_declare(populated_project, invoke) -> None:
    out = await _ran(
        invoke, [P.third, str(REVIEW), f"add-{P.third_kind}", "Dead branch", FIELD_FLAG, "Bad"]
    )
    assert out == (
        1,
        f"error: unknown {P.third_field} 'Bad' (one of: {P.third_codes})\n",
    )


@pytest.mark.covers("<type> <kind> update", "--<field>")
async def test_update_changes_the_kinds_field(populated_project, invoke) -> None:
    out = await _ran(
        invoke,
        [P.third, str(REVIEW), P.third_kind, "1", "update", FIELD_FLAG, P.third_other_value],
    )
    assert out == (0, f"updated {THIRD_ID} {P.third_kind_prefix}1\n")
    shown = (await _entry(invoke, 1))["badges"][P.third_field]
    assert shown.lower() == P.third_other_value.lower()


@pytest.mark.covers("<type> <kind> update", "--<field>")
async def test_update_refuses_a_value_the_field_does_not_declare(populated_project, invoke) -> None:
    out = await _ran(
        invoke, [P.third, str(REVIEW), P.third_kind, "1", "update", FIELD_FLAG, "bogus"]
    )
    assert out == (
        1,
        f"error: unknown {P.third_field} 'bogus' (one of: {P.third_codes})\n",
    )


@pytest.mark.covers("<type> add-<kind>", "--json")
async def test_add_json_prints_the_entry_that_was_added(populated_project, invoke) -> None:
    printed = json.loads(
        await _ok(invoke, [P.third, str(REVIEW), f"add-{P.third_kind}", "Dead branch", "--json"])
    )
    assert printed["local_id"] == f"{P.third_kind_prefix}3"


@pytest.mark.covers("<type> <kind> update", "--json")
async def test_update_json_prints_the_entry_after_the_update(populated_project, invoke) -> None:
    args = [P.third, str(REVIEW), P.third_kind, "1", "update", FIELD_FLAG, P.third_other_value]
    printed = json.loads(await _ok(invoke, [*args, "--json"]))
    assert printed["entry"]["local_id"] == f"{P.third_kind_prefix}1"


@pytest.mark.covers("<type> <kind> body", "--json")
async def test_body_json_prints_the_entry_after_the_write(populated_project, invoke) -> None:
    args = [P.third, str(REVIEW), P.third_kind, "1", "body", "-m", "Text", "--json"]
    printed = json.loads(await _ok(invoke, args))
    assert printed["entry"]["local_id"] == f"{P.third_kind_prefix}1"


@pytest.mark.covers("<type> refs", "--out", "--in", "--all")
async def test_refs_list_each_direction_an_item_is_linked(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "ref", "add", str(REVIEW)])

    out = json.loads(await _ok(invoke, [P.ref, str(TASK), "refs", "--out", "--json"]))
    back = json.loads(await _ok(invoke, [P.third, str(REVIEW), "refs", "--in", "--json"]))
    both = json.loads(await _ok(invoke, [P.ref, str(TASK), "refs", "--all", "--json"]))

    assert [r["id"] for r in out["out"]] == [THIRD_ID]
    assert [r["id"] for r in back["in"]] == [f"{P.ref_prefix}-{TASK}"]
    assert set(both) == {"out", "in"}


@pytest.mark.covers("<type> show", "--full", "--comments")
async def test_show_adds_the_sub_entities_and_the_discussion_on_request(
    populated_project, invoke
) -> None:
    await _ok(invoke, [P.ref, str(TASK), "comment", "--as", "manager", "-m", "Looks good"])

    full = await _ok(invoke, [P.ref, str(TASK), "show", "--full"])
    discussed = await _ok(invoke, [P.ref, str(TASK), "show", "--comments"])

    assert f"{P.kind_prefix}1 " in full
    assert "Looks good" in discussed


@pytest.mark.covers("show", "--full", "--comments", "--raw")
async def test_the_bare_show_takes_the_same_views(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "comment", "--as", "manager", "-m", "Looks good"])

    full = await _ok(invoke, ["show", str(TASK), "--full"])
    discussed = await _ok(invoke, ["show", str(TASK), "--comments"])
    raw = await _ok(invoke, ["show", str(TASK), "--raw"])

    assert (
        f"{P.kind_prefix}1 " in full,
        "Looks good" in discussed,
        f"{P.ref_prefix}-3" in raw,
    ) == (
        True,
        True,
        True,
    )


@pytest.mark.covers("create <type>", "--json")
async def test_create_json_prints_the_created_item(populated_project, invoke) -> None:
    args = ["create", P.ref, "Loose end", "--author", "manager", *P.parent_args(P.ref), "--json"]
    printed = json.loads(await _ok(invoke, args))
    assert printed["type"] == P.ref


@pytest.mark.covers("operator show", "--raw", "--comments")
async def test_an_operator_shows_raw_and_with_its_discussion(populated_project, invoke) -> None:
    await _ok(invoke, ["operator", "add", "Alice Tester"])
    await _ok(invoke, ["operator", "op-alice", "comment", "--as", "manager", "-m", "Welcome."])

    raw = await _ok(invoke, ["operator", "op-alice", "show", "--raw"])
    discussed = await _ok(invoke, ["operator", "op-alice", "show", "--comments"])

    assert raw == await _ok(invoke, ["operator", "op-alice", "show"])
    assert "Welcome." in discussed


@pytest.mark.covers("skill show")
async def test_the_squads_skill_shows(seeded_project, invoke) -> None:
    shown = await _ok(invoke, ["skill", "squads", "show"])
    assert f"sq {P.ref} " in shown
