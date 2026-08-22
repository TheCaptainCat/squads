"""``Service.get()`` returns a deep copy of the item, preserving a contract that already held
before the request-scoped read cache existed: every ``get()`` used to come out of a freshly
parsed db, so no two callers ever shared an object. With one cached snapshot now potentially
served to many ``get()`` calls in the same invocation (``squads._index._store.read_scope``),
the copy at that seam is what keeps a caller's in-place mutation from contaminating a later
read of the same snapshot.
"""

import pytest

from _helpers import create_item
from squads._index._store import read_scope

pytestmark = pytest.mark.anyio


async def test_mutating_a_get_result_never_contaminates_a_later_read_in_the_same_scope(svc):
    created = await create_item(svc, "task", "original title")

    with read_scope():
        first = await svc.get(created.item.id)
        first.title = "mutated locally, must not stick"

        second = await svc.get(created.item.id)
        assert second.title == "original title"


async def test_two_get_calls_in_the_same_scope_never_return_the_same_object(svc):
    created = await create_item(svc, "task", "t")

    with read_scope():
        first = await svc.get(created.item.id)
        second = await svc.get(created.item.id)
        assert first is not second
