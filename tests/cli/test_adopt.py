"""`sq adopt`: indexing a squad folder that has no index or configuration, the roles it
activates, and the agent files it writes."""

import shutil
from pathlib import Path

import pytest

from tests._squadwide import agent_files, flat, listed, region
from tests.cli._output import json_text

pytestmark = pytest.mark.anyio

TAIL = "Migratelegacydocswithsq--at<date>create…topreservehistory;thensqcheck."
CORE_ROLES = [
    ("ROLE-5", "Robert Architect"),
    ("ROLE-6", "Olivia Lead"),
    ("ROLE-7", "Paul Reviewer"),
]
EXISTING = [
    ("ROLE-1", "Catherine Manager"),
    ("FEAT-2", "Search"),
    ("TASK-3", "Build the query parser"),
    ("REV-4", "Review the query parser"),
]


@pytest.fixture
def adoptable(populated_project) -> Path:
    """The populated squad's folder with its configuration, index and agent files removed."""
    root = populated_project.root
    (root / ".squads.toml").unlink()
    (root / "squads/.squads.json").unlink()
    shutil.rmtree(root / ".claude")
    (root / "CLAUDE.md").unlink()
    return root


async def _held(invoke) -> list[tuple[str, str]]:
    """The squad's items other than the skills adopt seeds."""
    return [(i, title) for i, title in await listed(invoke) if not i.startswith("SKILL-")]


def _adopted(root: Path, folder: str, activated: str) -> str:
    """The flattened panel and closing line `sq adopt` prints for the populated squad."""
    return (
        f"squadsadoptedsquad:{root / folder}imported:4existingitem(s)"
        f"rolesactivated:{activated}{TAIL}"
    )


@pytest.mark.covers("adopt", "--squad-dir")
async def test_squad_dir_names_the_folder_to_adopt(adoptable, invoke) -> None:
    shutil.move(adoptable / "squads", adoptable / "other")
    result = await invoke(["adopt", "--roles", "core", "--squad-dir", "other"])
    assert result.exit_code == 0, result.output
    assert flat(result.output) == _adopted(adoptable, "other", "architect,tech-lead,reviewer")
    assert await _held(invoke) == [*EXISTING, *CORE_ROLES]


@pytest.mark.covers("adopt", "--squad-dir")
async def test_squad_dir_refuses_a_folder_outside_the_project(adoptable, invoke) -> None:
    result = await invoke(["adopt", "--roles", "core", "--squad-dir", "../up"])
    assert (result.exit_code, result.output) == (
        1,
        "error: --squad-dir must stay inside the project root, got '../up'\n",
    )
    assert not (adoptable / ".squads.toml").exists()


@pytest.mark.covers("adopt", "--renumber")
async def test_renumber_gives_a_shared_number_a_new_one_and_adopts(adoptable, invoke) -> None:
    squad = adoptable / "squads"
    original = (squad / "tasks/TASK-000003-build-the-query-parser.md").read_text(encoding="utf-8")
    (squad / "features/FEAT-000003-twin.md").write_text(
        original.replace("id: TASK-3", "id: FEAT-3"), encoding="utf-8"
    )
    result = await invoke(["adopt", "--roles", "core", "--renumber"])
    assert result.exit_code == 0, result.output
    assert flat(result.output) == _adopted(
        adoptable, "squads", "architect,tech-lead,reviewer"
    ).replace("imported:4", "imported:5").replace(TAIL, "renumberedTASK-3->TASK-5" + TAIL)


@pytest.mark.covers("adopt", "--roles")
async def test_roles_activates_the_roles_the_folder_does_not_hold_yet(adoptable, invoke) -> None:
    result = await invoke(["adopt", "--roles", "architect,qa"])
    assert result.exit_code == 0, result.output
    assert flat(result.output) == _adopted(adoptable, "squads", "architect,qa")
    assert await _held(invoke) == [
        *EXISTING,
        ("ROLE-5", "Robert Architect"),
        ("ROLE-6", "Mara Tester"),
    ]


@pytest.mark.covers("adopt", "--roles")
async def test_roles_refuses_a_name_that_is_neither_a_bundle_nor_a_role(adoptable, invoke) -> None:
    result = await invoke(["adopt", "--roles", "bogus"])
    assert (result.exit_code, result.output) == (
        1,
        "error: no bundle or role 'bogus' (bundles: all, core, minimal; roles: manager, "
        "architect, tech-lead, reviewer, qa, devops, product-owner, tech-writer)\n",
    )


@pytest.mark.covers("adopt", "--json")
async def test_json_prints_the_squad_adopted_and_what_it_held(adoptable, invoke) -> None:
    (adoptable / "squads/tasks/TASK-000009-broken.md").write_text(
        "---\n: : bad\n", encoding="utf-8"
    )
    result = await invoke(["adopt", "--roles", "architect,qa", "--backend", "none", "--json"])
    assert (result.exit_code, result.output) == (
        1,
        json_text(
            {
                "squad": str(adoptable / "squads"),
                "imported": 4,
                "roles": ["architect", "qa"],
                "notice": None,
                "unreadable": [
                    "TASK-000009-broken.md: file has no `id` in frontmatter — its previous index "
                    "entry, if any, was carried forward as-is; fix the file and repair again"
                ],
                "renumbered": [],
                "warnings": [],
            }
        ),
    )


@pytest.mark.covers("adopt", "--backend")
async def test_backend_agents_md_writes_the_agents_md_region(adoptable, invoke) -> None:
    result = await invoke(["adopt", "--roles", "core", "--backend", "agents_md"])
    assert result.exit_code == 0, result.output
    assert agent_files(adoptable) == ["AGENTS.md"]
    assert "- **Catherine Manager** — manager (`manager`)" in region(adoptable / "AGENTS.md")


@pytest.mark.covers("adopt", "--backend")
async def test_backend_none_writes_no_agent_files(adoptable, invoke) -> None:
    result = await invoke(["adopt", "--roles", "core", "--backend", "none"])
    assert result.exit_code == 0, result.output
    assert agent_files(adoptable) == []
    assert await _held(invoke) == [*EXISTING, *CORE_ROLES]


@pytest.mark.covers("adopt", "--backend")
async def test_backend_refuses_a_name_that_is_not_registered(adoptable, invoke) -> None:
    result = await invoke(["adopt", "--backend", "bogus"])
    assert (result.exit_code, result.output) == (
        1,
        "error: unknown backend 'bogus' (available: claude_code, agents_md)\n",
    )
    assert not (adoptable / ".squads.toml").exists()
    retried = await invoke(["adopt", "--roles", "core", "--backend", "claude_code"])
    assert retried.exit_code == 0, retried.output


@pytest.mark.covers("adopt", "--no-claude")
async def test_no_claude_writes_the_pointers_and_skips_settings_and_claude_md(
    adoptable, invoke
) -> None:
    result = await invoke(["adopt", "--roles", "core", "--no-claude"])
    assert result.exit_code == 0, result.output
    assert agent_files(adoptable) == [
        ".claude/agents/architect.md",
        ".claude/agents/reviewer.md",
        ".claude/agents/tech-lead.md",
    ]


@pytest.mark.covers("adopt", "--roles")
async def test_adopt_writes_settings_and_claude_md_by_default(adoptable, invoke) -> None:
    result = await invoke(["adopt", "--roles", "core"])
    assert result.exit_code == 0, result.output
    assert agent_files(adoptable) == [
        ".claude/agents/architect.md",
        ".claude/agents/reviewer.md",
        ".claude/agents/tech-lead.md",
        ".claude/settings.json",
        "CLAUDE.md",
    ]


@pytest.mark.covers("adopt", "--renumber")
async def test_renumber_json_lists_the_items_that_moved(adoptable, invoke) -> None:
    squad = adoptable / "squads"
    original = (squad / "tasks/TASK-000003-build-the-query-parser.md").read_text(encoding="utf-8")
    (squad / "features/FEAT-000003-twin.md").write_text(
        original.replace("id: TASK-3", "id: FEAT-3"), encoding="utf-8"
    )
    result = await invoke(["adopt", "--roles", "core", "--renumber", "--json"])
    assert (result.exit_code, result.output) == (
        0,
        json_text(
            {
                "squad": str(squad),
                "imported": 5,
                "roles": ["architect", "tech-lead", "reviewer"],
                "notice": None,
                "unreadable": [],
                "renumbered": ["  renumbered TASK-3 -> TASK-5"],
                "warnings": [],
            }
        ),
    )
