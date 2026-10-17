"""``sq sync`` brings back a deleted managed skill file whole, and ``sq check`` is clean after."""

import pytest

from squads import _aio
from squads._sections import split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("slug", ["squads", "sq-task"])
async def test_sync_then_check_after_deleting_a_managed_skill(tmp_path, monkeypatch, invoke, slug):
    monkeypatch.chdir(tmp_path)
    await service.init(root=tmp_path, roles_spec="minimal")
    (md,) = (tmp_path / "squads" / "agents" / "skills").glob(f"SKILL-*-{slug}.md")
    md.unlink()

    synced = await invoke(["sync"])
    checked = await invoke(["check"])

    assert synced.exit_code == 0, synced.output
    assert checked.exit_code == 0, checked.output
    assert split_frontmatter(await _aio.read_text(md))[0]["id"].startswith("SKILL-")
