"""The four roster ``--json`` viewers carry a top-level ``pronouns`` key beside ``full_name``: the
resolved value, a string or null, always present. Item rows, discussion entries and comment
headers carry none, and the output is the same whatever ``[display]`` says."""

import json
from pathlib import Path
from typing import Any

import pytest

from _helpers import create_item
from squads import __version__
from squads._rendering._engine import invalidate_squad_dir
from squads._services._service import Service

pytestmark = pytest.mark.anyio

ROLE_LIST_KEYS = {
    "id", "slug", "full_name", "pronouns", "title", "description", "is_default", "capabilities",
    "status", "origin",
}  # fmt: skip
ROLE_SHOW_KEYS = {
    "slug", "id", "activated", "origin", "full_name", "pronouns", "title", "mission", "model",
    "is_default", "can_spawn", "capabilities", "create_lane", "responsibilities", "skills",
}  # fmt: skip
OPERATOR_LIST_KEYS = {"id", "slug", "full_name", "pronouns", "status"}
OPERATOR_SHOW_KEYS = {"id", "slug", "full_name", "pronouns", "status", "path"}

# (shape, own value, default declared, expected resolved)
ROLE_CASES: list[tuple[str, str | None, bool, str | None]] = [
    ("own-value", "she/her", False, "she/her"),
    ("unset", None, False, None),
    ("default-only", None, True, "they/them"),
    ("own-over-default", "she/her", True, "she/her"),
]
OPERATOR_CASES: list[tuple[str, str | None, bool, str | None]] = [
    ("own-value", "he/him", False, "he/him"),
    ("unset", None, False, None),
    ("unset-with-a-default-declared", None, True, None),
]


def _declare_default(svc: Service) -> None:
    target = svc.paths.squad_dir / ".overrides" / "roles.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        f'# squads:override-base:{__version__}\n[defaults]\npronouns = "they/them"\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(svc.paths.squad_dir)


def _set_display(svc: Service, pronouns: bool) -> None:
    path: Path = svc.paths.config_path
    text = path.read_text(encoding="utf-8")
    path.write_text(f"{text}\n[display]\npronouns = {str(pronouns).lower()}\n", encoding="utf-8")


async def _json(invoke: Any, args: list[str]) -> Any:
    result = await invoke([*args, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


@pytest.mark.parametrize(
    ("case", "own", "default", "expected"), ROLE_CASES, ids=[c[0] for c in ROLE_CASES]
)
async def test_the_role_payloads_carry_the_resolved_value_under_an_exact_key_set(
    svc: Service, invoke: Any, case: str, own: str | None, default: bool, expected: str | None
) -> None:
    await svc.activate_role("architect", pronouns=own)
    if default:
        _declare_default(svc)

    listing = await _json(invoke, ["role", "list"])
    shown = await _json(invoke, ["role", "architect", "show"])

    row = next(r for r in listing if r["slug"] == "architect")
    assert set(row) == ROLE_LIST_KEYS
    assert set(shown) == ROLE_SHOW_KEYS
    assert row["pronouns"] == expected
    assert shown["pronouns"] == expected
    assert list(row)[list(row).index("full_name") + 1] == "pronouns"


@pytest.mark.parametrize(
    ("case", "own", "default", "expected"), ROLE_CASES, ids=[c[0] for c in ROLE_CASES]
)
async def test_a_bundled_role_not_yet_activated_resolves_the_default_alone(
    svc: Service, invoke: Any, case: str, own: str | None, default: bool, expected: str | None
) -> None:
    if default:
        _declare_default(svc)

    shown = await _json(invoke, ["role", "architect", "show"])

    assert set(shown) == ROLE_SHOW_KEYS
    assert shown["activated"] is False
    assert shown["pronouns"] == ("they/them" if default else None)


@pytest.mark.parametrize(
    ("case", "own", "default", "expected"), OPERATOR_CASES, ids=[c[0] for c in OPERATOR_CASES]
)
async def test_the_operator_payloads_carry_the_own_value_and_never_the_default(
    svc: Service, invoke: Any, case: str, own: str | None, default: bool, expected: str | None
) -> None:
    await svc.add_operator("Alex Rivera", pronouns=own)
    if default:
        _declare_default(svc)

    listing = await _json(invoke, ["operator", "list"])
    shown = await _json(invoke, ["operator", "op-alex", "show"])

    assert [set(r) for r in listing] == [OPERATOR_LIST_KEYS]
    assert set(shown) == OPERATOR_SHOW_KEYS
    assert listing[0]["pronouns"] == expected
    assert shown["pronouns"] == expected


async def test_an_invalid_stored_value_is_null_in_every_payload(svc: Service, invoke: Any) -> None:
    role = await svc.activate_role("architect", pronouns="she/her")
    operator = await svc.add_operator("Alex Rivera", pronouns="he/him")
    for item in (role, operator):
        path = svc.paths.abspath(item.path)
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace("she/her", "a" * 41).replace("he/him", "a" * 41), encoding="utf-8"
        )
    await svc.repair()

    payloads = [
        await _json(invoke, ["role", "list"]),
        await _json(invoke, ["role", "architect", "show"]),
        await _json(invoke, ["operator", "list"]),
        await _json(invoke, ["operator", "op-alex", "show"]),
    ]

    flat = [p if isinstance(p, dict) else p[-1] for p in payloads]
    assert [p["pronouns"] for p in flat] == [None, None, None, None]


async def test_item_rows_and_discussion_entries_gain_no_pronouns_key(
    svc: Service, invoke: Any
) -> None:
    await svc.activate_role("architect", pronouns="she/her")
    number = str((await create_item(svc, "task", "A task", author="architect")).item.sequence_id)
    await invoke(["task", number, "comment", "--as", "architect", "-m", "hello"])

    shown = await _json(invoke, ["task", number, "show", "--full", "--comments"])
    listed = await _json(invoke, ["list", "--type", "task"])

    assert "pronouns" not in shown
    assert shown["discussion"] and all("pronouns" not in e for e in shown["discussion"])
    assert all("pronouns" not in row for row in listed)


@pytest.mark.parametrize("display", [True, False], ids=["display-on", "display-off"])
async def test_the_payloads_are_identical_whatever_display_says(
    svc: Service, invoke: Any, display: bool
) -> None:
    await svc.activate_role("architect", pronouns="she/her")
    await svc.add_operator("Alex Rivera", pronouns="he/him")
    commands = [
        ["role", "list"],
        ["role", "architect", "show"],
        ["operator", "list"],
        ["operator", "op-alex", "show"],
    ]
    baseline = [await _json(invoke, c) for c in commands]

    _set_display(svc, display)
    after = [await _json(invoke, c) for c in commands]

    assert after == baseline
