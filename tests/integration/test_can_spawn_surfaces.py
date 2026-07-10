"""can_spawn reaching the two agent-facing surfaces: the rendered .claude pointer's Agent
denylist, and ``sq role <slug> show`` (text + --json).

The RoleDef field itself is proven at tests/unit/test_can_spawn.py.
"""

import json

import pytest
import yaml

from squads._sections import split_frontmatter

pytestmark = pytest.mark.anyio


def _read_pointer(project, slug: str) -> str:
    return (project.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")


class TestPointerDenylist:
    async def test_manager_pointer_has_no_disallowed_tools(self, project) -> None:
        fm, _ = split_frontmatter(_read_pointer(project, "manager"))
        assert "disallowedTools" not in fm

    async def test_tech_lead_pointer_has_no_disallowed_tools(self, project, svc) -> None:
        await svc.activate_role("tech-lead")
        fm, _ = split_frontmatter(_read_pointer(project, "tech-lead"))
        assert "disallowedTools" not in fm

    async def test_a_leaf_role_pointer_denies_the_agent_tool(self, project, svc) -> None:
        await svc.activate_role("reviewer")
        fm, _ = split_frontmatter(_read_pointer(project, "reviewer"))
        assert fm.get("disallowedTools") == "Agent"

    async def test_a_dev_role_pointer_denies_the_agent_tool(self, project, svc) -> None:
        await svc.add_dev("python")
        fm, _ = split_frontmatter(_read_pointer(project, "python-dev"))
        assert fm.get("disallowedTools") == "Agent"

    async def test_leaf_pointer_frontmatter_is_valid_yaml(self, project, svc) -> None:
        await svc.activate_role("reviewer")
        text = _read_pointer(project, "reviewer")
        raw = text[text.index("---") + 3 : text.index("---", text.index("---") + 3)]
        parsed = yaml.safe_load(raw)
        assert isinstance(parsed, dict)
        assert parsed.get("disallowedTools") == "Agent"

    async def test_spawner_pointer_frontmatter_is_valid_yaml_with_no_denylist(
        self, project
    ) -> None:
        text = _read_pointer(project, "manager")
        raw = text[text.index("---") + 3 : text.index("---", text.index("---") + 3)]
        parsed = yaml.safe_load(raw)
        assert isinstance(parsed, dict)
        assert "disallowedTools" not in parsed

    async def test_every_leaf_bundled_role_denies_the_agent_tool(self, project, svc) -> None:
        leaf_slugs = ["reviewer", "qa", "devops", "product-owner", "tech-writer", "architect"]
        for slug in leaf_slugs:
            await svc.activate_role(slug)
        for slug in leaf_slugs:
            fm, _ = split_frontmatter(_read_pointer(project, slug))
            assert fm.get("disallowedTools") == "Agent", slug


class TestRoleShowSurfacesCanSpawn:
    async def test_a_spawner_shows_can_spawn_yes(self, project, invoke) -> None:
        r = await invoke(["role", "manager", "show"])
        assert r.exit_code == 0, r.output
        assert "can spawn" in r.output and "yes" in r.output

    async def test_a_leaf_role_shows_can_spawn_no_even_if_not_yet_activated(
        self, project, invoke
    ) -> None:
        r = await invoke(["role", "reviewer", "show"])
        assert r.exit_code == 0, r.output
        assert "can spawn" in r.output and "no" in r.output

    async def test_json_output_carries_the_boolean(self, project, invoke) -> None:
        r = await invoke(["role", "manager", "show", "--json"])
        assert json.loads(r.output)["can_spawn"] is True
        r = await invoke(["role", "reviewer", "show", "--json"])
        assert json.loads(r.output)["can_spawn"] is False
