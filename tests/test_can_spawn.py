"""Tests for TASK-000156: can_spawn on RoleDef + backend Agent denylist.

Three seam-level checks:
1. RoleDef.can_spawn is True only for manager + tech-lead; False for all
   other bundled roles and for dev_role().
2. The rendered .claude/agents/<slug>.md frontmatter carries disallowedTools:
   Agent for leaf roles and omits it for spawner roles; frontmatter parses as
   valid YAML.
3. sq role <slug> show surfaces the can_spawn capability.
"""

import pytest
import yaml

from squads._roles._catalog import PREDEFINED, RoleDef, dev_role
from squads._sections import split_frontmatter

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# 1. RoleDef.can_spawn — catalog / dev_role()
# ---------------------------------------------------------------------------


class TestCanSpawnField:
    def test_manager_can_spawn(self):
        manager = next(r for r in PREDEFINED if r.slug == "manager")
        assert manager.can_spawn is True

    def test_tech_lead_can_spawn(self):
        tl = next(r for r in PREDEFINED if r.slug == "tech-lead")
        assert tl.can_spawn is True

    def test_leaf_bundled_roles_cannot_spawn(self):
        leaf_slugs = {"architect", "reviewer", "qa", "devops", "product-owner", "tech-writer"}
        for role in PREDEFINED:
            if role.slug in leaf_slugs:
                assert role.can_spawn is False, f"{role.slug} should have can_spawn=False"

    def test_dev_role_cannot_spawn(self):
        role = dev_role("python")
        assert role.can_spawn is False

    def test_dev_role_different_tech_cannot_spawn(self):
        for tech in ("dotnet", "go", "rust", "typescript"):
            r = dev_role(tech)
            assert r.can_spawn is False, f"dev_role({tech!r}) should have can_spawn=False"

    def test_default_can_spawn_is_false(self):
        """Newly constructed RoleDef without can_spawn defaults to False."""
        r = RoleDef(
            slug="custom",
            full_name="Custom Role",
            title="custom",
            description="A custom role.",
            mission="Do custom things.",
        )
        assert r.can_spawn is False

    def test_round_trip_through_extra(self):
        """can_spawn survives to_extra / from_extra round-trip for both True and False."""
        for slug in ("manager", "tech-lead"):
            r = next(role for role in PREDEFINED if role.slug == slug)
            assert r.can_spawn is True
            extra = r.to_extra()
            restored = RoleDef.from_extra(extra)
            assert restored.can_spawn is True

        architect = next(r for r in PREDEFINED if r.slug == "architect")
        extra = architect.to_extra()
        restored = RoleDef.from_extra(extra)
        assert restored.can_spawn is False


# ---------------------------------------------------------------------------
# 2. Backend: rendered agent pointer frontmatter
# ---------------------------------------------------------------------------


def _read_pointer(project, slug: str) -> str:
    return (project.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")


class TestPointerFrontmatter:
    """Generated .claude/agents/<slug>.md carries disallowedTools for leaf roles."""

    async def test_manager_pointer_has_no_disallowed_tools(self, project, svc):
        """manager keeps spawn authority — no disallowedTools line."""
        text = _read_pointer(project, "manager")
        fm, _ = split_frontmatter(text)
        assert "disallowedTools" not in fm

    async def test_tech_lead_pointer_has_no_disallowed_tools(self, project, svc):
        """tech-lead keeps spawn authority — no disallowedTools line."""
        await svc.activate_role("tech-lead")
        text = _read_pointer(project, "tech-lead")
        fm, _ = split_frontmatter(text)
        assert "disallowedTools" not in fm

    async def test_leaf_role_pointer_denies_agent(self, project, svc):
        """A leaf bundled role (reviewer) denies the Agent spawn tool."""
        await svc.activate_role("reviewer")
        text = _read_pointer(project, "reviewer")
        fm, _ = split_frontmatter(text)
        assert fm.get("disallowedTools") == "Agent"

    async def test_dev_role_pointer_denies_agent(self, project, svc):
        """A <tech>-dev role denies the Agent spawn tool."""
        await svc.add_dev("python")
        text = _read_pointer(project, "python-dev")
        fm, _ = split_frontmatter(text)
        assert fm.get("disallowedTools") == "Agent"

    async def test_leaf_pointer_frontmatter_is_valid_yaml(self, project, svc):
        """Leaf role pointer frontmatter parses as valid YAML (structural test)."""
        await svc.activate_role("reviewer")
        text = _read_pointer(project, "reviewer")
        # split_frontmatter returns the already-parsed dict, but also verify the
        # raw YAML block is independently parseable to catch whitespace regressions.
        raw_start = text.index("---") + 3
        raw_end = text.index("---", raw_start)
        raw_block = text[raw_start:raw_end]
        parsed = yaml.safe_load(raw_block)
        assert isinstance(parsed, dict)
        assert parsed.get("disallowedTools") == "Agent"

    async def test_spawner_pointer_frontmatter_is_valid_yaml(self, project, svc):
        """Manager pointer frontmatter is valid YAML and has no disallowedTools key."""
        text = _read_pointer(project, "manager")
        raw_start = text.index("---") + 3
        raw_end = text.index("---", raw_start)
        raw_block = text[raw_start:raw_end]
        parsed = yaml.safe_load(raw_block)
        assert isinstance(parsed, dict)
        assert "disallowedTools" not in parsed

    async def test_multiple_leaf_roles_all_deny_agent(self, project, svc):
        """All leaf bundled roles produce a disallowedTools: Agent line."""
        leaf_slugs = ["reviewer", "qa", "devops", "product-owner", "tech-writer", "architect"]
        for slug in leaf_slugs:
            await svc.activate_role(slug)
        for slug in leaf_slugs:
            text = _read_pointer(project, slug)
            fm, _ = split_frontmatter(text)
            assert fm.get("disallowedTools") == "Agent", (
                f"{slug} pointer should deny Agent but got: {fm.get('disallowedTools')!r}"
            )


# ---------------------------------------------------------------------------
# 3. CLI smoke test: sq role <slug> show surfaces can_spawn
# ---------------------------------------------------------------------------


class TestRoleShowSurfacesCanSpawn:
    async def test_spawner_role_show_displays_can_spawn_yes(self, project, invoke):
        """sq role manager show prints 'can spawn: yes'."""
        result = await invoke(["role", "manager", "show"])
        assert result.exit_code == 0, result.output
        assert "can spawn" in result.output
        assert "yes" in result.output

    async def test_leaf_role_show_displays_can_spawn_no(self, project, invoke):
        """sq role show for a leaf bundled slug (not yet activated) prints 'can spawn: no'."""
        # reviewer is not activated but sq role <slug> show still renders a catalog card.
        result = await invoke(["role", "reviewer", "show"])
        assert result.exit_code == 0, result.output
        assert "can spawn" in result.output
        assert "no" in result.output

    async def test_tech_lead_role_show_displays_can_spawn_yes(self, project, invoke):
        """sq role tech-lead show prints 'can spawn: yes'."""
        result = await invoke(["role", "tech-lead", "show"])
        assert result.exit_code == 0, result.output
        assert "can spawn" in result.output
        assert "yes" in result.output

    async def test_role_show_json_includes_can_spawn(self, project, invoke):
        """sq role manager show --json includes can_spawn: true."""
        import json

        result = await invoke(["role", "manager", "show", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["can_spawn"] is True

    async def test_leaf_role_show_json_includes_can_spawn_false(self, project, invoke):
        """sq role reviewer show --json includes can_spawn: false."""
        import json

        result = await invoke(["role", "reviewer", "show", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["can_spawn"] is False
