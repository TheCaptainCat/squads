"""A system (template-owned) skill's definition is not storage: no code path writes AUTHORED
content into the skill item's ``sq:body`` region, so a second ``sq sync`` is a byte-for-byte
no-op on every skill file. Every system skill — one of the three permanently-system skills
(squads/greeting/sq-memory) or a per-item-type ``sq-<type>`` skill alike — carries its own
``sq:view:<name>`` placement tag instead, seeded at creation the same way a role's is, and
renders fresh at read time off that tag.

The backend still owes the file's *shape* — the seeding step stamps a ``SKILL`` id onto the
file it creates, so a managed skill with no file would never become an indexed item at all —
but it owes nothing authored inside the region, and it never reports a body artifact for one.

Read through the marker helpers rather than by substring, so a region that is absent is
distinguishable from one that is present and tagged; a tag names a view and nothing else.
"""

import ast
import inspect
from pathlib import Path

import pytest

from squads import _sections as sections
from squads._backends._base import BackendContext
from squads._backends._registry import get_backend
from squads._interactions import ITEM_SKILL_VIEW_NAME, SYSTEM_SKILL_VIEW_NAMES, is_system_skill
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._services import _service as service

pytestmark = pytest.mark.anyio


@pytest.fixture
async def seeded(tmp_path, monkeypatch, frozen_time):
    """A real ``sq init`` with skills seeded, plus a developer role so the roster-dependent
    ``has_dev`` gate is exercised on the definitions that carry a ``*dev`` guide."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="all")
    svc = service.Service(result.paths)
    await svc.add_dev("python")
    await svc.sync()
    return svc


def _skill_files(paths) -> dict[str, str]:
    folder = paths.squad_dir / "agents" / "skills"
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(folder.glob("*.md"))}


async def test_every_system_skill_file_carries_its_own_placement_tag_and_nothing_else(seeded):
    skills = await seeded.list_items(item_type="skill")
    assert skills, "the fixture must have seeded skill items to say anything"

    for item in skills:
        slug = item.extra.get(X.SLUG, item.slug)
        assert is_system_skill(slug, seeded.spec), f"{slug} unexpectedly custom in this fixture"
        text = (seeded.paths.abspath(item.path)).read_text(encoding="utf-8")
        assert sections.has_section(text, markers.BODY), f"{slug}: body region missing entirely"
        region = (sections.get_section(text, markers.BODY) or "").strip("\n")
        # One of the three permanently-system slugs names its own view; every other
        # template-owned skill is a per-item-type one and shares the single ITEM_SKILL_VIEW_NAME.
        view_name = SYSTEM_SKILL_VIEW_NAMES.get(slug, ITEM_SKILL_VIEW_NAME)
        assert region == markers.open_marker(markers.view_tag(view_name)), (
            f"{slug}: body region carries something other than its own placement tag"
        )


async def test_a_system_skills_definition_reads_through_the_shared_body_boundary(seeded):
    """Every system skill — permanently-system or per-item-type alike — reads its definition
    through the tag its own ``sq:body`` carries, via the same shared body-read boundary any
    other item's body goes through (``read_body``); there is no second render path any more."""
    for slug in ("squads", "greeting", "sq-memory", "sq-task", "sq-milestone"):
        item = await seeded.roster_item("skill", slug)
        assert item is not None, slug
        rendered = await seeded.read_body(item.id)
        assert rendered.startswith("#"), f"{slug}: no rendered definition"
        assert rendered == rendered.strip("\n"), f"{slug}: definition is not newline-trimmed"


async def test_a_second_sync_produces_no_diff_on_any_skill_file_or_pointer(seeded):
    before_files = _skill_files(seeded.paths)
    pointer_dir = seeded.paths.root / ".claude" / "skills"
    before_pointers = {
        p.name: (p / "SKILL.md").read_text(encoding="utf-8")
        for p in sorted(pointer_dir.iterdir())
        if p.is_dir()
    }
    assert before_files and before_pointers

    await seeded.sync()

    assert _skill_files(seeded.paths) == before_files
    assert {
        p.name: (p / "SKILL.md").read_text(encoding="utf-8")
        for p in sorted(pointer_dir.iterdir())
        if p.is_dir()
    } == before_pointers


async def test_write_managed_reports_a_pointer_for_each_skill_and_no_body_artifact(seeded):
    """The artifact half: the pointer is still declared to the caller, the body is not — there is
    no longer any body write to report."""
    backend = get_backend("claude_code")
    ctx = BackendContext(
        paths=seeded.paths,
        skill_paths={
            it.extra[X.SLUG]: seeded.paths.abspath(it.path)
            for it in await seeded.list_items(item_type="skill")
        },
        spec=seeded.spec,
        playbook=seeded.playbook,
    )
    artifacts = await backend.write_managed(ctx, await seeded.roster(), await seeded.operators())

    kinds = {a.kind for a in artifacts}
    assert "skill_pointer" in kinds
    assert "skill_body" not in kinds
    pointer_paths = {a.path for a in artifacts if a.kind == "skill_pointer"}
    assert len(pointer_paths) == len(await seeded.list_items(item_type="skill"))


def test_the_show_command_module_reaches_no_backend_for_a_definition() -> None:
    """Invariant 6, satisfied by direction: the service produces the definition and the reader
    goes through it. A CLI module importing a backend to obtain content is exactly the failure
    that constraint exists to prevent, so the import itself is what is checked."""
    from squads._cli import _skill

    tree = ast.parse(inspect.getsource(_skill))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not [m for m in imported if m.startswith("squads._backends")], sorted(imported)


@pytest.mark.anyio
async def test_the_resolved_definition_matches_the_pinned_render_for_every_bundled_type(
    tmp_path, monkeypatch, frozen_time
) -> None:
    """The byte-identity bar for the move: what a read resolves is what was written into the
    region before, for every bundled type that ships a pinned reference render.

    The roster is pinned to the one those references were captured against (every bundled role
    plus one developer): the generated text is roster-dependent through the ``has_dev`` gate, so
    a comparison against a differently-rostered squad measures the roster, not the render.
    """
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="all")
    svc = service.Service(result.paths)
    await svc.add_dev("python")

    goldens = sorted((Path(__file__).parents[1] / "goldens").glob("skill_body_sq-*.txt"))
    assert goldens, "no pinned reference renders found"
    for golden in goldens:
        slug = golden.stem.removeprefix("skill_body_")
        expected = golden.read_text(encoding="utf-8").strip("\n")
        item = await svc.roster_item("skill", slug)
        assert item is not None, slug
        assert await svc.read_body(item.id) == expected, f"{slug} drifted"
