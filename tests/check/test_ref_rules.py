"""The ref rules of `sq check`: each reports the one edge that breaks it, a sibling at the boundary
stays unreported, and a selection can move a rule to the other level.

A ref the CLI refuses to write is arranged by editing the item file and re-indexing the squad;
every other breach goes through the CLI.
"""

import pytest

from tests.check._arrange import (
    activate,
    add_ref,
    create,
    edit_item_file,
    issue,
    remove_ref,
    repair,
    set_status,
)

pytestmark = pytest.mark.anyio


async def _task_with_two_refs(invoke) -> tuple[str, str, str]:
    """A task that fixes a bug and relates to a feature; returns the task, bug and feature."""
    await activate(invoke, "tech-lead", "product-owner", "qa")
    feature = await create(invoke, "feature", "Search", "product-owner")
    bug = await create(invoke, "bug", "Crash", "qa")
    task = await create(invoke, "task", "Index", "tech-lead")
    await add_ref(invoke, task, bug, "fixes")
    await add_ref(invoke, task, feature)
    return task, bug, feature


def _dangling(task: str, level: str) -> dict[str, str]:
    return issue("dangling_ref", level, task, "dangling ref BUG-99")


@pytest.mark.breaches("dangling_ref")
async def test_a_ref_to_an_item_that_does_not_exist_is_a_warning(
    project, invoke, check_json
) -> None:
    task, bug, _feature = await _task_with_two_refs(invoke)
    assert await check_json() == ([], 0)

    # the CLI refuses a ref to an item that does not exist
    edit_item_file(project, task, f"- {bug}:fixes", "- BUG-99:fixes")
    await repair(invoke)

    assert await check_json() == ([_dangling(task, "warn")], 0)


@pytest.mark.breaches("dangling_ref@error")
async def test_dangling_ref_selected_at_error_fails_the_check(
    project, invoke, check_json, select_validators
) -> None:
    task, bug, _feature = await _task_with_two_refs(invoke)
    select_validators("dangling_ref@error", on="task")
    assert await check_json() == ([], 0)

    # the CLI refuses a ref to an item that does not exist
    edit_item_file(project, task, f"- {bug}:fixes", "- BUG-99:fixes")
    await repair(invoke)

    assert await check_json() == ([_dangling(task, "error")], 3)


def _unknown_kind(task: str, feature: str, level: str) -> dict[str, str]:
    return issue("ref_kind_valid", level, task, f"unknown ref kind 'bogus' on edge → {feature}")


@pytest.mark.breaches("ref_kind_valid")
async def test_a_ref_of_an_undeclared_kind_is_a_warning(project, invoke, check_json) -> None:
    task, _bug, feature = await _task_with_two_refs(invoke)
    assert await check_json() == ([], 0)

    # the CLI refuses a ref kind the spec does not declare
    edit_item_file(project, task, f"- {feature}\n", f"- {feature}:bogus\n")
    await repair(invoke)

    assert await check_json() == ([_unknown_kind(task, feature, "warn")], 0)


@pytest.mark.breaches("ref_kind_valid@error")
async def test_ref_kind_valid_selected_at_error_fails_the_check(
    project, invoke, check_json, select_validators
) -> None:
    task, _bug, feature = await _task_with_two_refs(invoke)
    select_validators("ref_kind_valid@error", on="task")
    assert await check_json() == ([], 0)

    # the CLI refuses a ref kind the spec does not declare
    edit_item_file(project, task, f"- {feature}\n", f"- {feature}:bogus\n")
    await repair(invoke)

    assert await check_json() == ([_unknown_kind(task, feature, "error")], 3)


async def _superseded_decisions(invoke) -> tuple[str, str, str, str]:
    """Two decisions each superseded by a later one; returns old, its successor, old, successor."""
    await activate(invoke, "architect")
    found: list[str] = []
    for _ in range(2):
        old = await create(invoke, "decision", "Old", "architect")
        new = await create(invoke, "decision", "New", "architect")
        await add_ref(invoke, new, old, "supersedes")
        await set_status(invoke, old, "Accepted", "Superseded")
        found += [old, new]
    return found[0], found[1], found[2], found[3]


def _no_successor(decision: str, level: str) -> dict[str, str]:
    return issue(
        "supersedes_incoming",
        level,
        decision,
        "status is Superseded but no incoming supersedes edge found",
    )


@pytest.mark.breaches("supersedes_incoming")
async def test_a_superseded_record_with_no_incoming_supersedes_edge_is_a_warning(
    project, invoke, check_json
) -> None:
    old, successor, _other_old, _other_successor = await _superseded_decisions(invoke)
    assert await check_json() == ([], 0)

    await remove_ref(invoke, successor, old)

    assert await check_json() == ([_no_successor(old, "warn")], 0)


@pytest.mark.breaches("supersedes_incoming@error")
async def test_supersedes_incoming_selected_at_error_fails_the_check(
    project, invoke, check_json, select_validators
) -> None:
    old, successor, _other_old, _other_successor = await _superseded_decisions(invoke)
    select_validators("supersedes_incoming@error", on="decision")
    assert await check_json() == ([], 0)

    await remove_ref(invoke, successor, old)

    assert await check_json() == ([_no_successor(old, "error")], 3)


async def _settled_feature_implementing(invoke) -> tuple[str, str, str]:
    """A Done feature with an `implements` edge to a contract, and a Draft feature with none;
    returns the Done feature, the contract and the Draft feature."""
    await activate(invoke, "product-owner")
    contract = await create(invoke, "contract", "Search API", "product-owner")
    done = await create(invoke, "feature", "Search", "product-owner")
    draft = await create(invoke, "feature", "Export", "product-owner")
    await add_ref(invoke, done, contract, "implements")
    await set_status(invoke, done, "Ready", "InProgress", "Done")
    return done, contract, draft


def _missing_contract(feature: str, level: str) -> dict[str, str]:
    return issue(
        "ref_rule_target_present",
        level,
        feature,
        "settled with no implements ref to contract — its functional contract slice may be stale",
    )


@pytest.mark.breaches("ref_rule_target_present@error")
async def test_ref_rule_target_present_selected_at_error_fails_the_check(
    project, invoke, check_json, select_validators
) -> None:
    done, contract, _draft = await _settled_feature_implementing(invoke)
    select_validators("ref_rule_target_present:contract@error", on="feature")
    assert await check_json() == ([], 0)

    await remove_ref(invoke, done, contract)

    assert await check_json() == ([_missing_contract(done, "error")], 3)


@pytest.mark.breaches("ref_rule_target_present", "ref_rule_target_present:param")
async def test_each_selected_target_type_is_resolved_and_the_selections_are_unioned(
    project, invoke, check_json, select_validators
) -> None:
    done, contract, _draft = await _settled_feature_implementing(invoke)
    milestone = await create(invoke, "milestone", "Launch", "product-owner")
    by_milestone = await create(invoke, "feature", "Billing", "product-owner")
    await add_ref(invoke, by_milestone, milestone, "targets")
    await set_status(invoke, by_milestone, "Ready", "InProgress", "Done")
    select_validators(
        "ref_rule_target_present:contract",
        "ref_rule_target_present:milestone",
        on="feature",
        ref_rules=[
            {"kind": "implements", "target": "contract"},
            {"kind": "targets", "target": "milestone"},
        ],
    )
    assert await check_json() == ([], 0)

    await remove_ref(invoke, done, contract)
    await remove_ref(invoke, by_milestone, milestone)

    message = (
        "settled with no implements/targets ref to contract/milestone — "
        "its functional contract slice may be stale"
    )
    assert await check_json() == (
        [
            issue("ref_rule_target_present", "warn", done, message),
            issue("ref_rule_target_present", "warn", by_milestone, message),
        ],
        0,
    )


async def _feature_implementing_a_contract(invoke) -> tuple[str, str, str, str]:
    """A feature that implements a contract and relates to a second feature; returns the feature,
    the contract, the second feature and an epic."""
    await activate(invoke, "product-owner")
    contract = await create(invoke, "contract", "Search API", "product-owner")
    epic = await create(invoke, "epic", "Roadmap", "product-owner")
    other = await create(invoke, "feature", "Export", "product-owner")
    feature = await create(invoke, "feature", "Search", "product-owner")
    await add_ref(invoke, feature, contract, "implements")
    await add_ref(invoke, feature, other)
    return feature, contract, other, epic


def _wrong_target(feature: str, epic: str, level: str) -> dict[str, str]:
    return issue(
        "ref_rule_target_typed",
        level,
        feature,
        f"implements edge to {epic} points at epic, but implements refs of "
        "feature must point at contract",
    )


@pytest.mark.breaches("ref_rule_target_typed")
async def test_an_edge_to_the_wrong_type_for_a_typed_ref_rule_is_a_warning(
    project, invoke, check_json, select_validators
) -> None:
    feature, _contract, _other, epic = await _feature_implementing_a_contract(invoke)
    select_validators("ref_rule_target_typed", on="feature")
    assert await check_json() == ([], 0)

    await add_ref(invoke, feature, epic, "implements")

    assert await check_json() == ([_wrong_target(feature, epic, "warn")], 0)


@pytest.mark.breaches("ref_rule_target_typed@error")
async def test_ref_rule_target_typed_selected_at_error_fails_the_check(
    project, invoke, check_json, select_validators
) -> None:
    feature, _contract, _other, epic = await _feature_implementing_a_contract(invoke)
    select_validators("ref_rule_target_typed@error", on="feature")
    assert await check_json() == ([], 0)

    await add_ref(invoke, feature, epic, "implements")

    assert await check_json() == ([_wrong_target(feature, epic, "error")], 3)
