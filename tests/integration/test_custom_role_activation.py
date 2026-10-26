"""Creating a role that defines itself end to end: ``add_role`` (``sq role add``) stores the
definition on a tracked ROLE item and writes the ``.claude/`` pointer with the custom fields
(not a bundled fallback), and ``can_spawn`` opts the role into spawning — default false,
explicit true honoured, reflected in the pointer's ``disallowedTools`` denylist and in
``sq role <slug> show`` / ``--json``. The resolver mechanics themselves are proven at
tests/unit/test_a_role_resolves_from_one_base_chosen_by_its_stored_facts.py; this file covers
the creation-plus-can_spawn slice on top of that.
"""

import json
from pathlib import Path

import pytest

from _helpers import catalog_of
from squads._roles._resolver import resolve_role_for_item
from squads._sections import split_frontmatter

pytestmark = pytest.mark.anyio

_ANALYST = {
    "name": "Sam Security",
    "job_title": "security analyst",
    "description": "Reviews changes for security issues.",
    "mission": "Keep the codebase free of security regressions.",
}


def _read_pointer(project, slug: str) -> str:
    return (project.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")


def _definition_file(project, slug: str, can_spawn: bool) -> Path:
    path = project.squad_dir / "role-definition.toml"
    path.write_text(
        'full_name = "Orin Orchestrator"\ntitle = "custom orchestrator"\n'
        'description = "Coordinates a swarm of specialist subagents."\n'
        'mission = "Plan and delegate work across the custom role roster."\n'
        f"can_spawn = {str(can_spawn).lower()}\n",
        encoding="utf-8",
    )
    return path


class TestCreationStoresTheDefinitionAndWritesThePointer:
    async def test_the_role_item_carries_the_custom_definition(self, project, svc) -> None:
        item = await svc.add_role("security-analyst", **_ANALYST)

        assert item.type == "role"
        assert item.slug == "security-analyst"
        assert item.title == "Sam Security"
        assert item.description == "Reviews changes for security issues."
        assert item.attribute("mission") == "Keep the codebase free of security regressions."
        assert item.attribute("job_title") == "security analyst"
        resolved = resolve_role_for_item(
            item, svc.paths.squad_dir, catalog=catalog_of(svc.paths.squad_dir)
        )
        assert resolved.title == "security analyst"
        assert resolved.mission == "Keep the codebase free of security regressions."

    async def test_the_pointer_is_written_with_the_custom_name_and_no_bundled_fallback(
        self, project, svc
    ) -> None:
        await svc.add_role(
            "incident-commander",
            name="Iris Commander",
            job_title="incident commander",
            description="Runs incident response.",
            mission="Own incidents from triage to resolution.",
        )
        pointer = _read_pointer(project, "incident-commander")
        assert "Iris Commander" in pointer
        assert "incident commander" in pointer

    async def test_show_renders_the_custom_card_not_a_bundled_fallback(
        self, project, svc, invoke
    ) -> None:
        await svc.add_role("security-analyst", **_ANALYST)
        r = await invoke(["role", "security-analyst", "show"])
        assert r.exit_code == 0, r.output
        assert "Sam Security" in r.output
        assert "security analyst" in r.output


class TestCanSpawnOptIn:
    async def test_default_is_false_and_the_pointer_denies_the_agent_tool(
        self, project, svc
    ) -> None:
        item = await svc.add_role("security-analyst", **_ANALYST)
        assert (
            resolve_role_for_item(
                item, svc.paths.squad_dir, catalog=catalog_of(svc.paths.squad_dir)
            ).can_spawn
            is False
        )
        fm, _ = split_frontmatter(_read_pointer(project, "security-analyst"))
        assert fm.get("disallowedTools") == "Agent"

    async def test_can_spawn_true_in_the_definition_is_honoured_with_no_denylist(
        self, project, svc
    ) -> None:
        import tomllib

        path = _definition_file(project, "orchestrator", can_spawn=True)
        item = await svc.add_role(
            "orchestrator", definition=tomllib.loads(path.read_text(encoding="utf-8"))
        )
        assert (
            resolve_role_for_item(
                item, svc.paths.squad_dir, catalog=catalog_of(svc.paths.squad_dir)
            ).can_spawn
            is True
        )
        fm, _ = split_frontmatter(_read_pointer(project, "orchestrator"))
        assert "disallowedTools" not in fm

    async def test_show_json_reflects_can_spawn_for_a_custom_role(
        self, project, svc, invoke
    ) -> None:
        path = _definition_file(project, "orchestrator", can_spawn=True)
        added = await invoke(["role", "add", "orchestrator", "--file", str(path)])
        assert added.exit_code == 0, added.output
        r = await invoke(["role", "orchestrator", "show", "--json"])
        assert r.exit_code == 0, r.output
        assert json.loads(r.output)["can_spawn"] is True


class TestCliAddSmoke:
    async def test_add_exits_zero_and_prints_the_added_name_and_id(self, project, invoke) -> None:
        r = await invoke(
            [
                *["role", "add", "security-analyst", "--name", "Sam Security"],
                *["--job-title", "security analyst", "--desc", "Reviews changes."],
                *["--mission", "Keep the codebase free of security regressions."],
            ]
        )
        assert r.exit_code == 0, r.output
        assert "Sam Security" in r.output
        assert "ROLE-" in r.output
