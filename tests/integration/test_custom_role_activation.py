"""Activating a brand-new (non-bundled) custom role end to end: scaffold → hand-fill →
``activate_role`` creates the tracked ROLE item and the ``.claude/`` pointer with the custom
fields (not a bundled fallback), and ``can_spawn`` opts a custom role into spawning — default
false, explicit true honoured, reflected in the pointer's ``disallowedTools`` denylist and in
``sq role <slug> show`` / ``--json``. The resolver merge mechanics themselves are proven at
tests/unit/test_role_override_field_merge.py and tests/service/test_role_and_dev_override_pickup_
at_instantiation.py; this file covers the activation-plus-can_spawn slice on top of that.
"""

import json
import re
from pathlib import Path

import pytest

from squads._models._extras import ExtraKey as X
from squads._overrides._service import scaffold_new_role
from squads._sections import split_frontmatter

pytestmark = pytest.mark.anyio


def _fill_essentials(path: Path, **values: str) -> None:
    """Overwrite a scaffolded new-role TOML's essential (placeholder) fields with real values."""
    text = path.read_text(encoding="utf-8")
    for field, value in values.items():
        text = re.sub(
            rf'^{field} = ".*"$', f'{field} = "{value}"', text, count=1, flags=re.MULTILINE
        )
    path.write_text(text, encoding="utf-8")


def _read_pointer(project, slug: str) -> str:
    return (project.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")


class TestActivationCreatesTheTrackedItemAndPointer:
    async def test_activating_a_filled_custom_toml_creates_the_role_item_with_custom_fields(
        self, project, svc
    ) -> None:
        path = scaffold_new_role(project.squad_dir, slug="security-analyst")
        _fill_essentials(
            path,
            full_name="Sam Security",
            title="security analyst",
            description="Reviews changes for security issues.",
            mission="Keep the codebase free of security regressions.",
        )

        item = await svc.activate_role("security-analyst")
        assert item.type == "role"
        assert item.extra.get(X.SLUG) == "security-analyst"
        assert item.extra.get(X.FULL_NAME) == "Sam Security"
        assert item.extra.get(X.TITLE) == "security analyst"
        assert item.extra.get(X.MISSION) == "Keep the codebase free of security regressions."

    async def test_the_pointer_is_written_with_the_custom_full_name_and_no_bundled_fallback(
        self, project, svc
    ) -> None:
        path = scaffold_new_role(project.squad_dir, slug="incident-commander")
        _fill_essentials(
            path,
            full_name="Iris Commander",
            title="incident commander",
            description="Runs incident response.",
            mission="Own incidents from triage to resolution.",
        )
        await svc.activate_role("incident-commander")
        pointer = _read_pointer(project, "incident-commander")
        assert "Iris Commander" in pointer
        assert "incident commander" in pointer

    async def test_show_renders_the_custom_card_not_a_bundled_fallback(
        self, project, svc, invoke
    ) -> None:
        path = scaffold_new_role(project.squad_dir, slug="security-analyst")
        _fill_essentials(
            path,
            full_name="Sam Security",
            title="security analyst",
            description="Reviews changes for security issues.",
            mission="Keep the codebase free of security regressions.",
        )
        await svc.activate_role("security-analyst")
        r = await invoke(["role", "security-analyst", "show"])
        assert r.exit_code == 0, r.output
        assert "Sam Security" in r.output
        assert "security analyst" in r.output


class TestCanSpawnOptIn:
    async def test_default_is_false_and_the_pointer_denies_the_agent_tool(
        self, project, svc
    ) -> None:
        path = scaffold_new_role(project.squad_dir, slug="security-analyst")
        _fill_essentials(
            path,
            full_name="Sam Security",
            title="security analyst",
            description="Reviews changes for security issues.",
            mission="Keep the codebase free of security regressions.",
        )
        item = await svc.activate_role("security-analyst")
        assert item.extra.get(X.CAN_SPAWN) is False
        fm, _ = split_frontmatter(_read_pointer(project, "security-analyst"))
        assert fm.get("disallowedTools") == "Agent"

    async def test_can_spawn_true_in_the_toml_is_honoured_with_no_denylist(
        self, project, svc
    ) -> None:
        path = scaffold_new_role(project.squad_dir, slug="orchestrator", can_spawn=True)
        _fill_essentials(
            path,
            full_name="Orin Orchestrator",
            title="custom orchestrator",
            description="Coordinates a swarm of specialist subagents.",
            mission="Plan and delegate work across the custom role roster.",
        )
        item = await svc.activate_role("orchestrator")
        assert item.extra.get(X.CAN_SPAWN) is True
        fm, _ = split_frontmatter(_read_pointer(project, "orchestrator"))
        assert "disallowedTools" not in fm

    async def test_show_json_reflects_can_spawn_for_a_custom_role(
        self, project, svc, invoke
    ) -> None:
        path = scaffold_new_role(project.squad_dir, slug="orchestrator", can_spawn=True)
        _fill_essentials(
            path,
            full_name="Orin Orchestrator",
            title="custom orchestrator",
            description="Coordinates a swarm of specialist subagents.",
            mission="Plan and delegate work across the custom role roster.",
        )
        await svc.activate_role("orchestrator")
        r = await invoke(["role", "orchestrator", "show", "--json"])
        assert r.exit_code == 0, r.output
        assert json.loads(r.output)["can_spawn"] is True


class TestCliActivateSmoke:
    async def test_activate_exits_zero_and_prints_the_activated_name_and_id(
        self, project, invoke
    ) -> None:
        path = scaffold_new_role(project.squad_dir, slug="security-analyst")
        _fill_essentials(
            path,
            full_name="Sam Security",
            title="security analyst",
            description="Reviews changes for security issues.",
            mission="Keep the codebase free of security regressions.",
        )
        r = await invoke(["role", "activate", "security-analyst"])
        assert r.exit_code == 0, r.output
        assert "Sam Security" in r.output
        assert "ROLE-" in r.output
