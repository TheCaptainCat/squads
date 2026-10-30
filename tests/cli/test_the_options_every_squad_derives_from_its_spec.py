"""The options a squad derives from its own declarations, and the verbs every squad has, run on
whichever squad the run is on: a field option on a sub-entity kind, the generic JSON of the
sub-entity verbs, the reference and discussion views of an item, and the squads skill.
"""

import json
from typing import Any

import pytest

from tests._populated import REVIEW, TASK
from tests._profile import selected
from tests.cli._roster import forced_terminal

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
async def test_add_json_prints_where_the_body_region_was_written(populated_project, invoke) -> None:
    payload = json.loads(
        await _ok(invoke, [P.third, str(REVIEW), f"add-{P.third_kind}", "Dead branch", "--json"])
    )
    path = payload.pop("path")
    assert path.endswith(f"{P.third_folder}/{THIRD_ID.replace('-', '-00000')}-{P.third_slug}.md")
    start, end = P.third_add_lines
    assert payload == {
        "local_id": f"{P.third_kind_prefix}3",
        "region": f"{P.third_kind}:{P.third_kind_prefix}3:body",
        "start_line": start,
        "end_line": end,
        "display": {
            "item": THIRD_ID,
            "body_command": (
                f'sq {P.third} {REVIEW} {P.third_kind} {P.third_kind_prefix}3 body -m "…"'
            ),
        },
    }


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

    assert f"=== {P.kind_prefix}1 — " in full
    assert f"=== {P.kind_prefix}1 — " not in await _ok(invoke, [P.ref, str(TASK), "show"])
    assert "Looks good" in discussed


@pytest.mark.covers("show", "--full", "--comments", "--raw")
async def test_the_bare_show_takes_the_same_views(populated_project, invoke) -> None:
    await _ok(invoke, [P.ref, str(TASK), "comment", "--as", "manager", "-m", "Looks good"])

    full = await _ok(invoke, ["show", str(TASK), "--full"])
    discussed = await _ok(invoke, ["show", str(TASK), "--comments"])
    raw = await _ok(invoke, ["show", str(TASK), "--raw"])

    assert f"=== {P.kind_prefix}1 — " in full
    assert "Looks good" in discussed
    assert raw.startswith(f"# {P.ref_prefix}-3 — ")
    assert not (await _ok(invoke, ["show", str(TASK)])).startswith("# ")


@pytest.mark.covers("create <type>", "--json")
async def test_create_json_prints_the_created_item(populated_project, invoke) -> None:
    args = ["create", P.ref, "Loose end", "--author", "manager", *P.parent_args(P.ref), "--json"]
    printed = json.loads(await _ok(invoke, args))
    assert (printed["type"], printed["title"]) == (P.ref, "Loose end")


@pytest.mark.covers("operator show", "--raw", "--comments")
async def test_an_operator_shows_raw_and_with_its_discussion(
    populated_project, invoke, monkeypatch
) -> None:
    await _ok(invoke, ["operator", "add", "Alice Tester"])
    await _ok(invoke, ["operator", "op-alice", "comment", "--as", "manager", "-m", "Welcome."])

    forced_terminal(monkeypatch)
    raw = await _ok(invoke, ["operator", "op-alice", "show", "--raw"])
    rendered = await _ok(invoke, ["operator", "op-alice", "show"])
    discussed = await _ok(invoke, ["operator", "op-alice", "show", "--comments"])

    assert raw != rendered
    assert "**Operator (human)**" in raw
    assert "Welcome." in discussed


@pytest.mark.covers("skill show")
async def test_the_squads_skill_shows(seeded_project, invoke) -> None:
    shown = await _ok(invoke, ["skill", "squads", "show"])
    assert f"sq {P.ref} " in shown


async def _loose(invoke) -> int:
    """Create an item of the type the profile retypes, with the parent it needs."""
    args = ["create", P.retype_from, "Loose end", "--author", "manager"]
    created = await _ok(invoke, [*args, *P.parent_args(P.retype_from)])
    return int(created.split("-", 1)[1].split()[0])


@pytest.mark.covers("<type> retype", "--as", "NEW-TYPE")
async def test_retype_attributes_the_edit_to_the_named_slug(populated_project, invoke) -> None:
    number = await _loose(invoke)
    await _ok(invoke, [P.retype_from, str(number), "retype", P.retype_to, "--as", "manager"])

    log = json.loads(
        await _ok(
            invoke,
            ["reflog", "--item", f"{P.retype_to_prefix}-{number}", "--op", "retype", "--json"],
        )
    )

    assert [entry["actor"] for entry in log] == ["manager"]


@pytest.mark.covers("<type> retype", "--as")
async def test_retype_refuses_an_actor_no_roster_entry_has(populated_project, invoke) -> None:
    number = await _loose(invoke)
    args = [P.retype_from, str(number), "retype", P.retype_to, "--as", "ghost"]
    assert await _ran(invoke, args) == (1, "error: unknown slug 'ghost'; valid slugs: manager\n")


@pytest.mark.covers("<type> retype", "--json")
async def test_retype_json_prints_the_item_under_its_new_type(populated_project, invoke) -> None:
    number = await _loose(invoke)
    printed = json.loads(
        await _ok(invoke, [P.retype_from, str(number), "retype", P.retype_to, "--json"])
    )

    entry = printed["entry"]
    assert (entry["type"], entry["id"], entry["status"]) == (
        P.retype_to,
        f"{P.retype_to_prefix}-{number}",
        P.retype_to_initial,
    )
    assert (
        printed["old_id"],
        printed["old_status"],
        printed["status_reset"],
        printed["rewritten"],
    ) == (f"{P.retype_from_prefix}-{number}", P.retype_from_initial, True, [])


@pytest.mark.covers("<type> <kind> update", "--<field>")
async def test_update_accepts_the_value_in_any_case(populated_project, invoke) -> None:
    args = [P.third, str(REVIEW), P.third_kind, "2", "update", FIELD_FLAG]
    await _ok(invoke, [*args, P.third_other_value.upper()])
    stored = (await _entry(invoke, 2))["badges"][P.third_field]
    assert stored.lower() == P.third_other_value.lower()


@pytest.mark.covers("<type> retype", "NEW-TYPE")
async def test_retype_reclassifies_the_item_and_keeps_its_number(populated_project, invoke) -> None:
    number = await _loose(invoke)
    out = await _ran(invoke, [P.retype_from, str(number), "retype", P.retype_to])
    assert out == (
        0,
        f"retyped {P.retype_from_prefix}-{number} → {P.retype_to_prefix}-{number}  "
        f"{P.retype_to_folder}/{P.retype_to_prefix}-{number:06d}-loose-end.md\n"
        f"  status reset: {P.retype_from_initial} → {P.retype_to_initial} (workflows differ)\n",
    )
    moved = json.loads(await _ok(invoke, [P.retype_to, str(number), "show", "--json"]))
    assert (moved["id"], moved["status"]) == (
        f"{P.retype_to_prefix}-{number}",
        P.retype_to_initial,
    )


@pytest.mark.covers("<type> retype", "NEW-TYPE")
async def test_retype_refuses_an_item_that_holds_sub_entities(populated_project, invoke) -> None:
    assert await _ran(invoke, [P.ref, str(TASK), "retype", P.retype_to]) == (
        1,
        f"error: cannot retype {P.ref_prefix}-3: it has sub-entities. "
        "Clear or move all sub-entities first, then retype.\n",
    )


@pytest.mark.covers("<type> retype", "NEW-TYPE")
async def test_retype_refuses_a_roster_type(populated_project, invoke) -> None:
    number = await _loose(invoke)
    assert await _ran(invoke, [P.retype_from, str(number), "retype", "role"]) == (
        1,
        f"error: cannot retype to 'role'; valid targets: {P.retype_targets}\n",
    )


@pytest.mark.covers("<type> retype", "NEW-TYPE")
async def test_retype_refuses_a_type_the_spec_does_not_declare(populated_project, invoke) -> None:
    number = await _loose(invoke)
    assert await _ran(invoke, [P.retype_from, str(number), "retype", P.target_kind]) == (
        1,
        f"error: unknown type '{P.target_kind}' (one of: {P.all_types})\n",
    )
