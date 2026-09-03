"""The bundled ``greeting`` skill is preloaded on every role's pointer: a thin pointer under
``.claude/``, a definition the service resolves on read, operator-facing content only
(subagents skip it), and the detect-then-register beats it teaches.
"""

import pytest

from squads import _sections as sections

pytestmark = pytest.mark.anyio


async def test_greeting_skill_has_a_resolved_definition_and_a_thin_pointer(svc, project):
    pointer = (project.root / ".claude" / "skills" / "greeting" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "sq skill greeting show" in pointer
    body = await svc.skill_definition_text("greeting")
    assert "spawned as a subagent" in body  # subagents skip the greeting
    assert "sq list -t operator" in body and "git config user.name" in body
    assert "Match their tone" in body


async def test_every_role_pointer_preloads_the_greeting_skill(project):
    fm, _ = sections.split_frontmatter(
        (project.root / ".claude" / "agents" / "manager.md").read_text(encoding="utf-8")
    )
    assert "greeting" in fm["skills"]
