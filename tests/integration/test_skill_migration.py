"""The 0.4->0.5 skill migration: stamps a SKILL-… id + convention filename onto every bundled
skill, backfills its registry description, is idempotent, and leaves `sq repair`/`sq check`
clean. The CLI surface (`sq migrate up`) is thin wiring over the same runner, proven once here
rather than re-deriving the runner's own behaviour.
"""

import json

import pytest

from squads._interactions import bundled_skill_slugs, skill_description
from squads._migrations._v0_4_to_v0_5 import migrate as migrate_v0_4_to_v0_5
from squads._models._schema import SCHEMA_VERSION
from squads._sections import split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def _make_pre_seed_squad(tmp_path, monkeypatch):
    """A squad initialized WITHOUT skill seeding — exactly the shape a pre-0.5 squad has on
    disk before this migration runs."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    return result.paths


async def test_migration_stamps_every_bundled_skill_with_an_id_and_convention_filename(
    tmp_path, monkeypatch, frozen_time
):
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    skills_dir = paths.squad_dir / "agents/skills"

    acted = await migrate_v0_4_to_v0_5(paths)
    assert acted > 0

    skill_ids: set[str] = set()
    for slug in bundled_skill_slugs():
        legacy = skills_dir / f"{slug}.md"
        assert not legacy.exists()
        convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        assert convention, f"no SKILL-*-{slug}.md found after migration"
        fm, _ = split_frontmatter(convention[0].read_text(encoding="utf-8"))
        assert str(fm.get("id", "")).startswith("SKILL-")
        assert fm.get("type") == "skill"
        assert fm.get("status") == "Active"
        assert fm.get("description") == skill_description(slug)
        skill_ids.add(str(fm["id"]))
    assert len(skill_ids) == acted


async def test_migration_is_idempotent_no_renames_or_id_changes_on_a_second_run(
    tmp_path, monkeypatch, frozen_time
):
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    first = await migrate_v0_4_to_v0_5(paths)
    assert first > 0

    skills_dir = paths.squad_dir / "agents/skills"
    ids_after_first = {
        md.name: split_frontmatter(md.read_text(encoding="utf-8"))[0].get("id")
        for md in sorted(skills_dir.glob("SKILL-*.md"))
    }

    second = await migrate_v0_4_to_v0_5(paths)
    assert second == 0

    for md in sorted(skills_dir.glob("SKILL-*.md")):
        fm, _ = split_frontmatter(md.read_text(encoding="utf-8"))
        assert fm.get("id") == ids_after_first[md.name]


async def test_migration_renames_an_already_stamped_but_still_slug_named_file(
    tmp_path, monkeypatch, frozen_time
):
    """A file stamped by a partial prior migration but never renamed still gets the convention
    name, without reallocating its id."""
    from squads._sections import join_frontmatter

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    skills_dir = paths.squad_dir / "agents/skills"
    slug = bundled_skill_slugs()[0]
    legacy = skills_dir / f"{slug}.md"
    existing = legacy.read_text(encoding="utf-8")
    fake_fm = {
        "id": "SKILL-000099",
        "sequence_id": 99,
        "type": "skill",
        "title": slug,
        "slug": slug,
        "status": "Active",
        "author": slug,
        "description": "",
        "path": f"agents/skills/{slug}.md",
        "id_padding": 6,
        "schema_version": "0.5",
    }
    legacy.write_text(join_frontmatter(fake_fm, existing), encoding="utf-8")

    acted = await migrate_v0_4_to_v0_5(paths)
    assert acted >= 1
    assert not legacy.exists()

    convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
    assert convention
    fm, _ = split_frontmatter(convention[0].read_text(encoding="utf-8"))
    assert fm.get("id") == "SKILL-000099"  # no reallocation


async def test_migration_leaves_a_pointer_that_resolves_to_the_renamed_body_file(
    tmp_path, monkeypatch, frozen_time
):
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_4_to_v0_5(paths)

    skills_dir = paths.squad_dir / "agents/skills"
    claude_skills = paths.root / ".claude" / "skills"
    for slug in bundled_skill_slugs():
        pointer = claude_skills / slug / "SKILL.md"
        if not pointer.exists():
            continue
        content = pointer.read_text(encoding="utf-8")
        assert "SKILL-" in content
        assert list(skills_dir.glob(f"SKILL-*-{slug}.md"))


async def test_repair_after_migration_rebuilds_the_index_cleanly(
    tmp_path, monkeypatch, frozen_time
):
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_4_to_v0_5(paths)

    svc = service.Service(paths)
    await svc.repair()
    issues = await svc.check()
    assert not [i for i in issues if i.level == "error"]
    assert await svc.list_items(item_type="skill")


# --------------------------------------------------------------------------- CLI wiring (thin)


async def test_sq_migrate_up_cli_stamps_skills_and_leaves_check_green(
    tmp_path, monkeypatch, frozen_time, invoke
):
    import tomllib

    from squads import _aio

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    cfg_path = paths.config_path
    cfg_text = await _aio.read_text(cfg_path)
    cfg_text_04 = cfg_text.replace(f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.4"')
    await _aio.write_text(cfg_path, cfg_text_04)

    r = await invoke(["migrate", "up"])
    assert r.exit_code == 0, r.output

    with cfg_path.open("rb") as fh:
        final = tomllib.load(fh)
    assert final["schema_version"] == SCHEMA_VERSION

    r = await invoke(["check"])
    assert r.exit_code == 0, r.output

    r = await invoke(["list", "--type", "skill", "--json"])
    assert r.exit_code == 0
    assert len(json.loads(r.output)) > 0


async def test_sq_migrate_up_is_idempotent_from_the_cli(tmp_path, monkeypatch, frozen_time, invoke):
    monkeypatch.chdir(tmp_path)
    await service.init(root=tmp_path, roles_spec="minimal")

    r = await invoke(["migrate", "up"])
    assert r.exit_code == 0
    assert f"already at schema v{SCHEMA_VERSION}" in r.output
