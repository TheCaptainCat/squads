"""TypeSpec/StatusSpec capability-flag reification — the generic replacement for the
hardcoded per-type checks the old enum suite used to need: ``category`` is ``"roster"`` only for
role/skill/operator; ``subentity_kind`` degrades to ``None`` (not KeyError) for an
undeclared type; ``parent_required`` is set only where declared (task); ``ref_rules`` is
populated only for task (fixes/addresses) and decision (supersedes), empty elsewhere, and
each ``RefRule``'s own fields are well-typed; ``parent_hint`` uses the declared hint text
rather than re-deriving a bundled-literal guess; ``extra_fields`` is declared on guide/review
and empty where undeclared; and the ``Superseded`` status carries a machine ``role`` that no
other bundled status carries.
"""

from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, RefRule, StatusSpec, WorkflowSpec

_ROSTER_TYPES = ("role", "skill", "operator")
_WORK_TYPES = ("epic", "feature", "task", "bug", "decision", "review", "guide")


def _spec() -> WorkflowSpec:
    return load_workflow_spec()


def test_category_is_roster_only_for_role_skill_and_operator() -> None:
    spec = _spec()
    for t in _ROSTER_TYPES:
        assert spec.items[t].category == "roster"
    for t in _WORK_TYPES:
        assert spec.items[t].category != "roster"


def test_subentity_kind_is_set_only_where_declared() -> None:
    spec = _spec()
    assert spec.items["feature"].subentity_kind == "story"
    assert spec.items["task"].subentity_kind == "subtask"
    assert spec.items["review"].subentity_kind == "finding"
    for t in ("epic", "bug", "decision", "guide", *_ROSTER_TYPES):
        assert spec.items[t].subentity_kind is None


def test_item_subentity_kind_degrades_to_none_for_an_undeclared_type() -> None:
    assert _spec().item_subentity_kind("not-a-real-type") is None


def test_parent_required_is_set_only_on_task() -> None:
    spec = _spec()
    assert spec.items["task"].parent_required == "feature"
    for t in ("epic", "feature", "bug", "decision", "review", "guide", *_ROSTER_TYPES):
        assert spec.items[t].parent_required is None


def test_ref_rules_populated_only_for_task_and_decision() -> None:
    spec = _spec()
    assert {r.kind for r in spec.items["task"].ref_rules} >= {"fixes", "addresses"}
    assert {r.kind for r in spec.items["decision"].ref_rules} >= {"supersedes"}
    for t in ("epic", "feature", "bug", "review", "guide", *_ROSTER_TYPES):
        assert spec.items[t].ref_rules == []


def test_ref_rule_fields_are_well_typed() -> None:
    for rule in _spec().items["task"].ref_rules:
        assert isinstance(rule.kind, str) and rule.kind
        assert isinstance(rule.hint, str)


def test_parent_hint_uses_the_declared_hint_text_not_a_re_derived_literal() -> None:
    """Proven on a renamed type/parent with a custom ref rule and hint — if parent_hint were
    still re-detecting 'fixes'/'addresses' by literal string and fabricating bundled prose,
    this custom hint text would never surface."""
    custom = WorkflowSpec.model_validate(
        {
            "items": {
                "role": ItemSpec(
                    prefix="ROLE", folder="roles", lifecycle="agent", category="roster"
                ),
                "skill": ItemSpec(
                    prefix="SKILL", folder="skills", lifecycle="agent", category="roster"
                ),
                "operator": ItemSpec(
                    prefix="OP", folder="operators", lifecycle="agent", category="roster"
                ),
                "feat": ItemSpec(prefix="FEAT", folder="feats", lifecycle="work"),
                "chore": ItemSpec(
                    prefix="CHORE",
                    folder="chores",
                    lifecycle="work",
                    parents=["feat"],
                    ref_rules=[RefRule(kind="mends", hint="see `sq ref add <chore> <id>`")],
                ),
            },
            "statuses": {
                "Draft": StatusSpec(terminal=False),
                "Active": StatusSpec(terminal=False),
                "Archived": StatusSpec(terminal=True),
                "Done": StatusSpec(terminal=True),
            },
            "lifecycles": {
                "agent": Lifecycle(
                    initial="Draft", transitions={"Draft": ["Active"], "Active": ["Archived"]}
                ),
                "work": Lifecycle(initial="Draft", transitions={"Draft": ["Done"]}),
            },
            "prefix_to_type": {},
            "alias_to_type": {},
        }
    )
    hint = custom.parent_hint("chore")
    assert hint == "a chore's parent must be of type feat; see `sq ref add <chore> <id>`"


def test_extra_fields_declared_on_guide_and_review_empty_where_undeclared() -> None:
    spec = _spec()
    assert spec.item_extra_fields("guide") == ["tags"]
    assert spec.item_extra_fields("review") == ["target_ref"]
    assert spec.item_extra_fields("task") == []


def test_exactly_superseded_inprogress_and_active_carry_a_bundled_role() -> None:
    """Superseded carries the terminal ``"superseded"`` role; InProgress (work-item) and
    Active (roster) carry the working ``"active"`` role. Every other bundled status carries
    no role at all."""
    spec = _spec()
    expected_roles = {
        "Superseded": "superseded",
        "InProgress": "active",
        "Active": "active",
    }
    for name, ss in spec.statuses.items():
        assert ss.role == expected_roles.get(name)
