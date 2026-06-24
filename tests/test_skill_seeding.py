"""Tests for FEAT-000178 / TASK-187 + TASK-188:
skill-body regen becomes frontmatter-preserving (TASK-187) and
sq init seeds bundled skills as first-class SKILL items (TASK-188).
"""

import pytest

from squads import _interactions as interactions
from squads._models._enums import ItemType, Status
from squads._sections import split_frontmatter
from squads._services import _service as service

pytestmark = pytest.mark.anyio

# --------------------------------------------------------------------------- fixtures


@pytest.fixture
async def project_with_skills(tmp_path, monkeypatch, frozen_time):
    """A freshly-initialized squad WITH skill seeding enabled.

    Uses the default _skip_skill_seed=False so bundled skills are stamped
    with SKILL ids.  Tests for TASK-187 idempotence and TASK-188 allocation
    use this fixture.
    """
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return result.paths


@pytest.fixture
def svc_with_skills(project_with_skills):
    return service.Service(project_with_skills)


# --------------------------------------------------------------------------- TASK-188: seeding


async def test_init_seeds_bundled_skills_as_skill_items(project_with_skills):
    """After sq init (with seeding), sq list -t skill is non-empty (FEAT-178 AC#1 / TASK-188)."""
    svc = service.Service(project_with_skills)
    skills = await svc.list_items(item_type=ItemType.SKILL)
    assert len(skills) > 0, "sq list -t skill must be non-empty after init with seeding"
    # All skills must have type=skill and status=Active
    for sk in skills:
        assert sk.type is ItemType.SKILL
        assert sk.status is Status.ACTIVE
    # Must include the core bundled skill slugs
    slugs = {sk.slug for sk in skills}
    assert "squads" in slugs
    assert "greeting" in slugs


async def test_skill_files_have_valid_frontmatter_after_seeding(project_with_skills):
    """Every skill file must have valid sq frontmatter with a unique SKILL-… id (AC#2)."""
    svc = service.Service(project_with_skills)
    skills = await svc.list_items(item_type=ItemType.SKILL)
    seen_ids: set[str] = set()
    for sk in skills:
        path = svc.paths.abspath(sk.path)
        assert path.is_file(), f"skill file {sk.path!r} does not exist"
        text = path.read_text(encoding="utf-8")
        fm, _ = split_frontmatter(text)
        assert fm.get("id"), f"{path.name}: missing id in frontmatter"
        assert fm.get("sequence_id"), f"{path.name}: missing sequence_id"
        assert fm.get("type") == "skill", f"{path.name}: type must be 'skill'"
        assert fm["id"].startswith("SKILL-"), f"{path.name}: id must start with SKILL-"
        assert fm["id"] not in seen_ids, f"duplicate id {fm['id']}"
        seen_ids.add(fm["id"])


async def test_repair_after_seeding_rebuilds_cleanly(project_with_skills):
    """sq repair after seeding reconstructs the index from skill file frontmatter (AC#2)."""
    svc = service.Service(project_with_skills)
    # Get current skill count
    before = await svc.list_items(item_type=ItemType.SKILL)
    # Nuke the index and rebuild
    svc.paths.index_path.unlink()
    result = await svc.repair()
    after = {it.id for it in result.db.items.values() if it.type is ItemType.SKILL}
    assert len(after) == len(before), "repair must recover all skill items"
    before_ids = {sk.id for sk in before}
    assert before_ids == after, "repair must recover the exact same skill ids"


async def test_skill_allocation_order_is_lexical_by_slug(project_with_skills):
    """Skills are allocated in lexical-by-slug order (ADR-000181 decision #5 / AC#5)."""
    svc = service.Service(project_with_skills)
    skills = await svc.list_items(item_type=ItemType.SKILL)
    # Sort by sequence_id to get allocation order
    ordered = sorted(skills, key=lambda sk: sk.sequence_id)
    slugs_in_order = [sk.slug for sk in ordered]
    expected_slugs = interactions.bundled_skill_slugs()
    assert slugs_in_order == expected_slugs, (
        f"skill allocation order must be lexical-by-slug.\n"
        f"expected: {expected_slugs}\n"
        f"got:      {slugs_in_order}"
    )


async def test_check_clean_after_seeding(project_with_skills):
    """sq check must be clean after seeding (no errors for skill items, AC#3)."""
    svc = service.Service(project_with_skills)
    issues = await svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors, f"sq check errors after seeding: {errors}"


# -------------------------------------------------------- TASK-187: frontmatter-preserving regen


async def test_sync_preserves_skill_frontmatter(svc_with_skills):
    """sq sync must not clobber skill frontmatter (ADR-000181 decision #3)."""
    skills = await svc_with_skills.list_items(item_type=ItemType.SKILL)
    squads_skill = next((sk for sk in skills if sk.slug == "squads"), None)
    assert squads_skill is not None, "squads skill must be in the index"

    path = svc_with_skills.paths.abspath(squads_skill.path)
    before_text = path.read_text(encoding="utf-8")
    before_fm, _ = split_frontmatter(before_text)

    # Run sync — should only replace the body region, not the frontmatter
    await svc_with_skills.sync()

    after_text = path.read_text(encoding="utf-8")
    after_fm, _ = split_frontmatter(after_text)

    assert after_fm.get("id") == before_fm.get("id"), "sync must not change skill id"
    assert after_fm.get("sequence_id") == before_fm.get("sequence_id"), (
        "sync must not change skill sequence_id"
    )
    assert after_fm.get("type") == "skill", "sync must not change skill type"


async def test_sync_twice_leaves_skill_ids_unchanged(svc_with_skills):
    """Running sq sync twice on a stamped squad must not change any skill's id or sequence_id.

    This is the mandatory idempotence test from FEAT-000178 AC#4 and TASK-187.
    """
    skills = await svc_with_skills.list_items(item_type=ItemType.SKILL)
    assert len(skills) > 0, "need at least one seeded skill for idempotence test"

    # Snapshot ids/sequence_ids before any sync (keyed by slug for clarity)
    original_ids: dict[str, str] = {sk.slug: sk.id for sk in skills}
    original_seqs: dict[str, int] = {sk.slug: sk.sequence_id for sk in skills}

    # First sync
    await svc_with_skills.sync()

    # Re-read from disk to verify frontmatter was preserved after first sync
    for sk in skills:
        path = svc_with_skills.paths.abspath(sk.path)
        fm, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        assert fm.get("id") == original_ids[sk.slug], (
            f"first sync changed id for {sk.slug}: was {original_ids[sk.slug]}, now {fm.get('id')}"
        )
        assert fm.get("sequence_id") == original_seqs[sk.slug], (
            f"first sync changed sequence_id for {sk.slug}"
        )

    # Second sync
    await svc_with_skills.sync()

    # Verify again after the second sync
    for sk in skills:
        path = svc_with_skills.paths.abspath(sk.path)
        fm, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        assert fm.get("id") == original_ids[sk.slug], (
            f"second sync changed id for {sk.slug}: was {original_ids[sk.slug]}, now {fm.get('id')}"
        )
        assert fm.get("sequence_id") == original_seqs[sk.slug], (
            f"second sync changed sequence_id for {sk.slug} after second sync"
        )


async def test_skill_body_region_updated_on_sync(svc_with_skills):
    """sync must update the sq:body region of a skill file (the content refreshes)."""
    from squads import _sections as sections
    from squads._models import _markers as markers

    skills = await svc_with_skills.list_items(item_type=ItemType.SKILL)
    squads_skill = next((sk for sk in skills if sk.slug == "squads"), None)
    assert squads_skill is not None

    path = svc_with_skills.paths.abspath(squads_skill.path)
    original = path.read_text(encoding="utf-8")

    # Corrupt the body region only
    corrupted = sections.replace_section(original, markers.BODY, "\n_corrupted_\n")
    path.write_text(corrupted, encoding="utf-8")
    assert "_corrupted_" in path.read_text(encoding="utf-8")

    # Sync should restore the body
    await svc_with_skills.sync()
    restored = path.read_text(encoding="utf-8")

    # Body content should be restored (not corrupted anymore)
    assert "_corrupted_" not in restored
    # But frontmatter must still be intact
    fm, _ = split_frontmatter(restored)
    assert fm.get("id") == squads_skill.id
    assert fm.get("sequence_id") == squads_skill.sequence_id


async def test_seed_bundled_skills_is_idempotent(svc_with_skills):
    """Calling seed_bundled_skills() twice must not allocate new ids (ADR-000181 decision #4)."""
    skills_before = await svc_with_skills.list_items(item_type=ItemType.SKILL)
    ids_before = {sk.id for sk in skills_before}
    seqs_before = {sk.sequence_id for sk in skills_before}

    # Call seeding again
    newly_seeded = await svc_with_skills.seed_bundled_skills()
    assert len(newly_seeded) == 0, "second seed call must return empty list (all already stamped)"

    skills_after = await svc_with_skills.list_items(item_type=ItemType.SKILL)
    ids_after = {sk.id for sk in skills_after}
    seqs_after = {sk.sequence_id for sk in skills_after}

    assert ids_before == ids_after, "seed must not allocate new ids on re-run"
    assert seqs_before == seqs_after, "seed must not change sequence_ids on re-run"


# --------------------------------------------------------------------------- CLI smoke tests


async def test_cli_init_seeds_skills_list_non_empty(invoke, tmp_path, monkeypatch, frozen_time):
    """CLI smoke: sq init (without --no-seed-skills) → sq list -t skill is non-empty."""
    monkeypatch.chdir(tmp_path)
    r = await invoke(["init", "--roles", "minimal"])
    assert r.exit_code == 0, r.output

    r = await invoke(["list", "--type", "skill"])
    assert r.exit_code == 0, r.output
    assert "SKILL-" in r.output, "sq list -t skill must show seeded skills after init"


async def test_cli_sq_list_t_skill_shows_bundled_skills(invoke, tmp_path, monkeypatch, frozen_time):
    """CLI smoke: after sq init, sq list -t skill shows all bundled skill slugs."""
    monkeypatch.chdir(tmp_path)
    r = await invoke(["init", "--roles", "minimal"])
    assert r.exit_code == 0, r.output

    r = await invoke(["list", "--type", "skill"])
    assert r.exit_code == 0, r.output
    for slug in interactions.bundled_skill_slugs():
        assert slug in r.output, f"bundled skill {slug!r} must appear in sq list -t skill"


# --------------------------------------------------------------------------- TASK-204: descriptions


async def test_init_seeds_skill_descriptions(project_with_skills):
    """After sq init, every seeded SKILL item carries the registry description (TASK-204 AC#1)."""
    from squads._interactions import skill_description

    svc = service.Service(project_with_skills)
    skills = await svc.list_items(item_type=ItemType.SKILL)
    assert skills, "need at least one seeded skill"
    for sk in skills:
        expected = skill_description(sk.slug)
        assert sk.description == expected, (
            f"skill {sk.slug!r}: expected {expected!r}, got {sk.description!r}"
        )


async def test_init_skill_pointer_description_matches_registry(project_with_skills):
    """After sq init, each .claude pointer's description line matches the registry text (AC#1)."""
    from squads._interactions import bundled_skill_slugs, skill_description

    claude_skills = project_with_skills.root / ".claude" / "skills"
    if not claude_skills.is_dir():
        pytest.skip("no .claude dir — claude_code backend not active")

    for slug in bundled_skill_slugs():
        pointer = claude_skills / slug / "SKILL.md"
        if not pointer.exists():
            continue
        content = pointer.read_text(encoding="utf-8")
        expected_desc = skill_description(slug)
        # The description should appear somewhere in the pointer (it's on the description line).
        assert expected_desc[:30] in content, (
            f"pointer for {slug!r} does not contain expected description start "
            f"{expected_desc[:30]!r}.\nPointer content:\n{content}"
        )
        # Must NOT be just the bare slug.
        assert content.count(f"description: {slug}") == 0, (
            f"pointer for {slug!r} description is the bare slug — registry not applied"
        )


async def test_cli_list_t_skill_shows_non_empty_descriptions(
    invoke, tmp_path, monkeypatch, frozen_time
):
    """CLI smoke: sq list -t skill shows non-empty descriptions after init (TASK-204 AC#1)."""
    import json

    monkeypatch.chdir(tmp_path)
    r = await invoke(["init", "--roles", "minimal"])
    assert r.exit_code == 0, r.output

    r = await invoke(["list", "--type", "skill", "--json"])
    assert r.exit_code == 0, r.output
    items = json.loads(r.output)
    assert items, "sq list -t skill must return items after init"
    for item in items:
        assert item["description"], (
            f"skill {item['slug']!r} has empty description in sq list output"
        )
        # Must not be the bare slug.
        assert item["description"] != item["slug"], (
            f"skill {item['slug']!r} description is the bare slug — registry not applied"
        )


async def test_cli_skill_show(invoke, tmp_path, monkeypatch, frozen_time):
    """CLI smoke: sq skill <n> show works on a seeded skill."""
    monkeypatch.chdir(tmp_path)
    r = await invoke(["init", "--roles", "minimal"])
    assert r.exit_code == 0, r.output

    # Get the first skill's sequence number
    r = await invoke(["list", "--type", "skill", "--json"])
    assert r.exit_code == 0, r.output
    import json

    items = json.loads(r.output)
    assert len(items) > 0
    first_seq = items[0]["sequence_id"]

    r = await invoke(["skill", str(first_seq), "show"])
    assert r.exit_code == 0, r.output
    assert "SKILL-" in r.output
