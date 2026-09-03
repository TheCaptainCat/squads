"""``[views]`` is a declared keyed section of the workflow document, validated on the merged
spec by the exact referential pass every other cross-reference goes through — no view-specific
guard. Table-driven across the three source-kind families (ref / subentity / subtree) rather
than one probe per family, since the failure shape (an undeclared name, an unresolvable field,
an unresolvable group/order key) is identical across all three.
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


def test_exactly_one_view_ships_bundled_and_it_is_type_attached() -> None:
    """Naming a bundled ref kind / sub-entity kind / item type as a source would ordinarily
    couple every project that later drops or renames it (an ordinary, already-tested
    customisation — see ``test_workflow_subentity_kinds_cli.py``'s dropped-kind cases) to
    keeping a view nothing consumes — the reason the mechanism itself shipped with none. The
    milestone roll-up is the one exception, and only because it's attached: something in the
    document actually reads it (``items.milestone.views``), and dropping ``milestone`` from
    ``[selected].items`` takes the attachment — and the loader then the view itself — with it
    (``tests/unit/test_milestone_view_deselect_cascade.py``). Every OTHER bundled view stays
    proven through test-only declarations instead (this module and
    ``tests/unit/test_view_expresses_the_subentity_summary_shape.py``)."""
    spec = bundled_spec()
    assert set(spec.views) == {"milestone_rollup"}
    assert spec.items["milestone"].views == ["milestone_rollup"]


# --------------------------------------------------------------------------- a valid declaration
# per source kind loads and resolves


@pytest.mark.parametrize(
    ("source_toml", "field_code"),
    [
        pytest.param('{ kind = "ref", name = "related" }', "status", id="ref"),
        pytest.param('{ kind = "subentity", name = "finding" }', "severity", id="subentity"),
        pytest.param('{ kind = "subtree", name = "task" }', "status", id="subtree"),
    ],
)
def test_a_valid_view_per_source_kind_loads_and_resolves(
    tmp_path: Path, source_toml: str, field_code: str
) -> None:
    _write_override(
        tmp_path,
        f"""
[views.probe]
source = {source_toml}
fields = [
  {{ code = "id", label = "Id" }},
  {{ code = "{field_code}", label = "Field" }},
]
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    view = spec.views["probe"]
    assert [f.code for f in view.fields] == ["id", field_code]


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
    _write_override(
        tmp_path,
        f"""
[views.probe]
source = {source_toml}
fields = [ {{ code = "id", label = "Id" }} ]
""",
    )
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    assert expected_substring in str(excinfo.value)


@pytest.mark.parametrize(
    ("source_toml", "bad_field_code"),
    [
        pytest.param('{ kind = "ref", name = "related" }', "severity", id="ref-badge-field"),
        pytest.param(
            '{ kind = "subentity", name = "story" }', "severity", id="subentity-undeclared-field"
        ),
        pytest.param('{ kind = "subtree", name = "task" }', "bogus", id="subtree-undeclared-field"),
    ],
)
def test_a_field_the_source_cannot_resolve_is_refused(
    tmp_path: Path, source_toml: str, bad_field_code: str
) -> None:
    """A ``ref`` source has no single type its records all share, so *no* badge field is ever
    resolvable for it — even one a bundled type declares (``severity`` here, via ``bug``).
    ``story`` (a subentity kind) declares no fields at all, so any badge-field code is refused."""
    _write_override(
        tmp_path,
        f"""
[views.probe]
source = {source_toml}
fields = [ {{ code = "{bad_field_code}", label = "Bad" }} ]
""",
    )
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    assert bad_field_code in str(excinfo.value)
    assert "neither a base attribute" in str(excinfo.value)


def test_a_view_with_no_fields_is_refused(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[views.probe]
source = { kind = "subentity", name = "finding" }
fields = []
""",
    )
    with pytest.raises(SquadsError, match="must declare at least one field"):
        load_workflow_spec(squad_dir=tmp_path)


def test_duplicate_field_codes_are_refused(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[views.probe]
source = { kind = "subentity", name = "finding" }
fields = [
  { code = "id", label = "Id" },
  { code = "id", label = "Also id" },
]
""",
    )
    with pytest.raises(SquadsError, match="duplicate field code"):
        load_workflow_spec(squad_dir=tmp_path)


@pytest.mark.parametrize(
    ("declaration", "expected_substring"),
    [
        pytest.param('group_by = "nope"', "group_by 'nope'", id="group-by-unresolvable"),
        pytest.param('order_by = ["nope"]', "order_by 'nope'", id="order-by-unresolvable"),
    ],
)
def test_group_by_and_order_by_must_name_a_declared_field(
    tmp_path: Path, declaration: str, expected_substring: str
) -> None:
    _write_override(
        tmp_path,
        f"""
[views.probe]
source = {{ kind = "subentity", name = "finding" }}
fields = [ {{ code = "id", label = "Id" }} ]
{declaration}
""",
    )
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    assert expected_substring in str(excinfo.value)


def test_group_by_and_order_by_may_name_a_declared_field(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[views.probe]
source = { kind = "subentity", name = "finding" }
fields = [ { code = "id", label = "Id" }, { code = "status", label = "Status" } ]
group_by = "status"
order_by = ["id"]
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert spec.views["probe"].group_by == "status"
    assert spec.views["probe"].order_by == ["id"]


# --------------------------------------------------------------------------- collect-all + selected


def test_lint_reports_every_view_violation_in_one_run_not_only_the_first(tmp_path: Path) -> None:
    from squads._workflow._loader import lint_workflow_spec

    _write_override(
        tmp_path,
        """
[views.bad_ref]
source = { kind = "ref", name = "nope" }
fields = [ { code = "id", label = "Id" } ]

[views.bad_field]
source = { kind = "subentity", name = "story" }
fields = [ { code = "severity", label = "Bad" } ]
""",
    )
    findings = lint_workflow_spec(tmp_path)
    messages = [f[2] for f in findings]
    assert any("bad_ref" in m for m in messages)
    assert any("bad_field" in m for m in messages)


def test_selected_may_drop_a_declared_view(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[views.kept]
source = { kind = "ref", name = "related" }
fields = [ { code = "id", label = "Id" } ]

[views.dropped]
source = { kind = "ref", name = "related" }
fields = [ { code = "id", label = "Id" } ]

[selected]
views = ["kept"]
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert set(spec.views) == {"kept"}


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
fields = [ { code = "id", label = "Id" } ]

[selected]
ref_kinds = [
  "related", "blocks", "depends-on", "implements", "fixes",
  "addresses", "supersedes", "duplicates", "scopes",
]
""",
    )
    with pytest.raises(SquadsError, match="dropped from a \\[selected\\] list"):
        load_workflow_spec(squad_dir=tmp_path)
