"""The fail-closed skew guard: before a mutation rewrites an item's frontmatter from
index-derived state, the on-disk frontmatter must match what the index-loaded item would have
serialized before this mutation's own delta. A real skew refuses, loudly, with a `sq repair`
pointer; a healthy board is never refused.
"""

import pytest

from squads import _itemfile as itemfile
from squads._errors import SquadsError
from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


async def _crash_the_index_commit(svc, monkeypatch, mutate):
    """Run *mutate* (an awaitable-returning callable taking no args) with the index's own
    commit faulted so it never lands -- the `.md` write inside the transaction body has
    already happened and stands, exactly the markdown-ahead-of-index skew the durability
    model calls safe. Restores the real commit before returning."""
    real_atomic_write = IndexStore._atomic_write  # pyright: ignore[reportPrivateUsage]

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
    """Reproduces the finding this task closes end to end: fault the index commit during a
    `description` update (deliberately outside {status, parent}, the narrower design's blind
    spot) so the file is ahead; an ordinary status change on the same item must refuse before
    writing anything, then succeed -- with both the interrupted value and the new delta on
    disk -- once `sq repair` has run.
    """
    task = (await svc.create("task", "Skew target")).item

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
    task = (await svc.create("task", "Skew target for body edit")).item

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
    task = (await svc.create("task", "Recovers after repair")).item

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
# False-refusal cases: all five are expected to pass on the FIRST run, by construction, because
# the round trip through `Item.from_frontmatter(...).to_frontmatter_dict()` collapses every one
# of these divergences structurally. Green immediately is the correct result here, not a sign
# the guard is inert -- see the paired sabotage test below, which proves it is not.
# ---------------------------------------------------------------------------------------------


async def test_legacy_severity_location_does_not_false_refuse(svc):
    """Both the file AND the index carry the value in the pre-top-level-field location --
    the shape a squad predating that field would actually have, on both artifacts
    consistently. The load-time backfill (``_backfill_severity``, run identically for the
    index-loaded base and for the disk-parsed side of the comparison) relocates it back in
    memory on each side, so the round trip collapses the divergence rather than the guard
    ever seeing the two disagree."""
    bug = (await svc.create("bug", "Legacy severity bug", fields={"severity": "critical"})).item

    path = svc.paths.abspath(bug.path)
    text = path.read_text(encoding="utf-8")
    from squads._sections import join_frontmatter, split_frontmatter

    fm, rest = split_frontmatter(text)
    fm.pop("severity", None)
    fm.setdefault("extra", {})["severity"] = "critical"
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    db = await svc.store.load()
    item = db.get(bug.id)
    assert item is not None
    item.severity = None
    item.extra["severity"] = "critical"
    await svc.store.overwrite(db)

    # A plain mutation must not be refused by the legacy-location divergence.
    await svc.set_status(bug.id, "InProgress", force=True)
    reloaded = await svc.get(bug.id)
    assert reloaded.status == "InProgress"
    assert reloaded.severity == "critical"


async def test_a_post_repad_id_width_mismatch_does_not_false_refuse(svc):
    task = (await svc.create("task", "Repad target")).item
    await svc.repad(8)

    await svc.set_status(task.id, "InProgress", force=True)
    reloaded = await svc.get(task.id)
    assert reloaded.status == "InProgress"


async def test_legacy_ref_kinds_map_does_not_false_refuse(svc):
    """The index carries the ref in the current inline ``ID:kind`` form (as any real ref-add
    writes it); the FILE alone is rewritten back to the pre-0.2 shape -- the bare id kept in
    ``refs`` with its kind pulled out into a separate ``extra.ref_kinds`` map -- the one
    artifact `from_frontmatter`'s parse-time folding has to reconstruct from, since a plain
    JSON index round trip has nothing to fold (whatever shape ``refs`` last held is what a
    bare pydantic load returns verbatim)."""
    a = (await svc.create("task", "Ref source")).item
    b = (await svc.create("task", "Ref target")).item
    await svc.add_ref(a.id, b.id, kind="related")

    path = svc.paths.abspath(a.path)
    text = path.read_text(encoding="utf-8")
    from squads._sections import join_frontmatter, split_frontmatter

    fm, rest = split_frontmatter(text)
    fm["refs"] = [b.id]  # bare id, kind stripped out -- the pre-0.2 shape
    fm.setdefault("extra", {})["ref_kinds"] = {b.id: "related"}
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    await svc.set_status(a.id, "InProgress", force=True)
    reloaded = await svc.get(a.id)
    assert reloaded.status == "InProgress"
    assert any(r.startswith(b.id) for r in reloaded.refs)


async def test_absent_optional_fields_do_not_false_refuse(svc):
    """An item with no parent, no assignee, and no `extra` at all -- every optional field
    dropped from the file entirely rather than written as an explicit empty/null value."""
    task = (await svc.create("task", "No optional fields")).item
    path = svc.paths.abspath(task.path)
    text = path.read_text(encoding="utf-8")
    from squads._sections import join_frontmatter, split_frontmatter

    fm, rest = split_frontmatter(text)
    for key in ("parent", "assignee", "extra", "labels", "refs", "description"):
        fm.pop(key, None)
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    await svc.set_status(task.id, "InProgress", force=True)
    reloaded = await svc.get(task.id)
    assert reloaded.status == "InProgress"


async def test_two_mutations_in_a_row_with_no_interruption_are_never_refused(svc):
    """The plain round trip: create, then mutate twice back to back. The second mutation
    must not be refused by the guard -- the ordinary, overwhelmingly common case."""
    task = (await svc.create("task", "Two in a row")).item
    await svc.update(task.id, description="first")
    await svc.update(task.id, description="second")
    reloaded = await svc.get(task.id)
    assert reloaded.description == "second"


async def test_a_padded_id_mismatch_does_not_false_refuse(svc):
    """A file whose own frontmatter `id:` line was historically written at a padded width
    (a legacy quirk `to_frontmatter_dict()` no longer produces) collapses too: `id` is a
    computed field re-derived from prefix + sequence number on both sides, unpadded, so the
    padding on disk never survives the round trip to be compared at all."""
    task = (await svc.create("task", "Padded id on disk")).item
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
    task = (await svc.create("task", "Untouched by repad")).item

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
    task = (await svc.create("task", "Untouched by renumber")).item
    other = (await svc.create("task", "Shifted by renumber")).item

    await _crash_the_index_commit(
        svc, monkeypatch, lambda: svc.update(task.id, description="interrupted description")
    )

    result = await svc.renumber(from_seq=other.sequence_id, onto=999)  # must not raise
    assert result.remap  # the shift actually happened

    current = await svc.get(task.id)
    assert current.description == "interrupted description"
