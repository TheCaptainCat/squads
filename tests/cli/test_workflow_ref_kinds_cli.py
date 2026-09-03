"""``sq workflow ref-kinds`` — the declared ref-kind vocabulary catalog.

Default prints a human Rich table; ``--json`` emits the frozen bare-array shape
(``{kind, label, hint, role, direction}``), ascending kind name. The byte-identical golden is
pinned in ``tests/cli/test_json_output_shape.py`` (``tests/goldens/workflow_ref_kinds.json``) —
this module covers the field-set/model contract and the human table, plus the same catalog
verified against an override that declares an extra kind.
"""

import json
from pathlib import Path

import pytest

from squads import __version__
from squads._cli._workflow_cmd import (
    REF_KIND_CATALOG_FIELDS,
    _ref_kind_catalog,
)
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio


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


async def test_default_output_is_a_human_table_with_every_declared_kind(project, invoke) -> None:
    result = await invoke(["workflow", "ref-kinds"])
    assert result.exit_code == 0
    for col in ("Kind", "Label", "Hint", "Role", "Direction"):
        assert col in result.output
    for kind in ("related", "blocks", "depends-on", "supersedes", "scopes", "targets"):
        assert kind in result.output


async def test_json_emits_a_bare_array_of_every_declared_kind_in_ascending_order(
    project, invoke
) -> None:
    result = await invoke(["workflow", "ref-kinds", "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert isinstance(rows, list)
    names = [r["kind"] for r in rows]
    assert names == sorted(names)


async def test_json_every_row_carries_the_frozen_field_set(project, invoke) -> None:
    result = await invoke(["workflow", "ref-kinds", "--json"])
    rows = json.loads(result.output)
    for row in rows:
        assert set(row.keys()) == set(REF_KIND_CATALOG_FIELDS)


async def test_json_exactly_one_row_carries_the_default_role(project, invoke) -> None:
    result = await invoke(["workflow", "ref-kinds", "--json"])
    rows = json.loads(result.output)
    defaults = [r for r in rows if r["role"] == "default"]
    assert len(defaults) == 1
    assert defaults[0]["kind"] == "related"


async def test_json_targets_ships_bundled_with_no_semantic(project, invoke) -> None:
    result = await invoke(["workflow", "ref-kinds", "--json"])
    rows = {r["kind"]: r for r in json.loads(result.output)}
    assert "targets" in rows
    assert rows["targets"]["role"] is None
    assert rows["targets"]["direction"] is None


async def test_json_dependency_kinds_carry_a_direction_others_do_not(project, invoke) -> None:
    result = await invoke(["workflow", "ref-kinds", "--json"])
    rows = {r["kind"]: r for r in json.loads(result.output)}
    assert rows["blocks"]["role"] == "dependency"
    assert rows["blocks"]["direction"] == "blocker"
    assert rows["depends-on"]["role"] == "dependency"
    assert rows["depends-on"]["direction"] == "dependent"
    assert rows["scopes"]["role"] == "preload"
    assert rows["scopes"]["direction"] is None
    assert rows["supersedes"]["role"] == "supersession"
    assert rows["supersedes"]["direction"] is None


# ─── field-set / model contract ─────────────────────────────────────────────────


def test_frozen_field_set_is_exactly_kind_label_hint_role_direction() -> None:
    assert REF_KIND_CATALOG_FIELDS == ("kind", "label", "hint", "role", "direction")


def test_every_catalog_row_has_exactly_the_frozen_field_set() -> None:
    spec = load_workflow_spec()
    for row in _ref_kind_catalog(spec):
        assert set(row.keys()) == set(REF_KIND_CATALOG_FIELDS)


def test_label_hint_role_direction_are_read_verbatim_off_refkindspec() -> None:
    spec = load_workflow_spec()
    rk = spec.ref_kinds["blocks"]
    row = next(r for r in _ref_kind_catalog(spec) if r["kind"] == "blocks")
    assert row["label"] == rk.label
    assert row["hint"] == rk.hint
    assert row["role"] == rk.role
    assert row["direction"] == rk.direction


# ─── an override's own declared kind joins the catalog with no engine change ────


async def test_an_override_declared_kind_joins_the_catalog(project, invoke) -> None:
    _write_override(
        project.squad_dir,
        '[ref_kinds.escalates]\nlabel = "Escalates"\nhint = "A escalates B"\n',
    )

    result = await invoke(["workflow", "ref-kinds", "--json"])
    assert result.exit_code == 0
    rows = {r["kind"]: r for r in json.loads(result.output)}
    assert "escalates" in rows
    assert rows["escalates"]["label"] == "Escalates"
    assert rows["escalates"]["role"] is None
    # The bundled kinds are still present — an addition, not a replacement.
    assert "related" in rows
    assert "blocks" in rows
