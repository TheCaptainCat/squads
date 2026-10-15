"""A bare ref is an edge of the spec's default kind, and both ref-rule checks read it that way.
`ref_rule_target_present` is satisfied by a bare edge or the same edge with the default kind
spelled out when its rule sits on the default kind, and an edge that satisfies it is never
reported by `ref_rule_target_typed`.
"""

import pytest

from _helpers import create_item
from _selection_table import REF_RULE_TARGET_TYPED, member_findings, service_with

pytestmark = pytest.mark.anyio

_PRESENT = "settled with no"
_DEFAULT_KIND_RULE = (
    '[items.feature]\nref_rules = [{ kind = "related", target = "milestone" }]\n'
    'validators = ["ref_rule_target_present:milestone"]\n\n'
    '[items.bug]\nref_rules = [{ kind = "addresses", target = "milestone" }]\n'
    'validators = ["ref_rule_target_present:milestone"]\n'
)


async def _deliver(svc, item_id: str, status: str) -> None:
    await svc.update(item_id, status=status, force=True)


async def test_a_rule_on_the_default_kind_is_satisfied_by_a_bare_or_a_spelled_edge(
    project,
) -> None:
    svc = service_with(project.squad_dir, _DEFAULT_KIND_RULE)
    milestone = (await create_item(svc, "milestone", "m")).item
    bare = (await create_item(svc, "feature", "bare edge")).item
    spelled = (await create_item(svc, "feature", "spelled edge")).item
    none = (await create_item(svc, "feature", "no edge")).item
    other_kind = (await create_item(svc, "bug", "edge of another kind")).item
    right_kind = (await create_item(svc, "bug", "edge of the rule's kind")).item
    no_edge_bug = (await create_item(svc, "bug", "no edge")).item

    await svc.add_ref(bare.id, milestone.id)
    await svc.add_ref(spelled.id, milestone.id, kind="related")
    await svc.add_ref(other_kind.id, milestone.id)
    await svc.add_ref(right_kind.id, milestone.id, kind="addresses")
    for feature in (bare, spelled, none):
        await _deliver(svc, feature.id, "Done")
    for bug in (other_kind, right_kind, no_edge_bug):
        await _deliver(svc, bug.id, "Verified")

    reported = {i.item for i in await svc.check() if _PRESENT in i.message}
    assert reported == {none.id, other_kind.id, no_edge_bug.id}


_EDGES = [
    ("milestone", ""),
    ("milestone", "related"),
    ("task", ""),
    ("task", "related"),
    ("milestone", "targets"),
    ("task", "targets"),
    ("milestone", "implements"),
]


@pytest.mark.parametrize(("target_type", "kind"), _EDGES, ids=lambda v: v or "bare")
async def test_an_edge_that_satisfies_the_presence_check_is_never_typed_wrong(
    project, target_type: str, kind: str
) -> None:
    toml = (
        '[items.feature]\nref_rules = [{ kind = "related", target = "milestone" }]\n'
        'validators = ["ref_rule_target_present:milestone", "ref_rule_target_typed"]\n'
    )
    svc = service_with(project.squad_dir, toml)
    await create_item(svc, "milestone", "m")
    target = (await create_item(svc, target_type, "target")).item
    feature = (await create_item(svc, "feature", "f")).item
    await svc.add_ref(feature.id, target.id, kind=kind)
    await _deliver(svc, feature.id, "Done")

    issues = await svc.check()
    unsatisfied = any(i.item == feature.id and _PRESENT in i.message for i in issues)
    misdirected = bool(member_findings(issues, REF_RULE_TARGET_TYPED))
    assert unsatisfied or not misdirected
    assert misdirected is (target_type != "milestone" and kind in ("", "related"))
