"""The fail-closed skew guard: before a mutation rewrites an item's frontmatter from
index-derived state, the on-disk frontmatter must match what the index-loaded item would have
serialized before this mutation's own delta. A real skew refuses, loudly, with a `sq repair`
pointer; a healthy board is never refused.
"""

import pytest

from _helpers import create_item
from squads import _itemfile as itemfile
from squads import _sections as sections
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
# PERMITTED_ATTRIBUTE_SKEW: a role's catalog-shaped attributes (`RoleDef.attribute_keys()`) are
# exempt for a squad whose index already lagged on them before the merge could be mirrored into
# the index in the same transaction. That is a
# permanent, by-design skew on those keys alone -- never a real one -- and the exclusion must
# hold for every OTHER seam that later mutates the same role, on a board where nothing was ever
# interrupted.
# ---------------------------------------------------------------------------------------------


async def test_a_permitted_extra_key_ahead_of_the_index_is_never_falsely_refused(svc):
    """A healthy board, no crash anywhere: a role file whose frontmatter carries a
    `PERMITTED_ATTRIBUTE_SKEW` key the index has not caught up on -- the divergence is written
    here directly, since no live writer produces it -- must not block an ordinary mutation
    through a different seam right after, nor refuse with a `sq repair` pointer for a
    divergence that never happened."""
    role = await svc.activate_role("qa")

    path = svc.paths.abspath(role.path)
    text = path.read_text(encoding="utf-8")
    from squads._sections import join_frontmatter, split_frontmatter

    fm, rest = split_frontmatter(text)
    fm["model"] = "haiku"  # a `PERMITTED_ATTRIBUTE_SKEW` member, on a non-dev role
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    # Must not raise -- disk is ahead of the index on a permitted key; the guard cannot and
    # must not tell a legacy-lag key apart from one a live writer just resynced.
    await svc.update(role.id, title="Renamed after a permitted-key skew")
    reloaded = await svc.get(role.id)
    assert reloaded.title == "Renamed after a permitted-key skew"


async def test_a_catalog_field_merged_by_sync_reaches_the_index_and_never_false_refuses(svc):
    """The broader shape: a role catalog changes (or an override edit does the same) and `sync`
    reconciles the role's file to it, so the reconcile reaches a value the index has not seen.
    Simulated by planting a stale value consistently on both sides, syncing, then mutating the
    role through an unrelated seam.

    The reconciled value is the **projection** -- the resolved full name and mission on the
    item's own ``title``/``description`` -- because that is what a role item stores of its
    definition; the rest is resolved on read and never written anywhere to go stale.

    Two properties. The reconcile reaches the *index* in the same transaction that writes the
    frontmatter, so a caller reading the item back sees the merged value, not the pre-merge
    one. And the following mutation through a different seam must not be refused."""
    role = await svc.activate_role("reviewer")
    catalog_mission = role.description

    path = svc.paths.abspath(role.path)
    text = path.read_text(encoding="utf-8")
    from squads._sections import join_frontmatter, split_frontmatter

    fm, rest = split_frontmatter(text)
    fm["description"] = "a stale mission the catalog no longer says"
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    db = await svc.store.load()
    item = db.get(role.id)
    assert item is not None
    item.description = "a stale mission the catalog no longer says"
    await svc.store.overwrite(db)

    skipped = await svc.sync()
    assert not skipped  # the reconcile write went through -- no false report either

    on_disk = itemfile.read_frontmatter(path=path)
    assert on_disk["description"] == catalog_mission  # reconciled back onto disk
    reloaded = await svc.get(role.id)
    # ... and mirrored into the index by the same transaction, so the two agree.
    assert reloaded.description == on_disk["description"]

    # Must not raise -- the two sides agree, so an unrelated seam mutates cleanly right after.
    await svc.update(role.id, title="Renamed after a catalog reconcile")
    final = await svc.get(role.id)
    assert final.title == "Renamed after a catalog reconcile"


async def test_a_project_override_role_under_a_new_slug_is_not_falsely_refused_after_sync(svc):
    """The same false-refusal shape, for a role that isn't one of the bundled eight at all --
    a project override defining a brand-new slug entirely by its own TOML.
    `_refresh_catalog_attributes` resolves any role through `resolve_role`, which merges override
    TOMLs too, not just bundled slugs -- so both properties must hold for one of those as
    well, not only for slugs the bundled catalog itself recognizes."""
    override = svc.paths.squad_dir / ".overrides" / "roles" / "security-expert.toml"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(
        'full_name = "Sam Security"\ntitle = "security expert"\n'
        'description = "Keeps the system secure."\nmission = "Find and fix security issues."\n'
        'model = "opus"\n',
        encoding="utf-8",
    )
    role = await svc.activate_role("security-expert")

    path = svc.paths.abspath(role.path)
    text = path.read_text(encoding="utf-8")
    from squads._sections import join_frontmatter, split_frontmatter

    fm, rest = split_frontmatter(text)
    fm["description"] = "a stale mission the override no longer declares"
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    db = await svc.store.load()
    item = db.get(role.id)
    assert item is not None
    item.description = "a stale mission the override no longer declares"
    await svc.store.overwrite(db)

    skipped = await svc.sync()
    assert not skipped  # the reconcile write went through -- no false report either

    on_disk = itemfile.read_frontmatter(path=path)
    assert on_disk["description"] == "Find and fix security issues."  # from the override
    reloaded = await svc.get(role.id)
    assert reloaded.description == on_disk["description"]  # ... mirrored into the index too

    # Must not raise -- the reconcile behaves the same for an override-defined role as for a
    # role the bundled catalog itself recognizes.
    await svc.update(role.id, title="Renamed after an override reconcile")
    final = await svc.get(role.id)
    assert final.title == "Renamed after an override reconcile"


async def test_an_index_left_lagging_on_a_catalog_field_still_mutates_without_refusing(svc):
    """Why the catalog half of the permitted set is KEPT even though `sync` mirrors its merge
    into the index: a squad last synced by a release without that mirror carries an index that
    already lags on those keys, and the guard must not refuse the very mutation (or the very
    sync) that would otherwise converge it.

    Reproduced from the lagging side only -- the file keeps the catalog value and the index
    copy loses it, which is exactly the state an older sync left behind -- with no sync in
    between, so nothing heals it before the mutation is attempted."""
    role = await svc.activate_role("reviewer")

    path = svc.paths.abspath(role.path)
    fm, rest = sections.split_frontmatter(path.read_text(encoding="utf-8"))
    fm["model"] = "haiku"  # the key the reconciler still exempts
    path.write_text(sections.join_frontmatter(fm, rest), encoding="utf-8")

    # Disk is ahead of the index on a permitted key, and nothing has re-synced.
    on_disk = itemfile.read_frontmatter(path=path)
    assert on_disk["model"] == "haiku"
    assert "model" not in (await svc.get(role.id)).attributes

    # Must not raise: an unrelated seam mutating a role a stale index lags on.
    await svc.update(role.id, title="Renamed against a lagging index")
    assert (await svc.get(role.id)).title == "Renamed against a lagging index"

    # That mutation's own pointer regen resolves the role through the catalog rather than the
    # still-lagging index, so the pointer it wrote already carries the real title — never the
    # blank one a mirror-backed regen would have produced — and this sync finds nothing to fix.
    pointer = svc.paths.root / ".claude" / "agents" / "reviewer.md"
    assert "code reviewer" in pointer.read_text(encoding="utf-8")
    assert await svc.sync() == []
    healed = await svc.get(role.id)
    assert healed.slug == "reviewer"


# ---------------------------------------------------------------------------------------------
# The permitted set above is by *key name*; whether it actually applies is a further, per-item
# question. `_refresh_catalog_attributes` does resolve a dev role (against a base built from the
# item's own stored identity, never a regenerated one), but it writes markdown and mirrors the
# index inside one transaction, so it introduces no permanent lag on that account either. Its
# catalog-shaped fields (`model`, `title`, ...) stay ordinary, transaction-guarded
# fields for a dev role -- a REAL skew on them must refuse like any other field, not slide
# through.
# ---------------------------------------------------------------------------------------------
