"""The one rule that classifies a role or skill as ``system`` or ``project``, by the shapes the
rule's inputs can take: the slug, whether the role is templated (carries ``tech``), and the spec.
"""

from datetime import UTC, datetime

import pytest

from squads._interactions import item_origin, role_origin, skill_origin
from squads._models._item import Item
from squads._workflow import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

_NOW = datetime(2026, 6, 7, tzinfo=UTC)


def _spec_with_a_declared_type() -> WorkflowSpec:
    base = load_workflow_spec()
    triage = Lifecycle(initial="Open", transitions={"Open": ["Done"], "Done": []})
    zebra = ItemSpec(prefix="ZEB", folder="zebras", lifecycle="triage")
    return WorkflowSpec.model_validate(
        {
            "items": {**base.items, "zebra": zebra},
            "statuses": base.statuses,
            "lifecycles": {**base.lifecycles, "triage": triage},
            "prefix_to_type": {**base.prefix_to_type, "ZEB": "zebra"},
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
            "roles": base.roles,
            "ref_kinds": base.ref_kinds,
            "views": base.views,
        }
    )


def _item(item_type: str, slug: str, **attributes: str) -> Item:
    return Item(
        sequence_id=1,
        type=item_type,
        title=slug,
        slug=slug,
        slug_in_file=True,
        status="Active",
        path=f"{item_type}s/{slug}.md",
        created_at=_NOW,
        updated_at=_NOW,
        attributes=dict(attributes),
    )


#: role shape -> (slug, templated, expected origin)
ROLE_SHAPES = {
    "bundled": ("manager", False, "system"),
    "bundled-with-a-project-override": ("architect", False, "system"),
    "bundled-and-retired": ("devops", False, "system"),
    "templated-developer": ("rust-dev", True, "system"),
    "declared-developer": ("auditor-dev", False, "project"),
    "project-role": ("security-analyst", False, "project"),
    "project-role-ending-in-dev": ("sandbox-dev", False, "project"),
    "bundled-slug-that-is-also-templated": ("manager", True, "system"),
}

#: skill shape -> (slug, expected origin)
SKILL_SHAPES = {
    "bundled": ("squads", "system"),
    "bundled-memory": ("sq-memory", "system"),
    "generated-for-a-bundled-type": ("sq-task", "system"),
    "generated-for-a-declared-type": ("sq-zebra", "system"),
    "generated-for-a-type-the-spec-no-longer-declares": ("sq-nonexistent", "project"),
    "project-skill": ("release-runbook", "project"),
    "project-skill-named-like-a-type": ("task", "project"),
}


@pytest.mark.parametrize("shape", list(ROLE_SHAPES))
def test_role_origin_by_shape(shape: str) -> None:
    slug, templated, expected = ROLE_SHAPES[shape]
    assert role_origin(slug, templated=templated) == expected


@pytest.mark.parametrize("shape", list(ROLE_SHAPES))
def test_item_origin_of_a_role_reads_the_tech_attribute_not_the_slug(shape: str) -> None:
    slug, templated, expected = ROLE_SHAPES[shape]
    item = _item("role", slug, **({"tech": "rust"} if templated else {}))
    assert item_origin(item, load_workflow_spec()) == expected


@pytest.mark.parametrize("shape", list(SKILL_SHAPES))
def test_skill_origin_by_shape(shape: str) -> None:
    slug, expected = SKILL_SHAPES[shape]
    assert skill_origin(slug, _spec_with_a_declared_type()) == expected
    assert item_origin(_item("skill", slug), _spec_with_a_declared_type()) == expected


def test_a_type_a_workflow_override_drops_keeps_its_skill_system() -> None:
    """The membership test is bundled-blind: a type the spec dropped leaves its ``sq-<type>``
    skill classified as it was made."""
    spec = load_workflow_spec()
    assert "zebra" not in spec.items
    assert skill_origin("sq-guide", spec) == "system"
    without_guide = spec.model_copy(
        update={"items": {k: v for k, v in spec.items.items() if k != "guide"}}
    )
    assert skill_origin("sq-guide", without_guide) == "system"
