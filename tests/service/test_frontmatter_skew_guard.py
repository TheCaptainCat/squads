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
    """Reproduces the finding this task closes end to end: fault the index commit during a
    `description` update (deliberately outside {status, parent}, the narrower design's blind
    spot) so the file is ahead; an ordinary status change on the same item must refuse before
    writing anything, then succeed -- with both the interrupted value and the new delta on
    disk -- once `sq repair` has run.
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
    bug = (
        await create_item(svc, "bug", "Legacy severity bug", fields={"severity": "critical"})
    ).item

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
    task = (await create_item(svc, "task", "Repad target")).item
    await svc.repad(8)

    await svc.set_status(task.id, "InProgress", force=True)
    reloaded = await svc.get(task.id)
    assert reloaded.status == "InProgress"


@pytest.mark.parametrize(
    ("kind", "legacy_kind"),
    [
        pytest.param("", "related", id="default-kind"),
        pytest.param("blocks", "blocks", id="non-default-kind"),
    ],
)
async def test_legacy_ref_kinds_map_does_not_false_refuse(svc, kind, legacy_kind):
    """The index carries the ref in the current inline ``ID:kind`` form (as any real ref-add
    writes it); the FILE alone is rewritten back to the pre-0.2 shape -- the bare id kept in
    ``refs`` with its kind pulled out into a separate ``extra.ref_kinds`` map -- the one
    artifact `from_frontmatter`'s parse-time folding has to reconstruct from, since a plain
    JSON index round trip has nothing to fold (whatever shape ``refs`` last held is what a
    bare pydantic load returns verbatim).

    Table-driven over both legs, restoring what this test was once narrowed to a single
    non-default leg to sidestep a regression: the declared **default** kind (``kind=""``,
    legacy map naming ``"related"``) is the leg that regression actually lived in -- the
    encoding invariant forbids ever spelling the default kind out, so the reloaded item's ref
    must come back **bare**, not merely present. The **non-default** leg (``"blocks"``) is
    kept alongside it so the legacy-map reconstruction itself stays pinned, not only the
    default-kind bare-normalisation riding along with it.
    """
    a = (await create_item(svc, "task", "Ref source")).item
    b = (await create_item(svc, "task", "Ref target")).item
    await svc.add_ref(a.id, b.id, kind=kind)

    path = svc.paths.abspath(a.path)
    text = path.read_text(encoding="utf-8")
    from squads._sections import join_frontmatter, split_frontmatter

    fm, rest = split_frontmatter(text)
    fm["refs"] = [b.id]  # bare id, kind stripped out -- the pre-0.2 shape
    fm.setdefault("extra", {})["ref_kinds"] = {b.id: legacy_kind}
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    await svc.set_status(a.id, "InProgress", force=True)
    reloaded = await svc.get(a.id)
    assert reloaded.status == "InProgress"
    expected_ref = b.id if kind == "" else f"{b.id}:{kind}"
    assert reloaded.refs == [expected_ref]


async def test_absent_optional_fields_do_not_false_refuse(svc):
    """An item with no parent, no assignee, and no `extra` at all -- every optional field
    dropped from the file entirely rather than written as an explicit empty/null value."""
    task = (await create_item(svc, "task", "No optional fields")).item
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
# PERMITTED_EXTRA_SKEW: a role's catalog-shaped `extra` fields (`RoleDef.extra_keys()`) are
# exempt for a squad a pre-mirror release last synced -- an index that already lagged on them
# before the merge could be mirrored into the index in the same transaction. That is a
# permanent, by-design skew on those keys alone -- never a real one -- and the exclusion must
# hold for every OTHER seam that later mutates the same role, on a board where nothing was ever
# interrupted.
# ---------------------------------------------------------------------------------------------


async def test_a_permitted_extra_key_ahead_of_the_index_is_never_falsely_refused(svc):
    """A healthy board, no crash anywhere: a role file whose frontmatter carries a
    `PERMITTED_EXTRA_SKEW` key the index has not caught up on -- disk ahead by construction
    here rather than by a writer that no longer exists (the resolved-skills cache this
    reproduced against is gone along with `link-role`'s write of it) -- must not block an
    ordinary mutation through a different seam right after, not refuse with a `sq repair`
    pointer for a divergence that never happened."""
    role = await svc.activate_role("qa")

    path = svc.paths.abspath(role.path)
    text = path.read_text(encoding="utf-8")
    from squads._sections import join_frontmatter, split_frontmatter

    fm, rest = split_frontmatter(text)
    fm["extra"]["color"] = "magenta"
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    # Must not raise -- disk is ahead of the index on a permitted key; the guard cannot and
    # must not tell a legacy-lag key apart from one a live writer just resynced.
    await svc.update(role.id, description="mutated after a permitted-key skew")
    reloaded = await svc.get(role.id)
    assert reloaded.description == "mutated after a permitted-key skew"


async def test_a_catalog_field_merged_by_sync_reaches_the_index_and_never_false_refuses(svc):
    """The second, broader trigger named in the finding: a role catalog gains a field (or an
    override edit does the same) and `sync` merges it into the role's file. Simulated by
    stripping a catalog field consistently from both sides, syncing, then mutating the role
    through an unrelated seam.

    Two properties, and the first one used to be the opposite: the merge now reaches the
    *index* in the same transaction that writes the frontmatter, so a caller reading the item
    back sees the merged value rather than the pre-merge one. The second is unchanged -- the
    following mutation through a different seam must not be refused."""
    role = await svc.activate_role("reviewer")  # a role whose catalog carries `agreements`

    path = svc.paths.abspath(role.path)
    text = path.read_text(encoding="utf-8")
    from squads._sections import join_frontmatter, split_frontmatter

    fm, rest = split_frontmatter(text)
    fm["extra"].pop("agreements", None)
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    db = await svc.store.load()
    item = db.get(role.id)
    assert item is not None
    item.extra.pop("agreements", None)
    await svc.store.overwrite(db)

    skipped = await svc.sync()
    assert not skipped  # the merge write went through -- no false report either

    on_disk = itemfile.read_frontmatter(path=path)
    assert on_disk["extra"]["agreements"]  # merged back onto disk
    reloaded = await svc.get(role.id)
    # ... and mirrored into the index by the same transaction, so the two agree.
    assert reloaded.extra["agreements"] == on_disk["extra"]["agreements"]

    # Must not raise -- the merged field is exempt everywhere, not just at the writer that
    # merged it.
    await svc.update(role.id, description="mutated after a catalog merge")
    final = await svc.get(role.id)
    assert final.description == "mutated after a catalog merge"


async def test_a_project_override_role_under_a_new_slug_is_not_falsely_refused_after_sync(svc):
    """The same false-refusal shape, for a role that isn't one of the bundled eight at all --
    a project override defining a brand-new slug entirely by its own TOML.
    `_refresh_catalog_extra` resolves any role through `resolve_role`, which merges override
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
    fm["extra"].pop("model", None)
    path.write_text(join_frontmatter(fm, rest), encoding="utf-8")

    db = await svc.store.load()
    item = db.get(role.id)
    assert item is not None
    item.extra.pop("model", None)
    await svc.store.overwrite(db)

    skipped = await svc.sync()
    assert not skipped  # the merge write went through -- no false report either

    on_disk = itemfile.read_frontmatter(path=path)
    assert on_disk["extra"]["model"] == "opus"  # merged back onto disk by the override
    reloaded = await svc.get(role.id)
    assert reloaded.extra["model"] == "opus"  # ... and mirrored into the index alongside it

    # Must not raise -- the merged field is exempt for an override-defined role too, not only
    # a role the bundled catalog itself recognizes.
    await svc.update(role.id, description="mutated after an override catalog merge")
    final = await svc.get(role.id)
    assert final.description == "mutated after an override catalog merge"


async def test_an_index_left_lagging_on_a_catalog_field_still_mutates_without_refusing(svc):
    """Why the catalog half of the permitted set is KEPT now that `sync` mirrors its merge
    into the index: a squad last synced by a release without that mirror carries an index that
    already lags on those keys, and the guard must not refuse the very mutation (or the very
    sync) that would otherwise converge it.

    Reproduced from the lagging side only -- the file keeps the catalog value and the index
    copy loses it, which is exactly the state an older sync left behind -- with no sync in
    between, so nothing heals it before the mutation is attempted."""
    role = await svc.activate_role("reviewer")

    db = await svc.store.load()
    item = db.get(role.id)
    assert item is not None
    item.extra.pop("agreements", None)
    item.extra.pop("title", None)
    await svc.store.overwrite(db)

    # Disk is ahead of the index on two catalog keys, and nothing has re-synced.
    on_disk = itemfile.read_frontmatter(path=svc.paths.abspath(role.path))
    assert on_disk["extra"]["title"]
    assert "title" not in (await svc.get(role.id)).extra

    # Must not raise: an unrelated seam mutating a role a stale index lags on.
    await svc.update(role.id, description="mutated against a lagging index")
    assert (await svc.get(role.id)).description == "mutated against a lagging index"

    # That mutation's own pointer regen resolves the role through the catalog rather than the
    # still-lagging index, so the pointer it wrote already carries the real title — never the
    # blank one a mirror-backed regen would have produced — and this sync finds nothing to fix.
    pointer = svc.paths.root / ".claude" / "agents" / "reviewer.md"
    assert on_disk["extra"]["title"] in pointer.read_text(encoding="utf-8")
    assert await svc.sync() == []
    healed = await svc.get(role.id)
    assert healed.extra["title"] == on_disk["extra"]["title"]


# ---------------------------------------------------------------------------------------------
# The permitted set above is by *key name*; whether it actually applies is a further, per-item
# question. `_refresh_catalog_extra` does resolve a dev role now (against a base built from the
# item's own stored identity, never a regenerated one), but it writes markdown and mirrors the
# index inside one transaction, so it introduces no permanent lag on that account either. Its
# catalog-shaped fields (`model`, `title`, ...) stay ordinary, transaction-guarded
# fields for a dev role -- a REAL skew on them must refuse like any other field, not slide
# through.
# ---------------------------------------------------------------------------------------------


async def test_interrupting_a_dev_roles_set_model_then_editing_elsewhere_refuses_not_reverts(
    svc, monkeypatch
):
    """The counterpart to the two false-refusal cases above: this key-name collides with a
    catalog role's exempt `model`, but a dev role's own catalog fields are not exempt (only
    `extra.skills` is), so nothing here is permitted skew. Interrupting `--set model=` must be
    treated as the real skew it is -- refusing the next mutation through any other seam --
    rather than the old behaviour, which let the mutation through and clobbered the committed
    value with the stale index-loaded one."""
    dev = await svc.add_dev("python")

    await _crash_the_index_commit(
        svc, monkeypatch, lambda: svc.update(dev.id, set_extra={"model": "haiku"})
    )

    # Markdown ahead of the index: the file carries the new model, the index doesn't.
    on_disk = itemfile.read_frontmatter(path=svc.paths.abspath(dev.path))
    assert on_disk["extra"]["model"] == "haiku"
    reloaded = await svc.get(dev.id)
    assert reloaded.extra.get("model") != "haiku"

    # An unrelated edit refuses -- before writing anything -- rather than silently reverting
    # the committed model back to the stale index-loaded value.
    with pytest.raises(SquadsError, match=rf"{dev.id}.*repair"):
        await svc.update(dev.id, description="mutated after an interrupted --set")

    still_on_disk = itemfile.read_frontmatter(path=svc.paths.abspath(dev.path))
    assert still_on_disk["extra"]["model"] == "haiku"  # not reverted by the refused attempt

    await svc.repair()
    await svc.update(dev.id, description="mutated after repair")
    final = await svc.get(dev.id)
    assert final.extra.get("model") == "haiku"
    assert final.description == "mutated after repair"
