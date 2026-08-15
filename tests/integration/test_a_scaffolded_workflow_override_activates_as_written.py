"""``sq override scaffold workflow`` writes a file an adopter can activate by following its own
instruction, end to end through the CLI.

The scaffold is the adopter's first contact with the mechanism and it says "uncomment and edit
to activate". Doing exactly that used to fail closed with a raw pydantic dump, because the
example declared a key ``StatusSpec`` had stopped having. The unit-level guard in ``tests/meta``
pins the example against the models; this pins the round trip an adopter actually performs —
scaffold, uncomment, lint, use the type — because the models loading is necessary and not
sufficient: the file also has to be *reachable* through the verbs, and the type it declares has
to actually work afterwards.
"""

import pytest

pytestmark = pytest.mark.anyio

_EXAMPLE_OPEN = "# --- Worked example"
_EXAMPLE_CLOSE = "# ----------------"


def _uncomment_the_worked_example(text: str) -> str:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(_EXAMPLE_OPEN))
    end = next(
        i for i, line in enumerate(lines[start + 1 :], start + 1) if line.startswith(_EXAMPLE_CLOSE)
    )
    activated = [
        line[2:] if line.startswith("# ") else line.removeprefix("#")
        for line in lines[start + 1 : end]
    ]
    return "\n".join([*lines[:start], *activated, *lines[end + 1 :]]) + "\n"


async def test_the_scaffolded_example_lints_clean_once_uncommented(project, invoke) -> None:
    assert (await invoke(["override", "scaffold", "workflow"])).exit_code == 0

    path = project.squad_dir / ".overrides" / "workflow.toml"
    path.write_text(_uncomment_the_worked_example(path.read_text(encoding="utf-8")), "utf-8")

    result = await invoke(["workflow", "lint"])

    assert result.exit_code == 0, result.output


async def test_the_type_the_example_declares_is_usable_afterwards(project, invoke) -> None:
    """Lint passing is not the same as the example being right — a spec can validate and still
    describe a type no command can address."""
    await invoke(["override", "scaffold", "workflow"])
    path = project.squad_dir / ".overrides" / "workflow.toml"
    path.write_text(_uncomment_the_worked_example(path.read_text(encoding="utf-8")), "utf-8")

    created = await invoke(["create", "incident", "Outage", "--author", "manager"])
    assert created.exit_code == 0, created.output

    listed = await invoke(["list", "-a"])
    assert "INC-" in listed.output


async def test_the_examples_statuses_carry_the_behaviour_the_adopter_asked_for(
    project, invoke
) -> None:
    """The stale key the example used to carry (``terminal``) was the *old* way to say this, and
    deleting it alone would have left the example silent about the axis that replaced it. Every
    status it declares resolves to a role, and they are not all the same role."""
    await invoke(["override", "scaffold", "workflow"])
    path = project.squad_dir / ".overrides" / "workflow.toml"
    path.write_text(_uncomment_the_worked_example(path.read_text(encoding="utf-8")), "utf-8")

    import json

    result = await invoke(["workflow", "statuses", "--json"])
    rows = {row["status"]: row for row in json.loads(result.output)}

    declared = {name: rows[name]["role"] for name in ("Triage", "Mitigating", "Resolved")}
    assert all(declared.values()), declared

    roles = {
        row["role"]: row
        for row in json.loads((await invoke(["workflow", "roles", "--json"])).output)
    }
    assert roles[declared["Resolved"]]["settled"] is True
    assert roles[declared["Mitigating"]]["settled"] is False
