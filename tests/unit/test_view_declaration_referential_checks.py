"""``[views]`` is a declared keyed section of the workflow document, reduced to a single
``source`` key. Referential validation of that source's ``name`` against its ``kind``'s
vocabulary runs on the merged spec by the same cross-reference pass every other declared
reference goes through — no view-specific guard. Table-driven across the three relation
source-kind families (ref / subentity / subtree) rather than one probe per family, since the
failure shape (an undeclared name) is identical across all three.

The retired ``fields``/``group_by``/``order_by``/``items.<type>.views`` grammar is covered by
``tests/unit/test_retired_view_grammar_keys_fail_at_load.py`` instead — every declared-key
error, one test per key, rather than a load-time-resolution assertion here.
"""

from pathlib import Path

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import bundled_spec, load_workflow_spec
from squads._workflow._loader import WORKFLOW_TOP_LEVEL_SECTIONS


def _write_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


# --------------------------------------------------------------------------- registration


def test_views_is_a_member_of_the_closed_top_level_section_set() -> None:
    assert "views" in WORKFLOW_TOP_LEVEL_SECTIONS


def test_exactly_one_relation_view_ships_bundled_and_none_are_type_attached() -> None:
    """Naming a bundled ref kind / sub-entity kind / item type as a source would ordinarily
    couple every project that later drops or renames it (an ordinary, already-tested
    customisation — see ``test_workflow_subentity_kinds_cli.py``'s dropped-kind cases) to
    keeping a view nothing consumes — the reason the mechanism itself shipped with no
    *relation*-sourced view beyond one. The milestone roll-up is that one exception.

    It is placed the same way the other five bundled views are: a ``sq:view:<name>`` tag
    seeded straight into its host's creation template (``templates/items/milestone.md.j2``).
    Every bundled view is reached only by a placed tag, never by declaring it against a type.
    """
    spec = bundled_spec()
    non_relation_views = {
        "role_definition",
        "squads_skill",
        "greeting_skill",
        "memory_skill",
        "item_skill",
    }
    relation_views = set(spec.views) - non_relation_views
    assert relation_views == {"milestone_rollup"}


# --------------------------------------------------------------------------- a valid declaration
# per source kind loads and resolves


@pytest.mark.parametrize(
    "source_toml",
    [
        pytest.param('{ kind = "ref", name = "related" }', id="ref"),
        pytest.param('{ kind = "subentity", name = "finding" }', id="subentity"),
        pytest.param('{ kind = "subtree", name = "task" }', id="subtree"),
        pytest.param('{ kind = "role" }', id="role"),
        pytest.param('{ kind = "self" }', id="self"),
        pytest.param('{ kind = "playbook" }', id="playbook-no-name"),
        pytest.param('{ kind = "playbook", name = "task" }', id="playbook-declared-name"),
    ],
)
def test_a_valid_view_per_source_kind_loads_with_only_a_source(
    tmp_path: Path, source_toml: str
) -> None:
    _write_override(tmp_path, f"[views.probe]\nsource = {source_toml}\n")
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert spec.views["probe"].source is not None


@pytest.mark.parametrize("kind", ["role", "self"])
def test_a_role_or_self_source_naming_a_name_is_refused(tmp_path: Path, kind: str) -> None:
    _write_override(tmp_path, f'[views.probe]\nsource = {{ kind = "{kind}", name = "bogus" }}\n')
    with pytest.raises(SquadsError, match=f"'{kind}' source takes no name"):
        load_workflow_spec(squad_dir=tmp_path)


def test_a_playbook_source_name_is_optional(tmp_path: Path) -> None:
    """No name at all — resolved at read time against the host's own type — loads clean,
    exactly like a declared one."""
    _write_override(tmp_path, '[views.probe]\nsource = { kind = "playbook" }\n')
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert spec.views["probe"].source.name is None


def test_a_playbook_source_naming_an_undeclared_type_is_refused(tmp_path: Path) -> None:
    _write_override(
        tmp_path, '[views.probe]\nsource = { kind = "playbook", name = "no-such-type" }\n'
    )
    with pytest.raises(SquadsError, match=r"not declared in \[items\]"):
        load_workflow_spec(squad_dir=tmp_path)


# --------------------------------------------------------------------------- referential floor


@pytest.mark.parametrize(
    ("source_toml", "expected_substring"),
    [
        pytest.param(
            '{ kind = "ref", name = "nope-kind" }',
            "not declared in [ref_kinds]",
            id="ref-source-undeclared-kind",
        ),
        pytest.param(
            '{ kind = "subentity", name = "nope-kind" }',
            "not declared in [subentity_kinds]",
            id="subentity-source-undeclared-kind",
        ),
        pytest.param(
            '{ kind = "subtree", name = "nope-type" }',
            "not declared in [items]",
            id="subtree-source-undeclared-type",
        ),
    ],
)
def test_a_source_naming_undeclared_vocabulary_is_refused(
    tmp_path: Path, source_toml: str, expected_substring: str
) -> None:
    _write_override(tmp_path, f"[views.probe]\nsource = {source_toml}\n")
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    assert expected_substring in str(excinfo.value)


# --------------------------------------------------------------------------- collect-all + selected


def test_lint_reports_every_view_violation_in_one_run_not_only_the_first(tmp_path: Path) -> None:
    from squads._workflow._loader import lint_workflow_spec

    _write_override(
        tmp_path,
        """
[views.bad_ref]
source = { kind = "ref", name = "nope" }

[views.bad_subtree]
source = { kind = "subtree", name = "nope-type" }
""",
    )
    findings = lint_workflow_spec(tmp_path)
    messages = [f[2] for f in findings]
    assert any("bad_ref" in m for m in messages)
    assert any("bad_subtree" in m for m in messages)


def test_selected_may_drop_a_declared_view(tmp_path: Path) -> None:
    """Dropping a declared view needs no companion edit — a view is reached only by placing
    its own ``sq:view:<name>`` tag, never by a type attachment, so there is no reciprocal
    binding to strand. ``[selected].views`` here re-selects the bundled ``milestone_rollup``
    alongside the test-declared ``kept`` view simply to prove a re-selected bundled view
    survives an otherwise-narrowing ``[selected]`` line unchanged."""
    _write_override(
        tmp_path,
        """
[views.kept]
source = { kind = "ref", name = "related" }

[views.dropped]
source = { kind = "ref", name = "related" }

[selected]
views = ["kept", "milestone_rollup"]
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert set(spec.views) == {"kept", "milestone_rollup"}


def test_a_selected_line_dropping_a_ref_kind_a_view_projects_fails_with_no_view_specific_guard(
    tmp_path: Path,
) -> None:
    """The referential pass runs on the *merged* spec, so this needs no code of its own: the
    view's declared ``ref`` source simply stops resolving once ``[selected]`` drops the kind
    it names."""
    _write_override(
        tmp_path,
        """
[views.by_targets]
source = { kind = "ref", name = "targets" }

[selected]
ref_kinds = [
  "related", "blocks", "depends-on", "implements", "fixes",
  "addresses", "supersedes", "duplicates", "scopes",
]
""",
    )
    with pytest.raises(SquadsError, match="dropped from a \\[selected\\] list"):
        load_workflow_spec(squad_dir=tmp_path)
