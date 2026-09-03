"""The 0.4->0.5 skill migration: stamps a SKILL-… id + convention filename onto every bundled
skill, backfills its registry description, is idempotent, and leaves `sq repair`/`sq check`
clean. The CLI surface (`sq migrate up`) is thin wiring over the same runner, proven once here
rather than re-deriving the runner's own behaviour.
"""

import json
from pathlib import PureWindowsPath

import pytest

from squads._interactions import bundled_skill_slugs, skill_description
from squads._migrations._v0_4_to_v0_5 import _posix_rel
from squads._migrations._v0_4_to_v0_5 import migrate as migrate_v0_4_to_v0_5
from squads._models._schema import SCHEMA_VERSION
from squads._sections import split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio


def test_posix_rel_normalizes_windows_style_separators_on_any_host():
    """`_posix_rel` must render `/`, never the host separator — pinned against
    `PureWindowsPath` (pure path arithmetic, no real filesystem, no host OS involved) so this
    fails on Linux CI too if the implementation ever regresses to a bare `str(relative_to(...))`,
    which renders `\\` on Windows but `/` on Linux/macOS and so would pass unnoticed there."""
    root = PureWindowsPath("C:\\squads")
    path = PureWindowsPath("C:\\squads\\agents\\skills\\SKILL-000002-greeting.md")
    assert _posix_rel(path, root) == "agents/skills/SKILL-000002-greeting.md"


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
    # `path` is model-only and derivable from the file's own location — the migration must
    # strip a stale copy rather than persist/refresh one that goes stale on the next rename.
    assert "path" not in fm


async def test_migration_leaves_a_pointer_naming_the_fetch_command_not_a_path(
    tmp_path, monkeypatch, frozen_time
):
    """A migration runner is frozen against the schema version it transforms, never against a
    regenerable artifact like this pointer — so it renders today's pointer shape, which names
    the definition-fetch command rather than a path (regardless of the body file's own renamed,
    convention-stamped location)."""
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_4_to_v0_5(paths)

    skills_dir = paths.squad_dir / "agents/skills"
    claude_skills = paths.root / ".claude" / "skills"
    for slug in bundled_skill_slugs():
        pointer = claude_skills / slug / "SKILL.md"
        if not pointer.exists():
            continue
        content = pointer.read_text(encoding="utf-8")
        assert f"sq skill {slug} show" in content
        assert "SKILL-" not in content
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


async def test_migration_backfills_description_onto_an_already_stamped_convention_file(
    tmp_path, monkeypatch, frozen_time
):
    """A live-repo corner case: a convention-named, already-stamped skill file whose
    description was wiped (e.g. by an older pre-backfill migration run) gets its
    description filled in on a *second* migration pass, not just the first."""
    from squads._sections import replace_frontmatter, split_frontmatter

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_4_to_v0_5(paths)  # first pass: creates convention files with description

    skills_dir = paths.squad_dir / "agents/skills"
    for slug in bundled_skill_slugs():
        convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        if not convention:
            continue
        text = convention[0].read_text(encoding="utf-8")
        fm, _ = split_frontmatter(text)
        fm["description"] = ""
        convention[0].write_text(replace_frontmatter(text, fm), encoding="utf-8")

    acted = await migrate_v0_4_to_v0_5(paths)
    assert acted > 0, "the re-run must backfill every description-less convention file"

    for slug in bundled_skill_slugs():
        convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        fm, _ = split_frontmatter(convention[0].read_text(encoding="utf-8"))
        assert fm.get("description") == skill_description(slug)


async def test_description_backfill_still_rewrites_the_pointer_with_no_path_frontmatter_key(
    tmp_path, monkeypatch, frozen_time
):
    """The backfill branch runs with a `path:` frontmatter key absent — the live model never
    writes one — and must still rewrite a stale pointer to today's shape, which names the
    definition-fetch command rather than any location, convention file's own or otherwise."""
    from squads._sections import replace_frontmatter, split_frontmatter

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_4_to_v0_5(paths)  # first pass: creates convention files + pointers

    skills_dir = paths.squad_dir / "agents/skills"
    slug = bundled_skill_slugs()[0]
    convention = next(iter(skills_dir.glob(f"SKILL-*-{slug}.md")))
    text = convention.read_text(encoding="utf-8")
    fm, _ = split_frontmatter(text)
    assert "path" not in fm  # the live model never writes this key
    fm["description"] = ""
    convention.write_text(replace_frontmatter(text, fm), encoding="utf-8")

    pointer = paths.root / ".claude" / "skills" / slug / "SKILL.md"
    pointer.write_text("STALE\n", encoding="utf-8")  # simulate a pointer that needs rewriting

    acted = await migrate_v0_4_to_v0_5(paths)
    assert acted > 0

    content = pointer.read_text(encoding="utf-8")
    assert "STALE" not in content
    assert f"sq skill {slug} show" in content
    assert convention.name not in content


async def test_backfill_strips_a_stale_path_key_even_with_a_description_already_present(
    tmp_path, monkeypatch, frozen_time
):
    """An already-migrated corpus from a pre-fix release can carry a stale `path:` key on a
    convention file that already has its description — the early-return no-op path must not
    let that survive forever; it has to reach the strip too."""
    from squads._sections import replace_frontmatter, split_frontmatter

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_4_to_v0_5(paths)  # first pass: creates convention files + description

    skills_dir = paths.squad_dir / "agents/skills"
    slug = bundled_skill_slugs()[0]
    convention = next(iter(skills_dir.glob(f"SKILL-*-{slug}.md")))
    text = convention.read_text(encoding="utf-8")
    fm, _ = split_frontmatter(text)
    assert fm.get("description")  # precondition: description already present
    fm["path"] = f"agents/skills/OLD-STALE-NAME-{slug}.md"  # what a pre-fix release stamped
    convention.write_text(replace_frontmatter(text, fm), encoding="utf-8")

    acted = await migrate_v0_4_to_v0_5(paths)
    assert acted > 0

    fm_after, _ = split_frontmatter(convention.read_text(encoding="utf-8"))
    assert "path" not in fm_after


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
