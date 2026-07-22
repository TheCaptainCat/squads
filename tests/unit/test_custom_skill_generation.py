"""The pure pieces behind a custom type's auto-generated thin skill: which types get one
(``custom_skill_slugs`` — custom, non-roster only, lexical order) and what it says
(``custom_item_skill_commands`` — the standard verb set, embedding the type's own name).
"""

from squads._interactions import (
    bundled_skill_slugs,
    custom_item_skill_commands,
    custom_skill_slugs,
    is_system_skill,
)
from squads._workflow import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec


def _spec_with(**extra_items: ItemSpec) -> WorkflowSpec:
    base = load_workflow_spec()
    triage = Lifecycle(initial="Open", transitions={"Open": ["Done"], "Done": []})
    new_prefix_to_type = dict(base.prefix_to_type)
    for name, item_spec in extra_items.items():
        new_prefix_to_type[item_spec.prefix] = name
    return WorkflowSpec.model_validate(
        {
            "items": {**base.items, **extra_items},
            "statuses": base.statuses,
            "lifecycles": {**base.lifecycles, "triage": triage},
            "prefix_to_type": new_prefix_to_type,
            "alias_to_type": base.alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )


def test_custom_skill_slugs_is_empty_for_the_bundled_spec() -> None:
    assert custom_skill_slugs(load_workflow_spec()) == []


def test_custom_skill_slugs_returns_only_custom_non_meta_types_in_lexical_order() -> None:
    spec = _spec_with(
        zebra=ItemSpec(prefix="ZEB", folder="zebras", lifecycle="triage"),
        alpha=ItemSpec(prefix="ALP", folder="alphas", lifecycle="triage"),
    )
    slugs = custom_skill_slugs(spec)
    assert slugs == sorted(slugs)
    assert slugs.index("sq-alpha") < slugs.index("sq-zebra")
    assert "sq-role" not in slugs and "sq-skill" not in slugs and "sq-operator" not in slugs


def test_is_system_skill_is_true_for_every_bundled_and_custom_type_slug() -> None:
    spec = _spec_with(zebra=ItemSpec(prefix="ZEB", folder="zebras", lifecycle="triage"))
    for slug in bundled_skill_slugs():
        assert is_system_skill(slug, spec)
    for slug in custom_skill_slugs(spec):
        assert is_system_skill(slug, spec)


def test_is_system_skill_is_false_for_an_author_defined_slug() -> None:
    assert not is_system_skill("release-runbook", load_workflow_spec())


def test_custom_item_skill_commands_has_the_standard_verbs_naming_the_type() -> None:
    cmds = custom_item_skill_commands("incident")
    verbs = (
        "create",
        "show",
        "list",
        "update",
        "status",
        "ref",
        "comment",
        "body",
        "remove",
        "retype",
    )
    for verb in verbs:
        assert any(verb in cmd for cmd in cmds), f"verb {verb!r} missing"
    assert any("sq create incident" in cmd for cmd in cmds)
