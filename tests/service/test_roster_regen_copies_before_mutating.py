"""``sq sync``'s roster-regen pass (``_services/_maintenance.py::sync``) copies each role item
out of the read scope's own snapshot before ``_refresh_catalog_extra`` mutates it and grafts it
into a fresh ``transaction()`` db via ``db.add`` — a locality fix, not a safety fix (the commit
path was already correct: ``ensure_no_skew`` gates the graft, and the excluded-key set is
exactly what the graft reasserts). The point of the copy is that a caller holding an item from
an earlier ``list_items`` call in the same read scope must never see it change out from under
them just because ``sync`` ran afterwards in that same scope.
"""

import pytest

from squads._index._resolver import item_file
from squads._index._store import read_scope
from squads._itemfile import update_frontmatter
from squads._models._extras import ExtraKey as X
from squads._services import _service as service
from squads._workflow import ROSTER_ROLE

pytestmark = pytest.mark.anyio


async def _make_role_stale(svc, role_id: str, key: str) -> None:
    """Directly remove one catalog-derived key from a role item's frontmatter, simulating
    "an item created before this field existed" — the exact scenario ``_refresh_catalog_extra``
    exists to backfill — without going through any of the API that would refuse or refresh it.
    """
    current = await svc.get(role_id)
    base = current.model_copy(deep=True)
    stale = current.model_copy(deep=True)
    stale.extra.pop(key, None)
    async with svc.store.transaction() as db:
        await update_frontmatter(
            item_file(svc.paths, stale), stale, base, default_kind=svc.spec.default_ref_kind()
        )
        db.add(stale)


async def test_sync_never_mutates_an_item_a_caller_is_still_holding_from_list_items(project):
    svc = service.Service(project)
    await _make_role_stale(svc, "ROLE-1", X.AGREEMENTS)

    with read_scope():
        before = await svc.list_items(item_type=ROSTER_ROLE)
        held = next(it for it in before if it.id == "ROLE-1")
        assert X.AGREEMENTS not in held.extra  # sanity: genuinely stale within this scope

        skipped = await svc.sync()
        assert not skipped, skipped

        # The object this test is still holding — handed out by list_items before sync ran —
        # must be exactly as it was. If sync mutated the snapshot's own alias in place (the
        # bug the copy fixes), this would now carry the merged field.
        assert X.AGREEMENTS not in held.extra

    # The commit itself is real: a fresh read (a new Service, no scope) sees the field
    # restored, so the copy is locality-only and changes no observable behaviour.
    refreshed = await service.Service(project).get("ROLE-1")
    assert X.AGREEMENTS in refreshed.extra


async def test_sync_output_and_frontmatter_are_unchanged_by_the_copy(project):
    """The copy is locality, not a behaviour change: ``sync`` still reports the same skip
    messages and still writes the same merged frontmatter, scope or no scope."""
    svc = service.Service(project)
    await _make_role_stale(svc, "ROLE-1", X.AGREEMENTS)

    scoped_svc = service.Service(project)
    with read_scope():
        scoped_skipped = await scoped_svc.sync()
    scoped_extra = (await service.Service(project).get("ROLE-1")).extra

    await _make_role_stale(svc, "ROLE-1", X.AGREEMENTS)
    unscoped_skipped = await service.Service(project).sync()
    unscoped_extra = (await service.Service(project).get("ROLE-1")).extra

    assert scoped_skipped == unscoped_skipped
    assert scoped_extra == unscoped_extra
