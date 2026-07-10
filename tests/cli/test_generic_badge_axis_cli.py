"""The CLI badge surface (``--set``, exact ``--badge CODE=VALUE`` filter, ``--min-badge``
threshold, ``--sort``, and the show-panel column) derives generically from ``fields_for()`` — none
of it hand-wired to priority/severity. Proven with the collection-reuse example (impact/urgency,
both bound to a custom 'level' collection) on a brand-new 'incident'
type, then cross-checked that the bundled priority axis is simply the built-in instance of the
same generic mechanism (its dedicated ``--priority``/``--min-priority`` flags are sugar over the
identical filter, not a second code path).
"""

import re
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
  { code = "urgency", label = "Urgency", collection = "level" },
]
"""


def _write_override(squad_dir: Path) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_OVERRIDE_TOML, encoding="utf-8")


def _created_id(prefix: str, output: str) -> str:
    m = re.search(rf"{prefix}-(\d+)", output)
    assert m is not None, f"could not find a {prefix}-N id in:\n{output}"
    return m.group(0)


def _num(item_id: str) -> str:
    return item_id.rsplit("-", 1)[-1]


async def test_generic_badge_set_filter_min_sort_and_column_all_derive_from_declared_fields(
    project, invoke
) -> None:
    _write_override(project.squad_dir)

    c1 = await invoke(["create", "incident", "DB timeout", "--author", "manager"])
    assert c1.exit_code == 0, c1.output
    inc1 = _created_id("INC", c1.output)
    c2 = await invoke(["create", "incident", "Slow query", "--author", "manager"])
    assert c2.exit_code == 0, c2.output
    inc2 = _created_id("INC", c2.output)

    u1 = await invoke(
        ["incident", _num(inc1), "update", "--set", "impact=high", "--set", "urgency=low"]
    )
    assert u1.exit_code == 0, u1.output
    u2 = await invoke(
        ["incident", _num(inc2), "update", "--set", "impact=low", "--set", "urgency=high"]
    )
    assert u2.exit_code == 0, u2.output

    # An unknown code for the field's own collection is rejected.
    bad = await invoke(["incident", _num(inc1), "update", "--set", "impact=medium"])
    assert bad.exit_code == 1 and "impact" in bad.output

    # show panel: one row per declared field, raw code resolved to its badge.
    show1 = await invoke(["incident", _num(inc1), "show"])
    assert "impact:" in show1.output and "🔴 high" in show1.output
    assert "urgency:" in show1.output and "🟢 low" in show1.output

    # exact filter: --badge CODE=VALUE for a field the CLI never hard-names.
    hi_impact = await invoke(["list", "--type", "incident", "--badge", "impact=high"])
    assert inc1 in hi_impact.output and inc2 not in hi_impact.output

    # threshold filter: --min-badge on an ordered collection (high=rank0, low=rank1).
    min_high = await invoke(["list", "--type", "incident", "--min-badge", "urgency=high"])
    assert inc2 in min_high.output and inc1 not in min_high.output
    min_low = await invoke(["list", "--type", "incident", "--min-badge", "urgency=low"])
    assert inc1 in min_low.output and inc2 in min_low.output

    # sort: --sort urgency orders high (rank0) before low (rank1).
    sorted_out = await invoke(["list", "--type", "incident", "--sort", "urgency"])
    assert sorted_out.output.index(inc2) < sorted_out.output.index(inc1)

    # tree derives the same generic filter/sort surface.
    tree_sorted = await invoke(["tree", "--type", "incident", "--all", "--sort", "urgency"])
    assert tree_sorted.output.index(inc2) < tree_sorted.output.index(inc1)
    tree_filtered = await invoke(["tree", "--type", "incident", "--badge", "impact=high"])
    assert inc1 in tree_filtered.output and inc2 not in tree_filtered.output


async def test_priority_is_the_bundled_instance_of_the_same_generic_axis(project, invoke) -> None:
    """``--priority``/``--min-priority`` sugar keeps working alongside the generic escape
    hatch — the two paths merge into one underlying filter, not two divergent ones."""
    _write_override(project.squad_dir)
    c1 = await invoke(["create", "task", "T1", "--author", "manager", "--priority", "urgent"])
    t1 = _created_id("TASK", c1.output)
    c2 = await invoke(["create", "task", "T2", "--author", "manager", "--priority", "low"])
    t2 = _created_id("TASK", c2.output)

    hi = await invoke(["list", "--priority", "urgent"])
    assert t1 in hi.output and t2 not in hi.output

    at_least_high = await invoke(["list", "--min-priority", "high"])
    assert t1 in at_least_high.output and t2 not in at_least_high.output

    everything = await invoke(["list", "--min-priority", "low"])
    assert t1 in everything.output and t2 in everything.output
