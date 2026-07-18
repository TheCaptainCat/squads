"""Every item-bearing ``--json`` surface carries a generic ``badges`` map (keyed by field
code, non-null values only) alongside the legacy bundled keys — additive, never a
replacement. Covers ``sq tree``, ``sq list``, ``sq show`` (top-level + each ``subentities``
entry), and a custom/renamed collection to prove nothing is hardcoded.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

_OVERRIDE_TOML = """\
[collections.level]
label = "Level"
ordered = true
badges = [
  { code = "high", label = "High", emoji = "\U0001f534" },
  { code = "low", label = "Low", emoji = "\U0001f7e2" },
]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
fields = [
  { code = "impact", label = "Impact", collection = "level" },
]
"""


def _write_override(squad_dir: Path) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_OVERRIDE_TOML, encoding="utf-8")


# --------------------------------------------------------------------------- bundled axis:
# additive superset (priority/severity/extra kept verbatim, badges layered alongside)


async def test_list_json_row_carries_badges_alongside_the_legacy_priority_key(
    project, invoke
) -> None:
    c = await invoke(["create", "task", "T1", "--author", "manager", "--priority", "high"])
    assert c.exit_code == 0, c.output
    result = await invoke(["list", "--type", "task", "--json"])
    rows = json.loads(result.output)
    assert len(rows) == 1
    row = rows[0]
    assert row["priority"] == "high"  # legacy key untouched
    assert row["badges"] == {"priority": "high"}


async def test_tree_json_node_carries_badges_alongside_the_legacy_priority_key(
    project, invoke
) -> None:
    c = await invoke(["create", "bug", "B1", "--author", "manager", "--priority", "urgent"])
    assert c.exit_code == 0, c.output
    result = await invoke(["tree", "--type", "bug", "--json"])
    nodes = json.loads(result.output)
    assert len(nodes) == 1
    assert nodes[0]["priority"] == "urgent"
    assert nodes[0]["badges"] == {"priority": "urgent"}


async def test_show_json_top_level_badges_alongside_priority_severity_and_extra(
    project, invoke
) -> None:
    c = await invoke(["create", "bug", "B1", "--author", "manager", "--priority", "high"])
    assert c.exit_code == 0, c.output
    u = await invoke(["bug", "2", "update", "--set", "severity=high"])
    assert u.exit_code == 0, u.output
    shown = await invoke(["bug", "2", "show", "--json"])
    payload = json.loads(shown.output)
    assert payload["priority"] == "high"
    assert payload["severity"] == "high"
    assert payload["extra"] == {}
    assert payload["badges"] == {"priority": "high", "severity": "high"}


async def test_show_json_subentities_each_carry_their_own_badges(project, invoke) -> None:
    await invoke(["create", "review", "R1", "--author", "manager"])
    await invoke(["review", "2", "add-finding", "Missing check", "--severity", "critical"])
    shown = await invoke(["review", "2", "show", "--json"])
    payload = json.loads(shown.output)
    finding = payload["subentities"][0]
    assert finding["severity"] == "critical"
    assert finding["badges"] == {"severity": "critical"}


async def test_a_field_with_no_value_is_omitted_from_the_badges_map(project, invoke) -> None:
    await invoke(["create", "task", "T1", "--author", "manager"])  # no --priority given
    shown = await invoke(["task", "2", "show", "--json"])
    payload = json.loads(shown.output)
    assert payload["priority"] is None
    assert payload["badges"] == {}


# --------------------------------------------------------------------------- spec-driven:
# a renamed/custom collection is faithfully represented with zero code changes


async def test_a_custom_collection_field_shows_up_in_badges_on_every_surface(
    project, invoke
) -> None:
    _write_override(project.squad_dir)
    c = await invoke(["create", "incident", "DB timeout", "--author", "manager"])
    assert c.exit_code == 0, c.output
    u = await invoke(["incident", "2", "update", "--set", "impact=high"])
    assert u.exit_code == 0, u.output

    rows = json.loads((await invoke(["list", "--type", "incident", "--json"])).output)
    assert rows[0]["badges"] == {"impact": "high"}

    nodes = json.loads((await invoke(["tree", "--type", "incident", "--json"])).output)
    assert nodes[0]["badges"] == {"impact": "high"}

    shown = json.loads((await invoke(["incident", "2", "show", "--json"])).output)
    assert shown["badges"] == {"impact": "high"}
    # the bundled priority/severity keys are absent on a type that never declared them.
    assert shown["priority"] is None
