"""The bulk importer's ``body`` op is refused by the same shared closure as the single-item
``body`` command, reached through the validate-first pre-pass before anything is written."""

import json

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio


def _lines(*events: dict[str, object]) -> str:
    return "\n".join(json.dumps(e) for e in events)


async def test_a_replace_on_a_role_is_refused_in_the_pre_pass(svc) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")

    result = await svc.import_events(
        _lines({"op": "body", "target": role.id, "body": "a doomed replace", "as": "manager"})
    )

    assert not result.plan.ok
    assert result.applied is None
    assert any("renders through its declared sq:view:" in i.message for i in result.plan.issues)
    assert any("roles.toml" in i.message for i in result.plan.issues)
    assert any("Drop the view from `[selected]`" in i.message for i in result.plan.issues)


async def test_an_append_on_a_role_is_refused_in_the_pre_pass(svc) -> None:
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")

    result = await svc.import_events(
        _lines(
            {
                "op": "body",
                "target": role.id,
                "body": "a doomed append",
                "append": True,
                "as": "manager",
            }
        )
    )

    assert not result.plan.ok
    assert result.applied is None
    assert any("renders through its declared sq:view:" in i.message for i in result.plan.issues)
    assert not any("required host" in i.message for i in result.plan.issues)


async def test_a_replace_on_a_milestone_created_earlier_in_the_same_batch_is_admitted(
    svc,
) -> None:
    """A milestone created within the same import batch is writable without ``--force``."""
    result = await svc.import_events(
        _lines(
            {
                "op": "create",
                "type": "milestone",
                "title": "M",
                "handle": "m1",
                "as": "manager",
            },
            {"op": "body", "target": "m1", "body": "a fine replace", "as": "manager"},
        )
    )

    assert result.plan.ok, [i.message for i in result.plan.issues]
    assert result.applied is not None
    mile_id = result.plan.handle_to_id["m1"]
    assert (await svc.read_body(mile_id)).startswith("a fine replace")


async def test_an_ordinary_replace_still_applies_through_the_same_batch(svc) -> None:
    """An ordinary task body op still writes normally through the same batch."""
    task = (await create_item(svc, "task", "A task")).item

    result = await svc.import_events(
        _lines({"op": "body", "target": task.id, "body": "Fine.", "as": "manager"})
    )

    assert result.plan.ok
    assert result.applied is not None
    assert await svc.read_body(task.id) == "Fine."


async def test_the_refusal_message_matches_the_single_item_commands_exactly(svc) -> None:
    """The importer's refusal message matches the single-item command's exactly."""
    from squads._errors import SquadsError

    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")

    with pytest.raises(SquadsError) as excinfo:
        await svc.set_body(role.id, "a doomed replace")
    single_item_message = str(excinfo.value)

    result = await svc.import_events(
        _lines({"op": "body", "target": role.id, "body": "a doomed replace", "as": "manager"})
    )

    assert any(i.message == single_item_message for i in result.plan.issues), [
        i.message for i in result.plan.issues
    ]


async def test_a_custom_skills_body_still_applies_through_the_bulk_importer(svc) -> None:
    """A custom skill's body op behaves exactly like the single-item one through the importer."""
    skill = await svc.add_skill("Release Runbook", description="Ship a release safely.")

    result = await svc.import_events(
        _lines(
            {
                "op": "body",
                "target": skill.id,
                "body": "## Instructions\n\nCut the branch.",
                "as": "manager",
            }
        )
    )

    assert result.plan.ok
    assert result.applied is not None
    assert await svc.read_body(skill.id) == "## Instructions\n\nCut the branch."
