"""``Service.list_roles`` enumerates the active roster (activated ``ROLE`` items) — distinct
from the bundled `role catalog`, which never touches the index at all.
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
    await svc.add_operator("Pierre Chat")
    roles = await svc.list_roles()
    assert all(r.type == "role" for r in roles)
