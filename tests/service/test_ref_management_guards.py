"""Ref-management fail-closed guards at the service layer: ``create(..., refs=[...])`` and
``add_ref`` both validate the edge kind against the closed vocabulary, and ``add_ref``/``rm_ref``
refuse a self-reference and remove an edge by id regardless of its stored kind.

``rm_ref``'s optional ``kind`` narrows removal to one kind of edge, leaving any other kind to
the same target untouched — the primitive the roster retirement gate's ``--unlink`` and
``unlink_role`` (now a thin wrapper over it) both build on.
"""

import pytest

from _helpers import create_item
from squads._errors import SquadsError

pytestmark = pytest.mark.anyio

_VALID_KINDS = ("related", "blocks", "fixes", "addresses", "supersedes", "duplicates")


async def test_create_with_a_ref_of_an_unknown_kind_is_rejected(svc):
    other = (await create_item(svc, "task", "other")).item
    with pytest.raises(SquadsError, match="unknown ref kind"):
        await create_item(svc, "task", "t", refs=[f"{other.id}:banana"])


async def test_add_ref_rejects_a_self_reference(svc):
    task = (await create_item(svc, "task", "t")).item
    with pytest.raises(SquadsError, match="cannot reference itself"):
        await svc.add_ref(task.id, task.id)


async def test_add_ref_rejects_an_unknown_kind_and_lists_the_valid_ones(svc):
    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    with pytest.raises(SquadsError) as exc_info:
        await svc.add_ref(a.id, b.id, kind="banana")
    message = str(exc_info.value)
    assert "banana" in message
    for kind in _VALID_KINDS:
        assert kind in message


async def test_rm_ref_removes_the_edge_by_id_regardless_of_its_stored_kind(svc):
    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    await svc.add_ref(a.id, b.id, kind="blocks")
    await svc.rm_ref(a.id, b.id)
    assert await svc.refs_out(a.id) == []


async def test_rm_ref_with_a_kind_removes_the_matching_edge_and_spares_another_target(svc):
    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    c = (await create_item(svc, "task", "c")).item
    await svc.add_ref(a.id, b.id, kind="blocks")
    await svc.add_ref(a.id, c.id, kind="related")

    await svc.rm_ref(a.id, b.id, kind="blocks")

    refs = await svc.refs_out(a.id)
    assert (b.id, "blocks") not in refs
    assert (c.id, "related") in refs


async def test_rm_ref_with_a_kind_leaves_a_different_kind_edge_to_the_same_target_intact(svc):
    a = (await create_item(svc, "task", "a")).item
    b = (await create_item(svc, "task", "b")).item
    await svc.add_ref(a.id, b.id, kind="fixes")

    await svc.rm_ref(a.id, b.id, kind="blocks")  # wrong kind: nothing to remove

    assert (b.id, "fixes") in await svc.refs_out(a.id)
