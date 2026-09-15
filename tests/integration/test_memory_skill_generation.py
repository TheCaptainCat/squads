"""The bundled ``sq-memory`` skill is generated like the other cross-role managed skills
(``squads``/``greeting``): a definition the service resolves on read, a thin pointer under
``.claude/``, and it's preloaded on every role's pointer — not just one type's, since it's
cross-role behaviour rather than a per-item-type ``sq-<type>`` skill. It also teaches the
team bulletin board (``sq board ...``), folded into this same skill rather than duplicated
as a separate one — the memory-vs-board boundary is stated once, here.
"""

import re

import pytest

from _helpers import resolved_skill_definition
from squads import _sections as sections
from squads._models._extras import ExtraKey as X
from squads._services import _service as service
from squads._workflow._models import ROSTER_SKILL

pytestmark = pytest.mark.anyio

#: Matches ``memory_skill.md.j2``'s own ``squad_dir`` phrasing.
_MEMORY_SKILL_SQUAD_DIR_RE = re.compile(r"\(`([^`]+)/agents/memory/<role>/`\)")

#: Matches ``claude/claude_section.md.j2``'s own ``squad_dir`` phrasing — the surface this is
#: compared against, since ``memory_skill.md.j2`` and ``claude_section.md.j2`` render the same
#: configured value under two independent templates.
_CLAUDE_MD_SQUAD_DIR_RE = re.compile(r"under `([^`]+)/` and indexed in `([^`]+)/\.squads\.json`")


async def test_memory_skill_has_a_resolved_definition_and_a_thin_pointer(svc, project):
    pointer = (project.root / ".claude" / "skills" / "sq-memory" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "sq skill sq-memory show" in pointer
    body = await resolved_skill_definition(svc, "sq-memory")
    assert "start of a run" in body
    assert "One fact per memory" in body
    assert "sq memory <role> forget <slug>" in body
    assert "sq memory <role> list" in body
    assert "sq memory <role> search" in body
    assert "sq memory <role> show" in body
    assert "sq memory <role> add" in body


async def test_memory_skill_states_the_memory_vs_board_boundary(svc):
    body = await resolved_skill_definition(svc, "sq-memory")
    assert "personal" in body.lower()
    assert "board is shared" in body.lower()


async def test_memory_skill_teaches_board_posting_discipline_and_commands(svc):
    body = await resolved_skill_definition(svc, "sq-memory")
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


async def test_squad_dir_renders_the_configured_folder_name_not_an_absolute_path(svc):
    """``{{ squad_dir }}`` in ``memory_skill.md.j2`` must render the squad's configured
    *folder name* (``svc.paths.config.squad_dir`` — e.g. ``"squads"``), matching every backend
    template's own rendering under this key — never the absolute resolved ``Path``
    (``svc.paths.squad_dir``). See the sibling pin on the ``squads`` skill in
    ``test_squads_skill_content_generation.py`` for the fuller regression note; this is the
    second of the two system skills the same regression reached."""
    body = await resolved_skill_definition(svc, "sq-memory")
    folder = svc.paths.config.squad_dir
    assert f"(`{folder}/agents/memory/<role>/`)" in body
    assert str(svc.paths.squad_dir) not in body


async def test_squad_dir_agrees_with_claude_md_for_a_nested_squad_dir(tmp_path, monkeypatch):
    """The single-segment default cannot distinguish "the configured string, verbatim" from
    "the resolved Path's last segment" — a nested ``squad_dir`` (``docs/squad``) separates the
    two. Drives the real read path against a real seeded skill item and compares two
    independently-rendered surfaces — this skill's view-rendered text and ``CLAUDE.md``'s
    backend-rendered managed section — against each other, not against a string pinned twice."""
    monkeypatch.chdir(tmp_path)
    nested = "docs/squad"
    result = await service.init(root=tmp_path, squad_dir=nested, roles_spec="minimal")
    paths = result.paths
    svc = service.Service(paths)

    db = await svc.store.load()
    skill_item = next(
        it
        for it in db.items.values()
        if it.type == ROSTER_SKILL and it.extra.get(X.SLUG, it.slug) == "sq-memory"
    )
    skill_body = await svc.read_body(skill_item.id)
    claude_md = (paths.root / "CLAUDE.md").read_text(encoding="utf-8")

    skill_match = _MEMORY_SKILL_SQUAD_DIR_RE.search(skill_body)
    claude_match = _CLAUDE_MD_SQUAD_DIR_RE.search(claude_md)
    assert skill_match is not None, f"squad_dir phrasing not found in skill body: {skill_body!r}"
    assert claude_match is not None, f"squad_dir phrasing not found in CLAUDE.md: {claude_md!r}"
    skill_folder = skill_match.group(1)
    claude_folder = claude_match.group(1)

    assert skill_folder == claude_folder
    assert skill_folder == nested
    assert claude_folder == nested

    assert str(paths.squad_dir) not in skill_body
    assert str(paths.squad_dir) not in claude_md
