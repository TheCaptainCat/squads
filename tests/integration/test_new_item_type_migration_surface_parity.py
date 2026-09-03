"""The two new item types' generated surface — a fresh `sq init` versus a squad migrated up
from one that predates them — must come out identical: skill body prose, pointer content, and
the fact that the type's own folder exists.

This is the comparison the corpus migration test (which only asserts `sq check` is clean) does
not perform: a squad can pass `sq check` while its migrate path produced a *different* surface
than `sq init` would have — the exact defect shape this suite exists to catch (a type addition
wired into `init` but left unregenerated on `migrate`).

Squad B starts from a real `sq init` too (so both squads share one roster), then has the two new
types' surface stripped back to what a squad that predates them looks like, then migrated —
rather than a frozen pre-0.14 corpus fixture, whose own roster (a single custom-named role) would
not hold the roster constant against a fresh init's bundled roles.

The strip covers the type folders, the two skill bodies/pointers/index entries, **and** every
existing role's own `.claude/agents/<slug>.md` preload list — the surface `_strip_new_type_surface`
used to leave alone, which let a squad B built from a `minimal` (manager-only) roster enter the
migration already looking converged: no role in that roster preloads either new type's skill, so
there was nothing for the omission to hide. A roster wide enough to hold a role that *does*
(`architect`, `product-owner`, `tech-lead`, and any `<tech>-dev`) is what actually exercises the
seam.
"""

import shutil

import pytest

from squads._migrations._v0_11_to_v0_14 import migrate as migrate_v0_11_to_v0_14
from squads._models._extras import ExtraKey as X
from squads._paths import SquadPaths
from squads._sections import split_frontmatter
from squads._services import _service as service
from squads._workflow import ROSTER_SKILL

pytestmark = pytest.mark.anyio

_NEW_TYPES = ("contract", "milestone")
_NEW_SKILL_SLUGS = ("sq-contract", "sq-milestone")


async def _strip_new_type_surface(svc: service.Service, paths: SquadPaths) -> None:
    """Remove everything provisioning the two new types would have created, so *paths* reads
    like a squad that predates them. The programmatic counterpart to a frozen pre-0.14 corpus
    fixture — built this way so its roster can be held identical to the comparison squad's."""
    for item_type in _NEW_TYPES:
        folder = paths.squad_dir / svc.spec.items[item_type].folder
        if folder.is_dir():
            shutil.rmtree(folder)

    skills_folder = paths.squad_dir / svc.spec.items[ROSTER_SKILL].folder
    for slug in _NEW_SKILL_SLUGS:
        for md in skills_folder.glob(f"*-{slug}.md"):
            md.unlink()
        pointer_dir = paths.root / ".claude" / "skills" / slug
        if pointer_dir.is_dir():
            shutil.rmtree(pointer_dir)

    async with svc.store.transaction() as db:
        stale = [seq for seq, it in db.items.items() if it.extra.get(X.SLUG) in _NEW_SKILL_SLUGS]
        for seq in stale:
            del db.items[seq]

    _strip_agent_pointer_preload_lines(paths)


def _strip_agent_pointer_preload_lines(paths: SquadPaths) -> None:
    """Drop the two new types' skill lines from every existing role's own generated
    `.claude/agents/<slug>.md` pointer — the half of a pre-0.14 squad's surface the folder/skill
    removal above never touched, so a role that interacts with either new type entered the
    migration already carrying the post-0.14 preload list it could only get from a regeneration.
    A no-op line-removal on any pointer that never had one (e.g. a role with no interaction with
    either type), so this is safe to run unconditionally over the whole roster."""
    agents_dir = paths.root / ".claude" / "agents"
    if not agents_dir.is_dir():
        return
    doomed_lines = {f"- {slug}" for slug in _NEW_SKILL_SLUGS}
    for pointer in agents_dir.glob("*.md"):
        text = pointer.read_text(encoding="utf-8")
        lines = text.splitlines()
        kept = [line for line in lines if line.strip() not in doomed_lines]
        if kept != lines:
            pointer.write_text("\n".join(kept) + "\n", encoding="utf-8")


def _skill_body(paths: SquadPaths, slug: str) -> str:
    skills_folder = paths.squad_dir / "agents" / "skills"
    (md_path,) = skills_folder.glob(f"*-{slug}.md")
    _, body = split_frontmatter(md_path.read_text(encoding="utf-8"))
    return body


def _pointer_text(paths: SquadPaths, slug: str) -> str:
    return (paths.root / ".claude" / "skills" / slug / "SKILL.md").read_text(encoding="utf-8")


async def test_new_type_folders_and_skill_surface_match_init(
    tmp_path, monkeypatch, frozen_time
) -> None:
    dir_a = tmp_path / "a"
    dir_a.mkdir()
    monkeypatch.chdir(dir_a)
    result_a = await service.init(root=dir_a, roles_spec="minimal")
    paths_a = result_a.paths

    dir_b = tmp_path / "b"
    dir_b.mkdir()
    monkeypatch.chdir(dir_b)
    result_b = await service.init(root=dir_b, roles_spec="minimal")
    paths_b = result_b.paths
    svc_b = service.Service(paths_b)
    await _strip_new_type_surface(svc_b, paths_b)
    # Preconditions: the strip actually removed what it means to.
    for item_type in _NEW_TYPES:
        assert not (paths_b.squad_dir / svc_b.spec.items[item_type].folder).is_dir()
    for slug in _NEW_SKILL_SLUGS:
        assert not list((paths_b.squad_dir / "agents" / "skills").glob(f"*-{slug}.md"))

    changed = await migrate_v0_11_to_v0_14(paths_b)
    assert changed > 0

    for item_type in _NEW_TYPES:
        assert (paths_a.squad_dir / svc_b.spec.items[item_type].folder).is_dir()
        assert (paths_b.squad_dir / svc_b.spec.items[item_type].folder).is_dir()

    for slug in _NEW_SKILL_SLUGS:
        assert _skill_body(paths_a, slug) == _skill_body(paths_b, slug)
        assert _pointer_text(paths_a, slug) == _pointer_text(paths_b, slug)


async def test_migrate_seeds_a_skill_item_for_each_new_type(
    tmp_path, monkeypatch, frozen_time
) -> None:
    dir_b = tmp_path / "b"
    dir_b.mkdir()
    monkeypatch.chdir(dir_b)
    result_b = await service.init(root=dir_b, roles_spec="minimal")
    paths_b = result_b.paths
    svc_b = service.Service(paths_b)
    await _strip_new_type_surface(svc_b, paths_b)

    await migrate_v0_11_to_v0_14(paths_b)

    skills = await svc_b.list_items(item_type=ROSTER_SKILL)
    slugs = {sk.extra.get(X.SLUG) for sk in skills}
    assert set(_NEW_SKILL_SLUGS) <= slugs


def _agent_pointer_text(paths: SquadPaths, slug: str) -> str:
    return (paths.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")


async def test_role_pointer_drift_is_either_absent_or_named_in_the_manual_runbook(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """A roster wide enough to hold every role whose preload list grows one of the two new
    types' skills — `architect`, `product-owner`, `tech-lead` (via the bundled playbook) and a
    `<tech>-dev` role (via the `*dev` sentinel) — held identical between squad A and squad B from
    before either diverges, so adding the dev role does not itself become a source of
    incomparability.

    Encodes the actual contract: a migrated squad's affected role pointers may legitimately
    still differ from a fresh init's (this runner does not regenerate per-entry role pointers —
    that stays `sq sync`'s job), but only if the runbook the operator just read names `sq sync`
    as the remedy — never silently, and never while still claiming no action is required. And
    the remedy has to actually work: running it must converge the two.
    """
    dir_a = tmp_path / "a"
    dir_a.mkdir()
    monkeypatch.chdir(dir_a)
    result_a = await service.init(root=dir_a, roles_spec="all")
    paths_a = result_a.paths
    svc_a = service.Service(paths_a)
    await svc_a.add_dev("python")

    dir_b = tmp_path / "b"
    dir_b.mkdir()
    monkeypatch.chdir(dir_b)
    result_b = await service.init(root=dir_b, roles_spec="all")
    paths_b = result_b.paths
    svc_b = service.Service(paths_b)
    await svc_b.add_dev("python")
    await _strip_new_type_surface(svc_b, paths_b)

    affected_roles = ("architect", "product-owner", "tech-lead", "python-dev")
    # Precondition: the strip actually put squad B's pointers back to a pre-0.14 shape — every
    # affected role's pointer differs from squad A's before migrate touches anything.
    assert all(
        _agent_pointer_text(paths_a, slug) != _agent_pointer_text(paths_b, slug)
        for slug in affected_roles
    )

    changed = await migrate_v0_11_to_v0_14(paths_b)
    assert changed > 0

    drifted = [
        slug
        for slug in affected_roles
        if _agent_pointer_text(paths_a, slug) != _agent_pointer_text(paths_b, slug)
    ]
    # With the roster held wide enough, the drift this runner leaves behind is real, not hidden
    # by a `minimal` roster with nothing to drift.
    assert drifted == list(affected_roles)

    from squads._migrations import _v0_11_to_v0_14

    manual_lower = _v0_11_to_v0_14.MANUAL.lower()
    assert "sq sync" in manual_lower
    assert "no action is required" not in manual_lower

    await svc_b.sync()
    for slug in drifted:
        assert _agent_pointer_text(paths_a, slug) == _agent_pointer_text(paths_b, slug)


async def test_migrate_is_idempotent_on_an_already_current_squad(
    tmp_path, monkeypatch, frozen_time
) -> None:
    dir_c = tmp_path / "c"
    dir_c.mkdir()
    monkeypatch.chdir(dir_c)
    result_c = await service.init(root=dir_c, roles_spec="minimal")
    paths_c = result_c.paths

    first = await migrate_v0_11_to_v0_14(paths_c)
    second = await migrate_v0_11_to_v0_14(paths_c)
    assert first == 0  # a fresh init already carries both types' surface
    assert second == 0
