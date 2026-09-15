"""``squads._views._resolve_self_source`` — the ``self`` source's resolver: a pass-through to
the host item, nothing computed. Identity, not just equality (the resolver hands back the exact
object the caller already held, never a re-fetch), and the emptiness case: a freshly-created
item with an empty body still resolves — an empty body is not an absent item."""

import pytest

from _helpers import create_item
from squads import _views as views

pytestmark = pytest.mark.anyio


async def test_the_resolver_returns_the_exact_item_object_passed_in(svc) -> None:
    task = (await create_item(svc, "task", "T")).item

    resolved = views._resolve_self_source(task)

    assert resolved is task


async def test_a_freshly_created_item_with_an_empty_body_still_resolves(svc) -> None:
    """An empty body is not an absent item.

    No creation path leaves a body genuinely empty by default any more — a role and the three
    permanently-system skills now seed their own placement tag at creation, so this clears an
    ordinary item's body explicitly instead of relying on any type's create-time scaffold to be
    blank."""
    task = (await create_item(svc, "task", "T")).item
    await svc.set_body(task.id, "")
    body = await svc.read_body(task.id)
    assert body == ""  # precondition: this item's body is genuinely empty, not absent

    resolved = views._resolve_self_source(task)

    assert resolved is task
    assert resolved.type == "task"
