"""``ref_rule_target_present`` — the advisory currency check keeping a feature's declared
implements edge honest — and the ``RefRule.target`` referential validation it rests on.

Exercised through ``svc.check()`` (the same path ``sq check`` takes) against a real corpus,
never a hand-built ``ValidatorContext``, so the inertness precondition's corpus scan is
genuinely covered rather than assumed.
"""

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._workflow import bundled_spec
from squads._workflow._models import WorkflowSpec

pytestmark = pytest.mark.anyio


def _messages(issues, item_id: str) -> list[str]:
    return [i.message for i in issues if i.item == item_id]


async def test_inert_while_the_corpus_holds_no_item_of_the_target_type(svc):
    """Before any contract exists, a settled feature with no implements edge produces nothing
    — the remedy (an edge into a collection that does not exist) is unavailable."""
    feat = (await create_item(svc, "feature", "f")).item
    for status in ("Ready", "InProgress", "Done"):
        await svc.set_status(feat.id, status)
    assert await svc.check() == []


async def test_warns_once_a_contract_exists_and_the_feature_carries_no_edge(svc):
    await create_item(svc, "contract", "c")
    feat = (await create_item(svc, "feature", "f")).item
    for status in ("Ready", "InProgress", "Done"):
        await svc.set_status(feat.id, status)

    issues = await svc.check()
    matching = [i for i in issues if i.item == feat.id]
    assert len(matching) == 1
    assert matching[0].level == "warn"


async def test_clears_once_the_feature_carries_an_implements_edge_to_a_contract(svc):
    contract = (await create_item(svc, "contract", "c")).item
    feat = (await create_item(svc, "feature", "f")).item
    await svc.add_ref(feat.id, contract.id, kind="implements")
    for status in ("Ready", "InProgress", "Done"):
        await svc.set_status(feat.id, status)

    assert _messages(await svc.check(), feat.id) == []


async def test_an_implements_edge_to_something_other_than_a_contract_does_not_clear_it(svc):
    """The rule types the edge by the target's actual resolved type, not by the kind alone —
    a `task`'s bundled feature->parent edge shares no kind with `implements`, but a feature
    could still carry `implements` pointed at, say, a decision; that must not satisfy a check
    whose declared target is `contract`."""
    await create_item(svc, "contract", "c")
    decision = (await create_item(svc, "decision", "d")).item
    feat = (await create_item(svc, "feature", "f")).item
    await svc.add_ref(feat.id, decision.id, kind="implements")
    for status in ("Ready", "InProgress", "Done"):
        await svc.set_status(feat.id, status)

    assert len(_messages(await svc.check(), feat.id)) == 1


async def test_does_not_fire_for_inreview_which_shares_the_active_role(svc):
    """The trigger keys on the `done` status role, never a status spelling — InReview shares
    `active` with InProgress/ChangesRequested/Fixed/Active, so it must stay silent."""
    await create_item(svc, "contract", "c")
    feat = (await create_item(svc, "feature", "f")).item
    for status in ("Ready", "InProgress", "InReview"):
        await svc.set_status(feat.id, status)

    assert _messages(await svc.check(), feat.id) == []


async def test_does_not_fire_for_a_cancelled_feature(svc):
    """Not the broader `settled` property either — Cancelled is settled too, and a feature
    that delivered nothing is not stale functional debt."""
    await create_item(svc, "contract", "c")
    feat = (await create_item(svc, "feature", "f")).item
    await svc.set_status(feat.id, "Cancelled")

    assert _messages(await svc.check(), feat.id) == []


async def test_the_gate_never_aborts_a_mutation_on_this_finding(svc):
    """Warn-level, always — a Done feature with no implements edge must still be settable to
    Done in the first place, contract or no contract, since the create/update gate only
    aborts on error-level issues."""
    await create_item(svc, "contract", "c")
    feat = (await create_item(svc, "feature", "f")).item
    await svc.set_status(feat.id, "Ready")
    await svc.set_status(feat.id, "InProgress")
    got = await svc.set_status(feat.id, "Done")  # would raise if this were a hard gate
    assert got.status == "Done"


# --------------------------------------------------------------------- RefRule.target, at load


def _spec_dict(base: WorkflowSpec, items) -> dict[str, object]:
    return {
        "items": items,
        "statuses": dict(base.statuses),
        "lifecycles": dict(base.lifecycles),
        "prefix_to_type": dict(base.prefix_to_type),
        "alias_to_type": dict(base.alias_to_type),
        "collections": dict(base.collections),
        "subentity_kinds": dict(base.subentity_kinds),
        "roles": dict(base.roles),
        "ref_kinds": dict(base.ref_kinds),
        "views": dict(base.views),
    }


def test_a_ref_rule_target_naming_an_undeclared_item_type_is_refused_at_load():
    from squads._workflow._models import RefRule

    base = bundled_spec()
    items = {
        **base.items,
        "feature": base.items["feature"].model_copy(
            update={"ref_rules": [RefRule(kind="implements", target="not-a-type")]}
        ),
    }
    with pytest.raises(SquadsError, match="does not name a declared item type"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


def test_a_validator_selecting_a_target_with_no_matching_ref_rule_is_refused_at_load():
    from squads._workflow._models import RefRule

    base = bundled_spec()
    items = {
        **base.items,
        # keeps the validators selection, but re-points its own ref_rules elsewhere
        "feature": base.items["feature"].model_copy(
            update={"ref_rules": [RefRule(kind="implements", target="decision")]}
        ),
    }
    with pytest.raises(SquadsError, match="declares no ref_rules entry with that target"):
        WorkflowSpec.model_validate(_spec_dict(base, items))


def test_a_matching_ref_rule_and_validator_selection_load_clean():
    spec = bundled_spec()
    assert spec.items["feature"].validators == ["ref_rule_target_present:contract"]
    assert any(rr.target == "contract" for rr in spec.items["feature"].ref_rules)


def test_a_paramless_ref_rule_target_present_is_refused_at_load_not_left_permanently_inert():
    """No ``:<T>`` parameter at all is a third, distinct shape from the two already covered
    above (an undeclared target type, and a target with no matching ``ref_rules`` entry): the
    bare name builds an empty target set at runtime and never fires, silently, for any type it
    is declared on."""
    base = bundled_spec()
    items = {
        **base.items,
        "bug": base.items["bug"].model_copy(update={"validators": ["ref_rule_target_present"]}),
    }
    with pytest.raises(SquadsError, match="missing its required target type parameter"):
        WorkflowSpec.model_validate(_spec_dict(base, items))
