"""`sq adopt` imports a pre-existing (non-sq-created) squad tree — the manager role plus any
already-authored item files — reconstructing `.squads.toml`/the index without an sq-managed
config already present, activating only the roles that weren't already implied by the
imported content, and never re-activating or re-importing anything on a second run.
"""

import pytest

from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def test_adopt_imports_a_legacy_tree_and_is_idempotent_on_a_second_run(
    tmp_path, monkeypatch, frozen_time
) -> None:
    monkeypatch.chdir(tmp_path)
    # A pre-existing squad with one task but no config/index — legacy/native files only.
    init = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    await service.Service(init.paths).create("task", "legacy")
    (tmp_path / ".squads.toml").unlink()
    (tmp_path / "squads" / ".squads.json").unlink()

    result = await service.adopt(root=tmp_path, roles_spec="core")
    assert (tmp_path / ".squads.toml").exists()
    assert result.imported == 2  # the manager role + the legacy task

    activated = {r.extra["slug"] for r in result.roles}
    assert "manager" not in activated  # already existed on disk -> imported, not re-activated
    assert {"architect", "tech-lead", "reviewer"} <= activated

    again = await service.adopt(root=tmp_path, roles_spec="core")
    assert again.roles == []
