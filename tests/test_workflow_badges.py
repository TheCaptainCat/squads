"""Tests for the additive Badge/Collection/Field spec schema (workflow badge-collection model).

Covers:
- The bundled priority/severity collections + fields reproduce today's Priority/Severity
  enum codes/labels/emoji/default exactly (byte-identical, no-override characterization).
- fields_for()/collection() accessors, for item types AND sub-entity kinds.
- Fail-closed validation: duplicate field code, reserved-key collision, unresolved
  collection, invalid default badge, required field with no resolvable default.
- A custom collection reused by two distinctly-coded fields on one type.
- Additive-only override support: new collections/subentity_kinds accepted; redefining a
  built-in collection or subentity_kinds entry raises.
- extra="forbid" on the new models.

Does NOT test runtime consumption — Priority/Severity still drive runtime this pass; this
is the parallel vocabulary alongside it (the next task switches the engine onto it).
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from squads._errors import SquadsError
from squads._models._enums import (
    DEFAULT_SEVERITY,
    PRIORITY_EMOJI,
    SEVERITY_EMOJI,
    Priority,
    Severity,
)
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import (
    Badge,
    Collection,
    Field,
    ItemSpec,
    SubentityKindSpec,
    WorkflowSpec,
)

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="module")
def spec() -> WorkflowSpec:
    return load_workflow_spec()


# ---------------------------------------------------------------------------
# Byte-identical bundled collections (vs the still-live Priority/Severity enums)
# ---------------------------------------------------------------------------


def test_priority_collection_matches_enum_exactly(spec: WorkflowSpec) -> None:
    coll = spec.collections["priority"]
    assert coll.ordered is True
    assert coll.default is None
    assert [b.code for b in coll.badges] == [p.value for p in Priority]
    for b in coll.badges:
        assert b.emoji == PRIORITY_EMOJI[Priority(b.code)]
        assert b.label == b.code.capitalize()


def test_severity_collection_matches_enum_exactly(spec: WorkflowSpec) -> None:
    coll = spec.collections["severity"]
    assert coll.ordered is True
    assert coll.default == DEFAULT_SEVERITY.value
    assert [b.code for b in coll.badges] == [s.value for s in Severity]
    for b in coll.badges:
        assert b.emoji == SEVERITY_EMOJI[Severity(b.code)]
        assert b.label == b.code.capitalize()


def test_priority_field_on_every_bundled_work_type(spec: WorkflowSpec) -> None:
    """Every bundled work type (not the 3 meta-types) carries a priority field."""
    for t in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
        codes = {f.code for f in spec.items[t].fields}
        assert "priority" in codes, f"{t!r} missing the bundled priority field"
    for t in ("role", "skill", "operator"):
        codes = {f.code for f in spec.items[t].fields}
        assert "priority" not in codes, f"meta-type {t!r} should not carry priority"


def test_severity_field_only_on_bug_and_finding(spec: WorkflowSpec) -> None:
    bug_codes = {f.code for f in spec.items["bug"].fields}
    assert "severity" in bug_codes
    finding_codes = {f.code for f in spec.subentity_kinds["finding"].fields}
    assert "severity" in finding_codes
    for t in spec.items:
        if t != "bug":
            assert "severity" not in {f.code for f in spec.items[t].fields}


def test_bug_severity_field_optional_finding_severity_required(spec: WorkflowSpec) -> None:
    bug_severity = next(f for f in spec.items["bug"].fields if f.code == "severity")
    assert bug_severity.required is False
    assert bug_severity.default == "medium"

    finding_severity = next(
        f for f in spec.subentity_kinds["finding"].fields if f.code == "severity"
    )
    assert finding_severity.required is True
    assert finding_severity.default == "medium"


# ---------------------------------------------------------------------------
# Accessors: fields_for() / collection()
# ---------------------------------------------------------------------------


def test_fields_for_item_type(spec: WorkflowSpec) -> None:
    codes = {f.code for f in spec.fields_for("task")}
    assert codes == {"priority"}


def test_fields_for_subentity_kind(spec: WorkflowSpec) -> None:
    codes = {f.code for f in spec.fields_for("finding")}
    assert codes == {"severity"}


def test_fields_for_unknown_name_returns_empty(spec: WorkflowSpec) -> None:
    assert spec.fields_for("not-a-real-type-or-kind") == []


def test_collection_accessor(spec: WorkflowSpec) -> None:
    assert spec.collection("priority") is spec.collections["priority"]


def test_collection_accessor_unknown_code_raises(spec: WorkflowSpec) -> None:
    with pytest.raises(KeyError):
        spec.collection("not-a-real-collection")


# ---------------------------------------------------------------------------
# Fail-closed validation: field-code uniqueness + reserved-key collision
# ---------------------------------------------------------------------------


def _rebuild(spec: WorkflowSpec, **overrides: object) -> WorkflowSpec:
    """Rebuild a WorkflowSpec from *spec*'s own fields, with the given overrides."""
    payload = {
        "items": spec.items,
        "statuses": spec.statuses,
        "lifecycles": spec.lifecycles,
        "prefix_to_type": spec.prefix_to_type,
        "alias_to_type": spec.alias_to_type,
        "collections": spec.collections,
        "subentity_kinds": spec.subentity_kinds,
        **overrides,
    }
    return WorkflowSpec.model_validate(payload)


def test_duplicate_field_code_within_one_type_fails_closed(spec: WorkflowSpec) -> None:
    task = spec.items["task"]
    dup_fields = [*task.fields, Field(code="priority", label="Priority 2", collection="priority")]
    new_items = {**spec.items, "task": task.model_copy(update={"fields": dup_fields})}
    with pytest.raises(SquadsError, match="duplicate field code 'priority'"):
        _rebuild(spec, items=new_items)


def test_field_code_shadowing_reserved_key_fails_closed(spec: WorkflowSpec) -> None:
    task = spec.items["task"]
    bad_fields = [Field(code="status", label="Status2", collection="priority")]
    new_items = {**spec.items, "task": task.model_copy(update={"fields": bad_fields})}
    with pytest.raises(SquadsError, match="field code 'status' shadows a reserved frontmatter key"):
        _rebuild(spec, items=new_items)


def test_field_code_shadowing_reserved_key_on_subentity_kind_fails_closed(
    spec: WorkflowSpec,
) -> None:
    bad_kind = SubentityKindSpec(
        fields=[Field(code="story", label="Story2", collection="priority")]
    )
    new_kinds = {**spec.subentity_kinds, "finding": bad_kind}
    with pytest.raises(SquadsError, match="field code 'story' shadows a reserved frontmatter key"):
        _rebuild(spec, subentity_kinds=new_kinds)


def test_priority_and_severity_codes_are_not_reserved(spec: WorkflowSpec) -> None:
    """The bundled priority/severity fields keep their literal code — the reserved-key
    check must exempt exactly those two, or the bundled defaults couldn't load at all."""
    assert spec is not None  # the bundled spec (with its priority/severity fields) loaded clean


# ---------------------------------------------------------------------------
# Fail-closed validation: collection referential integrity
# ---------------------------------------------------------------------------


def test_field_with_undeclared_collection_fails_closed(spec: WorkflowSpec) -> None:
    task = spec.items["task"]
    bad_fields = [Field(code="impact", label="Impact", collection="not-a-collection")]
    new_items = {**spec.items, "task": task.model_copy(update={"fields": bad_fields})}
    with pytest.raises(SquadsError, match="collection 'not-a-collection' not declared"):
        _rebuild(spec, items=new_items)


def test_field_default_not_a_badge_in_collection_fails_closed(spec: WorkflowSpec) -> None:
    task = spec.items["task"]
    bad_fields = [
        Field(code="impact", label="Impact", collection="priority", default="not-a-badge"),
    ]
    new_items = {**spec.items, "task": task.model_copy(update={"fields": bad_fields})}
    with pytest.raises(SquadsError, match="default 'not-a-badge' not a badge in collection"):
        _rebuild(spec, items=new_items)


def test_collection_level_default_not_a_badge_fails_closed(spec: WorkflowSpec) -> None:
    bad_collection = spec.collections["severity"].model_copy(update={"default": "nope"})
    new_collections = {**spec.collections, "severity": bad_collection}
    with pytest.raises(
        SquadsError, match="collection 'severity': default 'nope' not a declared badge"
    ):
        _rebuild(spec, collections=new_collections)


def test_required_field_with_no_resolvable_default_fails_closed(spec: WorkflowSpec) -> None:
    task = spec.items["task"]
    bad_fields = [Field(code="impact", label="Impact", collection="priority", required=True)]
    new_items = {**spec.items, "task": task.model_copy(update={"fields": bad_fields})}
    with pytest.raises(SquadsError, match="required with no resolvable default badge"):
        _rebuild(spec, items=new_items)


def test_required_field_resolving_via_collection_default_succeeds(spec: WorkflowSpec) -> None:
    """A required field with no field-level default is fine when the collection has one."""
    task = spec.items["task"]
    ok_fields = [Field(code="impact", label="Impact", collection="severity", required=True)]
    new_items = {**spec.items, "task": task.model_copy(update={"fields": ok_fields})}
    result = _rebuild(spec, items=new_items)
    assert result.fields_for("task")[0].code == "impact"


# ---------------------------------------------------------------------------
# Custom collection reused by two distinctly-coded fields on one type
# ---------------------------------------------------------------------------


def test_custom_collection_reused_by_two_relabeled_fields(spec: WorkflowSpec) -> None:
    """Two fields off ONE collection with distinct codes/labels — the reuse case."""
    level = Collection(
        label="Level",
        ordered=True,
        badges=[
            Badge(code="high", label="High", emoji="🔴"),
            Badge(code="low", label="Low", emoji="🟢"),
        ],
    )
    new_collections = {**spec.collections, "level": level}
    incident = ItemSpec(
        prefix="INC",
        folder="incidents",
        lifecycle="work",
        fields=[
            Field(code="impact", label="Impact", collection="level"),
            Field(code="urgency", label="Urgency", collection="level"),
        ],
    )
    new_items = {**spec.items, "incident": incident}
    new_prefix_to_type = {**spec.prefix_to_type, "INC": "incident"}
    result = _rebuild(
        spec, items=new_items, collections=new_collections, prefix_to_type=new_prefix_to_type
    )
    codes = {f.code for f in result.fields_for("incident")}
    assert codes == {"impact", "urgency"}
    assert result.collection("level").badge_codes == {"high", "low"}


# ---------------------------------------------------------------------------
# extra="forbid" on the new models
# ---------------------------------------------------------------------------


def test_badge_rejects_unknown_key() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Badge.model_validate({"code": "x", "label": "X", "bogus": True})


def test_collection_rejects_unknown_key() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Collection.model_validate({"label": "X", "bogus": True})


def test_field_rejects_unknown_key() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Field.model_validate({"code": "x", "label": "X", "collection": "priority", "bogus": True})


def test_subentity_kind_spec_rejects_unknown_key() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SubentityKindSpec.model_validate({"fields": [], "bogus": True})


# ---------------------------------------------------------------------------
# Loader: bundled TOML parses [collections.*] and .fields correctly
# ---------------------------------------------------------------------------


def test_loader_field_parse_error_has_context() -> None:
    """A malformed field entry in items.* raises SquadsError naming the owning type."""
    from squads._workflow._loader import _build_spec  # pyright: ignore[reportPrivateUsage]

    raw = {
        "lifecycles": {"work": {"initial": "Draft", "transitions": {"Draft": []}}},
        "statuses": {"Draft": {"terminal": True}},
        "items": {
            "task": {
                "prefix": "TASK",
                "folder": "tasks",
                "lifecycle": "work",
                "fields": [{"code": "priority"}],  # missing required 'label'/'collection'
            },
        },
    }
    with pytest.raises(SquadsError, match=r"items\.task field"):
        _build_spec(raw)


# ---------------------------------------------------------------------------
# Additive-only override support: new collections / subentity_kinds
# ---------------------------------------------------------------------------


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


def test_override_can_add_a_new_collection_and_field(tmp_path: Path) -> None:
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
    assert "level" in spec.collections
    assert {b.code for b in spec.collections["level"].badges} == {"high", "low"}
    assert [f.code for f in spec.fields_for("incident")] == ["impact"]
    # Bundled collections/fields stay untouched.
    assert "priority" in spec.collections
    assert [f.code for f in spec.fields_for("task")] == ["priority"]


def test_override_can_add_a_new_subentity_kind_field(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[subentity_kinds.subtask]
fields = [{ code = "priority", label = "Priority", collection = "priority" }]
""",
    )
    spec = load_workflow_spec(squad_dir=tmp_path)
    assert [f.code for f in spec.fields_for("subtask")] == ["priority"]
    # The finding kind (bundled) is untouched.
    assert [f.code for f in spec.fields_for("finding")] == ["severity"]


def test_override_redefining_builtin_collection_raises(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[collections.priority]
label = "Renamed"
ordered = true
badges = []
""",
    )
    with pytest.raises(SquadsError, match="may not redefine built-in collection 'priority'"):
        load_workflow_spec(squad_dir=tmp_path)


def test_override_redefining_builtin_subentity_kind_raises(tmp_path: Path) -> None:
    _write_override(
        tmp_path,
        """
[subentity_kinds.finding]
fields = []
""",
    )
    with pytest.raises(
        SquadsError, match="may not redefine built-in subentity_kinds entry 'finding'"
    ):
        load_workflow_spec(squad_dir=tmp_path)
