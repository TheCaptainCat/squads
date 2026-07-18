"""The 0.8->0.10 migration: makes the legacy, untracked `sq-memory.md` a tracked SKILL item
(a SKILL-<NNNNNN>-sq-memory.md convention file), like every other bundled skill already is.
Mirrors tests/integration/test_skill_migration.py (the 0.4->0.5 precedent this one is modeled
on), scoped to the single sq-memory slug.
"""

import pytest

from squads._migrations._v0_8_to_v0_10 import migrate as migrate_v0_8_to_v0_10
from squads._models._schema import SCHEMA_VERSION
from squads._sections import split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def _make_pre_seed_squad(tmp_path, monkeypatch):
    """A squad initialized WITHOUT skill seeding — the shape a pre-fix squad has on disk:
    every bundled skill (including sq-memory) is a plain, untracked `<slug>.md` file."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    return result.paths


async def test_schema_version_is_bumped_to_0_10():
    assert SCHEMA_VERSION == "0.10"


async def test_migration_stamps_sq_memory_with_an_id_and_convention_filename(
    tmp_path, monkeypatch, frozen_time
):
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    skills_dir = paths.squad_dir / "agents/skills"
    legacy = skills_dir / "sq-memory.md"
    assert legacy.is_file()  # precondition: untracked legacy file

    acted = await migrate_v0_8_to_v0_10(paths)
    assert acted == 1

    assert not legacy.exists()
    convention = list(skills_dir.glob("SKILL-*-sq-memory.md"))
    assert convention, "no SKILL-*-sq-memory.md found after migration"
    fm, _ = split_frontmatter(convention[0].read_text(encoding="utf-8"))
    assert str(fm.get("id", "")).startswith("SKILL-")
    assert fm.get("type") == "skill"
    assert fm.get("status") == "Active"
    assert fm.get("extra", {}).get("slug") == "sq-memory"
    assert fm.get("description")


async def test_migration_is_idempotent_no_new_id_or_rename_on_a_second_run(
    tmp_path, monkeypatch, frozen_time
):
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    first = await migrate_v0_8_to_v0_10(paths)
    assert first == 1

    skills_dir = paths.squad_dir / "agents/skills"
    convention_before = list(skills_dir.glob("SKILL-*-sq-memory.md"))
    assert len(convention_before) == 1
    fm_before, _ = split_frontmatter(convention_before[0].read_text(encoding="utf-8"))
    id_before = fm_before["id"]

    second = await migrate_v0_8_to_v0_10(paths)
    assert second == 0

    convention_after = list(skills_dir.glob("SKILL-*-sq-memory.md"))
    assert len(convention_after) == 1
    assert convention_after[0].name == convention_before[0].name
    fm_after, _ = split_frontmatter(convention_after[0].read_text(encoding="utf-8"))
    assert fm_after["id"] == id_before


async def test_migration_renames_an_already_stamped_but_still_slug_named_file(
    tmp_path, monkeypatch, frozen_time
):
    """A file stamped by a partial prior migration but never renamed still gets the
    convention name, without reallocating its id."""
    from squads._sections import join_frontmatter

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    skills_dir = paths.squad_dir / "agents/skills"
    legacy = skills_dir / "sq-memory.md"
    existing = legacy.read_text(encoding="utf-8")
    fake_fm = {
        "id": "SKILL-000099",
        "sequence_id": 99,
        "type": "skill",
        "title": "sq-memory",
        "slug": "sq-memory",
        "status": "Active",
        "author": "sq-memory",
        "description": "",
        "path": "agents/skills/sq-memory.md",
        "id_padding": 6,
        "schema_version": "0.10",
    }
    legacy.write_text(join_frontmatter(fake_fm, existing), encoding="utf-8")

    acted = await migrate_v0_8_to_v0_10(paths)
    assert acted == 1
    assert not legacy.exists()

    convention = list(skills_dir.glob("SKILL-*-sq-memory.md"))
    assert convention
    fm, _ = split_frontmatter(convention[0].read_text(encoding="utf-8"))
    assert fm.get("id") == "SKILL-000099"  # no reallocation


async def test_migration_is_a_noop_when_already_tracked(tmp_path, monkeypatch, frozen_time):
    """A fresh squad (normal seeding, no skip) already tracks sq-memory as a SKILL item —
    this migration must leave it completely untouched."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    paths = result.paths
    skills_dir = paths.squad_dir / "agents/skills"
    convention_before = list(skills_dir.glob("SKILL-*-sq-memory.md"))
    assert convention_before, "fresh init should already seed sq-memory as a tracked SKILL"

    acted = await migrate_v0_8_to_v0_10(paths)
    assert acted == 0
    convention_after = list(skills_dir.glob("SKILL-*-sq-memory.md"))
    assert convention_after == convention_before


async def test_migration_leaves_a_pointer_that_resolves_to_the_renamed_body_file(
    tmp_path, monkeypatch, frozen_time
):
    """The pointer's @-path must be root-relative (squad_dir/agents/skills/SKILL-…), not
    squad_dir-relative — a squad whose squad_dir != repo root (the default, "squads") caught a
    real bug here where the squad_dir segment was dropped from the rewritten pointer."""
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    assert paths.squad_dir.name == "squads"  # precondition: default init nests under squad_dir
    await migrate_v0_8_to_v0_10(paths)

    skills_dir = paths.squad_dir / "agents/skills"
    pointer = paths.root / ".claude" / "skills" / "sq-memory" / "SKILL.md"
    content = pointer.read_text(encoding="utf-8")
    convention = list(skills_dir.glob("SKILL-*-sq-memory.md"))
    assert convention
    assert f"@squads/agents/skills/{convention[0].name}" in content


async def test_repair_after_migration_rebuilds_the_index_cleanly(
    tmp_path, monkeypatch, frozen_time
):
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_8_to_v0_10(paths)

    svc = service.Service(paths)
    await svc.repair()
    issues = await svc.check()
    assert not [i for i in issues if i.level == "error"]
    skills = await svc.list_items(item_type="skill")
    assert any(getattr(i, "slug", None) == "sq-memory" for i in skills)


async def test_sq_migrate_up_cli_stamps_sq_memory_and_leaves_check_green(
    tmp_path, monkeypatch, frozen_time, invoke
):
    from squads import _aio

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    cfg_path = paths.config_path
    cfg_text = await _aio.read_text(cfg_path)
    cfg_text_08 = cfg_text.replace(f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.8"')
    await _aio.write_text(cfg_path, cfg_text_08)

    r = await invoke(["migrate", "up"])
    assert r.exit_code == 0, r.output

    r = await invoke(["check"])
    assert r.exit_code == 0, r.output

    skills_dir = paths.squad_dir / "agents/skills"
    assert list(skills_dir.glob("SKILL-*-sq-memory.md"))
