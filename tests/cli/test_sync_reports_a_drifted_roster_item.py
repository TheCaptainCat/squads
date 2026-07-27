"""`sq sync`'s CLI surface: a drifted roster item is reported as a warning, not a failure."""

import pytest

from squads import _itemfile as itemfile
from squads._index._resolver import item_file
from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


async def test_sync_command_warns_on_a_drifted_role_and_still_exits_clean(svc, invoke, monkeypatch):
    role = await svc.activate_role("tech-writer")

    real_atomic_write = IndexStore._atomic_write

    async def _boom(self, db):
        raise OSError("simulated crash during the index commit")

    monkeypatch.setattr(IndexStore, "_atomic_write", _boom)
    with pytest.raises(OSError):
        await svc.update(role.id, description="interrupted role description")
    monkeypatch.setattr(IndexStore, "_atomic_write", real_atomic_write)

    r = await invoke(["sync"])
    assert r.exit_code == 0, r.output
    assert "warning" in r.output.lower()
    assert role.id in r.output

    # The surviving value is still on disk -- the CLI's sync never overwrote it.
    on_disk = itemfile.read_frontmatter(text=item_file(svc.paths, role).read_text())
    assert on_disk["description"] == "interrupted role description"
