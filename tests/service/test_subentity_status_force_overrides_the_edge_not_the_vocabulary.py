"""``--force`` on a sub-entity status write waives the lifecycle *edge*, never the declared
*vocabulary*.

A sub-entity's status is the kind's own vocabulary: the ``subtask`` machine declares
Todo/InProgress/Blocked/Done/Cancelled, the ``finding`` machine declares Open/Fixed/Verified/
WontFix. A value that belongs to one kind's machine and not another's still passes the CLI
parser, because that parser only knows the spec's global status set — so the kind-scoped
membership check has to happen on the write path itself. The seed door (``add_block``) has
always performed it; the transition door (``set_block_status``/``update_block``) did not, and
its ``--force`` branch therefore wrote a value ``sq check`` then reports as an error while the
write itself exited 0.

The split this pins, per kind and in both directions:

* **vocabulary** — a status the kind does not declare is refused with or without ``force``,
  with nothing written, in the same message shape the seed door already uses;
* **edge** — a transition between two declared states that the machine does not permit still
  succeeds under ``force`` and still fails without it.

Plus the two pipeline-level invariants, which are what make the pair safe rather than merely
symmetric: every write this door accepts leaves the integrity gate clean, and every corpus it
can reach is recoverable through it. The second one is not free — recovery forces a sub-entity
whose *stored* status is not a node on the machine at all, so the transition lookup reads an
origin it does not know, and while an invalid status stands every gated door on the parent
item refuses. Were this door to consult the machine before ``force`` short-circuits it, the
parent would be stranded with no way out.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._errors import InvalidTransitionError, SquadsError
from squads._index._resolver import item_file
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


#: One row per bundled kind: the parent item type, the kind, a declared state that is NOT
#: reachable from the kind's initial state (so writing it exercises the edge waiver), and a
#: status that is real vocabulary in the squad but belongs to a *different* kind's machine.
KIND_ROWS = [
    pytest.param("task", "subtask", "Done", "Verified", id="subtask"),
    pytest.param("feature", "story", "Done", "Fixed", id="story"),
    pytest.param("review", "finding", "Verified", "Done", id="finding"),
]


async def _parent_with_one_block(svc, item_type: str, kind: str):
    item = (await create_item(svc, item_type, "Parent")).item
    block = await svc.add_block(item.id, kind, "Only block")
    return item, block.local_id


async def _stored_status(svc, item_id: str, kind: str, local_id: str) -> str:
    (sub,) = [s for s in await svc.list_blocks(item_id, kind) if s.local_id == local_id]
    return sub.status


def _write_stored_status(path: Path, index: int, status: str) -> None:
    """Set one sub-entity's stored status directly in frontmatter, bypassing every service
    seam — the only way left to build this corpus now that the door refuses one, and the shape
    an adopted or hand-edited corpus arrives in."""
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["subentities"][index]["status"] = status
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")


# --------------------------------------------------------------- vocabulary: refused either way


@pytest.mark.parametrize("force", [False, True], ids=["without-force", "with-force"])
@pytest.mark.parametrize(("item_type", "kind", "unreachable", "cross_kind"), KIND_ROWS)
async def test_a_status_the_kind_does_not_declare_is_refused_and_writes_nothing(
    svc, item_type: str, kind: str, unreachable: str, cross_kind: str, force: bool
) -> None:
    item, local_id = await _parent_with_one_block(svc, item_type, kind)
    before = await _stored_status(svc, item.id, kind, local_id)

    with pytest.raises(SquadsError) as excinfo:
        await svc.set_block_status(item.id, kind, local_id, cross_kind, force=force)

    message = str(excinfo.value)
    assert repr(cross_kind) in message
    assert f"not a valid {kind} status" in message
    for declared in svc.spec.subentity_workflow(kind).states:
        assert declared in message
    assert await _stored_status(svc, item.id, kind, local_id) == before


@pytest.mark.parametrize("force", [False, True], ids=["without-force", "with-force"])
@pytest.mark.parametrize(("item_type", "kind", "unreachable", "cross_kind"), KIND_ROWS)
async def test_the_metadata_door_refuses_the_same_status_the_status_door_does(
    svc, item_type: str, kind: str, unreachable: str, cross_kind: str, force: bool
) -> None:
    """``update_block`` and ``set_block_status`` are two doors onto one machine; a value one
    refuses must not be writable through the other, and a refused update must not land the
    other fields it was carrying either."""
    item, local_id = await _parent_with_one_block(svc, item_type, kind)
    before = await _stored_status(svc, item.id, kind, local_id)

    with pytest.raises(SquadsError):
        await svc.update_block(
            item.id, kind, local_id, title="Renamed", status=cross_kind, force=force
        )

    assert await _stored_status(svc, item.id, kind, local_id) == before
    (sub,) = await svc.list_blocks(item.id, kind)
    assert sub.title == "Only block"


@pytest.mark.parametrize(("item_type", "kind", "unreachable", "cross_kind"), KIND_ROWS)
async def test_the_seed_door_and_the_transition_door_word_the_refusal_identically(
    svc, item_type: str, kind: str, unreachable: str, cross_kind: str
) -> None:
    item, local_id = await _parent_with_one_block(svc, item_type, kind)

    with pytest.raises(SquadsError) as seeded:
        await svc.add_block(item.id, kind, "Second block", status=cross_kind)
    with pytest.raises(SquadsError) as moved:
        await svc.set_block_status(item.id, kind, local_id, cross_kind, force=True)

    assert str(seeded.value) == str(moved.value)


# --------------------------------------------------------------------- edge: still waivable


@pytest.mark.parametrize(("item_type", "kind", "unreachable", "cross_kind"), KIND_ROWS)
async def test_an_edge_the_machine_forbids_still_succeeds_under_force(
    svc, item_type: str, kind: str, unreachable: str, cross_kind: str
) -> None:
    item, local_id = await _parent_with_one_block(svc, item_type, kind)
    initial = await _stored_status(svc, item.id, kind, local_id)
    assert not svc.spec.subentity_can_transition(kind, initial, unreachable)

    await svc.set_block_status(item.id, kind, local_id, unreachable, force=True)

    assert await _stored_status(svc, item.id, kind, local_id) == unreachable


@pytest.mark.parametrize(("item_type", "kind", "unreachable", "cross_kind"), KIND_ROWS)
async def test_an_edge_the_machine_forbids_still_fails_without_force(
    svc, item_type: str, kind: str, unreachable: str, cross_kind: str
) -> None:
    item, local_id = await _parent_with_one_block(svc, item_type, kind)
    initial = await _stored_status(svc, item.id, kind, local_id)

    with pytest.raises(InvalidTransitionError) as excinfo:
        await svc.set_block_status(item.id, kind, local_id, unreachable)

    assert "use --force to override" in str(excinfo.value)
    assert await _stored_status(svc, item.id, kind, local_id) == initial


# ------------------------------------------------------------------- pipeline-level invariants


@pytest.mark.parametrize(("item_type", "kind", "unreachable", "cross_kind"), KIND_ROWS)
async def test_every_status_this_door_accepts_leaves_the_integrity_gate_clean(
    svc, item_type: str, kind: str, unreachable: str, cross_kind: str
) -> None:
    """Walk the kind's whole declared vocabulary through the forced door — the set of writes
    this path can still accept — and assert the corpus each one produces is one ``sq check``
    reports no error on."""
    item, local_id = await _parent_with_one_block(svc, item_type, kind)

    for status in sorted(svc.spec.subentity_workflow(kind).states):
        await svc.set_block_status(item.id, kind, local_id, status, force=True)
        assert await _stored_status(svc, item.id, kind, local_id) == status
        errors = [i for i in await svc.check() if i.level == "error"]
        assert errors == [], f"{status} left {errors}"


@pytest.mark.parametrize(("item_type", "kind", "unreachable", "cross_kind"), KIND_ROWS)
async def test_a_stored_status_outside_the_machine_is_still_recoverable_through_this_door(
    svc, item_type: str, kind: str, unreachable: str, cross_kind: str
) -> None:
    """The corpus the old behaviour could produce — and the one an adopted or hand-edited tree
    can still arrive in — must stay recoverable, because the forced status door is the only way
    out of it: while the invalid value stands, the parent's gated doors all refuse.

    The trap is that recovery reads an origin state the machine does not know. ``force`` has to
    short-circuit the transition lookup before it does.
    """
    item, local_id = await _parent_with_one_block(svc, item_type, kind)
    _write_stored_status(item_file(svc.paths, item), 0, cross_kind)
    await svc.repair()

    assert await _stored_status(svc, item.id, kind, local_id) == cross_kind
    assert any("invalid status" in i.message for i in await svc.check())
    with pytest.raises(SquadsError):  # the parent is stranded until the sub-entity is fixed
        await svc.update(item.id, title="Stranded")

    recovered = svc.spec.subentity_initial(kind)
    await svc.set_block_status(item.id, kind, local_id, recovered, force=True)

    assert await _stored_status(svc, item.id, kind, local_id) == recovered
    assert [i for i in await svc.check() if i.level == "error"] == []
    await svc.update(item.id, title="Unstranded")  # the parent's gated doors open again
    assert (await svc.get(item.id)).title == "Unstranded"
