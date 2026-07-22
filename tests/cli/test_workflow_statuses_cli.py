"""``sq workflow statuses`` — the status-vocabulary machine surface.

Default prints a human Rich table; ``--json`` emits the frozen bare-array shape
(``{status, role, badge}``), ascending status name. The byte-identical golden is pinned in
``tests/cli/test_json_output_shape.py`` (``tests/goldens/workflow_statuses.json``) — this module
covers the field-set/model contract and the human table. Every declared status now carries a
role reference (the sole status axis; ``terminal``/``is_open`` are derived from it, not carried
here) — this is catalog-only: no per-item ``role``/``is_active`` field is added anywhere, proven
negatively here against ``sq show``/``sq tree``/``sq list``.
"""

import json

import pytest

from squads._cli._workflow_cmd import (
    STATUS_CATALOG_FIELDS,
    _status_catalog,  # pyright: ignore[reportPrivateUsage]
)
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio


# ─── CLI surface ────────────────────────────────────────────────────────────────


async def test_default_output_is_a_human_table_with_every_declared_status(project, invoke) -> None:
    result = await invoke(["workflow", "statuses"])
    assert result.exit_code == 0
    for col in ("Status", "Role", "Badge"):
        assert col in result.output
    for status in ("Draft", "InProgress", "Done", "Active", "Superseded"):
        assert status in result.output


async def test_json_emits_a_bare_array_of_every_declared_status_in_ascending_order(
    project, invoke
) -> None:
    result = await invoke(["workflow", "statuses", "--json"])
    assert result.exit_code == 0
    rows = json.loads(result.output)
    assert isinstance(rows, list)
    names = [r["status"] for r in rows]
    assert names == sorted(names)


async def test_json_role_and_badge_match_the_spec(project, invoke) -> None:
    result = await invoke(["workflow", "statuses", "--json"])
    rows = {r["status"]: r for r in json.loads(result.output)}
    spec = load_workflow_spec()
    for name, st in spec.statuses.items():
        assert rows[name]["role"] == st.role
        assert rows[name]["badge"] == st.badge
    assert "terminal" not in rows["Draft"]


async def test_json_inprogress_and_active_carry_the_active_role(project, invoke) -> None:
    result = await invoke(["workflow", "statuses", "--json"])
    rows = {r["status"]: r for r in json.loads(result.output)}
    assert rows["InProgress"]["role"] == "active"
    assert rows["Active"]["role"] == "active"


async def test_json_superseded_role_is_unchanged(project, invoke) -> None:
    result = await invoke(["workflow", "statuses", "--json"])
    rows = {r["status"]: r for r in json.loads(result.output)}
    assert rows["Superseded"]["role"] == "superseded"


async def test_json_every_status_carries_a_declared_role_badge_may_be_null(project, invoke) -> None:
    result = await invoke(["workflow", "statuses", "--json"])
    rows = {r["status"]: r for r in json.loads(result.output)}
    assert rows["Draft"]["role"] == "pending"
    assert rows["Draft"]["badge"] is None
    assert set(rows["Draft"].keys()) == set(STATUS_CATALOG_FIELDS)


# ─── field-set / model contract ─────────────────────────────────────────────────


def test_frozen_field_set_is_exactly_status_role_badge() -> None:
    assert STATUS_CATALOG_FIELDS == ("status", "role", "badge")


def test_every_catalog_row_has_exactly_the_frozen_field_set() -> None:
    spec = load_workflow_spec()
    for row in _status_catalog(spec):
        assert set(row.keys()) == set(STATUS_CATALOG_FIELDS)


def test_role_and_badge_are_read_verbatim_off_statusspec() -> None:
    spec = load_workflow_spec()
    st = spec.statuses["InProgress"]
    row = next(r for r in _status_catalog(spec) if r["status"] == "InProgress")
    assert row["role"] == st.role
    assert row["badge"] == st.badge


# ─── catalog-only — no per-item role/is_active field anywhere ──────────────


async def test_no_per_item_surface_gains_a_role_or_is_active_field(project, invoke) -> None:
    await invoke(["create", "task", "T1", "--author", "manager"])
    await invoke(["task", "2", "status", "InProgress"])

    shown = json.loads((await invoke(["task", "2", "show", "--json"])).output)
    assert "role" not in shown
    assert "is_active" not in shown

    rows = json.loads((await invoke(["list", "--json"])).output)
    row = next(r for r in rows if r["id"] == "TASK-2")
    assert "role" not in row
    assert "is_active" not in row

    nodes = json.loads((await invoke(["tree", "--json"])).output)
    node = next(n for n in nodes if n["id"] == "TASK-2")
    assert "role" not in node
    assert "is_active" not in node
