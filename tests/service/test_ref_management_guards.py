"""Ref-management fail-closed guards at the service layer: ``create(..., refs=[...])`` and
``add_ref`` both validate the edge kind against the closed vocabulary, and ``add_ref``/``rm_ref``
refuse a self-reference and remove an edge by id regardless of its stored kind.
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio

_VALID_KINDS = ("related", "blocks", "fixes", "addresses", "supersedes", "duplicates")


async def test_create_with_a_ref_of_an_unknown_kind_is_rejected(svc):
    other = (await svc.create("task", "other")).item
    with pytest.raises(SquadsError, match="unknown ref kind"):
        await svc.create("task", "t", refs=[f"{other.id}:banana"])


async def test_add_ref_rejects_a_self_reference(svc):
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="cannot reference itself"):
        await svc.add_ref(task.id, task.id)


async def test_add_ref_rejects_an_unknown_kind_and_lists_the_valid_ones(svc):
    a = (await svc.create("task", "a")).item
    b = (await svc.create("task", "b")).item
    with pytest.raises(SquadsError) as exc_info:
        await svc.add_ref(a.id, b.id, kind="banana")
    message = str(exc_info.value)
    assert "banana" in message
    for kind in _VALID_KINDS:
        assert kind in message


async def test_rm_ref_removes_the_edge_by_id_regardless_of_its_stored_kind(svc):
    a = (await svc.create("task", "a")).item
    b = (await svc.create("task", "b")).item
    await svc.add_ref(a.id, b.id, kind="blocks")
    await svc.rm_ref(a.id, b.id)
    assert await svc.refs_out(a.id) == []
