"""resolve_slug_or_raise: the one validator every slug-accepting CLI surface calls.
Needs a real roster/operator lookup, so it lives at the service layer (not unit).

Every CLI surface that calls it (mine/inbox/comment --as/update assignee+author/list
--assignee/subtask add+update) gets its own thin test — deliberately repeated, since each
is an independent wiring point that could forget to call the validator — in
tests/cli/test_slug_validation_surfaces.py.
"""

import pytest

from squads._cli._common import resolve_slug_or_raise  # pyright: ignore[reportPrivateUsage]
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio


async def test_accepts_a_registered_agent_slug(svc) -> None:
    assert await resolve_slug_or_raise("manager", svc) == "manager"


async def test_accepts_a_registered_operator_slug(svc) -> None:
    await svc.add_operator("Pierre Chat")
    assert await resolve_slug_or_raise("op-pierre", svc) == "op-pierre"


async def test_accepts_the_legacy_anonymous_operator_sentinel(svc) -> None:
    assert await resolve_slug_or_raise("operator", svc) == "operator"


async def test_normalises_the_at_prefix(svc) -> None:
    assert await resolve_slug_or_raise("@manager", svc) == "manager"


async def test_raises_on_an_unknown_slug(svc) -> None:
    with pytest.raises(SquadsError, match="unknown slug"):
        await resolve_slug_or_raise("ghost", svc)


async def test_error_message_names_at_least_one_valid_slug(svc) -> None:
    await svc.add_operator("Pierre Chat")
    with pytest.raises(SquadsError) as exc_info:
        await resolve_slug_or_raise("nobody", svc)
    assert "manager" in str(exc_info.value) or "op-pierre" in str(exc_info.value)


async def test_an_operator_slug_is_a_valid_author_on_a_work_item(svc) -> None:
    await svc.add_operator("Pierre Chat")
    res = await svc.create("task", "manual", author="op-pierre")
    assert res.item.author == "op-pierre"
