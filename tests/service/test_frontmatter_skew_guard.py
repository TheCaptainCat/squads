"""The fail-closed skew guard: before a mutation rewrites an item's frontmatter from
index-derived state, the on-disk frontmatter must match what the index-loaded item would have
serialized before this mutation's own delta. A real skew refuses, loudly, with a `sq repair`
pointer; a healthy board is never refused.
"""

import pytest

from _helpers import create_item
from squads import _itemfile as itemfile
from squads._errors import SquadsError
from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


async def _crash_the_index_commit(svc, monkeypatch, mutate):
    """Run *mutate* (an awaitable-returning callable taking no args) with the index's own
    commit faulted so it never lands -- the `.md` write inside the transaction body has
    already happened and stands, exactly the markdown-ahead-of-index skew the durability
    model calls safe. Restores the real commit before returning."""
    real_atomic_write = IndexStore._atomic_write

    async def _boom(self, db):
        raise OSError("simulated crash during the index commit")

    monkeypatch.setattr(IndexStore, "_atomic_write", _boom)
    try:
        with pytest.raises(OSError):
            await mutate()
    finally:
        monkeypatch.setattr(IndexStore, "_atomic_write", real_atomic_write)


async def test_a_real_skew_on_a_field_outside_status_or_parent_refuses_the_next_mutation(
    svc, monkeypatch
):
    """The shape: a faulted index commit during a mutation, on a field outside
    {status, parent}, so the file is ahead of the index on `description` alone. An ordinary
    status change on the same item must refuse before writing anything, then succeed -- with
    both the interrupted value and the new delta on disk -- once `sq repair` has run.
    """
    task = (await create_item(svc, "task", "Skew target")).item

    await _crash_the_index_commit(
        svc, monkeypatch, lambda: svc.update(task.id, description="interrupted description")
    )

    # Markdown ahead of the index: the file carries the new description, the index doesn't.
    on_disk = itemfile.read_frontmatter(path=svc.paths.abspath(task.path))
    assert on_disk["description"] == "interrupted description"
    reloaded = await svc.get(task.id)
    assert reloaded.description == ""

    # An ordinary, unrelated mutation refuses -- before writing anything -- rather than
    # silently reverting the surviving value.
    with pytest.raises(SquadsError, match=rf"{task.id}.*repair"):
        await svc.set_status(task.id, "InProgress", force=True)

    # Nothing was written by the refused attempt: the file is untouched, still at Draft.
    still_on_disk = itemfile.read_frontmatter(path=svc.paths.abspath(task.path))
    assert still_on_disk["description"] == "interrupted description"
    assert still_on_disk["status"] == "Draft"

    await svc.repair()
    await svc.set_status(task.id, "InProgress", force=True)

    final = await svc.get(task.id)
    assert final.description == "interrupted description"
    assert final.status == "InProgress"


async def test_a_real_skew_refuses_a_body_or_comment_edit_too(svc, monkeypatch):
    """The second write seam (the shared section-edit core body/comment edits go through)
    enforces the same guard as the metadata/status seam -- a real skew refuses there too."""
    task = (await create_item(svc, "task", "Skew target for body edit")).item

    await _crash_the_index_commit(
        svc, monkeypatch, lambda: svc.update(task.id, description="interrupted description")
    )

    with pytest.raises(SquadsError, match=rf"{task.id}.*repair"):
        await svc.set_body(task.id, "a note written over an unrepaired skew")

    await svc.repair()
    await svc.set_body(task.id, "a note written after repair")
    body = await svc.read_body(task.id)
    assert "a note written after repair" in body


async def test_repair_converges_and_further_mutations_are_unaffected(svc, monkeypatch):
    """Once repaired, the item is fully mutable again -- the guard's cost (blocked mutations)
    is scoped to the one drifted item and to the window before repair, not permanent."""
    task = (await create_item(svc, "task", "Recovers after repair")).item

    await _crash_the_index_commit(
        svc, monkeypatch, lambda: svc.update(task.id, description="interrupted description")
    )
    await svc.repair()

    await svc.update(task.id, description="second description")
    await svc.set_status(task.id, "InProgress", force=True)
    final = await svc.get(task.id)
    assert final.description == "second description"
    assert final.status == "InProgress"


# ---------------------------------------------------------------------------------------------
# False-refusal cases: shapes where the file and the index look different on the page but are
# the same item. Each passes with no guard-side special-casing, because the round trip through
# `Item.from_frontmatter(...).to_frontmatter_dict()` collapses the divergence structurally
# before the guard ever compares the two sides. Green with nothing to explain it is the
# correct result here, not a sign the guard is inert -- the real-skew cases at the top of this
# file are what show it is not.
# ---------------------------------------------------------------------------------------------


async def test_a_post_repad_id_width_mismatch_does_not_false_refuse(svc):
    task = (await create_item(svc, "task", "Repad target")).item
    await svc.repad(8)

    await svc.set_status(task.id, "InProgress", force=True)
    reloaded = await svc.get(task.id)
    assert reloaded.status == "InProgress"


async def test_absent_optional_fields_do_not_false_refuse(svc):
    """An item with no parent, no assignee and no attributes at all -- every optional field
    dropped from the file entirely rather than written as an explicit empty/null value."""
    task = (await create_item(svc, "task", "No optional fields")).item
    path = svc.paths.abspath(task.path)
    text = path.read_text(encoding="utf-8")
    from squads._sections import join_frontmatter, split_frontmatter

    fm, rest = split_frontmatter(text)
    for key in ("parent", "assignee", "labels", "refs", "description"):
        fm.pop(key, None)
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    await svc.set_status(task.id, "InProgress", force=True)
    reloaded = await svc.get(task.id)
    assert reloaded.status == "InProgress"


async def test_two_mutations_in_a_row_with_no_interruption_are_never_refused(svc):
    """The plain round trip: create, then mutate twice back to back. The second mutation
    must not be refused by the guard -- the ordinary, overwhelmingly common case."""
    task = (await create_item(svc, "task", "Two in a row")).item
    await svc.update(task.id, description="first")
    await svc.update(task.id, description="second")
    reloaded = await svc.get(task.id)
    assert reloaded.description == "second"


async def test_a_padded_id_mismatch_does_not_false_refuse(svc):
    """A file whose own frontmatter `id:` line was historically written at a padded width
    (a legacy quirk `to_frontmatter_dict()` no longer produces) collapses too: `id` is a
    computed field re-derived from prefix + sequence number on both sides, unpadded, so the
    padding on disk never survives the round trip to be compared at all."""
    task = (await create_item(svc, "task", "Padded id on disk")).item
    path = svc.paths.abspath(task.path)
    text = path.read_text(encoding="utf-8")
    from squads._sections import join_frontmatter, split_frontmatter

    fm, rest = split_frontmatter(text)
    fm["id"] = f"TASK-{task.sequence_id:06d}"  # padded, unlike the unpadded id normally written
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    await svc.set_status(task.id, "InProgress", force=True)
    reloaded = await svc.get(task.id)
    assert reloaded.status == "InProgress"


async def test_repad_is_unaffected_by_a_real_skew(svc, monkeypatch):
    """`repad` attaches to file writes (renaming files, bytes untouched), not to
    index-derived frontmatter substitution -- it must run cleanly on a board carrying a
    real, unrepaired skew rather than the guard's write path ever being reached for it.
    ``repad`` ends in a full index rebuild from disk, so it heals the skew as a side effect
    of what it already does -- the point here is that it never raises getting there."""
    task = (await create_item(svc, "task", "Untouched by repad")).item

    await _crash_the_index_commit(
        svc, monkeypatch, lambda: svc.update(task.id, description="interrupted description")
    )

    await svc.repad(8)  # must not raise

    current = await svc.get(task.id)
    assert current.description == "interrupted description"


async def test_renumber_is_unaffected_by_a_real_skew(svc, monkeypatch):
    """`renumber` rewrites id strings inside files' own content and ends in a full index
    rebuild from disk -- same non-applicability as `repad`: it must run cleanly on a board
    carrying a real, unrepaired skew on an item outside the shifted range."""
    task = (await create_item(svc, "task", "Untouched by renumber")).item
    other = (await create_item(svc, "task", "Shifted by renumber")).item

    await _crash_the_index_commit(
        svc, monkeypatch, lambda: svc.update(task.id, description="interrupted description")
    )

    result = await svc.renumber(from_seq=other.sequence_id, onto=999)  # must not raise
    assert result.remap  # the shift actually happened

    current = await svc.get(task.id)
    assert current.description == "interrupted description"


# ---------------------------------------------------------------------------------------------
# A role's stored model is an operator setting like any other field: no role key is exempt from
# the skew guard, so a hand edit ahead of the index refuses the next write instead of being
# overwritten by it.
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["catalog", "template"])
async def test_a_hand_edited_role_model_then_editing_elsewhere_refuses_not_reverts(svc, kind):
    from squads._sections import join_frontmatter, split_frontmatter

    if kind == "catalog":
        role = await svc.activate_role("qa")
    else:
        role = await svc.activate_role(None, from_template="dev", tech="python")
    path = svc.paths.abspath(role.path)
    front, rest = split_frontmatter(path.read_text(encoding="utf-8"))
    front["model"] = "haiku"
    path.write_text(join_frontmatter(front, rest), encoding="utf-8")
    assert (await svc.get(role.id)).attributes.get("model") != "haiku"

    with pytest.raises(SquadsError, match=rf"{role.id}.*repair"):
        await svc.update(role.id, title="Renamed after a hand edit")

    assert itemfile.read_frontmatter(path=path)["model"] == "haiku"  # not reverted

    await svc.repair()
    await svc.update(role.id, title="Renamed after repair")
    final = await svc.get(role.id)
    assert final.attributes.get("model") == "haiku"
    assert final.title == "Renamed after repair"
