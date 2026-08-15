"""``Service.set_default_role()`` — the ``is_default`` designation move.

No interactive command wrote ``is_default`` before this: it was set once from the bundled
catalog at ``sq role activate`` and otherwise only reachable through the bulk importer's
``update`` event replaying history. The projection resolves the designation by first match
over the roster and nothing validates a single holder at item level, so a plain set (the
generic ``update(set_extra=...)`` seam already allows writing the key directly) can silently
leave two holders and an arbitrary winner — the move clears every other holder in the same
transaction instead.
"""

import pytest

from squads._errors import SquadsError
from squads._models._extras import ExtraKey as X

pytestmark = pytest.mark.anyio


def _default_holders(items) -> list[str]:
    return sorted(it.id for it in items if it.extra.get(X.IS_DEFAULT))


# --------------------------------------------------------------------------- the move itself


async def test_move_designates_the_target_and_clears_the_previous_holder(svc):
    manager = await svc.roster_item("role", "manager")
    qa = await svc.activate_role("qa")

    result = await svc.set_default_role(qa.id)

    assert result.changed
    assert result.item.id == qa.id
    assert result.cleared == [manager.id]
    assert (await svc.get(qa.id)).extra.get(X.IS_DEFAULT) is True
    assert not (await svc.get(manager.id)).extra.get(X.IS_DEFAULT)


async def test_move_leaves_exactly_one_holder(svc):
    await svc.activate_role("qa")
    qa = await svc.roster_item("role", "qa")

    await svc.set_default_role(qa.id)

    roles = await svc.list_roles()
    assert _default_holders(roles) == [qa.id]


async def test_generated_config_presents_the_new_default_without_a_sq_sync(project, svc):
    await svc.activate_role("qa")
    qa = await svc.roster_item("role", "qa")

    await svc.set_default_role(qa.id)

    claude_md = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "default to **Mara Tester** (`qa`)" in claude_md
    assert "default to **Catherine Manager**" not in claude_md


async def test_one_reflog_line_records_the_move(svc):
    await svc.activate_role("qa")
    qa = await svc.roster_item("role", "qa")

    await svc.set_default_role(qa.id)

    entries = await svc.read_reflog(op_filter="default_role")
    assert len(entries) == 1
    assert entries[0].target == qa.id


# --------------------------------------------------------------------------- already holds it


async def test_designating_the_current_holder_is_a_reported_no_op(svc):
    manager = await svc.roster_item("role", "manager")

    result = await svc.set_default_role(manager.id)

    assert result.changed is False
    assert result.cleared == []
    assert (await svc.get(manager.id)).extra.get(X.IS_DEFAULT) is True


async def test_no_op_writes_no_reflog_line(svc):
    manager = await svc.roster_item("role", "manager")

    await svc.set_default_role(manager.id)

    assert await svc.read_reflog(op_filter="default_role") == []


# --------------------------------------------------------------------------- non-live refusal


async def test_designating_a_non_live_role_is_refused(svc):
    qa = await svc.activate_role("qa")
    await svc.set_roster_status(qa.id, "Archived")

    with pytest.raises(SquadsError, match="not live"):
        await svc.set_default_role(qa.id)

    manager = await svc.roster_item("role", "manager")
    assert (await svc.get(manager.id)).extra.get(X.IS_DEFAULT) is True  # untouched


async def test_refusing_a_non_live_target_writes_nothing(svc):
    qa = await svc.activate_role("qa")
    await svc.set_roster_status(qa.id, "Archived")

    with pytest.raises(SquadsError):
        await svc.set_default_role(qa.id)

    assert await svc.read_reflog(op_filter="default_role") == []


# --------------------------------------------------------------------------- repairing two holders


async def test_the_move_repairs_a_pre_existing_two_holder_state(svc):
    """The exposure the architect reproduced: two live roles both carrying ``is_default``.
    Designating either one must converge the roster to a single holder."""
    manager = await svc.roster_item("role", "manager")
    qa = await svc.activate_role("qa")
    await svc.update(qa.id, set_extra={"is_default": "true"})  # hand-plant a second holder
    roles = await svc.list_roles()
    assert _default_holders(roles) == sorted([manager.id, qa.id])  # sanity: two holders

    result = await svc.set_default_role(qa.id)

    assert result.changed
    assert result.cleared == [manager.id]
    roles = await svc.list_roles()
    assert _default_holders(roles) == [qa.id]


async def test_redesignating_the_current_holder_still_clears_a_stray_second_holder(svc):
    """Re-designating the role that already holds the flag is only a true no-op when it is the
    *sole* holder — if another role also carries it (the two-holder repro), that stray holder
    is still cleared even though the target's own flag does not change value."""
    manager = await svc.roster_item("role", "manager")
    qa = await svc.activate_role("qa")
    await svc.update(qa.id, set_extra={"is_default": "true"})  # manager AND qa both carry it now

    result = await svc.set_default_role(manager.id)  # manager already holds it

    assert result.changed  # not a no-op: qa's stray flag was cleared
    assert result.cleared == [qa.id]
    roles = await svc.list_roles()
    assert _default_holders(roles) == [manager.id]


# ------------------------------------------------------ pinning the gap a plain set would leave


async def test_a_plain_set_without_the_move_leaves_two_holders(svc):
    """Characterizes the exact gap that makes a move-semantics verb necessary: the generic
    ``update(set_extra=...)`` seam already lets a caller write ``is_default`` directly, and it
    does nothing to clear any
    existing holder — so a plain set (never routed through ``set_default_role``) silently
    produces two holders and an arbitrary winner. This pins that the gap is structural (the
    generic seam's own behaviour), not merely un-exercised, and is exactly why the move verb
    exists rather than a flag on the generic update path."""
    manager = await svc.roster_item("role", "manager")
    qa = await svc.activate_role("qa")

    await svc.update(qa.id, set_extra={"is_default": "true"})

    roles = await svc.list_roles()
    assert _default_holders(roles) == sorted([manager.id, qa.id])  # two holders, arbitrary winner
