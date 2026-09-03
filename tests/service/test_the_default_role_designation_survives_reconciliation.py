"""The default-role designation, driven across ``sync`` and ``repair`` for both role shapes.

The designation has two possible sources — the role catalog's own ``is_default``, and the
item's stored ``extra.is_default`` override that ``sq role set-default`` writes — and exactly
one live role may hold it. Two failures live at that seam, and this file drives both:

- **the revert**: a reconcile writing the catalog's answer back over the operator's, so the
  designation silently returns to the bundled role on the next ``sq sync``;
- **the un-cleared holder**: a move that clears only roles carrying the *stored* key, leaving
  the catalog's own designated role — which stores nothing — holding it too, so the squad
  generates config naming two live defaults.

Every assertion resolves the designation the way every reader of it does, rather than reading
``extra.is_default``: a raw read cannot see the second failure at all, which is how it survived
into a shipped build once already.
"""

import pytest

pytestmark = pytest.mark.anyio


async def _holders(svc) -> list[str]:
    """The slugs holding the designation, resolved — the answer ``sq role list`` prints and
    every backend compiles its default-role line from."""
    return sorted(r.slug for r in await svc.roster_all() if r.is_default)


async def _reconcile(svc) -> None:
    """The reconciliation an operator actually runs, in the order they run it."""
    await svc.sync()
    await svc.repair()
    await svc.sync()


async def test_the_catalog_designates_exactly_one_role_before_anything_moves(svc):
    """The baseline the two tests below are measured against — and the reason a raw
    ``extra.is_default`` read is not enough: this holder stores nothing at all."""
    await svc.activate_role("qa")
    assert await _holders(svc) == ["manager"]

    manager = await svc.roster_item("role", "manager")
    assert manager is not None
    assert "is_default" not in manager.extra


async def test_a_designation_moved_onto_a_bundled_role_survives_sync_and_repair(project, svc):
    qa = await svc.activate_role("qa")

    await svc.set_default_role(qa.id)
    assert await _holders(svc) == ["qa"]

    await _reconcile(svc)

    assert await _holders(svc) == ["qa"]
    claude_md = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "default to **Mara Tester** (`qa`)" in claude_md
    assert "default to **Catherine Manager**" not in claude_md


async def test_a_designation_moved_onto_a_developer_role_survives_sync_and_repair(project, svc):
    """The developer shape resolves through a different merge base (``dev_base_from_item``), so
    it is a second seam, not a second spelling of the first."""
    dev = await svc.add_dev("rust", name="Priya Rust")

    await svc.set_default_role(dev.id)
    assert await _holders(svc) == ["rust-dev"]

    await _reconcile(svc)

    assert await _holders(svc) == ["rust-dev"]
    claude_md = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "default to **Priya Rust** (`rust-dev`)" in claude_md


async def test_the_move_clears_the_catalogs_own_holder_which_stores_nothing(svc):
    """The un-cleared-holder failure, isolated: the role the catalog designates carries no
    stored key, so clearing it means *writing* the override rather than removing one."""
    qa = await svc.activate_role("qa")

    result = await svc.set_default_role(qa.id)

    manager = await svc.roster_item("role", "manager")
    assert manager is not None
    assert manager.id in result.cleared
    assert manager.extra["is_default"] is False  # written, not absent — an absence resolves True
    assert await _holders(svc) == ["qa"]


async def test_check_stays_clean_across_the_whole_move(svc):
    dev = await svc.add_dev("rust", name="Priya Rust")
    await svc.set_default_role(dev.id)
    await _reconcile(svc)
    assert await svc.check() == []
