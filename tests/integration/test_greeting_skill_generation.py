"""The bundled ``greeting`` skill is generated and preloaded on every role's pointer: a real
body under the squad folder, a thin pointer under ``.claude/``, operator-facing content only
(subagents skip it), and the detect-then-register beats it teaches.
"""

import pytest

from squads import _sections as sections

pytestmark = pytest.mark.anyio


async def test_greeting_skill_has_a_real_body_and_a_thin_pointer(project):
    pointer = (project.root / ".claude" / "skills" / "greeting" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "@squads/agents/skills/greeting.md" in pointer
    body = (project.squad_dir / "agents" / "skills" / "greeting.md").read_text(encoding="utf-8")
    assert "spawned as a subagent" in body  # subagents skip the greeting
    assert "sq list -t operator" in body and "git config user.name" in body
    assert "Match their tone" in body


async def test_every_role_pointer_preloads_the_greeting_skill(project):
    fm, _ = sections.split_frontmatter(
        (project.root / ".claude" / "agents" / "manager.md").read_text(encoding="utf-8")
    )
    assert "greeting" in fm["skills"]
