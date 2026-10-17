"""Where the CLI prints a role's or operator's name it prints ``Name (pronouns)`` when the display
setting is on, and the bare name otherwise; a column that holds a slug never changes."""

from typing import Any

import pytest

from squads._services._service import Service

pytestmark = pytest.mark.anyio

# (id, pronouns, display on, expected name text, forbidden fragment)
CASES: list[tuple[str, str | None, bool, str, str]] = [
    ("set-and-on", "they/them", True, "{n} (they/them)", ""),
    ("set-and-off", "they/them", False, "{n}", "they/them"),
    ("unset", None, True, "{n}", "()"),
    ("brackets", "[x]", True, "{n} ([x])", ""),
]
_IDS = [c[0] for c in CASES]


def _set_display(svc: Service, on: bool) -> None:
    if not on:
        path = svc.paths.config_path
        path.write_text(
            path.read_text(encoding="utf-8") + "\n[display]\npronouns = false\n", encoding="utf-8"
        )


def _flat(output: str) -> str:
    return " ".join(output.split())


# (surface, command, name, kind)
SURFACES: list[tuple[str, list[str], str, str]] = [
    ("role-list", ["role", "list"], "Robert Architect", "role"),
    ("role-show", ["role", "architect", "show"], "Robert Architect", "role"),
    ("operator-list", ["operator", "list"], "Alex Rivera", "operator"),
    ("operator-show", ["operator", "op-alex", "show"], "Alex Rivera", "operator"),
    ("dev-list", ["dev", "list"], "Elias Python", "dev"),
]


@pytest.mark.parametrize(
    ("surface", "command", "name", "kind"), SURFACES, ids=[s[0] for s in SURFACES]
)
@pytest.mark.parametrize(("case", "pronouns", "on", "expected", "forbidden"), CASES, ids=_IDS)
async def test_a_name_surface_prints_the_name_with_pronouns_under_the_setting(
    svc: Service,
    invoke: Any,
    surface: str,
    command: list[str],
    name: str,
    kind: str,
    case: str,
    pronouns: str | None,
    on: bool,
    expected: str,
    forbidden: str,
) -> None:
    await svc.activate_role("architect", pronouns=pronouns)
    await svc.add_dev("python", name="Elias Python", pronouns=pronouns)
    await svc.add_operator("Alex Rivera", pronouns=pronouns)
    _set_display(svc, on)

    result = await invoke(command)

    assert result.exit_code == 0, result.output
    out = _flat(result.output)
    # The role table wraps a long cell at the pinned width, so it is judged on the pronouns alone.
    wanted = expected.format(n=name)
    if surface == "role-list":
        wanted = wanted.removeprefix(name).strip()
    assert wanted in out
    if forbidden:
        assert forbidden not in out
    assert " )" not in out


@pytest.mark.parametrize(("case", "pronouns", "on", "expected", "forbidden"), CASES, ids=_IDS)
async def test_the_creation_messages_print_the_name_the_same_way(
    svc: Service,
    invoke: Any,
    case: str,
    pronouns: str | None,
    on: bool,
    expected: str,
    forbidden: str,
) -> None:
    _set_display(svc, on)
    args = ["--pronouns", pronouns] if pronouns else []

    activated = await invoke(["role", "activate", "architect", *args])
    registered = await invoke(["operator", "add", "Alex Rivera", *args])

    assert expected.format(n="Robert Architect") in _flat(activated.output)
    assert expected.format(n="Alex Rivera") in _flat(registered.output)


async def test_a_slug_column_is_unchanged_in_every_case(svc: Service, invoke: Any) -> None:
    await svc.activate_role("architect", pronouns="she/her")
    await svc.add_operator("Alex Rivera", pronouns="he/him")

    listed = await invoke(["workload"])
    mine = await invoke(["mine", "architect"])

    assert "she/her" not in listed.output + mine.output
    assert "he/him" not in listed.output + mine.output
