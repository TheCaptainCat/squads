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


def test_exactly_one_relation_view_ships_bundled_and_none_are_type_attached() -> None:
    """Naming a bundled ref kind / sub-entity kind / item type as a source would ordinarily
    couple every project that later drops or renames it (an ordinary, already-tested
    customisation — see ``test_workflow_subentity_kinds_cli.py``'s dropped-kind cases) to
    keeping a view nothing consumes — the reason the mechanism itself shipped with no
    *relation*-sourced view beyond one. The milestone roll-up is that one exception.

    It is placed the same way the other five bundled views are: a ``sq:view:<name>`` tag
    seeded straight into its host's creation template (``templates/items/milestone.md.j2``),
    never an ``items.<type>.views`` attachment — no bundled type declares one any more, which
    is what this test pins. ``milestone_rollup`` is therefore freestanding: deselecting
    ``milestone`` changes nothing about whether it stays declared
    (``tests/unit/test_milestone_view_deselect_cascade.py`` covers that, and keeps the
    now-unreachable-against-bundled-vocabulary type-owned-prune mechanism itself covered
    through a simulated bundled attachment). Every OTHER bundled relation-sourced view stays
    proven through test-only declarations instead (this module and
    ``tests/unit/test_view_expresses_the_subentity_summary_shape.py``).

    The other five bundled views (``role_definition``, ``squads_skill``, ``greeting_skill``,
    ``memory_skill``, ``item_skill``) are non-relation-sourced; their own end-to-end content is
    covered by ``tests/integration/test_role_body_content_generation.py``,
    ``tests/service/test_a_system_skills_definition_is_never_stored_in_its_file.py`` and the
    ``tests/integration/test_*_skill_content_generation.py``/``test_*_skill_generation.py``/
    ``test_item_skill_body_generation.py`` modules — the generic ``role``/``playbook``/``self``
    *mechanism* those five use is what
    ``tests/service/test_role_playbook_self_views_end_to_end.py`` covers instead, against
    test-declared probe views rather than these bundled names."""
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
    for t, ts in spec.items.items():
        assert ts.views == [], f"{t}: unexpected attached views {ts.views}"


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


# --------------------------------------------------------------------------- role / playbook /
# self: no field grammar, and each kind's own name rule


@pytest.mark.parametrize(
    "source_toml",
    [
        pytest.param('{ kind = "role" }', id="role"),
        pytest.param('{ kind = "self" }', id="self"),
        pytest.param('{ kind = "playbook" }', id="playbook-no-name"),
        pytest.param('{ kind = "playbook", name = "task" }', id="playbook-declared-name"),
    ],
)
def test_a_non_relation_source_loads_with_no_fields_declared_at_all(
    tmp_path: Path, source_toml: str
) -> None:
    """``role``/``playbook``/``self`` never reach the fields/``group_by``/``order_by``
    grammar — unlike every relation kind (``test_a_view_with_no_fields_is_refused``), an
    entirely field-less declaration is not an error for any of the three."""
    _write_override(tmp_path, f"[views.probe]\nsource = {source_toml}\n")
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert spec.views["probe"].fields == []


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
        pytest.param(
            '{ kind = "subentity", name = "story" }', "severity", id="subentity-undeclared-field"
        ),
        pytest.param('{ kind = "subtree", name = "task" }', "bogus", id="subtree-undeclared-field"),
    ],
)
def test_a_field_the_source_cannot_resolve_is_refused(
    tmp_path: Path, source_toml: str, bad_field_code: str
) -> None:
    """``story`` (a subentity kind) declares no fields at all, so any badge-field code is
    refused. A ``subtree`` source's declared-field set is exactly its named type's own — see
    ``test_a_subtree_source_field_no_matching_type_carries_is_refused`` for that shape kept
    correctly refused post-amendment. The ``ref`` shape now lives in its own tests below — its
    declared-field vocabulary was narrowed and its message differs."""
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


# --------------------------------------------------------------------------- ref-source field
# codes: a code at least one declared item type carries is projectable; a code no declared
# type carries anywhere stays refused.


def test_a_ref_source_field_no_declared_item_type_carries_is_refused(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[views.probe]
source = { kind = "ref", name = "related" }
fields = [ { code = "id", label = "Id" }, { code = "wibble", label = "Bad" } ]
""",
    )
    with pytest.raises(SquadsError) as excinfo:
        load_workflow_spec(squad_dir=tmp_path)
    message = str(excinfo.value)
    assert "wibble" in message
    assert "not declared by any item type" in message
    # The remedy is performable — never "make a ref kind declare a field", which no spec
    # grammar expresses.
    assert "ref kind" not in message


def test_a_ref_source_field_a_sub_entity_kind_alone_declares_is_still_refused(
    tmp_path: Path,
) -> None:
    """The union is over item *types* only — a ``ref`` source's records are always items,
    never sub-entities (``_record_from_item``) — so a code declared solely on a sub-entity
    kind, by no item type anywhere, stays refused."""
    _write_override(
        tmp_path,
        """
[collections.impact]
label = "Impact"
ordered = true
badges = [ { code = "low", label = "Low" }, { code = "high", label = "High" } ]

[[subentity_kinds.finding.fields]]
code = "impact"
label = "Impact"
collection = "impact"

[views.probe]
source = { kind = "ref", name = "related" }
fields = [ { code = "id", label = "Id" }, { code = "impact", label = "Impact" } ]
""",
    )
    with pytest.raises(SquadsError, match="not declared by any item type"):
        load_workflow_spec(squad_dir=tmp_path)


def test_a_ref_source_may_project_a_field_at_least_one_declared_item_type_carries(
    tmp_path: Path,
) -> None:
    """``priority`` is declared by every bundled work/records type — a ``ref`` source may now
    name it, structurally unblocking the case the bundled ``milestone_rollup`` view exists
    for."""
    _write_override(
        tmp_path,
        """
[views.probe]
source = { kind = "ref", name = "related" }
fields = [ { code = "id", label = "Id" }, { code = "priority", label = "Priority" } ]
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "priority" in {f.code for f in spec.views["probe"].fields}


def test_a_ref_source_may_project_a_field_only_a_roster_type_carries(tmp_path: Path) -> None:
    """Roster types are in scope, deliberately — a ``field_badge_codes``-style
    ``non_roster_types()`` narrowing would refuse an adopter's field declared on ``role``
    while it resolves perfectly for a ref source whose records are role items."""
    _write_override(
        tmp_path,
        """
[collections.impact]
label = "Impact"
ordered = true
badges = [ { code = "low", label = "Low" }, { code = "high", label = "High" } ]

[[items.role.fields]]
code = "impact"
label = "Impact"
collection = "impact"

[views.probe]
source = { kind = "ref", name = "related" }
fields = [ { code = "id", label = "Id" }, { code = "impact", label = "Impact" } ]
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert "impact" in {f.code for f in spec.views["probe"].fields}


def test_a_subtree_source_field_no_matching_type_carries_is_refused(tmp_path: Path) -> None:
    """Scope proof: the amendment touches the ``ref`` branch only. A ``subtree`` source's
    records are already homogeneous (filtered to its own named type by
    ``_resolve_subtree_source``), so its declared-field set was already exactly right and
    stays refused for a code that type does not carry — even one another type carries."""
    _write_override(
        tmp_path,
        """
[views.probe]
source = { kind = "subtree", name = "task" }
fields = [ { code = "id", label = "Id" }, { code = "severity", label = "Sev" } ]
""",
    )
    with pytest.raises(SquadsError, match="neither a base attribute"):
        load_workflow_spec(squad_dir=tmp_path)


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
    """Dropping a genuinely freestanding view — one no item type's own ``views`` list
    attaches — needs no companion edit. ``[selected].views`` here re-selects the bundled
    ``milestone_rollup`` alongside the test-declared ``kept`` view simply to prove a
    re-selected bundled view survives an otherwise-narrowing ``[selected]`` line unchanged —
    milestone_rollup itself is freestanding today (no type attaches it), so omitting it here
    would just drop it too, cleanly, with no reciprocal-attachment refusal to trip; see
    ``test_a_dropped_declared_view_still_attached_by_its_type_is_refused_at_load`` below for
    that refusal's own shape, driven through a project-declared attachment instead."""
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


# --------------------------------------------------------------------------- ItemSpec.views
# reciprocal check — the attached-by-name direction: does a name items.<type>.views carries
# actually resolve, and (for a subentity source) does the attaching type host that kind.


def test_a_dropped_declared_view_still_attached_by_its_type_is_refused_at_load(
    tmp_path: Path,
) -> None:
    """No bundled type carries a ``views`` attachment any more (``milestone_rollup``, the last
    one that did, is placed by a template-seeded tag instead — see
    ``tests/unit/test_milestone_view_deselect_cascade.py``), so this drives the dangling shape
    through a project's own attachment: ``items.milestone`` names ``milestone_rollup`` in its
    own ``views`` list, and ``[selected] views = []`` then drops every declared view including
    it. That dangling attachment is refused at load, naming the type, the dangling view name
    and the ``[selected]`` provenance, rather than surviving until the first
    ``sq milestone <n> show``."""
    _write_override(
        tmp_path, '[items.milestone]\nviews = ["milestone_rollup"]\n\n[selected]\nviews = []\n'
    )
    with pytest.raises(SquadsError, match=r"milestone.*milestone_rollup.*selected\.views"):
        load_workflow_spec(squad_dir=tmp_path)


def test_a_typo_d_view_attachment_is_refused_at_load_not_on_first_show(tmp_path: Path) -> None:
    """A name in ``items.<type>.views`` that was simply never declared as a ``[views]`` entry
    (never mind ``[selected]``) is the same dangling shape, with no deselection to blame."""
    _write_override(
        tmp_path,
        """
[items.milestone]
views = ["milestone_rollup", "typo_view"]
""",
    )
    with pytest.raises(SquadsError, match=r"milestone.*typo_view.*does not name a declared"):
        load_workflow_spec(squad_dir=tmp_path)


def test_a_subentity_source_view_attached_to_a_type_hosting_none_is_refused_at_load(
    tmp_path: Path,
) -> None:
    """A view whose source projects a sub-entity kind may only attach to a type that hosts
    that kind. ``guide`` hosts none, so attaching a ``story``-sourced view to it is refused —
    fully determinable at load, never left to brick every ``sq guide <n> show`` instead."""
    _write_override(
        tmp_path,
        """
[views.story_summary]
source = { kind = "subentity", name = "story" }
fields = [ { code = "id", label = "Id" } ]

[items.guide]
views = ["story_summary"]
""",
    )
    with pytest.raises(SquadsError, match=r"guide.*story_summary.*projects 'story'.*hosts"):
        load_workflow_spec(squad_dir=tmp_path)


def test_a_self_sourced_view_attached_to_a_type_is_refused_at_load(tmp_path: Path) -> None:
    """``items.<type>.views`` may only attach a relation-sourced view — ``self`` resolves to
    the bare host item, which ``squads._views.projection_json`` (the only serializer
    ``build_item_json``'s type-attached ``views`` key calls) has no shape for. Refused here,
    naming the source kind and the attaching type, rather than left to break ``show --json``
    for every item of that type on a spec that loads clean."""
    _write_override(
        tmp_path,
        """
[views.self_card]
source = { kind = "self" }

[items.task]
views = ["self_card"]
""",
    )
    with pytest.raises(SquadsError, match=r"task.*self_card.*'self' source"):
        load_workflow_spec(squad_dir=tmp_path)


def test_a_role_sourced_view_attached_to_a_type_is_refused_at_load(tmp_path: Path) -> None:
    """Same refusal, for a ``role``-sourced view attached to a type that is not even the role
    type — a type-attachment ``resolve_view`` also has no serializer for, so this is refused
    before ``show``/``show --raw`` can crash on it at read time."""
    _write_override(
        tmp_path,
        """
[views.role_card]
source = { kind = "role" }

[items.task]
views = ["role_card"]
""",
    )
    with pytest.raises(SquadsError, match=r"task.*role_card.*'role' source"):
        load_workflow_spec(squad_dir=tmp_path)


def test_sq_workflow_lint_reports_a_dangling_view_attachment_before_any_item_is_read(
    tmp_path: Path,
) -> None:
    """The same refusal, through the collect-all lint entry point rather than the fail-fast
    loader — ``sq workflow lint`` must catch this before ``sq <type> <n> show`` ever would.
    No bundled type carries a ``views`` attachment any more, so this drives the shape through
    a project-declared one, the same as the loader-refusal test above."""
    from squads._workflow._loader import lint_workflow_spec

    _write_override(
        tmp_path, '[items.milestone]\nviews = ["milestone_rollup"]\n\n[selected]\nviews = []\n'
    )
    findings = lint_workflow_spec(tmp_path)
    assert any(
        "milestone" in msg and "milestone_rollup" in msg for _level, _loc, msg, _hint in findings
    )
