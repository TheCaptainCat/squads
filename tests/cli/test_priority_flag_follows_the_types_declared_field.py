"""``--priority`` is sugar for one declared field, so every part of it — the enumerated help,
whether the flag is offered at all, and what values it accepts — must resolve through the
binding the type actually declares.

Two shapes, one cause (a same-named collection answering for an undeclared field):

- a type whose ``priority`` field is bound to a *different* collection (``tshirt``) advertised
  ``s|m|l`` but validated against the collection literally named ``priority``, so ``m`` was
  refused by the CLI and ``high`` was refused by the service — unusable in both directions;
- a type declaring no ``priority`` field at all still advertised ``--priority`` with the
  bundled codes, a flag that can only ever error.

The cross-type filter (``sq list``/``tree``) is a third door with its own rule: it spans every
type, so it accepts any code any type's binding of the field declares.
"""

from pathlib import Path

import pytest

from squads import __version__
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_TSHIRT_ON_TASK = """\
[collections.tshirt]
label = "Size"
ordered = true
badges = [
  { code = "s", label = "Small" },
  { code = "m", label = "Medium" },
  { code = "l", label = "Large" },
]

[items.task]
fields = [{ code = "priority", label = "Priority", collection = "tshirt" }]
"""

_INCIDENT_WITHOUT_PRIORITY = """\
[collections.urgency]
label = "Urgency"
ordered = true
badges = [
  { code = "p1", label = "P1" },
  { code = "p2", label = "P2" },
]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
order = 75
fields = [{ code = "urgency", label = "Urgency", collection = "urgency" }]
"""


def _write_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)
    # Prove the override actually loads: the CLI's spec resolution is fail-soft, so a
    # malformed or invalid override degrades silently to the bundled spec and every assertion
    # below would keep passing against bundled vocabulary. Load it eagerly so a broken
    # fixture is a setup error, not a misleading pass.
    load_workflow_spec(squad_dir=squad_dir)


async def _new_task(invoke) -> str:
    created = await invoke(["create", "task", "Ship it", "--author", "manager"])
    assert created.exit_code == 0, created.output
    return created.output.split("TASK-")[1].split()[0].lstrip("0")


# ─── a re-bound collection ────────────────────────────────────────────────────


async def test_create_accepts_the_bound_collections_codes(project, invoke) -> None:
    _write_override(project.squad_dir, _TSHIRT_ON_TASK)
    result = await invoke(["create", "task", "Ship it", "--author", "manager", "--priority", "m"])
    assert result.exit_code == 0, result.output


async def test_create_refuses_a_code_from_the_same_named_collection(project, invoke) -> None:
    _write_override(project.squad_dir, _TSHIRT_ON_TASK)
    result = await invoke(["create", "task", "Ship", "--author", "manager", "--priority", "high"])
    assert result.exit_code != 0
    assert "s, m, l" in result.output


async def test_update_accepts_the_bound_collections_codes(project, invoke) -> None:
    _write_override(project.squad_dir, _TSHIRT_ON_TASK)
    num = await _new_task(invoke)
    result = await invoke(["task", num, "update", "--priority", "l"])
    assert result.exit_code == 0, result.output

    shown = await invoke(["task", num, "show", "--json"])
    assert '"priority": "l"' in shown.output


async def test_help_enumerates_the_bound_collection_on_create_and_update(project, invoke) -> None:
    _write_override(project.squad_dir, _TSHIRT_ON_TASK)
    num = await _new_task(invoke)
    for args in (["create", "task", "--help"], ["task", num, "update", "--help"]):
        result = await invoke(args)
        assert result.exit_code == 0, result.output
        assert "s|m|l" in result.output


# ─── a type declaring no priority field ───────────────────────────────────────


async def test_priority_is_not_advertised_on_a_type_that_declares_no_priority_field(
    project, invoke
) -> None:
    _write_override(project.squad_dir, _INCIDENT_WITHOUT_PRIORITY)
    created = await invoke(["create", "incident", "Outage", "--author", "manager"])
    assert created.exit_code == 0, created.output
    num = created.output.split("INC-")[1].split()[0].lstrip("0")

    create_help = await invoke(["create", "incident", "--help"])
    assert create_help.exit_code == 0, create_help.output
    assert "--priority" not in create_help.output

    update_help = await invoke(["incident", num, "update", "--help"])
    assert update_help.exit_code == 0, update_help.output
    assert "--priority" not in update_help.output
    assert "--no-priority" not in update_help.output


async def test_the_unadvertised_flag_still_gets_the_accurate_service_refusal(
    project, invoke
) -> None:
    """Hidden, not removed — the one gate that knows the type's declared fields owns the
    message, rather than Click reporting an unknown option."""
    _write_override(project.squad_dir, _INCIDENT_WITHOUT_PRIORITY)
    result = await invoke(
        ["create", "incident", "Outage", "--author", "manager", "--priority", "high"]
    )
    assert result.exit_code != 0
    assert "urgency" in result.output


# ─── the cross-type filter door ───────────────────────────────────────────────


async def test_the_list_filter_accepts_any_declared_binding(project, invoke) -> None:
    _write_override(project.squad_dir, _TSHIRT_ON_TASK)
    created = await invoke(["create", "task", "Ship", "--author", "manager", "--priority", "l"])
    assert created.exit_code == 0, created.output
    bug = await invoke(["create", "bug", "Crash", "--author", "manager", "--priority", "high"])
    assert bug.exit_code == 0, bug.output

    by_tshirt = await invoke(["list", "--priority", "l"])
    assert by_tshirt.exit_code == 0, by_tshirt.output
    assert "Ship" in by_tshirt.output
    assert "Crash" not in by_tshirt.output

    by_bundled = await invoke(["list", "--priority", "high"])
    assert by_bundled.exit_code == 0, by_bundled.output
    assert "Crash" in by_bundled.output


async def test_the_list_filter_still_refuses_a_code_no_type_declares(project, invoke) -> None:
    _write_override(project.squad_dir, _TSHIRT_ON_TASK)
    result = await invoke(["list", "--priority", "enormous"])
    assert result.exit_code != 0
    assert "unknown priority" in result.output


# ─── an unmodified squad is unchanged ─────────────────────────────────────────


async def test_a_plain_squad_keeps_the_bundled_priority_behaviour(project, invoke) -> None:
    num = await _new_task(invoke)
    create_help = await invoke(["create", "task", "--help"])
    assert "urgent|high|medium|low" in create_help.output

    update_help = await invoke(["task", num, "update", "--help"])
    assert "urgent|high|medium|low" in update_help.output
    assert "--no-priority" in update_help.output

    assert (await invoke(["task", num, "update", "--priority", "high"])).exit_code == 0
    assert (await invoke(["list", "--priority", "high"])).exit_code == 0

    bad = await invoke(["list", "--priority", "nope"])
    assert bad.exit_code != 0
    assert "unknown priority 'nope' (one of: urgent, high, medium, low)" in bad.output
