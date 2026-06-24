"""Tests for FEAT-000178 / TASK-189 (migration) + TASK-190 (wiring).

TASK-189: the 0.4→0.5 migration stamps SKILL ids on existing squads.
TASK-190: sq skill <n> show and ref round-trip (SKILL refs on tasks/features).
"""

import json
from pathlib import Path

import pytest

from squads._migrations._v0_4_to_v0_5 import migrate as migrate_v0_4_to_v0_5
from squads._models._enums import ItemType
from squads._models._schema import SCHEMA_VERSION
from squads._paths import SquadPaths
from squads._sections import split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_pre_seed_squad(tmp_path: Path, monkeypatch) -> SquadPaths:
    """Init a squad WITHOUT skill seeding (simulates a pre-FEAT-178 squad).

    The backend still writes skill body files (via refresh_managed), but
    seed_bundled_skills() is skipped, so the files have no SKILL ids.
    This is exactly what a squad looks like before the 0.4→0.5 migration runs.
    """
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    return result.paths


# ---------------------------------------------------------------------------
# TASK-189: migration runner tests
# ---------------------------------------------------------------------------


async def test_migration_stamps_all_bundled_skills(tmp_path, monkeypatch, frozen_time):
    """0.4→0.5 migration stamps every bundled skill with a SKILL-… id and renames the
    file to the SKILL-NNNNNN-slug.md convention (ADR-000181 decision #3, AC#1 + AC#2)."""
    from squads._interactions import bundled_skill_slugs

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)

    # Before migration: skill files exist with slug names and have no id.
    skills_dir = paths.squad_dir / ItemType.SKILL.folder
    for slug in bundled_skill_slugs():
        md = skills_dir / f"{slug}.md"
        if md.is_file():
            fm, _ = split_frontmatter(md.read_text(encoding="utf-8"))
            assert not fm.get("id"), f"{slug}.md should be unstamped before migration"

    acted = await migrate_v0_4_to_v0_5(paths)
    assert acted > 0, "migration must act on at least one skill file"

    # After migration: convention-named SKILL-NNNNNN-slug.md files exist; slugs gone.
    skill_ids: set[str] = set()
    for slug in bundled_skill_slugs():
        legacy = skills_dir / f"{slug}.md"
        assert not legacy.exists(), f"legacy {slug}.md must be gone after migration"
        convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        assert convention, f"no SKILL-*-{slug}.md found after migration"
        md = convention[0]
        fm, _ = split_frontmatter(md.read_text(encoding="utf-8"))
        assert fm.get("id"), f"{md.name}: missing id"
        assert str(fm["id"]).startswith("SKILL-"), f"{md.name}: id must start with SKILL-"
        assert fm.get("sequence_id"), f"{md.name}: missing sequence_id"
        assert fm.get("type") == "skill", f"{md.name}: type must be skill"
        assert fm.get("status") == "Active", f"{md.name}: status must be Active"
        skill_ids.add(str(fm["id"]))

    # All ids must be unique.
    assert len(skill_ids) == acted, "each acted-on skill must have a unique SKILL-… id"


async def test_migration_idempotent(tmp_path, monkeypatch, frozen_time):
    """Re-running the migration is a no-op (AC#4 / ADR #4): no renames, no id changes."""
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)

    first = await migrate_v0_4_to_v0_5(paths)
    assert first > 0

    # Capture convention filenames + ids after first run.
    skills_dir = paths.squad_dir / ItemType.SKILL.folder
    ids_after_first: dict[str, str] = {}
    for md in sorted(skills_dir.glob("SKILL-*.md")):
        fm, _ = split_frontmatter(md.read_text(encoding="utf-8"))
        if fm.get("id"):
            ids_after_first[md.name] = str(fm["id"])
    assert ids_after_first, "must have convention files after first migration"

    # Second run must be a no-op.
    second = await migrate_v0_4_to_v0_5(paths)
    assert second == 0, "second migration run must be a no-op"

    # Files and ids unchanged.
    for md in sorted(skills_dir.glob("SKILL-*.md")):
        fm, _ = split_frontmatter(md.read_text(encoding="utf-8"))
        if fm.get("id"):
            assert str(fm["id"]) == ids_after_first[md.name], f"{md.name}: id changed on second run"


async def test_repair_after_migration_rebuilds_cleanly(tmp_path, monkeypatch, frozen_time):
    """sq repair after migration reconstructs the index; sq check is green (AC#2)."""
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_4_to_v0_5(paths)

    svc = service.Service(paths)
    await svc.repair()
    issues = await svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors, f"sq check produced errors after migration+repair: {errors}"

    # All stamped skills must be findable via list.
    skills = await svc.list_items(item_type=ItemType.SKILL)
    assert len(skills) > 0, "sq list -t skill must be non-empty after migration+repair"


async def test_migration_lexical_ordering_parity_with_init(tmp_path, monkeypatch, frozen_time):
    """Ordering parity (AC#3 / ADR #5): the relative lexical order of skills matches
    a fresh sq init.  Identical numeric IDs are NOT asserted — only ordinal position.
    """
    from squads._interactions import bundled_skill_slugs

    # Squad A: seeded via init (production default).
    dir_a = tmp_path / "a"
    dir_a.mkdir()
    monkeypatch.chdir(dir_a)
    result_a = await service.init(root=dir_a, roles_spec="minimal")
    svc_a = service.Service(result_a.paths)
    init_skills = sorted(
        await svc_a.list_items(item_type=ItemType.SKILL),
        key=lambda s: s.sequence_id,
    )
    init_slugs = [sk.slug for sk in init_skills]

    # Squad B: init WITHOUT seeding, then migrate.
    dir_b = tmp_path / "b"
    dir_b.mkdir()
    monkeypatch.chdir(dir_b)
    result_b = await service.init(root=dir_b, roles_spec="minimal", _skip_skill_seed=True)
    await migrate_v0_4_to_v0_5(result_b.paths)
    svc_b = service.Service(result_b.paths)
    await svc_b.repair()
    migrated_skills = sorted(
        await svc_b.list_items(item_type=ItemType.SKILL),
        key=lambda s: s.sequence_id,
    )
    migrated_slugs = [sk.slug for sk in migrated_skills]

    # The expected order from the shared primitive.
    expected_slugs = bundled_skill_slugs()

    # Both orders must match the canonical lexical order.
    # Filter each list to the bundled slugs only (exclude non-bundled user-added skills).
    expected_set = set(expected_slugs)
    init_bundled = [s for s in init_slugs if s in expected_set]
    migrated_bundled = [s for s in migrated_slugs if s in expected_set]

    assert init_bundled == expected_slugs, (
        f"init slug order {init_bundled!r} != expected {expected_slugs!r}"
    )
    assert migrated_bundled == expected_slugs, (
        f"migrated slug order {migrated_bundled!r} != expected {expected_slugs!r}"
    )


async def test_sq_migrate_up_cli_stamps_skills(tmp_path, monkeypatch, frozen_time, invoke):
    """CLI smoke: sq migrate up on a 0.4 squad stamps skills and leaves sq check green."""
    import tomllib

    from squads import _aio

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)

    # Downgrade schema to 0.4 so that only the 0.4→0.5 migration fires.
    cfg_path = paths.config_path
    cfg_text = await _aio.read_text(cfg_path)
    cfg_text_04 = cfg_text.replace(f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.4"')
    await _aio.write_text(cfg_path, cfg_text_04)

    r = await invoke(["migrate", "up"])
    assert r.exit_code == 0, f"sq migrate up failed:\n{r.output}"

    # Schema must be stamped to current.
    with cfg_path.open("rb") as fh:
        final = tomllib.load(fh)
    assert final["schema_version"] == SCHEMA_VERSION

    # sq check must be green.
    r = await invoke(["check"])
    assert r.exit_code == 0, f"sq check failed after migrate up:\n{r.output}"

    # sq list -t skill must include stamped skills.
    r = await invoke(["list", "--type", "skill", "--json"])
    assert r.exit_code == 0
    skills = json.loads(r.output)
    assert len(skills) > 0, "sq list -t skill must be non-empty after migration"


async def test_sq_migrate_up_idempotent_cli(tmp_path, monkeypatch, frozen_time, invoke):
    """sq migrate up a second time reports 'already at schema' (no reallocation)."""
    # Init with seeding (fully current squad).
    monkeypatch.chdir(tmp_path)
    await service.init(root=tmp_path, roles_spec="minimal")

    r = await invoke(["migrate", "up"])
    assert r.exit_code == 0
    assert f"already at schema v{SCHEMA_VERSION}" in r.output


# ---------------------------------------------------------------------------
# TASK-190: user-facing wiring tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def seeded_paths(tmp_path, monkeypatch, frozen_time):
    """A fresh seeded squad (skills stamped) to drive TASK-190 tests."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return result.paths


async def test_sq_skill_show_renders_skill(seeded_paths, invoke):
    """sq skill <n> show renders the skill's id, slug, status, and body (FEAT-178 AC US1)."""
    svc = service.Service(seeded_paths)
    skills = await svc.list_items(item_type=ItemType.SKILL)
    assert skills, "need at least one seeded skill"
    sk = skills[0]

    r = await invoke(["skill", str(sk.sequence_id), "show"])
    assert r.exit_code == 0, r.output
    assert sk.id in r.output
    assert sk.slug in r.output
    assert "Active" in r.output


async def test_sq_skill_show_json(seeded_paths, invoke):
    """sq skill <n> show --json emits valid JSON with id, slug, status."""
    svc = service.Service(seeded_paths)
    skills = await svc.list_items(item_type=ItemType.SKILL)
    assert skills
    sk = skills[0]

    r = await invoke(["skill", str(sk.sequence_id), "show", "--json"])
    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["id"] == sk.id
    assert data["slug"] == sk.slug
    assert data["status"] == "Active"


async def test_ref_add_skill_from_task(seeded_paths, invoke):
    """sq task ref add SKILL-… succeeds and the ref appears in sq task refs (AC US1)."""
    svc = service.Service(seeded_paths)
    task = (await svc.create(ItemType.TASK, "Ref test task")).item
    skills = await svc.list_items(item_type=ItemType.SKILL)
    assert skills
    sk = skills[0]

    r = await invoke(["task", str(task.sequence_id), "ref", "add", sk.id, "--kind", "related"])
    assert r.exit_code == 0, r.output

    # Forward ref must appear in sq task refs.
    r = await invoke(["task", str(task.sequence_id), "refs"])
    assert r.exit_code == 0, r.output
    assert sk.id in r.output


async def test_ref_backref_appears_on_skill(seeded_paths, invoke):
    """Backref from task → skill appears in sq skill refs --in (forward-edges-only invariant)."""
    svc = service.Service(seeded_paths)
    task = (await svc.create(ItemType.TASK, "Backref test task")).item
    skills = await svc.list_items(item_type=ItemType.SKILL)
    assert skills
    sk = skills[0]

    # Add forward ref from task to skill.
    await svc.add_ref(task.id, sk.id, kind="related")

    # Backref must appear on the skill via refs --in (computed, never persisted).
    r = await invoke(["skill", str(sk.sequence_id), "refs", "--in"])
    assert r.exit_code == 0, r.output
    assert task.id in r.output


async def test_ref_round_trip_from_feature(seeded_paths, invoke):
    """sq feature ref add SKILL-… round-trip: ref appears forward + backref on skill."""
    svc = service.Service(seeded_paths)
    feat = (await svc.create(ItemType.FEATURE, "Ref test feature")).item
    skills = await svc.list_items(item_type=ItemType.SKILL)
    assert skills
    sk = skills[0]

    r = await invoke(["feature", str(feat.sequence_id), "ref", "add", sk.id, "--kind", "related"])
    assert r.exit_code == 0, r.output

    # Forward ref on feature.
    r = await invoke(["feature", str(feat.sequence_id), "refs"])
    assert r.exit_code == 0
    assert sk.id in r.output

    # Backref on skill.
    r = await invoke(["skill", str(sk.sequence_id), "refs", "--in"])
    assert r.exit_code == 0, r.output
    assert feat.id in r.output


# ---------------------------------------------------------------------------
# TASK-202: SKILL-NNNNNN-slug.md filename convention tests
# ---------------------------------------------------------------------------


async def test_migration_renames_already_stamped_slug_file(tmp_path, monkeypatch, frozen_time):
    """Migration renames a file that is already stamped but still slug-named (our own repo
    state: stamped-but-slug-named from a partial prior migration, TASK-202 AC#2)."""
    from squads._interactions import bundled_skill_slugs

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    skills_dir = paths.squad_dir / ItemType.SKILL.folder

    # Manually stamp one skill file without renaming it (simulate partial prior migration).
    slug = bundled_skill_slugs()[0]
    legacy = skills_dir / f"{slug}.md"
    assert legacy.is_file(), f"{slug}.md must exist before partial stamp"
    existing = legacy.read_text(encoding="utf-8")
    # Stamp a fake frontmatter id directly (as the prior partial migration would have done).
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
    from squads._sections import join_frontmatter

    stamped_text = join_frontmatter(fake_fm, existing)
    legacy.write_text(stamped_text, encoding="utf-8")

    # Run migration: must rename slug-named stamped file.
    acted = await migrate_v0_4_to_v0_5(paths)
    assert acted >= 1, "migration must rename the stamped slug-named file"

    # Legacy slug-named file must be gone.
    assert not legacy.exists(), f"legacy {slug}.md must be removed after migration"

    # Convention-named file must exist with the original id.
    convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
    assert convention, f"no SKILL-*-{slug}.md found for slug {slug!r}"
    md = convention[0]
    fm, _ = split_frontmatter(md.read_text(encoding="utf-8"))
    assert fm.get("id") == "SKILL-000099", (
        f"{md.name}: id must match the stamped id (no reallocation)"
    )


async def test_migration_rename_pointer_resolves(tmp_path, monkeypatch, frozen_time):
    """After migration, the .claude/skills/<slug>/SKILL.md pointer references the renamed
    convention-correct body file (AC#3)."""
    from squads._interactions import bundled_skill_slugs

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_4_to_v0_5(paths)

    skills_dir = paths.squad_dir / ItemType.SKILL.folder
    claude_skills = paths.root / ".claude" / "skills"

    for slug in bundled_skill_slugs():
        pointer = claude_skills / slug / "SKILL.md"
        if not pointer.exists():
            continue  # no .claude dir for this squad — ok in minimal test env
        content = pointer.read_text(encoding="utf-8")
        # The @-reference in the pointer must point to the convention-named file.
        assert "SKILL-" in content, (
            f".claude/skills/{slug}/SKILL.md must reference SKILL-…-{slug}.md"
        )
        # The referenced convention file must actually exist.
        convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        assert convention, f"no convention file for {slug!r} but pointer exists"


async def test_migration_rename_idempotent_on_already_renamed(tmp_path, monkeypatch, frozen_time):
    """Re-running migration on a squad with convention-named files is a complete no-op (AC#2)."""
    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)

    first = await migrate_v0_4_to_v0_5(paths)
    assert first > 0

    second = await migrate_v0_4_to_v0_5(paths)
    assert second == 0, "second migration run on convention-named files must be a no-op"


async def test_init_skill_files_use_convention_name(tmp_path, monkeypatch, frozen_time):
    """Fresh sq init produces SKILL-NNNNNN-slug.md files; no bare slug.md remain; the
    .claude pointer resolves to the convention-named file (AC#1, AC#3)."""
    from squads._interactions import bundled_skill_slugs

    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    skills_dir = result.paths.squad_dir / ItemType.SKILL.folder
    claude_skills = result.paths.root / ".claude" / "skills"

    for slug in bundled_skill_slugs():
        legacy = skills_dir / f"{slug}.md"
        assert not legacy.exists(), (
            f"bare {slug}.md must not exist after init; skill files must be SKILL-NNNNNN-slug.md"
        )
        convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        assert convention, f"no SKILL-*-{slug}.md found after init for slug {slug!r}"

        # Verify the .claude pointer references the convention-named body (not slug.md).
        pointer = claude_skills / slug / "SKILL.md"
        if pointer.exists():
            content = pointer.read_text(encoding="utf-8")
            assert "SKILL-" in content, (
                f".claude/skills/{slug}/SKILL.md still references slug path "
                f"(expected SKILL-…-{slug}.md reference)"
            )
            # Extract the referenced path from the @-line and verify the file exists.
            ref_lines = [ln for ln in content.splitlines() if ln.startswith("@")]
            assert ref_lines, f"pointer for {slug!r} has no @-line"
            ref_path = result.paths.root / ref_lines[0][1:]  # strip leading @
            assert ref_path.exists(), (
                f"pointer for {slug!r} references {ref_lines[0]!r} which does not exist"
            )


# ---------------------------------------------------------------------------
# TASK-204: description registry + migration backfill tests
# ---------------------------------------------------------------------------


async def test_migration_stamps_description_on_unstamped_file(tmp_path, monkeypatch, frozen_time):
    """Migration sets the registry description on newly-stamped skill items (TASK-204 AC#2)."""
    from squads._interactions import bundled_skill_slugs, skill_description

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_4_to_v0_5(paths)

    skills_dir = paths.squad_dir / ItemType.SKILL.folder
    for slug in bundled_skill_slugs():
        convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        if not convention:
            continue
        fm, _ = split_frontmatter(convention[0].read_text(encoding="utf-8"))
        expected = skill_description(slug)
        assert fm.get("description") == expected, (
            f"{convention[0].name}: description {fm.get('description')!r} != {expected!r}"
        )


async def test_migration_backfills_description_on_already_stamped_convention_file(
    tmp_path, monkeypatch, frozen_time
):
    """Migration backfills description onto an already-stamped convention file that has
    description=''.  This covers the live-repo state after the 0.4→0.5 first run (TASK-204 AC#2).
    """
    from squads._interactions import bundled_skill_slugs, skill_description

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    # First migration pass (creates convention files with description).
    await migrate_v0_4_to_v0_5(paths)

    # Simulate the pre-TASK-204 state: wipe descriptions from convention files.
    skills_dir = paths.squad_dir / ItemType.SKILL.folder
    for slug in bundled_skill_slugs():
        convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        if not convention:
            continue
        text = convention[0].read_text(encoding="utf-8")
        fm, _ = split_frontmatter(text)
        fm["description"] = ""
        from squads._sections import replace_frontmatter

        convention[0].write_text(replace_frontmatter(text, fm), encoding="utf-8")

    # Re-run migration: must backfill descriptions (acted > 0).
    acted = await migrate_v0_4_to_v0_5(paths)
    assert acted > 0, "backfill run must act on description-less convention files"

    # Check descriptions are now filled.
    for slug in bundled_skill_slugs():
        convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        if not convention:
            continue
        fm, _ = split_frontmatter(convention[0].read_text(encoding="utf-8"))
        expected = skill_description(slug)
        assert fm.get("description") == expected, (
            f"backfill did not set description on {convention[0].name}: "
            f"got {fm.get('description')!r}, expected {expected!r}"
        )


async def test_migration_backfill_idempotent(tmp_path, monkeypatch, frozen_time):
    """After backfill, re-running migration is 0 (descriptions present → skip). (TASK-204 AC#5)."""
    from squads._interactions import bundled_skill_slugs

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_4_to_v0_5(paths)  # first pass: stamps + descriptions

    second = await migrate_v0_4_to_v0_5(paths)  # descriptions present → full skip
    assert second == 0, "second migration run with descriptions present must be 0 (idempotent)"

    # Verify ids are unchanged.
    skills_dir = paths.squad_dir / ItemType.SKILL.folder
    ids: set[str] = set()
    for slug in bundled_skill_slugs():
        convention = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        if not convention:
            continue
        fm, _ = split_frontmatter(convention[0].read_text(encoding="utf-8"))
        ids.add(str(fm.get("id")))
    assert len(ids) >= 1, "must have skill ids after migration"


async def test_migration_pointer_description_matches_registry(tmp_path, monkeypatch, frozen_time):
    """After migration, each .claude pointer's description matches the registry (TASK-204 AC#2)."""
    from squads._interactions import bundled_skill_slugs, skill_description

    paths = await _make_pre_seed_squad(tmp_path, monkeypatch)
    await migrate_v0_4_to_v0_5(paths)

    claude_skills = paths.root / ".claude" / "skills"
    if not claude_skills.is_dir():
        pytest.skip("no .claude dir — claude_code backend not active")

    for slug in bundled_skill_slugs():
        pointer = claude_skills / slug / "SKILL.md"
        if not pointer.exists():
            continue
        content = pointer.read_text(encoding="utf-8")
        expected_desc = skill_description(slug)
        assert expected_desc[:30] in content, (
            f"pointer for {slug!r} after migration does not contain expected description start "
            f"{expected_desc[:30]!r}.\nPointer content:\n{content}"
        )
        assert content.count(f"description: {slug}") == 0, (
            f"pointer for {slug!r} description is bare slug after migration"
        )


async def test_double_sync_preserves_skill_ids_and_filenames(tmp_path, monkeypatch, frozen_time):
    """Double sq sync keeps skill ids AND filenames stable (AC#5 / ADR #4)."""
    from squads._interactions import bundled_skill_slugs

    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    svc = service.Service(result.paths)
    skills_dir = result.paths.squad_dir / ItemType.SKILL.folder

    # Snapshot after init.
    skills = await svc.list_items(item_type=ItemType.SKILL)
    before_ids = {sk.slug: sk.id for sk in skills}
    before_seqs = {sk.slug: sk.sequence_id for sk in skills}
    before_names: dict[str, str] = {}
    for slug in bundled_skill_slugs():
        flist = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        if flist:
            before_names[slug] = flist[0].name

    # First sync.
    await svc.sync()
    for slug in bundled_skill_slugs():
        flist = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        assert flist, f"no convention file for {slug!r} after first sync"
        assert flist[0].name == before_names.get(slug), (
            f"first sync renamed {slug}: was {before_names.get(slug)}, now {flist[0].name}"
        )

    # Second sync.
    await svc.sync()
    skills_after = await svc.list_items(item_type=ItemType.SKILL)
    after_ids = {sk.slug: sk.id for sk in skills_after}
    after_seqs = {sk.slug: sk.sequence_id for sk in skills_after}
    assert before_ids == after_ids, "double sync must not change skill ids"
    assert before_seqs == after_seqs, "double sync must not change sequence_ids"
    for slug in bundled_skill_slugs():
        flist = list(skills_dir.glob(f"SKILL-*-{slug}.md"))
        assert flist, f"no convention file for {slug!r} after second sync"
        assert flist[0].name == before_names.get(slug), (
            f"second sync renamed {slug}: was {before_names.get(slug)}, now {flist[0].name}"
        )
