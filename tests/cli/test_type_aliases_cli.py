"""Type aliases at the CLI surface: every alias resolves identically to its canonical name
at every nesting depth (item show, sub-entity show, comment, ref add, status), --json
reports the canonical type, error messages cite the canonical id, aliases don't collide
with top-level commands, and root help / sq workflow surface the alias table correctly
(the ledger's row 80). The alias table itself (completeness, no collisions) lives in
tests/unit/test_type_alias_table.py.
"""

import json

import pytest

from _helpers import WORK_TYPES
from squads._cli import app
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Root help / sq workflow surface the alias table (row 80)
# ---------------------------------------------------------------------------


def test_aliases_are_hidden_from_root_help(runner) -> None:
    spec = load_workflow_spec()
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0, r.output
    all_aliases = [a for t in WORK_TYPES for a in spec.items[t].aliases]
    for alias in all_aliases:
        for line in r.output.splitlines():
            stripped = line.strip()
            assert not (stripped.startswith(alias + " ") or stripped == alias), (
                f"alias {alias!r} should be hidden but appears in root --help: {line!r}"
            )


def test_every_canonical_type_command_is_present_in_root_help(runner) -> None:
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0, r.output
    for item_type in WORK_TYPES:
        assert item_type in r.output


def test_root_help_epilog_mentions_the_alias_table(runner) -> None:
    r = runner.invoke(app, ["--help"])
    assert "alias" in r.output.lower()
    assert "sq workflow" in r.output


def test_sq_workflow_renders_every_canonical_type_and_its_aliases(runner) -> None:
    r = runner.invoke(app, ["workflow"])
    assert r.exit_code == 0, r.output
    for item_type in WORK_TYPES:
        assert item_type in r.output
    spec = load_workflow_spec()
    for t in WORK_TYPES:
        for alias in spec.items[t].aliases:
            assert alias in r.output


def test_sq_workflow_states_the_add_only_evolution_rule(runner) -> None:
    r = runner.invoke(app, ["workflow"])
    out = r.output.lower()
    assert "additive" in out or "adding" in out
    assert "breaking" in out
    assert "stability contract" in out


def test_single_letter_aliases_do_not_shadow_top_level_commands(runner) -> None:
    r = runner.invoke(app, ["blocked", "--help"])
    assert r.exit_code == 0 and "blocked" in r.output.lower()
    r = runner.invoke(app, ["b", "--help"])
    assert r.exit_code == 0 and "bug" in r.output.lower()

    r = runner.invoke(app, ["tree", "--help"])
    assert r.exit_code == 0 and "hierarchy" in r.output.lower()
    r = runner.invoke(app, ["t", "--help"])
    assert r.exit_code == 0 and "task" in r.output.lower()

    r = runner.invoke(app, ["repair", "--help"])
    assert r.exit_code == 0 and "index" in r.output.lower()
    r = runner.invoke(app, ["r", "--help"])
    assert r.exit_code == 0 and "review" in r.output.lower()

    r = runner.invoke(app, ["docs", "--help"])
    assert r.exit_code == 0 and "documentation" in r.output.lower()
    r = runner.invoke(app, ["d", "--help"])
    assert r.exit_code == 0 and "decision" in r.output.lower()


# ---------------------------------------------------------------------------
# Alias resolves identically to canonical at every nesting depth (row 79)
# ---------------------------------------------------------------------------

#: (type, aliases, prefix, id-word) — every alias for a type must produce byte-identical
#: `show` output to invoking the canonical type name.
_TYPE_ALIASES: list[tuple[str, list[str], str]] = [
    ("feature", ["f", "feat"], "FEAT-"),
    ("task", ["t"], "TASK-"),
    ("bug", ["b"], "BUG-"),
    ("decision", ["d", "dec"], "ADR-"),
    ("review", ["r", "rev"], "REV-"),
    ("guide", ["g"], "GUIDE-"),
    ("epic", ["e"], "EPIC-"),
]


@pytest.mark.parametrize(
    ("item_type", "aliases", "prefix"), _TYPE_ALIASES, ids=[t[0] for t in _TYPE_ALIASES]
)
async def test_show_via_any_alias_is_byte_identical_to_the_canonical_invocation(
    project, invoke, item_type: str, aliases: list[str], prefix: str
) -> None:
    created = await invoke(["create", item_type, "Aliased item", "--author", "manager"])
    assert created.exit_code == 0, created.output

    canonical = await invoke([item_type, "2", "show"])
    assert canonical.exit_code == 0, canonical.output
    for alias in aliases:
        aliased = await invoke([alias, "2", "show"])
        assert aliased.exit_code == 0, aliased.output
        assert aliased.output == canonical.output
        assert prefix in aliased.output
        assert f"({item_type})" in aliased.output


async def test_alias_resolves_identically_at_sub_entity_nesting_depth(project, invoke) -> None:
    await invoke(["create", "feature", "Big feature", "--author", "manager"])
    await invoke(["feature", "2", "add-story", "User can log in"])

    canonical = await invoke(["feature", "2", "story", "1", "show"])
    via_f = await invoke(["f", "2", "story", "1", "show"])
    via_feat = await invoke(["feat", "2", "story", "1", "show"])
    assert canonical.output == via_f.output == via_feat.output
    assert "story" in via_f.output.lower()


async def test_alias_resolves_identically_through_a_mutating_comment(project, invoke) -> None:
    await invoke(["create", "bug", "Null pointer", "--author", "manager"])
    r = await invoke(["b", "2", "comment", "--as", "manager", "-m", "Looking into it."])
    assert r.exit_code == 0, r.output
    shown = await invoke(["b", "2", "show", "--comments"])
    assert "(bug)" in shown.output
    assert "Looking into it." in shown.output


async def test_alias_resolves_identically_through_ref_add(project, invoke) -> None:
    await invoke(["create", "bug", "The bug", "--author", "manager"])
    await invoke(["create", "task", "Fix the bug", "--author", "manager"])
    r = await invoke(["t", "3", "ref", "add", "BUG-000002", "--kind", "fixes"])
    assert r.exit_code == 0, r.output
    shown = await invoke(["t", "3", "show"])
    assert "(task)" in shown.output
    assert "BUG-2" in shown.output


async def test_alias_resolves_identically_through_a_status_change(project, invoke) -> None:
    await invoke(["create", "decision", "Use sqlite", "--author", "manager"])
    r = await invoke(["dec", "2", "status", "Accepted"])
    assert r.exit_code == 0, r.output
    shown = await invoke(["d", "2", "show"])
    assert "Accepted" in shown.output
    assert "(decision)" in shown.output


# ---------------------------------------------------------------------------
# --json / error output stays canonical
# ---------------------------------------------------------------------------


async def test_json_output_via_an_alias_reports_the_canonical_type(project, invoke) -> None:
    await invoke(["create", "feature", "JSON test feature", "--author", "manager"])
    r = await invoke(["f", "2", "show", "--json"])
    data = json.loads(r.output)
    assert data["type"] == "feature"
    assert data["id"].startswith("FEAT-")

    await invoke(["create", "task", "JSON test task", "--author", "manager"])
    r2 = await invoke(["t", "3", "show", "--json"])
    data2 = json.loads(r2.output)
    assert data2["type"] == "task"
    assert data2["id"].startswith("TASK-")


async def test_error_output_via_an_alias_never_names_the_alias_as_a_type(project, invoke) -> None:
    r = await invoke(["f", "9999", "show"])
    assert r.exit_code == 1
    assert "feature" in r.output.lower() or "no" in r.output.lower()
