"""The bundled ``sq-memory`` skill is generated like the other cross-role managed skills
(``squads``/``greeting``): a real body under the squad folder, a thin pointer under
``.claude/``, and it's preloaded on every role's pointer — not just one type's, since it's
cross-role behaviour rather than a per-item-type ``sq-<type>`` skill. It also teaches the
team bulletin board (``sq board ...``), folded into this same skill rather than duplicated
as a separate one — the memory-vs-board boundary is stated once, here.
"""

import pytest

from squads import _sections as sections
from squads._services import _service as service

pytestmark = pytest.mark.anyio


async def test_memory_skill_has_a_real_body_and_a_thin_pointer(project):
    pointer = (project.root / ".claude" / "skills" / "sq-memory" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "@squads/agents/skills/sq-memory.md" in pointer
    body = (project.squad_dir / "agents" / "skills" / "sq-memory.md").read_text(encoding="utf-8")
    assert "start of a run" in body
    assert "One fact per memory" in body
    assert "sq memory <role> forget <slug>" in body
    assert "sq memory <role> list" in body
    assert "sq memory <role> search" in body
    assert "sq memory <role> show" in body
    assert "sq memory <role> add" in body


async def test_memory_skill_states_the_memory_vs_board_boundary(project):
    body = (project.squad_dir / "agents" / "skills" / "sq-memory.md").read_text(encoding="utf-8")
    assert "personal" in body.lower()
    assert "board is shared" in body.lower()


async def test_memory_skill_teaches_board_posting_discipline_and_commands(project):
    body = (project.squad_dir / "agents" / "skills" / "sq-memory.md").read_text(encoding="utf-8")
    assert "short and prescriptive" in body.lower()
    assert "--until" in body
    assert "sq board post" in body
    assert "sq board list" in body
    assert "sq board clear" in body
    # The memory-vs-board boundary is stated in its own section; board instructions don't repeat it.
    assert "## The memory-vs-board boundary" in body
    assert body.count("## The board") == 1


async def test_every_role_pointer_preloads_the_memory_skill(project):
    fm, _ = sections.split_frontmatter(
        (project.root / ".claude" / "agents" / "manager.md").read_text(encoding="utf-8")
    )
    assert "sq-memory" in fm["skills"]


async def test_memory_skill_is_surfaced_across_every_role_not_just_one_type(tmp_path, monkeypatch):
    """Cross-role: every bundled role's pointer preloads sq-memory, unlike a per-type sq-<type>
    skill which only reaches the roles that interact with that item type."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="all", _skip_skill_seed=True)
    paths = result.paths
    for slug in ("manager", "architect", "tech-lead", "reviewer", "qa", "devops", "product-owner"):
        pointer_path = paths.root / ".claude" / "agents" / f"{slug}.md"
        fm, _ = sections.split_frontmatter(pointer_path.read_text(encoding="utf-8"))
        assert "sq-memory" in fm["skills"], f"{slug} pointer missing sq-memory"


async def test_memory_skill_is_registered_among_bundled_skill_slugs():
    from squads._interactions import MEMORY_SKILL, bundled_skill_slugs, skill_description

    assert MEMORY_SKILL in bundled_skill_slugs()
    assert skill_description(MEMORY_SKILL)  # non-empty description registered
