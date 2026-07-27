"""`sq sync`'s roster regen path: the same guard as a single mutation, the opposite response.

A drifted role's frontmatter is left untouched and named in `sync`'s output rather than
refused -- `sync` is bulk regeneration of derived state and is itself what an operator reaches
for when generated files are wrong, so aborting the run would block the remedy over a
condition `sync` did not cause.
"""

import pytest

from squads import _itemfile as itemfile
from squads._index._resolver import item_file
from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


async def test_a_drifted_role_is_skipped_and_named_while_the_rest_of_the_roster_syncs(
    svc, monkeypatch
):
    role = await svc.activate_role("tech-writer")
    other_role = await svc.activate_role("reviewer")

    real_atomic_write = IndexStore._atomic_write

    async def _boom(self, db):
        raise OSError("simulated crash during the index commit")

    monkeypatch.setattr(IndexStore, "_atomic_write", _boom)
    with pytest.raises(OSError):
        await svc.update(role.id, description="interrupted role description")
    monkeypatch.setattr(IndexStore, "_atomic_write", real_atomic_write)

    on_disk_before = itemfile.read_frontmatter(text=item_file(svc.paths, role).read_text())
    assert on_disk_before["description"] == "interrupted role description"

    skipped = await svc.sync()  # must not raise -- sync always exits clean

    assert any(role.id in msg for msg in skipped)

    # The drifted role's frontmatter is untouched -- the surviving value is still there.
    on_disk_after = itemfile.read_frontmatter(text=item_file(svc.paths, role).read_text())
    assert on_disk_after["description"] == "interrupted role description"

    # Everything else still regenerated: the other, healthy role's pointer/body sync normally
    # (no exception reached them, and it is not itself named in the skip list).
    assert not any(other_role.id in msg for msg in skipped)


async def test_a_clean_roster_syncs_with_no_skip_output(svc):
    await svc.activate_role("tech-writer")
    await svc.add_skill("Runbook")

    skipped = await svc.sync()

    assert skipped == []

    # Running it again is exactly as clean -- no behaviour change, no new output.
    skipped_again = await svc.sync()
    assert skipped_again == []
