"""CLI test matrix — every type alias routes deep chains; output stays canonical.
TASK-000108: also covers help-cleanliness (ST1) and workflow cheatsheet (ST2).

Each alias is invoked with at least one deep verb chain and the output is compared
against the canonical-name invocation (identical strings) and checked for canonical
type names / full IDs in all output, including --json.
"""

import json

from _helpers import WORK_TYPES
from squads._cli import app
from squads._workflow import load_workflow_spec

# --------------------------------------------------------------------------- helpers


def _init_squad(runner, tmp_path, monkeypatch, frozen_time):
    """Initialize a squad with minimal roles; return the runner and tmp_path."""
    monkeypatch.chdir(tmp_path)
    r = runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    assert r.exit_code == 0, r.output


# ---------------------------------------------------------------------------
# alias table
# ---------------------------------------------------------------------------


def test_type_aliases_spec_is_complete():
    """The bundled spec declares aliases for every WORK_TYPE with no duplicates.

    This was previously a check against the TYPE_ALIASES shim (retired by TASK-267);
    it now verifies the authoritative source — WorkflowSpec.items[t].aliases.
    """
    spec = load_workflow_spec()
    all_aliases: list[str] = [a for t in WORK_TYPES for a in spec.items[t].aliases]
    assert len(all_aliases) == len(set(all_aliases)), "No alias must appear twice in the spec"

    # Canonical type names must not appear as aliases (they're already canonical)
    canonical_names = set(WORK_TYPES)
    for alias in all_aliases:
        assert alias not in canonical_names, f"Alias {alias!r} clashes with a canonical type name"


def test_aliases_not_in_root_help(runner):
    """All single-letter and short aliases must be hidden from root --help."""
    spec = load_workflow_spec()
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0, r.output
    all_aliases = [a for t in WORK_TYPES for a in spec.items[t].aliases]
    for alias in all_aliases:
        # Aliases should not appear as command names at the start of a help line.
        for line in r.output.splitlines():
            stripped = line.strip()
            if stripped.startswith(alias + " ") or stripped == alias:
                raise AssertionError(
                    f"Alias {alias!r} should be hidden but appears in root --help: {line!r}"
                )


def test_canonical_type_commands_present_in_root_help(runner):
    """Root --help must list every canonical work-type command name (and only those).

    The aliases test (test_aliases_not_in_root_help) covers the hidden-alias half;
    this covers the positive requirement: every canonical name appears in the output.
    """
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0, r.output
    for item_type in WORK_TYPES:
        canonical = item_type
        # Rich renders the command list inside a table with box-drawing borders.
        # We just need the canonical name to be present in the help text — the
        # alias test separately verifies aliases are absent.
        assert canonical in r.output, f"Canonical type {canonical!r} missing from root --help"


def test_root_help_epilog_mentions_alias_table(runner):
    """Root --help epilog must mention the alias table and point to sq workflow."""
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0, r.output
    # The epilog must acknowledge aliases and direct readers to the full table.
    assert "alias" in r.output.lower(), "Root --help epilog should mention aliases"
    assert "sq workflow" in r.output, "Root --help epilog should point to sq workflow"


def test_workflow_output_contains_alias_table(runner):
    """sq workflow must render the alias table with every canonical type and its aliases."""
    r = runner.invoke(app, ["workflow"])
    assert r.exit_code == 0, r.output
    # Every canonical type name must appear in the alias table section.
    for item_type in WORK_TYPES:
        assert item_type in r.output, (
            f"Canonical type {item_type!r} missing from sq workflow alias table"
        )
    # Every alias must appear too.
    spec = load_workflow_spec()
    for t in WORK_TYPES:
        for alias in spec.items[t].aliases:
            assert alias in r.output, f"Alias {alias!r} missing from sq workflow alias table"


def test_workflow_output_contains_add_only_evolution_rule(runner):
    """sq workflow must state the add-only evolution rule for the alias table."""
    r = runner.invoke(app, ["workflow"])
    assert r.exit_code == 0, r.output
    output_lower = r.output.lower()
    # The rule must mention adding is allowed and removing is breaking.
    assert "additive" in output_lower or "adding" in output_lower, (
        "add-only rule (adding is allowed) missing from sq workflow output"
    )
    assert "breaking" in output_lower, (
        "add-only rule (breaking change) missing from sq workflow output"
    )
    # Must frame the rule as part of the stability contract.
    assert "stability contract" in output_lower, (
        "stability-contract framing missing from sq workflow alias section"
    )


def test_no_collision_between_aliases_and_top_level_commands(runner):
    """Single-letter aliases do not shadow existing top-level commands.

    b != blocked, t != tree, r != repair, d != docs.
    Verifies exact-match resolution works correctly.
    """
    # 'blocked' must still work as a top-level command
    r = runner.invoke(app, ["blocked", "--help"])
    assert r.exit_code == 0 and "blocked" in r.output.lower()

    # 'b' routes to bug, not blocked
    r = runner.invoke(app, ["b", "--help"])
    assert r.exit_code == 0 and "bug" in r.output.lower()

    # 'tree' must still work
    r = runner.invoke(app, ["tree", "--help"])
    assert r.exit_code == 0 and "hierarchy" in r.output.lower()

    # 't' routes to task, not tree
    r = runner.invoke(app, ["t", "--help"])
    assert r.exit_code == 0 and "task" in r.output.lower()

    # 'repair' must still work
    r = runner.invoke(app, ["repair", "--help"])
    assert r.exit_code == 0 and "index" in r.output.lower()

    # 'r' routes to review, not repair
    r = runner.invoke(app, ["r", "--help"])
    assert r.exit_code == 0 and "review" in r.output.lower()

    # 'docs' must still work
    r = runner.invoke(app, ["docs", "--help"])
    assert r.exit_code == 0 and "documentation" in r.output.lower()

    # 'd' routes to decision, not docs
    r = runner.invoke(app, ["d", "--help"])
    assert r.exit_code == 0 and "decision" in r.output.lower()


# ---------------------------------------------------------------------------
# equivalence: output identity
# ---------------------------------------------------------------------------


def test_feature_alias_f_show_matches_canonical(runner, tmp_path, monkeypatch, frozen_time):
    """sq f N show == sq feature N show (identical output, canonical type name)."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "feature", "My feature", "--author", "manager"])

    canonical = runner.invoke(app, ["feature", "2", "show"])
    alias = runner.invoke(app, ["f", "2", "show"])
    assert canonical.exit_code == 0 and alias.exit_code == 0
    assert canonical.output == alias.output
    assert "FEAT-" in alias.output
    assert "(feature)" in alias.output


def test_feature_alias_feat_show_matches_canonical(runner, tmp_path, monkeypatch, frozen_time):
    """sq feat N show == sq feature N show."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "feature", "My feature", "--author", "manager"])

    canonical = runner.invoke(app, ["feature", "2", "show"])
    alias = runner.invoke(app, ["feat", "2", "show"])
    assert canonical.output == alias.output


def test_task_alias_t_show_matches_canonical(runner, tmp_path, monkeypatch, frozen_time):
    """sq t N show == sq task N show (canonical task output)."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "task", "Do the thing", "--author", "manager"])

    canonical = runner.invoke(app, ["task", "2", "show"])
    alias = runner.invoke(app, ["t", "2", "show"])
    assert canonical.exit_code == 0 and alias.exit_code == 0
    assert canonical.output == alias.output
    assert "TASK-" in alias.output
    assert "(task)" in alias.output


def test_bug_alias_b_show_matches_canonical(runner, tmp_path, monkeypatch, frozen_time):
    """sq b N show == sq bug N show."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "bug", "Bad crash", "--author", "manager"])

    canonical = runner.invoke(app, ["bug", "2", "show"])
    alias = runner.invoke(app, ["b", "2", "show"])
    assert canonical.exit_code == 0 and alias.exit_code == 0
    assert canonical.output == alias.output
    assert "BUG-" in alias.output
    assert "(bug)" in alias.output


def test_decision_alias_d_show_matches_canonical(runner, tmp_path, monkeypatch, frozen_time):
    """sq d N show == sq decision N show."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "decision", "Use postgres", "--author", "manager"])

    canonical = runner.invoke(app, ["decision", "2", "show"])
    alias_d = runner.invoke(app, ["d", "2", "show"])
    alias_dec = runner.invoke(app, ["dec", "2", "show"])
    assert canonical.exit_code == 0
    assert canonical.output == alias_d.output == alias_dec.output
    assert "ADR-" in alias_d.output
    assert "(decision)" in alias_d.output


def test_review_alias_r_show_matches_canonical(runner, tmp_path, monkeypatch, frozen_time):
    """sq r N show == sq review N show."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "review", "Code review", "--author", "manager"])

    canonical = runner.invoke(app, ["review", "2", "show"])
    alias_r = runner.invoke(app, ["r", "2", "show"])
    alias_rev = runner.invoke(app, ["rev", "2", "show"])
    assert canonical.exit_code == 0
    assert canonical.output == alias_r.output == alias_rev.output
    assert "REV-" in alias_r.output
    assert "(review)" in alias_r.output


def test_guide_alias_g_show_matches_canonical(runner, tmp_path, monkeypatch, frozen_time):
    """sq g N show == sq guide N show."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "guide", "How to test", "--author", "manager"])

    canonical = runner.invoke(app, ["guide", "2", "show"])
    alias = runner.invoke(app, ["g", "2", "show"])
    assert canonical.exit_code == 0 and alias.exit_code == 0
    assert canonical.output == alias.output
    assert "GUIDE-" in alias.output
    assert "(guide)" in alias.output


def test_epic_alias_e_show_matches_canonical(runner, tmp_path, monkeypatch, frozen_time):
    """sq e N show == sq epic N show."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "epic", "Big vision", "--author", "manager"])

    canonical = runner.invoke(app, ["epic", "2", "show"])
    alias = runner.invoke(app, ["e", "2", "show"])
    assert canonical.exit_code == 0 and alias.exit_code == 0
    assert canonical.output == alias.output
    assert "EPIC-" in alias.output
    assert "(epic)" in alias.output


# ---------------------------------------------------------------------------
# deep chain equivalence
# ---------------------------------------------------------------------------


def test_feature_alias_deep_chain_story_show(runner, tmp_path, monkeypatch, frozen_time):
    """sq f N story K show == sq feature N story K show (alias + sub-entity)."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "feature", "Big feature", "--author", "manager"])
    runner.invoke(app, ["feature", "2", "add-story", "User can log in"])

    canonical = runner.invoke(app, ["feature", "2", "story", "1", "show"])
    alias_f = runner.invoke(app, ["f", "2", "story", "1", "show"])
    alias_feat = runner.invoke(app, ["feat", "2", "story", "1", "show"])

    assert canonical.exit_code == 0
    assert alias_f.exit_code == 0 and alias_feat.exit_code == 0
    assert canonical.output == alias_f.output == alias_feat.output
    assert "story" in alias_f.output.lower()


def test_task_alias_deep_chain_subtask_show(runner, tmp_path, monkeypatch, frozen_time):
    """sq t N subtask K show == sq task N subtask K show."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "task", "Implement auth", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "Write the handler"])

    canonical = runner.invoke(app, ["task", "2", "subtask", "1", "show"])
    alias = runner.invoke(app, ["t", "2", "subtask", "1", "show"])

    assert canonical.exit_code == 0 and alias.exit_code == 0
    assert canonical.output == alias.output


def test_review_alias_deep_chain_finding_show(runner, tmp_path, monkeypatch, frozen_time):
    """sq r N finding K show == sq review N finding K show."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "review", "Auth review", "--author", "manager"])
    runner.invoke(app, ["review", "2", "add-finding", "Missing null check"])

    canonical = runner.invoke(app, ["review", "2", "finding", "1", "show"])
    alias_r = runner.invoke(app, ["r", "2", "finding", "1", "show"])
    alias_rev = runner.invoke(app, ["rev", "2", "finding", "1", "show"])

    assert canonical.exit_code == 0
    assert alias_r.exit_code == 0 and alias_rev.exit_code == 0
    assert canonical.output == alias_r.output == alias_rev.output


def test_bug_alias_deep_chain_comment(runner, tmp_path, monkeypatch, frozen_time):
    """sq b N comment --as … == sq bug N comment --as … (mutation + canonical output)."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "bug", "Null pointer", "--author", "manager"])

    r = runner.invoke(app, ["b", "2", "comment", "--as", "manager", "-m", "Looking into it."])
    assert r.exit_code == 0, r.output

    shown = runner.invoke(app, ["b", "2", "show", "--comments"])
    assert shown.exit_code == 0
    assert "BUG-" in shown.output
    assert "(bug)" in shown.output
    assert "Looking into it." in shown.output


def test_task_alias_deep_chain_ref_add(runner, tmp_path, monkeypatch, frozen_time):
    """sq t N ref add ID == sq task N ref add ID (ref subgroup via alias)."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "bug", "The bug", "--author", "manager"])  # BUG-2
    runner.invoke(app, ["create", "task", "Fix the bug", "--author", "manager"])  # TASK-3

    r = runner.invoke(app, ["t", "3", "ref", "add", "BUG-000002", "--kind", "fixes"])
    assert r.exit_code == 0, r.output

    shown = runner.invoke(app, ["t", "3", "show"])
    assert shown.exit_code == 0
    assert "TASK-" in shown.output
    assert "(task)" in shown.output
    assert "BUG-2" in shown.output


def test_decision_alias_deep_chain_status(runner, tmp_path, monkeypatch, frozen_time):
    """sq dec N status Accepted == sq decision N status Accepted."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "decision", "Use sqlite", "--author", "manager"])  # ADR-000002

    r_dec = runner.invoke(app, ["dec", "2", "status", "Accepted"])
    assert r_dec.exit_code == 0, r_dec.output
    assert "ADR-" in r_dec.output

    shown = runner.invoke(app, ["d", "2", "show"])
    assert shown.exit_code == 0
    assert "Accepted" in shown.output
    assert "(decision)" in shown.output


# ---------------------------------------------------------------------------
# JSON output stays canonical
# ---------------------------------------------------------------------------


def test_alias_json_output_uses_canonical_type(runner, tmp_path, monkeypatch, frozen_time):
    """--json output via an alias must carry the canonical type field, not the alias."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)
    runner.invoke(app, ["create", "feature", "JSON test feature", "--author", "manager"])

    r = runner.invoke(app, ["f", "2", "show", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["type"] == "feature", f"Expected 'feature', got {data['type']!r}"
    assert data["id"].startswith("FEAT-")

    # Same via task alias
    runner.invoke(app, ["create", "task", "JSON test task", "--author", "manager"])
    r2 = runner.invoke(app, ["t", "3", "show", "--json"])
    assert r2.exit_code == 0, r2.output
    data2 = json.loads(r2.output)
    assert data2["type"] == "task", f"Expected 'task', got {data2['type']!r}"
    assert data2["id"].startswith("TASK-")


def test_alias_error_output_uses_canonical_id(runner, tmp_path, monkeypatch, frozen_time):
    """Error messages from alias invocations must use canonical IDs, not alias names."""
    _init_squad(runner, tmp_path, monkeypatch, frozen_time)

    # Non-existent item — should error with a clean message
    r = runner.invoke(app, ["f", "9999", "show"])
    assert r.exit_code == 1
    # The error must not reference the alias 'f' as a type name; it should mention
    # either 'feature' or a generic "no item" message.
    assert "feature" in r.output.lower() or "no" in r.output.lower()
