"""The generic badge/collection/field engine: every item badge axis (priority,
severity, or a project-declared one) is spec vocabulary resolved through ``fields_for()`` /
``collection()`` — proven once here, not re-tested per axis. Includes the fail-closed cluster
(P4): duplicate field codes, reserved-key shadowing, dangling collection references, a default
that isn't one of its own collection's badges, and an unordered collection (reserved, not yet
supported).
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from squads._errors import SquadsError
from squads._workflow import load_workflow_spec
from squads._workflow._models import (
    Badge,
    Collection,
    Field,
    ItemSpec,
    SubentityKindSpec,
    WorkflowSpec,
)


@pytest.fixture(scope="module")
def spec() -> WorkflowSpec:
    return load_workflow_spec()


def _rebuild(spec: WorkflowSpec, **overrides: object) -> WorkflowSpec:
    payload = {
        "items": spec.items,
        "statuses": spec.statuses,
        "lifecycles": spec.lifecycles,
        "prefix_to_type": spec.prefix_to_type,
        "alias_to_type": spec.alias_to_type,
        "collections": spec.collections,
        "subentity_kinds": spec.subentity_kinds,
        "roles": spec.roles,
        **overrides,
    }
    return WorkflowSpec.model_validate(payload)


# --------------------------------------------------------------------------- bundled axes are
# byte-identical to the retired Priority/Severity enums (the de-typing regression floor)


def test_priority_collection_is_byte_identical_to_the_retired_enum(spec: WorkflowSpec) -> None:
    coll = spec.collections["priority"]
    assert coll.ordered is True
    assert coll.default is None
    assert [(b.code, b.label, b.emoji) for b in coll.badges] == [
        ("urgent", "Urgent", "🔴"),
        ("high", "High", "🟠"),
        ("medium", "Medium", "🟡"),
        ("low", "Low", "🟢"),
    ]


def test_severity_collection_is_byte_identical_to_the_retired_enum(spec: WorkflowSpec) -> None:
    coll = spec.collections["severity"]
    assert coll.ordered is True
    assert coll.default == "medium"
    assert [(b.code, b.label, b.emoji) for b in coll.badges] == [
        ("critical", "Critical", "🔴"),
        ("high", "High", "🟠"),
        ("medium", "Medium", "🟡"),
        ("low", "Low", "🟢"),
        ("info", "Info", "🔵"),
    ]


def test_priority_is_declared_on_every_bundled_work_type_but_no_meta_type(
    spec: WorkflowSpec,
) -> None:
    for t in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
        assert "priority" in {f.code for f in spec.items[t].fields}
    for t in ("role", "skill", "operator"):
        assert "priority" not in {f.code for f in spec.items[t].fields}


def test_severity_is_declared_only_on_bug_and_the_finding_subentity_kind(
    spec: WorkflowSpec,
) -> None:
    assert "severity" in {f.code for f in spec.items["bug"].fields}
    assert "severity" in {f.code for f in spec.subentity_kinds["finding"].fields}
    for t in spec.items:
        if t != "bug":
            assert "severity" not in {f.code for f in spec.items[t].fields}


def test_bug_severity_is_optional_but_finding_severity_is_required_both_defaulting_medium(
    spec: WorkflowSpec,
) -> None:
    bug_severity = next(f for f in spec.items["bug"].fields if f.code == "severity")
    assert bug_severity.required is False and bug_severity.default == "medium"
    finding_severity = next(
        f for f in spec.subentity_kinds["finding"].fields if f.code == "severity"
    )
    assert finding_severity.required is True and finding_severity.default == "medium"


# --------------------------------------------------------------------------- P1: the generic
# resolution mechanism, once


def test_fields_for_resolves_by_item_type_and_by_subentity_kind(spec: WorkflowSpec) -> None:
    assert {f.code for f in spec.fields_for("task")} == {"priority"}
    assert {f.code for f in spec.fields_for("finding")} == {"severity"}


def test_fields_for_an_unknown_name_degrades_to_empty_not_a_crash(spec: WorkflowSpec) -> None:
    assert spec.fields_for("not-a-real-type-or-kind") == []


def test_collection_accessor_resolves_by_code_and_raises_cleanly_on_unknown(
    spec: WorkflowSpec,
) -> None:
    assert spec.collection("priority") is spec.collections["priority"]
    with pytest.raises(KeyError):
        spec.collection("not-a-real-collection")


# --------------------------------------------------------------------------- P4: fail-closed
# validation cluster


def test_duplicate_field_code_within_one_type_fails_closed(spec: WorkflowSpec) -> None:
    task = spec.items["task"]
    dup_fields = [*task.fields, Field(code="priority", label="Priority 2", collection="priority")]
    with pytest.raises(SquadsError, match="duplicate field code 'priority'"):
        _rebuild(spec, items={**spec.items, "task": task.model_copy(update={"fields": dup_fields})})


@pytest.mark.parametrize(
    ("owner_type", "reserved_code"),
    [("task", "status"), ("task", "prefix")],
)
def test_field_code_shadowing_a_reserved_frontmatter_key_fails_closed(
    spec: WorkflowSpec, owner_type: str, reserved_code: str
) -> None:
    """'prefix' is a *tolerated* legacy key (Item.id always wins, never written) — NOT exempt
    like 'path'; a live field coded 'prefix' would be silently read-and-discarded on round-trip,
    so it must stay reserved."""
    owner = spec.items[owner_type]
    bad_fields = [Field(code=reserved_code, label="Shadow", collection="priority")]
    bad_owner = owner.model_copy(update={"fields": bad_fields})
    with pytest.raises(SquadsError, match=f"field code '{reserved_code}' shadows a reserved"):
        _rebuild(spec, items={**spec.items, owner_type: bad_owner})


def test_field_code_shadowing_a_reserved_key_on_a_subentity_kind_fails_closed(
    spec: WorkflowSpec,
) -> None:
    bad_kind = spec.subentity_kinds["finding"].model_copy(
        update={"fields": [Field(code="story", label="Story2", collection="priority")]}
    )
    with pytest.raises(SquadsError, match="field code 'story' shadows a reserved frontmatter key"):
        _rebuild(spec, subentity_kinds={**spec.subentity_kinds, "finding": bad_kind})


def test_field_with_an_undeclared_collection_fails_closed(spec: WorkflowSpec) -> None:
    task = spec.items["task"]
    bad_fields = [Field(code="impact", label="Impact", collection="not-a-collection")]
    with pytest.raises(SquadsError, match="collection 'not-a-collection' not declared"):
        _rebuild(spec, items={**spec.items, "task": task.model_copy(update={"fields": bad_fields})})


def test_a_default_that_is_not_a_badge_in_its_collection_fails_closed_at_field_and_collection_level(
    spec: WorkflowSpec,
) -> None:
    task = spec.items["task"]
    bad_fields = [
        Field(code="impact", label="Impact", collection="priority", default="not-a-badge"),
    ]
    with pytest.raises(SquadsError, match="default 'not-a-badge' not a badge in collection"):
        _rebuild(spec, items={**spec.items, "task": task.model_copy(update={"fields": bad_fields})})

    bad_collection = spec.collections["severity"].model_copy(update={"default": "nope"})
    with pytest.raises(
        SquadsError, match="collection 'severity': default 'nope' not a declared badge"
    ):
        _rebuild(spec, collections={**spec.collections, "severity": bad_collection})


def test_an_unordered_collection_fails_closed_directly_and_through_the_override_loader(
    spec: WorkflowSpec, tmp_path: Path
) -> None:
    """Ordered-only for now — ``ordered`` stays in the schema, but an unordered collection must
    fail load rather than silently rank badges by declaration order."""
    bad_collection = spec.collections["severity"].model_copy(update={"ordered": False})
    with pytest.raises(
        SquadsError, match="collection 'severity': unordered collections are not supported yet"
    ):
        _rebuild(spec, collections={**spec.collections, "severity": bad_collection})

    override_dir = tmp_path / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        '[collections.level]\nlabel = "Level"\nordered = false\n'
        'badges = [{ code = "high", label = "High" }]\n',
        encoding="utf-8",
    )
    with pytest.raises(
        SquadsError, match="collection 'level': unordered collections are not supported yet"
    ):
        load_workflow_spec(squad_dir=tmp_path)


def test_a_required_field_with_no_default_fails_closed_but_resolves_via_the_collection_default(
    spec: WorkflowSpec,
) -> None:
    task = spec.items["task"]
    no_default = [Field(code="impact", label="Impact", collection="priority", required=True)]
    bad_task = task.model_copy(update={"fields": no_default})
    with pytest.raises(SquadsError, match="required with no resolvable default badge"):
        _rebuild(spec, items={**spec.items, "task": bad_task})

    via_collection = [Field(code="impact", label="Impact", collection="severity", required=True)]
    result = _rebuild(
        spec, items={**spec.items, "task": task.model_copy(update={"fields": via_collection})}
    )
    assert result.fields_for("task")[0].code == "impact"


def test_loader_field_parse_error_names_the_owning_type() -> None:
    from squads._workflow._loader import _build_spec  # pyright: ignore[reportPrivateUsage]

    raw = {
        "lifecycles": {"work": {"initial": "Draft", "transitions": {"Draft": []}}},
        "statuses": {"Draft": {}},
        "items": {
            "task": {
                "prefix": "TASK",
                "folder": "tasks",
                "lifecycle": "work",
                "fields": [{"code": "priority"}],  # missing required label/collection
            },
        },
    }
    with pytest.raises(SquadsError, match=r"items\.task field"):
        _build_spec(raw)


# --------------------------------------------------------------------------- P1: a custom
# collection reused by two distinctly-coded fields on one type


def test_a_custom_collection_reused_by_two_relabeled_fields_on_one_type(spec: WorkflowSpec) -> None:
    level = Collection(
        label="Level",
        ordered=True,
        badges=[
            Badge(code="high", label="High", emoji="🔴"),
            Badge(code="low", label="Low", emoji="🟢"),
        ],
    )
    incident = ItemSpec(
        prefix="INC",
        folder="incidents",
        lifecycle="work",
        fields=[
            Field(code="impact", label="Impact", collection="level"),
            Field(code="urgency", label="Urgency", collection="level"),
        ],
    )
    result = _rebuild(
        spec,
        items={**spec.items, "incident": incident},
        collections={**spec.collections, "level": level},
        prefix_to_type={**spec.prefix_to_type, "INC": "incident"},
    )
    assert {f.code for f in result.fields_for("incident")} == {"impact", "urgency"}
    assert result.collection("level").badge_codes == {"high", "low"}


# --------------------------------------------------------------------------- extra="forbid"


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (Badge, {"code": "x", "label": "X", "bogus": True}),
        (Collection, {"label": "X", "bogus": True}),
        (Field, {"code": "x", "label": "X", "collection": "priority", "bogus": True}),
        (
            SubentityKindSpec,
            {
                "lifecycle": "x",
                "completion": "y",
                "plural": "xs",
                "local_prefix": "X",
                "bogus": True,
            },
        ),
    ],
    ids=["Badge", "Collection", "Field", "SubentityKindSpec"],
)
def test_badge_domain_models_reject_an_unknown_key(model: type, payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model.model_validate(payload)


# --------------------------------------------------------------------------- override support:
# new collection/field/subentity_kind additive; redefining a builtin one raises


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


def test_override_adds_a_new_collection_and_field_leaving_bundled_ones_untouched(
    tmp_path: Path,
) -> None:
    _write_override(
        tmp_path,
        """
[collections.level]
label = "Level"
ordered = true
badges = [
  { code = "high", label = "High", emoji = "\U0001f534" },
  { code = "low", label = "Low", emoji = "\U0001f7e2" },
]

[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done"]
Done = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
fields = [{ code = "impact", label = "Impact", collection = "level" }]
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert {b.code for b in spec.collections["level"].badges} == {"high", "low"}
    assert [f.code for f in spec.fields_for("incident")] == ["impact"]
    assert "priority" in spec.collections
    assert [f.code for f in spec.fields_for("task")] == ["priority"]


def test_override_adds_a_new_subentity_kind_leaving_bundled_kinds_untouched(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[lifecycles.action]
initial = "Open"
[lifecycles.action.transitions]
Open = ["Done"]
Done = []

[subentity_kinds.action]
lifecycle = "action"
completion = "Done"
plural = "actions"
local_prefix = "AC"
fields = [{ code = "priority", label = "Priority", collection = "priority" }]
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert [f.code for f in spec.fields_for("action")] == ["priority"]
    assert spec.subentity_completion("action") == "Done"
    assert [f.code for f in spec.fields_for("finding")] == ["severity"]  # untouched


@pytest.mark.parametrize(
    ("toml", "match"),
    [
        ('[collections.priority]\nlabel = "Renamed"\nordered = true\nbadges = []\n', "priority"),
        ("[subentity_kinds.finding]\nfields = []\n", "finding"),
    ],
    ids=["collection", "subentity_kind"],
)
def test_redefining_a_builtin_collection_or_subentity_kind_raises(
    tmp_path: Path, toml: str, match: str
) -> None:
    _write_override(tmp_path, toml)
    with pytest.raises(SquadsError, match=f"may not redefine built-in .* '{match}'"):
        load_workflow_spec(squad_dir=tmp_path)
