"""``Service.rename_status()`` composes each moved item's new text in memory and writes it once,
before the index commit; items outside the moved set are not written.
"""

import pytest

from _helpers import create_item
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("moved", [1, 3])
@pytest.mark.parametrize("bystander", [False, True], ids=["alone", "with-bystander"])
async def test_a_status_rename_writes_each_moved_file_once(svc, write_ledger, moved, bystander):
    tasks = [(await create_item(svc, "task", f"Task {n}")).item for n in range(moved)]
    if bystander:
        await create_item(svc, "bug", "Untouched")

    res = await svc.rename_status("task", "Draft", "Ready")

    unit = next(u for u in reversed(write_ledger.finished) if u.method == "rename_status")
    assert set(unit.counts.values()) == {1}
    assert len(unit.counts) == moved
    assert res.renamed == moved
    for task in tasks:
        path = svc.paths.abspath((await svc.get(task.id)).path)
        assert read_frontmatter(path)["status"] == "Ready"
        assert "status renamed Draft → Ready" in path.read_text(encoding="utf-8")


async def test_a_status_rename_cli_smoke(svc, invoke):
    await create_item(svc, "task", "Subject")

    result = await invoke(["migrate", "rename-status", "task", "Draft", "Ready"])

    assert result.exit_code == 0
