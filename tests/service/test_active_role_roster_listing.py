"""``Service.list_roles`` enumerates the active roster (activated ``ROLE`` items) — distinct
from the bundled `role catalog`, which never touches the index at all.

Also covers the ``roster()``/``roster_all()`` (and ``operators()``/``operators_all()``) split
the split introduces: ``roster()``/``operators()`` narrow to **live-only** — the projection
``write_managed`` compiles from — while ``roster_all()``/``operators_all()`` return every entry
regardless of status, for the callers that need the full vocabulary (orphan detection,
authorship display, registration checks, the roster's own views).
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_lists_every_activated_role(svc):
    roles = await svc.list_roles()
    assert [r.extra.get("slug", r.slug) for r in roles] == ["manager"]


async def test_a_newly_activated_role_appears_in_the_listing(svc):
    await svc.activate_role("architect")
    roles = await svc.list_roles()
    assert {r.extra.get("slug", r.slug) for r in roles} == {"manager", "architect"}


async def test_an_operator_never_appears_in_the_role_listing(svc):
    await svc.add_operator("Alice Tester")
    roles = await svc.list_roles()
    assert all(r.type == "role" for r in roles)


# --------------------------------------------------------------------------- roster()/roster_all()


async def test_roster_excludes_a_retired_role_but_roster_all_still_lists_it(svc):
    item = await svc.activate_role("qa")
    await svc.set_status(item.id, "Archived")

    live = {r.slug for r in await svc.roster()}
    everyone = {r.slug for r in await svc.roster_all()}
    assert "qa" not in live
    assert "manager" in live
    assert "qa" in everyone
    assert "manager" in everyone


async def test_roster_all_returns_the_same_count_as_roster_when_nothing_is_retired(svc):
    await svc.activate_role("architect")
    assert len(await svc.roster()) == len(await svc.roster_all()) == 2


# ----------------------------------------------------------------- operators()/operators_all()


async def test_operators_excludes_a_retired_operator_but_operators_all_still_lists_it(svc):
    op = await svc.add_operator("Alice Tester")
    await svc.set_status(op.id, "Archived")

    live = [o.slug for o in await svc.operators()]
    everyone = [o.slug for o in await svc.operators_all()]
    assert live == []
    assert everyone == [op.extra.get("slug", op.slug)]
