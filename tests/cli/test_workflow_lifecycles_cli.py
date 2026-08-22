"""``sq workflow lifecycles`` — the lifecycle catalog machine surface.

Default prints a human Rich table; ``--json`` emits the frozen bare-array shape
(``{lifecycle, initial, states, transitions}``) ascending lifecycle name. It is the sixth
member of the ``sq workflow`` catalog family and follows the family's row grammar — one row
per declared entry in a documented order, a module-level frozen field-set tuple, every key
present on every row, and references carried by NAME (a type's or a sub-entity kind's own
``lifecycle`` field joins this catalog's identity key of the same name).

``states`` is ``lifecycle_states_in_order`` (BFS discovery order from ``initial``) —
deliberately never ``linearize_lifecycle``'s prettier spine-then-side ordering, whose
side-state canonicalization is keyed on bundled status names. ``transitions`` is
``[{from, to}]`` in that same source order, targets in each source's declared order — never a
positional pair, never a map keyed on adopter-declared status names.

The byte-identical golden is pinned in ``tests/cli/test_json_output_shape.py``
(``tests/goldens/workflow_lifecycles.json``); this module covers the field-set/model contract,
the BFS-not-spine ordering, cross-process byte stability, and an adopter squad that adds a
lifecycle and drops a bundled one.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from squads import __version__
from squads._cli._workflow_cmd import (
    LIFECYCLE_CATALOG_FIELDS,
    TRANSITION_ENTRY_FIELDS,
    _lifecycle_catalog,
)
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec
from squads._workflow._models import lifecycle_edges_in_order, lifecycle_states_in_order

pytestmark = pytest.mark.anyio

#: A squad that rebinds the ``guide`` type off the ``guide`` lifecycle (so it can legitimately
#: be dropped), adds a wholly custom lifecycle, binds it to a new type, and drops the
#: now-unreferenced bundled lifecycle via ``[selected]``.
_CUSTOMIZED = """\
[statuses.Triaged]
role = "pending"
[statuses.Escalated]
role = "active"
[statuses.Closed]
role = "done"

[lifecycles.triage]
initial = "Triaged"
[lifecycles.triage.transitions]
Triaged = ["Escalated"]
Escalated = ["Closed"]

[items.guide]
lifecycle = "work"

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"

[selected]
lifecycles = ["work", "adr", "review", "agent", "subentity", "finding", "bug", "triage"]
"""


def _write_override(squad_dir: Path, body: str) -> None:
    """Write the override, then *prove it loads* — a probe whose setup silently degraded to
    the bundled spec would keep asserting happily against bundled vocabulary."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)
    load_workflow_spec(squad_dir=squad_dir)


# ─── CLI surface ────────────────────────────────────────────────────────────────


async def test_default_output_is_a_human_table_with_every_declared_lifecycle(
    project, invoke
) -> None:
    result = await invoke(["workflow", "lifecycles"])
    assert result.exit_code == 0, result.output
    for col in ("Lifecycle", "Initial", "States", "Transitions"):
        assert col in result.output
    for lifecycle in ("work", "bug", "adr", "review", "guide", "agent", "subentity", "finding"):
        assert lifecycle in result.output


async def test_json_emits_a_bare_array_ascending_lifecycle_name(project, invoke) -> None:
    result = await invoke(["workflow", "lifecycles", "--json"])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.output)
    assert isinstance(rows, list)
    names = [r["lifecycle"] for r in rows]
    assert names == sorted(names)
    assert set(names) == {
        "work",
        "bug",
        "adr",
        "review",
        "guide",
        "agent",
        "subentity",
        "finding",
    }


async def test_json_matches_the_spec_declarations_key_for_key(project, invoke) -> None:
    result = await invoke(["workflow", "lifecycles", "--json"])
    rows = {r["lifecycle"]: r for r in json.loads(result.output)}
    spec = load_workflow_spec()
    for name, machine in spec.lifecycles.items():
        row = rows[name]
        assert row["initial"] == machine.initial
        assert row["states"] == lifecycle_states_in_order(machine)
        assert row["transitions"] == [
            {"from": src, "to": dst} for src, dst in lifecycle_edges_in_order(machine)
        ]


async def test_a_type_and_a_kind_join_the_catalog_by_the_identical_lifecycle_name(
    project, invoke
) -> None:
    types = json.loads((await invoke(["workflow", "types", "--json"])).output)
    kinds = json.loads((await invoke(["workflow", "subentity-kinds", "--json"])).output)
    lifecycle_rows = json.loads((await invoke(["workflow", "lifecycles", "--json"])).output)
    lifecycles = {r["lifecycle"] for r in lifecycle_rows}
    for row in types:
        assert row["lifecycle"] in lifecycles
    for row in kinds:
        assert row["lifecycle"] in lifecycles


# ─── field-set / model contract ─────────────────────────────────────────────────


def test_frozen_field_set_is_exactly_the_four_declared_keys() -> None:
    assert LIFECYCLE_CATALOG_FIELDS == ("lifecycle", "initial", "states", "transitions")


def test_transition_entry_field_set_is_exactly_from_and_to() -> None:
    assert TRANSITION_ENTRY_FIELDS == ("from", "to")


def test_every_catalog_row_has_exactly_the_frozen_field_set() -> None:
    spec = load_workflow_spec()
    for row in _lifecycle_catalog(spec):
        assert set(row.keys()) == set(LIFECYCLE_CATALOG_FIELDS)


def test_every_transition_entry_has_exactly_the_frozen_entry_set() -> None:
    spec = load_workflow_spec()
    for row in _lifecycle_catalog(spec):
        row_transitions = cast("list[dict[str, str]]", row["transitions"])
        for entry in row_transitions:
            assert set(entry.keys()) == set(TRANSITION_ENTRY_FIELDS)


def test_transitions_is_never_a_positional_pair_or_a_status_keyed_map() -> None:
    spec = load_workflow_spec()
    for row in _lifecycle_catalog(spec):
        assert isinstance(row["transitions"], list)
        for entry in row["transitions"]:
            assert isinstance(entry, dict)


# ─── ordering contract ───────────────────────────────────────────────────────────


def test_states_follow_bfs_discovery_order_not_the_spine_then_side_ordering() -> None:
    """The one case a client could plausibly get wrong: ``states`` is
    ``lifecycle_states_in_order`` (BFS from ``initial``), never ``linearize_lifecycle``'s
    prettier spine-then-side ordering. On the bundled ``bug`` machine, BFS discovers
    ``WontFix`` (declared second from ``Open``) before ``Fixed`` (declared first from
    ``InProgress``, one BFS layer later) — the spine-first ordering puts ``Fixed`` ahead of
    ``WontFix`` instead."""
    spec = load_workflow_spec()
    machine = spec.lifecycles["bug"]
    row = next(r for r in _lifecycle_catalog(spec) if r["lifecycle"] == "bug")
    row_states = cast("list[str]", row["states"])
    assert row_states == lifecycle_states_in_order(machine)
    assert row_states.index("WontFix") < row_states.index("Fixed")


def test_transitions_are_sourced_in_states_order_targets_in_declared_order() -> None:
    spec = load_workflow_spec()
    for row in _lifecycle_catalog(spec):
        states_order = cast("list[str]", row["states"])
        row_transitions = cast("list[dict[str, str]]", row["transitions"])
        seen_sources: list[str] = []
        for entry in row_transitions:
            if entry["from"] not in seen_sources:
                seen_sources.append(entry["from"])
        # Sources appear in `states` relative order.
        positions = [states_order.index(s) for s in seen_sources]
        assert positions == sorted(positions)


def test_two_separate_processes_emit_byte_identical_json(tmp_path: Path) -> None:
    """The published order is a contract, not an accident of one process's hash seed —
    ``Lifecycle.states`` is a ``frozenset``, so this is the guard that would catch a
    regression back to iterating it directly."""

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "squads", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=tmp_path,
        )

    assert run("init", "--no-seed-skills", "--roles", "minimal").returncode == 0
    first = run("workflow", "lifecycles", "--json")
    second = run("workflow", "lifecycles", "--json")
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout


# ─── exit codes ───────────────────────────────────────────────────────────────────


async def test_exits_1_when_the_workflow_override_refuses_to_load(project, invoke) -> None:
    override_dir = project.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        '[items.broken]\nprefix = "BRK"\nfolder = "brokens"\nlifecycle = "no_such_lifecycle"\n',
        encoding="utf-8",
    )
    result = await invoke(["workflow", "lifecycles"])
    assert result.exit_code == 1, result.output
    result_json = await invoke(["workflow", "lifecycles", "--json"])
    assert result_json.exit_code == 1, result_json.output


# ─── an adopter who adds and drops ───────────────────────────────────────────────


async def test_a_customized_squad_publishes_its_added_lifecycle_and_drops_the_unbound_one(
    project, invoke
) -> None:
    _write_override(project.squad_dir, _CUSTOMIZED)
    result = await invoke(["workflow", "lifecycles", "--json"])
    assert result.exit_code == 0, result.output
    rows = {r["lifecycle"]: r for r in json.loads(result.output)}

    assert "guide" not in rows
    triage = rows["triage"]
    assert triage["initial"] == "Triaged"
    assert triage["states"] == ["Triaged", "Escalated", "Closed"]
    assert triage["transitions"] == [
        {"from": "Triaged", "to": "Escalated"},
        {"from": "Escalated", "to": "Closed"},
    ]


async def test_the_type_row_joins_the_lifecycle_catalog_in_a_customized_squad(
    project, invoke
) -> None:
    _write_override(project.squad_dir, _CUSTOMIZED)
    types = json.loads((await invoke(["workflow", "types", "--json"])).output)
    lifecycles = {
        r["lifecycle"]: r
        for r in json.loads((await invoke(["workflow", "lifecycles", "--json"])).output)
    }
    by_type = {r["type"]: r for r in types}
    assert by_type["incident"]["lifecycle"] == "triage"
    assert by_type["incident"]["lifecycle"] in lifecycles
    assert by_type["guide"]["lifecycle"] == "work"


async def test_the_frozen_key_set_holds_on_a_customized_squad_too(project, invoke) -> None:
    _write_override(project.squad_dir, _CUSTOMIZED)
    rows = json.loads((await invoke(["workflow", "lifecycles", "--json"])).output)
    for row in rows:
        assert list(row) == list(LIFECYCLE_CATALOG_FIELDS)
        for entry in row["transitions"]:
            assert list(entry) == list(TRANSITION_ENTRY_FIELDS)


async def test_the_human_table_renders_the_customized_vocabulary(project, invoke) -> None:
    _write_override(project.squad_dir, _CUSTOMIZED)
    result = await invoke(["workflow", "lifecycles"])
    assert result.exit_code == 0, result.output
    for token in ("triage", "Triaged", "Escalated", "Closed"):
        assert token in result.output
