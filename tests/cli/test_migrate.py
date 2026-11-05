"""`sq migrate`: running the pending migrations, reading the changelog, and the bulk
renames of a status, a type and the item-number padding."""

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from squads import __version__
from squads._models import SCHEMA_VERSION
from tests.cli import _bundled_documents as documents
from tests.cli._output import json_text, printed

pytestmark = pytest.mark.anyio

REGENERATED_CONFIG = f"""\
# squads project configuration
schema_version = "{SCHEMA_VERSION}"
squad_dir = "squads"
active_backends = ["claude_code"]
working_language = "en"

[daemon]
enabled = true
idle_timeout_minutes = 5
browser = false
"""

OLD_SQUAD = Path(__file__).parents[1] / "fixtures" / "corpus" / "v0_14"
SCHEMA_17_SQUAD = Path(__file__).parents[1] / "fixtures" / "corpus" / "v0_17"
SCHEMA_19_SQUAD = Path(__file__).parents[1] / "fixtures" / "corpus" / "v0_19"
SCHEMA_4_SQUAD = Path(__file__).parents[1] / "fixtures" / "corpus" / "v0_4"
SCHEMA_19_SKILLS_SQUAD = Path(__file__).parents[1] / "fixtures" / "corpus" / "v0_19_skills"
CHECK_HINT = "  run `sq check` to verify integrity\n"
NO_SQUAD = "error: no .squads.toml found in this or any parent directory — run `sq init`\n"


async def _shown(invoke, item_type: str, number: int) -> dict[str, Any]:
    """The `show --json` object of the item *item_type* *number*."""
    result = await invoke([item_type, str(number), "show", "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


# ------------------------------------------------------------------------------------- up


@pytest.mark.covers("migrate up")
async def test_up_on_a_current_squad_has_nothing_to_migrate(project, invoke) -> None:
    result = await invoke(["migrate", "up"])
    assert (result.exit_code, result.output) == (
        0,
        f"already at schema v{SCHEMA_VERSION}; nothing to migrate\n",
    )


@pytest.mark.covers("migrate up")
async def test_up_brings_an_older_squad_to_the_current_schema(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = shutil.copytree(OLD_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    refused = await invoke(["list"])
    assert (refused.exit_code, refused.output) == (
        1,
        f"error: this squad is at schema v0.14; squads {__version__} expects v{SCHEMA_VERSION}. "
        "Run sq migrate up to upgrade it (see `sq migrate help`).\n",
    )
    result = await invoke(["migrate", "up"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert f"migrated to schema v{SCHEMA_VERSION}; index rebuilt — agent files regenerated" in lines
    assert not any("run `sq sync`" in line for line in lines)
    listed = await invoke(["list", "--json"])
    assert listed.exit_code == 0, listed.output
    assert [i["id"] for i in json.loads(listed.output)][:6] == [
        "ROLE-1",
        "FEAT-2",
        "TASK-3",
        "BUG-4",
        "ADR-5",
        "REV-6",
    ]
    again = await invoke(["migrate", "up"])
    assert (again.exit_code, again.output) == (
        0,
        f"already at schema v{SCHEMA_VERSION}; nothing to migrate\n",
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    """Every file under *root* except the index and its lock file, with its bytes."""
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name not in (".squads.json", ".squads.json.lock")
    }


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _edit(path: Path, old: str, new: str) -> None:
    text = _text(path)
    assert text.count(old) == 1, old
    path.write_text(text.replace(old, new), encoding="utf-8")


def _migrated_head(text: str) -> str:
    """The frontmatter block of an item file, the opening and closing rules included."""
    return text.split("\n---\n", 1)[0] + "\n---\n"


def _tail(text: str) -> str:
    return text.split("\n---\n", 1)[1]


TASK_FILE = "tasks/TASK-000003-implement-auth.md"
REVIEW_FILE = "reviews/REV-000004-auth-review.md"
BUG_FILE = "bugs/BUG-000005-login-fails-on-empty-password.md"

TASK_HEAD = """---
id: TASK-3
sequence_id: 3
type: task
title: Implement auth
status: Draft
parent: FEAT-2
author: manager
subentities:
- local_id: ST1
  title: Validate tokens
  status: Todo
  maps_to: US1
- local_id: ST2
  title: Refresh tokens
  status: Todo
created_at: '2026-10-29T20:55:26Z'
updated_at: '2026-10-29T20:55:27Z'
priority: high
---
"""
REVIEW_HEAD = """---
id: REV-4
sequence_id: 4
type: review
title: Auth review
status: Requested
author: manager
subentities:
- local_id: F1
  title: Unchecked read
  status: Open
  severity: high
  note: ''
  attributes:
    x: 1
- local_id: F2
  title: Dead branch
  status: Open
- local_id: F3
  title: Slow path
  status: Open
  severity: medium
  urgency: low
created_at: '2026-10-29T20:55:27Z'
updated_at: '2026-10-29T20:55:36Z'
---
"""
BUG_HEAD = """---
id: BUG-5
sequence_id: 5
type: bug
title: Login fails on empty password
status: Open
author: manager
created_at: '2026-10-29T20:55:30Z'
updated_at: '2026-10-29T20:55:30Z'
priority: low
severity: critical
---
"""


@pytest.mark.covers("migrate up")
async def test_up_flattens_entries_and_puts_item_keys_in_the_writers_order(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = shutil.copytree(SCHEMA_17_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    before = _snapshot(squad)
    result = await invoke(["migrate", "up"])
    assert result.exit_code == 0, result.output
    after = _snapshot(squad)

    for name, head in ((TASK_FILE, TASK_HEAD), (REVIEW_FILE, REVIEW_HEAD), (BUG_FILE, BUG_HEAD)):
        assert after[name].decode() == head + _tail(before[name].decode()), name
    untouched = "features/FEAT-000002-user-login.md"
    assert after[untouched] == before[untouched], untouched
    role = "agents/roles/ROLE-000001-manager.md"
    assert after[role] == before[role].replace(
        b"<!-- sq:view:role_definition -->\n",
        b"<!-- sq:view:role_definition -->\n\n<!-- sq:view:role_playbook -->\n",
    )

    subtask = json.loads((await invoke(["task", "3", "subtask", "1", "show", "--json"])).output)
    assert subtask["maps_to"] == "US1"
    finding = json.loads((await invoke(["review", "4", "finding", "3", "show", "--json"])).output)
    assert (finding["severity"], finding["urgency"]) == ("medium", "low")


@pytest.mark.covers("migrate up")
async def test_up_takes_a_story_beside_an_empty_maps_to_as_the_mapping(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = shutil.copytree(SCHEMA_17_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    _edit(squad / TASK_FILE, "  story: US1\n", "  maps_to: ''\n  story: US1\n")
    _edit(squad / TASK_FILE, "  title: Refresh tokens\n", "  title: Refresh tokens\n  maps_to:\n")

    result = await invoke(["migrate", "up"])
    assert result.exit_code == 0, result.output
    assert _migrated_head(_text(squad / TASK_FILE)) == TASK_HEAD


@pytest.mark.covers("migrate up")
async def test_up_refuses_an_entry_holding_both_story_and_maps_to_and_writes_nothing(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = shutil.copytree(SCHEMA_17_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    _edit(squad / TASK_FILE, "  story: US1\n", "  story: US1\n  maps_to: US2\n")
    before = _snapshot(squad)
    result = await invoke(["migrate", "up"])
    assert (result.exit_code, result.output) == (
        1,
        "error: TASK-3 ST1: holds both 'story' and a non-empty 'maps_to'\n"
        "1 problem(s) found; fix the entries by hand.\n"
        "This step wrote nothing and the schema stamp is unchanged.\n"
        "The squad is still at schema v0.17: fix the cause, then re-run `sq migrate up`, "
        "which rebuilds the index from the files first.\n",
    )
    assert _snapshot(squad) == before


@pytest.mark.covers("migrate up")
async def test_up_refuses_an_extra_key_that_is_already_a_key_of_the_entry(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = shutil.copytree(SCHEMA_17_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    _edit(squad / REVIEW_FILE, "    urgency: low\n", "    severity: low\n")
    before = _snapshot(squad)
    result = await invoke(["migrate", "up"])
    assert (result.exit_code, result.output) == (
        1,
        "error: REV-4 F3: has an 'extra' key 'severity' that is also a key of the entry\n"
        "1 problem(s) found; fix the entries by hand.\n"
        "This step wrote nothing and the schema stamp is unchanged.\n"
        "The squad is still at schema v0.17: fix the cause, then re-run `sq migrate up`, "
        "which rebuilds the index from the files first.\n",
    )
    assert _snapshot(squad) == before


@pytest.mark.covers("migrate up")
async def test_up_flattens_the_mapping_of_a_squad_with_its_own_vocabulary(
    override_project, invoke
) -> None:
    job = next((override_project.squad_dir / "jobs").glob("*.md"))
    number = re.search(r"^sequence_id: (\d+)$", _text(job), re.MULTILINE)
    assert number is not None
    mapped_now = await invoke(["job", number[1], "action", "1", "update", "--outcome", "1"])
    assert mapped_now.exit_code == 0, mapped_now.output
    flat = _text(job)
    assert "  maps_to: " in flat
    job.write_text(flat.replace("  maps_to: ", "  story: "), encoding="utf-8")
    _edit(
        override_project.root / ".squads.toml",
        f'schema_version = "{SCHEMA_VERSION}"',
        'schema_version = "0.17"',
    )

    result = await invoke(["migrate", "up"])
    assert result.exit_code == 0, result.output
    assert _text(job) == flat


@pytest.mark.covers("migrate up")
async def test_up_stamps_a_clean_0_19_squad_and_adds_only_the_playbook_tag_to_each_role_body(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = shutil.copytree(SCHEMA_19_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    before = _snapshot(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert "stripped retired regions" not in result.output
    assert "run `sq sync`" not in result.output
    assert f'schema_version = "{SCHEMA_VERSION}"' in _text(squad / ".squads.toml")
    after = _snapshot(squad)
    after.pop(".reflog.jsonl", None)
    assert after.pop(".gitignore") == b".squads.toml.*.tmp\n"
    placed = b"\n<!-- sq:view:role_playbook -->\n"
    roles = [name for name in after if name.startswith("agents/roles/")]
    assert roles
    assert all(placed in after[name] for name in roles)
    assert {k: v.replace(placed, b"") for k, v in after.items() if k != ".squads.toml"} == {
        k: v for k, v in before.items() if k != ".squads.toml"
    }


@pytest.mark.covers("migrate up")
async def test_up_lists_every_case_a_0_19_corpus_holds_and_stamps_nothing(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = shutil.copytree(SCHEMA_19_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    _edit(
        squad / "features/FEAT-000002-user-login.md",
        "title: User login\n",
        "title: User login\nsource: tracker\n",
    )
    _edit(squad / "agents/roles/ROLE-000001-manager.md", "slug: manager\n", "slug: source\n")
    _edit(
        squad / "tasks/TASK-000003-implement-auth.md",
        "<!-- sq:discussion -->\n",
        "<!-- sq:discussion -->\n- [2026-11-02T09:14:00Z] `manager` Catherine Manager:\n"
        '  <!-- sq:attrs {"author_handle":"pchat"} -->\n  - A comment.\n',
    )
    before = _snapshot(squad)

    result = await invoke(["migrate", "up"])

    assert (result.exit_code, result.output) == (
        1,
        "error: ROLE-1: is a role with the reserved slug 'source'\n"
        "FEAT-2: has a top-level 'source' key, now a core key\n"
        "TASK-3: line 64 directly under a comment header has the shape of a comment attribute\n"
        "3 problem(s) found; fix them by hand (`sq migrate chlog v0.19.0..v0.20.0` lists the "
        "steps).\n"
        "This step wrote nothing and the schema stamp is unchanged.\n"
        "The squad is still at schema v0.19: fix the cause, then re-run `sq migrate up`, "
        "which rebuilds the index from the files first.\n",
    )
    assert _snapshot(squad) == before
    assert 'schema_version = "0.19"' in _text(squad / ".squads.toml")


def _skills_squad(tmp_path: Path, monkeypatch) -> Path:
    """A copy of the 0.19 squad that holds the per-type and base skills, a project skill and the
    Claude pointers for them, as the working directory."""
    squad = shutil.copytree(SCHEMA_19_SKILLS_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    return squad


def _skill_file(squad: Path, slug: str) -> Path:
    (path,) = (squad / "squads/agents/skills").glob(f"SKILL-*-{slug}.md")
    return path


def _skill_data(path: Path) -> dict[str, Any]:
    return yaml.safe_load(_text(path).removeprefix("---\n").split("\n---\n")[0])


@pytest.mark.covers("migrate up")
async def test_up_retires_the_per_type_skills_and_renames_the_two_base_skills(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = _skills_squad(tmp_path, monkeypatch)
    role = squad / "squads/agents/roles/ROLE-000001-manager.md"
    _edit(role, "origin: system\n", "origin: system\nrefs:\n- SKILL-13\n")
    how_to_before = _skill_data(_skill_file(squad, "squads"))

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in (squad / "squads/agents/skills").glob("*.md")) == [
        "SKILL-000002-sq-greeting.md",
        "SKILL-000009-sq-memory.md",
        "SKILL-000013-sq-how-to.md",
        "SKILL-000014-release-notes.md",
    ]
    how_to = _skill_data(_skill_file(squad, "sq-how-to"))
    assert how_to == {
        **how_to_before,
        "title": "sq-how-to",
        "slug": "sq-how-to",
        "author": "sq-how-to",
        "description": how_to["description"],
    }
    assert how_to["description"].startswith("How to track work on this project")
    assert sorted(p.name for p in (squad / ".claude/skills").iterdir()) == [
        "release-notes",
        "sq-greeting",
        "sq-how-to",
        "sq-memory",
        "sq-role-manager",
    ]
    shown = await _shown(invoke, "skill", 13)
    assert (shown["id"], shown["slug"]) == ("SKILL-13", "sq-how-to")
    inbound = await invoke(["skill", "13", "refs", "--in", "--json"])
    assert json.loads(inbound.output) == {"in": [{"id": "ROLE-1", "kind": "related"}]}
    assert _text(role).count("<!-- sq:view:role_playbook -->") == 1
    allowed = json.loads(_text(squad / ".claude/settings.json"))["permissions"]["allow"]
    assert {"Skill(sq-greeting)", "Skill(sq-how-to)"} <= set(allowed)
    claude = _text(squad / "CLAUDE.md")
    assert "invoke the `sq-greeting` skill" in claude
    assert "`squads` skill" not in claude
    checked = await invoke(["check", "--json"])
    assert (checked.exit_code, checked.output) == (0, "[]\n")


@pytest.mark.covers("migrate up")
async def test_up_lists_every_skill_it_refuses_and_what_the_skill_holds(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = _skills_squad(tmp_path, monkeypatch)
    _edit(
        _skill_file(squad, "sq-task"),
        "<!-- sq:view:item_skill -->\n",
        "<!-- sq:view:item_skill -->\nTeam notes on tasks.\n",
    )
    _edit(
        _skill_file(squad, "sq-bug"),
        "<!-- sq:discussion -->\n",
        "<!-- sq:discussion -->\n- [2026-11-02T09:14:00Z] `manager` Catherine Manager:\n"
        "  - Keep this skill.\n",
    )
    _edit(
        squad / "squads/agents/roles/ROLE-000001-manager.md",
        "origin: system\n",
        "origin: system\nrefs:\n- SKILL-6\n",
    )
    role_skill = _skill_file(squad, "sq-review")
    _edit(role_skill, "slug: sq-review\n", "slug: sq-role-manager\n")
    project = _skill_file(squad, "release-notes")
    _edit(project, "slug: release-notes\n", "slug: sq-how-to\n")
    twin = _skill_file(squad, "sq-guide")
    _edit(twin, "slug: sq-guide\n", "slug: sq-greeting\n")
    before = _snapshot(squad)

    result = await invoke(["migrate", "up"])

    assert (result.exit_code, result.output) == (
        1,
        "error: SKILL-3: per-type skill 'sq-bug' holds a discussion comment; move it first\n"
        "SKILL-6: per-type skill 'sq-epic' holds a ref from ROLE-1; move it first\n"
        "SKILL-11: skill 'sq-role-manager' is named like a role skill, a name 0.20 generates\n"
        "SKILL-12: per-type skill 'sq-task' holds prose in its body; move it first\n"
        "SKILL-8: skill 'sq-greeting' exists beside the 'greeting' skill it would replace\n"
        "SKILL-14: project skill holds the name 'sq-how-to', which 0.20 gives to the 'squads' "
        "skill\n"
        "6 problem(s) found; fix them by hand (`sq migrate chlog v0.19.0..v0.20.0` lists the "
        "steps).\n"
        "This step wrote nothing and the schema stamp is unchanged.\n"
        "The squad is still at schema v0.19: fix the cause, then re-run `sq migrate up`, "
        "which rebuilds the index from the files first.\n",
    )
    assert _snapshot(squad) == before
    assert 'schema_version = "0.19"' in _text(squad / ".squads.toml")


@pytest.mark.covers("migrate up")
async def test_up_completes_once_the_refused_content_is_moved(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = _skills_squad(tmp_path, monkeypatch)
    task_skill = _skill_file(squad, "sq-task")
    original = _text(task_skill)
    _edit(task_skill, "<!-- sq:view:item_skill -->\n", "<!-- sq:view:item_skill -->\nNotes.\n")
    assert (await invoke(["migrate", "up"])).exit_code == 1

    task_skill.write_text(original, encoding="utf-8")
    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert not list((squad / "squads/agents/skills").glob("*-sq-task.md"))
    assert 'schema_version = "0.20"' in _text(squad / ".squads.toml")


@pytest.mark.covers("migrate up")
async def test_up_removes_a_per_type_skill_whatever_its_origin_or_type(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = _skills_squad(tmp_path, monkeypatch)
    _edit(_skill_file(squad, "sq-task"), "origin: system\n", "origin: project\n")
    dropped = _skill_file(squad, "sq-guide")
    for old, new in (
        ("title: sq-guide", "title: sq-widget"),
        ("slug: sq-guide", "slug: sq-widget"),
    ):
        _edit(dropped, old, new)
    _edit(dropped, "author: sq-guide", "author: sq-widget")
    _edit(dropped, "<!-- sq:view:item_skill -->\n", "")
    (squad / ".claude/skills/sq-guide").rename(squad / ".claude/skills/sq-widget")

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in (squad / "squads/agents/skills").glob("*.md")) == [
        "SKILL-000002-sq-greeting.md",
        "SKILL-000009-sq-memory.md",
        "SKILL-000013-sq-how-to.md",
        "SKILL-000014-release-notes.md",
    ]
    assert "sq-widget" not in {p.name for p in (squad / ".claude/skills").iterdir()}


@pytest.mark.covers("migrate up")
async def test_up_brings_a_squad_made_by_release_0_4_to_the_current_skills(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = shutil.copytree(SCHEMA_4_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert sorted(p.name for p in (squad / "squads/agents/skills").iterdir()) == [
        "SKILL-000002-sq-greeting.md",
        "SKILL-000010-sq-how-to.md",
        "SKILL-000011-sq-memory.md",
    ]
    assert sorted(p.name for p in (squad / ".claude/skills").iterdir()) == [
        "sq-greeting",
        "sq-how-to",
        "sq-memory",
        "sq-role-manager",
    ]
    checked = await invoke(["check"])
    assert (checked.exit_code, checked.output) == (0, "✓ no issues\n")


@pytest.mark.covers("migrate up")
async def test_up_leaves_base_skills_already_named_sq_greeting_and_sq_how_to(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = _skills_squad(tmp_path, monkeypatch)
    for old, new in (("greeting", "sq-greeting"), ("squads", "sq-how-to")):
        skill = _skill_file(squad, old)
        for key in ("title", "slug", "author"):
            _edit(skill, f"{key}: {old}\n", f"{key}: {new}\n")
        skill.rename(skill.with_name(skill.name.replace(f"-{old}.md", f"-{new}.md")))
        (squad / ".claude/skills" / old).rename(squad / ".claude/skills" / new)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    assert (_skill_data(_skill_file(squad, "sq-greeting"))["id"]) == "SKILL-2"
    assert (_skill_data(_skill_file(squad, "sq-how-to"))["id"]) == "SKILL-13"
    assert 'schema_version = "0.20"' in _text(squad / ".squads.toml")


@pytest.mark.covers("migrate up")
async def test_up_writes_the_role_bodies_into_agents_md_for_an_agents_md_squad(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = _skills_squad(tmp_path, monkeypatch)
    _edit(
        squad / ".squads.toml",
        'active_backends = ["claude_code"]',
        'active_backends = ["agents_md"]',
    )

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    shown = await invoke(["role", "manager", "show", "--raw", "--no-header"])
    assert shown.exit_code == 0, shown.output
    assert shown.output.rstrip("\n") in _text(squad / "AGENTS.md")


@pytest.mark.covers("migrate up")
async def test_up_refuses_a_workflow_override_naming_a_type_or_alias_source_and_names_the_manual(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = shutil.copytree(SCHEMA_19_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    override = squad / ".overrides" / "workflow.toml"
    override.parent.mkdir()
    override.write_text('[items.task]\naliases = ["t", "source"]\n', encoding="utf-8")
    before = _snapshot(squad)

    result = await invoke(["migrate", "up"])

    assert (result.exit_code, result.output) == (
        1,
        "error: this squad's workflow override could not be loaded, so `sq migrate up` cannot "
        "run under the vocabulary it declares.\n"
        f"  file:  {override}\n"
        "  cause: Invalid workflow spec:\n"
        "  - item 'task': alias 'source' shadows the built-in `sq source` command \u2014 rename "
        "or drop the alias; a squad upgrading follows the steps `sq migrate chlog "
        "v0.19.0..v0.20.0` prints, run with the release it is upgrading from\n"
        "Correct the file, then re-run `sq migrate up`.\n",
    )
    assert _snapshot(squad) == before


@pytest.mark.covers("migrate up")
async def test_up_refuses_a_playbook_override_setting_lifecycle_or_commands_and_writes_nothing(
    tmp_path, monkeypatch, invoke
) -> None:
    squad = shutil.copytree(SCHEMA_19_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    override = squad / ".overrides" / "playbook.toml"
    override.parent.mkdir()
    override.write_text(
        '[types.task]\nlifecycle = "Draft"\ncommands = ["sq task"]\n', encoding="utf-8"
    )
    before = _snapshot(squad)

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 1
    assert "types.task.lifecycle: 'lifecycle' is not a key of a playbook entry" in result.output
    assert "types.task.commands: 'commands' is not a key of a playbook entry" in result.output
    assert result.output.endswith("Correct the file, then re-run `sq migrate up`.\n")
    assert _snapshot(squad) == before


@pytest.mark.covers("migrate up")
async def test_up_run_again_changes_no_file(tmp_path, monkeypatch, invoke) -> None:
    squad = shutil.copytree(SCHEMA_17_SQUAD, tmp_path / "old")
    monkeypatch.chdir(squad)
    assert (await invoke(["migrate", "up"])).exit_code == 0
    items = {str(p): p.read_bytes() for p in squad.rglob("*.md")}
    _edit(squad / ".squads.toml", f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.17"')

    result = await invoke(["migrate", "up"])
    assert result.exit_code == 0, result.output
    assert {str(p): p.read_bytes() for p in squad.rglob("*.md")} == items


@pytest.mark.covers("migrate up")
async def test_up_keeps_a_daemon_table_when_it_regenerates_the_config(project, invoke) -> None:
    config = project.root / ".squads.toml"
    text = config.read_text(encoding="utf-8")
    config.write_text(
        text.replace(f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "0.17"')
        + '\ndefault_backend = "claude_code"\n\n[daemon]\nidle_timeout_minutes = 5\n',
        encoding="utf-8",
    )

    result = await invoke(["migrate", "up"])

    assert result.exit_code == 0, result.output
    regenerated = config.read_text(encoding="utf-8")
    assert regenerated == REGENERATED_CONFIG


@pytest.mark.covers("migrate up")
async def test_up_refuses_a_squad_newer_than_the_package(project, invoke) -> None:
    config = project.root / ".squads.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            f'schema_version = "{SCHEMA_VERSION}"', 'schema_version = "9.0"'
        ),
        encoding="utf-8",
    )
    result = await invoke(["migrate", "up"])
    assert (result.exit_code, result.output) == (
        1,
        f"error: this squad is at schema v9.0, newer than squads {__version__} "
        f"(v{SCHEMA_VERSION}). Upgrade the squads package.\n",
    )


@pytest.mark.covers("migrate up")
async def test_up_refuses_a_directory_with_no_squad(invoke) -> None:
    result = await invoke(["migrate", "up"])
    assert (result.exit_code, result.output) == (1, NO_SQUAD)


# ---------------------------------------------------------------------------- help and chlog


@pytest.mark.covers("migrate help")
async def test_help_lists_the_migrations_oldest_first_outside_any_squad(invoke) -> None:
    result = await invoke(["migrate", "help"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0].strip() == "migration changelog — read steps with `sq migrate chlog vfrom..vto`"
    assert [c.strip() for c in lines[2].strip("┃").split("┃")] == [
        "Release",
        "Schema",
        "Summary",
        "Manual",
    ]
    rows = [ln.strip("│").split("│") for ln in lines if ln.startswith("│ v")]
    releases = [tuple(int(n) for n in row[0].strip().lstrip("v").split(".")) for row in rows]
    assert releases[0] == (0, 2, 0)
    assert releases == sorted(releases)
    assert rows[-1][1].strip().endswith(f"→v{SCHEMA_VERSION}")


@pytest.mark.covers("migrate chlog", "vfrom..vto")
async def test_chlog_prints_the_manual_steps_of_each_migration_in_the_range(invoke) -> None:
    result = await invoke(["migrate", "chlog", "v0.1.1..v0.2.0"])
    assert result.exit_code == 0, result.output
    lines = result.output.splitlines()
    assert lines[0].rstrip() == "v0.2.0 — manual steps (schema v0.1→v0.2)"
    assert [ln for ln in lines if "manual steps (schema" in ln] == [lines[0]]


@pytest.mark.covers("migrate chlog", "vfrom..vto")
async def test_chlog_says_so_when_the_range_holds_no_manual_step(invoke) -> None:
    result = await invoke(["migrate", "chlog", "v0.10.0..v0.11.0"])
    assert (result.exit_code, result.output) == (0, "no manual steps for v0.10.0..v0.11.0\n")


@pytest.mark.covers("migrate chlog", "vfrom..vto")
async def test_chlog_refuses_a_range_without_two_dots(invoke) -> None:
    result = await invoke(["migrate", "chlog", "v0.2.0"])
    assert (result.exit_code, result.output) == (
        1,
        "error: expected a range like v0.1.1..v0.2.0 (vfrom..vto, from below to), got 'v0.2.0'\n",
    )


@pytest.mark.covers("migrate chlog", "vfrom..vto")
@pytest.mark.parametrize(
    "span", ["a..b", "v1x..v2y", "v0.1.0..v0.2.0..v0.3.0", "v0.17.0..v0.1.0", "v0.2.0..v0.2.0"]
)
async def test_chlog_refuses_a_bound_that_is_no_version_or_a_range_not_ascending(
    invoke, span
) -> None:
    result = await invoke(["migrate", "chlog", span])
    assert (result.exit_code, result.output) == (
        1,
        f"error: expected a range like v0.1.1..v0.2.0 (vfrom..vto, from below to), got {span!r}\n",
    )


@pytest.mark.covers("migrate chlog", "vfrom..vto")
async def test_chlog_requires_a_range(invoke) -> None:
    result = await invoke(["migrate", "chlog"])
    assert (result.exit_code, result.output) == (
        2,
        "Usage: sq migrate chlog [OPTIONS] {vfrom..vto}\n"
        "Try 'sq migrate chlog --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Missing argument 'vfrom..vto'.                                               │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


# --------------------------------------------------------------------------- rename-status


@pytest.mark.covers("migrate rename-status", "type")
@pytest.mark.covers("migrate rename-status", "old-status")
@pytest.mark.covers("migrate rename-status", "new-status")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_rename_status_relabels_the_items_of_the_type_at_that_status(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-status", "task", "Draft", "Ready"])
    assert (result.exit_code, result.output) == (
        0,
        "rename-status done: task: Draft → Ready, 1 item(s) renamed\n" + CHECK_HINT,
    )
    assert (await _shown(invoke, "task", 3))["status"] == "Ready"
    assert (await _shown(invoke, "feature", 2))["status"] == "Draft"


@pytest.mark.covers("migrate rename-status", "old-status")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_rename_status_refuses_a_status_outside_the_lifecycle(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-status", "task", "Draft", "Bogus"])
    assert (result.exit_code, result.output) == (
        1,
        "error: 'Bogus' is not a state of task's lifecycle "
        "(states: Blocked, Cancelled, Done, Draft, InProgress, InReview, Ready)\n",
    )
    assert (await _shown(invoke, "task", 3))["status"] == "Draft"


@pytest.mark.covers("migrate rename-status", "type")
async def test_rename_status_refuses_a_type_the_spec_does_not_declare(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-status", "nosuch", "Draft", "Ready"])
    assert (result.exit_code, result.output) == (
        1,
        "error: 'nosuch' is not declared in the active spec\n",
    )


# ----------------------------------------------------------------------------- rename-type


@pytest.mark.covers("migrate rename-type", "old-type")
@pytest.mark.covers("migrate rename-type", "new-type")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_rename_type_moves_the_items_to_the_new_type_and_prefix(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-type", "task", "bug"])
    assert (result.exit_code, result.output) == (
        0,
        "rename-type done: task → bug, 1 item(s) renamed; index rebuilt\n" + CHECK_HINT,
    )
    moved = await _shown(invoke, "bug", 3)
    assert (moved["id"], moved["title"], moved["parent"]) == (
        "BUG-3",
        "Build the query parser",
        "FEAT-2",
    )
    assert [s["local_id"] for s in moved["subentities"]] == ["ST1", "ST2"]


@pytest.mark.covers("migrate rename-type", "old-type")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_rename_type_refuses_a_roster_type(populated_project, invoke) -> None:
    result = await invoke(["migrate", "rename-type", "task", "role"])
    assert (result.exit_code, result.output) == (
        1,
        "error: 'role' is a reserved roster type (role/skill/operator) and cannot be renamed\n",
    )


@pytest.mark.covers("migrate rename-type", "old-type", "new-type")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_rename_type_refuses_to_rename_a_type_to_itself(populated_project, invoke) -> None:
    result = await invoke(["migrate", "rename-type", "task", "task"])
    assert (result.exit_code, result.output) == (1, "error: cannot rename 'task' to itself\n")


@pytest.mark.covers("migrate rename-type", "old-type")
@pytest.mark.bundled_only("refuses a bundled type name the squad's spec does not declare")
async def test_rename_type_refuses_a_type_the_spec_does_not_declare(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-type", "task", "nosuch"])
    assert (result.exit_code, result.output) == (
        1,
        "error: 'nosuch' is not declared in the active spec\n",
    )


@pytest.mark.covers("migrate rename-type", "new-type")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_rename_type_refuses_a_move_that_leaves_a_child_with_an_invalid_parent(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-type", "feature", "bug"])
    assert (result.exit_code, result.output) == (
        1,
        "error: cannot rename feature to bug: child item(s) TASK-3 would have an invalid "
        "parent type. Re-parent or remove those children first.\n",
    )
    assert (await _shown(invoke, "feature", 2))["id"] == "FEAT-2"


# ---------------------------------------------------------------------------------- repad


@pytest.mark.covers("migrate repad", "width")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_repad_widens_the_item_files_numbers_and_leaves_the_ids(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "repad", "8"])
    assert (result.exit_code, result.output) == (
        0,
        "repad done: padding 6 → 8; 4 file(s) renamed; index rebuilt\n" + CHECK_HINT,
    )
    task = await _shown(invoke, "task", 3)
    assert (task["id"], task["path"]) == ("TASK-3", "tasks/TASK-00000003-build-the-query-parser.md")


@pytest.mark.covers("migrate repad", "width")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_repad_refuses_a_width_that_does_not_exceed_the_current_one(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "repad", "6"])
    assert (result.exit_code, result.output) == (
        1,
        "error: new padding 6 must be greater than the current padding 6; padding can only "
        "increase (one-way format bump)\n",
    )
    task = await _shown(invoke, "task", 3)
    assert task["path"] == "tasks/TASK-000003-build-the-query-parser.md"


@pytest.mark.covers("migrate repad", "width")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_repad_refuses_a_width_above_the_maximum_and_renames_nothing(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "repad", "99"])
    assert (result.exit_code, result.output) == (
        1,
        "error: new padding 99 is above the maximum of 32 digits; padding can only increase, "
        "so a width that wide could not be taken back\n",
    )
    task = await _shown(invoke, "task", 3)
    assert task["path"] == "tasks/TASK-000003-build-the-query-parser.md"


@pytest.mark.covers("migrate repad", "width")
async def test_repad_refuses_a_width_that_is_not_an_integer(populated_project, invoke) -> None:
    result = await invoke(["migrate", "repad", "wide"])
    assert (result.exit_code, result.output) == (
        2,
        "Usage: sq migrate repad [OPTIONS] {width}\nTry 'sq migrate repad --help' for help.\n"
        "╭─ Error ──────────────────────────────────────────────────────────────────────╮\n"
        "│ Invalid value for 'width': 'wide' is not a valid int.                        │\n"
        "╰──────────────────────────────────────────────────────────────────────────────╯\n",
    )


@pytest.mark.covers("migrate help", "--json")
async def test_help_json_lists_each_migration_with_its_manual_steps(invoke) -> None:
    output = await printed(invoke, ["migrate", "help", "--json"])
    assert output == json_text(documents.MIGRATIONS)


@pytest.mark.covers("migrate chlog", "--json")
async def test_chlog_json_prints_the_range_and_its_migrations_with_manual_steps(invoke) -> None:
    result = await invoke(["migrate", "chlog", "v0.10.0..v0.11.0", "--json"])
    assert result.exit_code == 0, result.output
    assert (
        result.output
        == json.dumps(
            {"from_version": "0.10.0", "to_version": "0.11.0", "migrations": []}, indent=2
        )
        + "\n"
    )


@pytest.mark.covers("migrate up", "--json")
async def test_up_json_reports_each_migration_run_on_an_older_squad(
    tmp_path, monkeypatch, invoke
) -> None:
    monkeypatch.chdir(shutil.copytree(OLD_SQUAD, tmp_path / "old"))
    result = await invoke(["migrate", "up", "--json"])
    shipped = {m["version"]: m for m in documents.MIGRATIONS["migrations"]}

    def applied(version: str, changed: int, reports: list[str]) -> dict[str, Any]:
        entry = shipped[version]
        return {
            "version": version,
            "from_schema": entry["from_schema"],
            "to_schema": entry["to_schema"],
            "summary": entry["summary"],
            "changed": changed,
            "reports": reports,
            "skipped": [],
            "manual": bool(entry["manual"]),
        }

    assert (result.exit_code, result.output) == (
        0,
        json_text(
            {
                "schema_version": SCHEMA_VERSION,
                "applied": [
                    applied("0.15.0", 4, []),
                    applied(
                        "0.16.0",
                        5,
                        [
                            "0 comment header(s) rewritten in 0 file(s); 0 already carried a slug",
                            "5 file(s) flattened; 0 key(s) lifted (none); 0 skill description(s) "
                            "dropped; 2 `path:` key(s) removed",
                            "0 operator title(s) set from the stored full name",
                            "0 dropped skill description(s) differed from the one kept",
                            "1 role(s) stamped origin project",
                            "2 skill(s) stamped origin system",
                            "2 skill(s) stamped origin project",
                            "4 skill(s) given a discussion region",
                        ],
                    ),
                    applied(
                        "0.17.0",
                        0,
                        [
                            "dev-agent: no catalog entry and no role file; define it with "
                            "`sq role dev-agent update --job-title … --desc … --mission …`"
                        ],
                    ),
                    applied("0.19.0", 1, []),
                    applied(
                        "0.20.0",
                        4,
                        [
                            "removed skill SKILL-9 sq-contract",
                            "removed skill SKILL-10 sq-milestone",
                            "renamed skill SKILL-7 greeting to sq-greeting",
                            "renamed skill SKILL-8 squads to sq-how-to",
                        ],
                    ),
                ],
                "reconciled": {"indexed": [], "missing": []},
                "config_dropped": ["squads_version"],
                "notice": "stripped retired regions from 3 item files — review the diff",
                "unreadable": [],
                "manual_span": "v0.14.0..v0.20.0",
                "agents_refreshed": True,
            }
        ),
    )


@pytest.mark.covers("migrate repad", "--json")
async def test_repad_json_prints_the_padding_before_and_after(populated_project, invoke) -> None:
    result = await invoke(["migrate", "repad", "8", "--json"])
    assert (result.exit_code, result.output) == (
        0,
        json_text({"previous": 6, "width": 8, "renamed": 4}),
    )


@pytest.mark.covers("migrate rename-type", "--json")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_rename_type_json_prints_the_items_moved_and_their_new_ids(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-type", "task", "bug", "--json"])
    assert (result.exit_code, result.output) == (
        0,
        json_text(
            {
                "old_type": "task",
                "new_type": "bug",
                "renamed": 1,
                "ids": [{"old": "TASK-3", "new": "BUG-3"}],
            }
        ),
    )


@pytest.mark.covers("migrate rename-status", "--json")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_rename_status_json_prints_how_many_items_were_relabelled(
    populated_project, invoke
) -> None:
    result = await invoke(["migrate", "rename-status", "task", "Draft", "Ready", "--json"])
    assert (result.exit_code, result.output) == (
        0,
        json_text({"type": "task", "old_status": "Draft", "new_status": "Ready", "renamed": 1}),
    )


# ---------------------------------------------------------------------------- rename-field

MOVED_WEIGHT = "rename-field done: weight → impact, 1 item(s) and 1 sub-entity entry(ies) moved\n"


def _squad_bytes(paths) -> dict[str, bytes]:
    """Every file under the squad folder, by relative path."""
    return {
        str(p.relative_to(paths.squad_dir)): p.read_bytes()
        for p in sorted(paths.squad_dir.rglob("*"))
        if p.is_file()
    }


def _item_file(paths, folder: str, number: int) -> Path:
    (found,) = (paths.squad_dir / folder).glob(f"*-{number:06d}-*.md")
    return found


def _declare_impact_on_jobs(paths) -> None:
    """The override squad's jobs also declare `impact`, the field its actions carry."""
    override = paths.squad_dir / ".overrides" / "workflow.toml"
    text = override.read_text(encoding="utf-8")
    field = '{ code = "work_size", label = "Work size", collection = "size", required = false },'
    assert field in text
    override.write_text(
        text.replace(
            field, field + '\n  { code = "impact", label = "Impact", collection = "impact" },'
        ),
        encoding="utf-8",
    )


async def _store_job_values_under_an_old_key(paths, invoke, value: str = "large") -> Path:
    """The job and its first action hold *value* under `weight`, a key the spec does not declare."""
    job = _item_file(paths, "jobs", 6)
    text = job.read_text(encoding="utf-8")
    assert "  impact: large\n" in text
    text = text.replace("  impact: large\n", f"  weight: {value}\n")
    text = text.replace("work_size: m\n", f"work_size: m\nweight: {value}\n")
    job.write_text(text, encoding="utf-8")
    await invoke(["repair"])
    return job


@pytest.mark.covers("migrate rename-field", "old")
@pytest.mark.covers("migrate rename-field", "new")
async def test_rename_field_moves_the_value_on_the_item_and_on_its_entries(
    override_project, invoke
) -> None:
    _declare_impact_on_jobs(override_project)
    job = await _store_job_values_under_an_old_key(override_project, invoke)

    result = await invoke(["migrate", "rename-field", "weight", "impact"])

    assert (result.exit_code, result.output) == (0, MOVED_WEIGHT + CHECK_HINT)
    frontmatter = re.sub(
        r"(created_at|updated_at): '[^']*'",
        "stamp: T",
        job.read_text(encoding="utf-8").split("---\n")[1],
    )
    assert frontmatter == (
        "id: JOB-6\nsequence_id: 6\ntype: job\ntitle: Write the onboarding guide\n"
        "status: Draft\nparent: INI-5\nauthor: manager\n"
        "subentities:\n- local_id: AC1\n  title: Draft the outline\n  status: Todo\n"
        "  impact: large\n"
        "- local_id: AC2\n  title: Record the walkthrough\n  status: Deferred\n"
        "  deferred_to: REC-7\n"
        "stamp: T\nstamp: T\n"
        "owner_team: docs\nneeds_review: true\nwork_size: m\nimpact: large\n"
    )
    checked = await invoke(["check", "--json"])
    assert (checked.exit_code, checked.output) == (0, "[]\n")


@pytest.mark.covers("migrate rename-field", "new")
async def test_rename_field_refuses_a_key_the_holder_does_not_declare(
    override_project, invoke
) -> None:
    _declare_impact_on_jobs(override_project)
    await _store_job_values_under_an_old_key(override_project, invoke)
    before = _squad_bytes(override_project)

    result = await invoke(["migrate", "rename-field", "weight", "urgency"])

    assert (result.exit_code, result.output) == (
        1,
        "error: cannot rename field 'weight' to 'urgency': JOB-6: 'job' does not declare "
        "'urgency'; AC1 of JOB-6: 'action' does not declare 'urgency' "
        "(limit the move with --type or --kind)\n",
    )
    assert _squad_bytes(override_project) == before


@pytest.mark.covers("migrate rename-field", "new")
async def test_rename_field_refuses_a_holder_that_already_holds_the_new_key(
    override_project, invoke
) -> None:
    _declare_impact_on_jobs(override_project)
    job = await _store_job_values_under_an_old_key(override_project, invoke)
    text = job.read_text(encoding="utf-8")
    job.write_text(text.replace("  weight: large\n", "  weight: large\n  impact: small\n"))
    await invoke(["repair"])
    before = _squad_bytes(override_project)

    result = await invoke(["migrate", "rename-field", "weight", "impact"])

    assert (result.exit_code, result.output) == (
        1,
        "error: cannot rename field 'weight' to 'impact': AC1 of JOB-6 already holds 'impact' "
        "(limit the move with --type or --kind)\n",
    )
    assert _squad_bytes(override_project) == before


@pytest.mark.covers("migrate rename-field", "old")
async def test_rename_field_refuses_a_value_the_new_field_does_not_accept(
    override_project, invoke
) -> None:
    _declare_impact_on_jobs(override_project)
    await _store_job_values_under_an_old_key(override_project, invoke, value="huge")
    before = _squad_bytes(override_project)

    result = await invoke(["migrate", "rename-field", "weight", "impact"])

    assert (result.exit_code, result.output) == (
        1,
        "error: cannot rename field 'weight' to 'impact': JOB-6: 'huge' is not a value of "
        "'impact' (collection 'impact'); AC1 of JOB-6: 'huge' is not a value of 'impact' "
        "(collection 'impact') (limit the move with --type or --kind)\n",
    )
    assert _squad_bytes(override_project) == before


@pytest.mark.covers("migrate rename-field", "--json")
async def test_rename_field_json_prints_how_many_items_and_entries_moved(
    override_project, invoke
) -> None:
    _declare_impact_on_jobs(override_project)
    await _store_job_values_under_an_old_key(override_project, invoke)

    result = await invoke(["migrate", "rename-field", "weight", "impact", "--json"])

    assert (result.exit_code, result.output) == (
        0,
        json_text({"old": "weight", "new": "impact", "items": 1, "entries": 1}),
    )


@pytest.mark.covers("migrate rename-field", "old")
@pytest.mark.bundled_only("migrates a squad written in the bundled vocabulary")
async def test_rename_field_moves_an_item_value_on_the_bundled_squad(
    populated_project, invoke
) -> None:
    task = _item_file(populated_project, "tasks", 3)
    task.write_text(
        task.read_text(encoding="utf-8").replace(
            "author: manager\n", "author: manager\nprio: high\n"
        )
    )
    await invoke(["repair"])

    result = await invoke(["migrate", "rename-field", "prio", "priority"])

    assert (result.exit_code, result.output) == (
        0,
        "rename-field done: prio → priority, 1 item(s) and 0 sub-entity entry(ies) moved\n"
        + CHECK_HINT,
    )
    assert (await _shown(invoke, "task", 3))["priority"] == "high"


@pytest.mark.covers("migrate rename-field", "new")
async def test_rename_field_refuses_to_rename_a_key_to_itself(override_project, invoke) -> None:
    before = _squad_bytes(override_project)

    result = await invoke(["migrate", "rename-field", "impact", "impact"])

    assert (result.exit_code, result.output) == (
        1,
        "error: cannot rename field 'impact' to itself\n",
    )
    assert _squad_bytes(override_project) == before


@pytest.mark.covers("migrate rename-field", "old")
async def test_rename_field_logs_one_line_and_one_system_comment_per_changed_item(
    override_project, invoke
) -> None:
    _declare_impact_on_jobs(override_project)
    await _store_job_values_under_an_old_key(override_project, invoke)
    await invoke(["migrate", "rename-field", "weight", "impact"])

    logged = await invoke(["reflog", "--json", "--op", "rename-field"])
    shown = await invoke(["job", "6", "show", "--comments"])

    assert json.loads(logged.output) == [
        {
            "v": SCHEMA_VERSION,
            "ts": "2026-06-07T10:00:00Z",
            "actor": "system",
            "op": "rename-field",
            "target": "JOB-6",
            "delta": {"old": "weight", "new": "impact"},
            "session_id": None,
            "parent_session_id": None,
        }
    ]
    header, bullet = shown.output.strip().splitlines()[-2:]
    assert re.fullmatch(r"--- \w+ \[2026-06-07T10:00:00Z\] squads ---", header)
    assert bullet == "- field renamed weight → impact"


@pytest.mark.covers("migrate rename-field", "new")
async def test_rename_field_refuses_an_entry_on_a_type_that_hosts_no_kind(
    override_project, invoke
) -> None:
    record = _item_file(override_project, "records", 7)
    text = record.read_text(encoding="utf-8")
    record.write_text(
        text.replace(
            "created_at:",
            "subentities:\n- local_id: X1\n  title: Stray\n  status: Todo\n"
            "  weight: large\ncreated_at:",
            1,
        )
    )
    await invoke(["repair"])
    before = _squad_bytes(override_project)

    result = await invoke(["migrate", "rename-field", "weight", "impact"])

    assert (result.exit_code, result.output) == (
        1,
        "error: cannot rename field 'weight' to 'impact': X1 of REC-7: record hosts no "
        "sub-entity kind (limit the move with --type or --kind)\n",
    )
    assert _squad_bytes(override_project) == before


# ---------------------------------------------------------------------------- rename-kind


def _redeclare_outcome_as_goal(paths, *, prefix: str = "OC", plural: str = "outcomes") -> None:
    """The override squad's outcome kind is declared as `goal`, with *prefix* and *plural*."""
    override = paths.squad_dir / ".overrides" / "workflow.toml"
    override.write_text(
        override.read_text(encoding="utf-8")
        .replace('subentity_kind = "outcome"', 'subentity_kind = "goal"')
        .replace("[subentity_kinds.outcome]", "[subentity_kinds.goal]")
        .replace('["outcome", "action"]', '["goal", "action"]')
        .replace('plural = "outcomes"', f'plural = "{plural}"')
        .replace('local_prefix = "OC"', f'local_prefix = "{prefix}"'),
        encoding="utf-8",
    )


async def _map_the_first_action_to_the_first_outcome(paths, invoke) -> None:
    job = _item_file(paths, "jobs", 6)
    job.write_text(
        job.read_text(encoding="utf-8").replace(
            "  status: Todo\n  impact: large\n", "  status: Todo\n  maps_to: OC1\n  impact: large\n"
        ),
        encoding="utf-8",
    )
    await invoke(["repair"])


RENAMED_INITIATIVE = (
    "---\nid: INI-5\nsequence_id: 5\ntype: initiative\ntitle: Open the beta\nstatus: Draft\n"
    "author: manager\nsubentities:\n- local_id: GO1\n  title: Fifty active teams\n"
    "  status: Todo\n- local_id: GO2\n  title: A published roadmap\n  status: Todo\n"
    "created_at: '2026-06-07T10:00:00Z'\nupdated_at: '2026-06-07T10:00:00Z'\n"
    "horizon: '2026-12-01'\nthemes:\n- growth\nurgency: now\n---\n"
    "<!-- sq:body -->\n## Description\n\n_TODO: describe this initiative._\n"
    "<!-- sq:body:end -->\n\n## Discussion\n\n<!-- sq:discussion -->\n"
    "- [2026-06-07T10:00:00Z] `squads` squads:\n"
    "  - kind spellings brought from outcome to goal\n<!-- sq:discussion:end -->\n\n\n"
    "## Desired Outcomes\n\n<!-- sq:goals -->\n\n"
    "<!-- sq:goal:GO1 -->\n### GO1 — Fifty active teams\n\n<!-- sq:goal:GO1:body -->\n"
    "Measured weekly.\n<!-- sq:goal:GO1:body:end -->\n\n#### Discussion\n\n"
    "<!-- sq:goal:GO1:discussion -->\n<!-- sq:goal:GO1:discussion:end -->\n"
    "<!-- sq:goal:GO1:end -->\n\n"
    "<!-- sq:goal:GO2 -->\n### GO2 — A published roadmap\n\n<!-- sq:goal:GO2:body -->\n"
    "Public.\n<!-- sq:goal:GO2:body:end -->\n\n#### Discussion\n\n"
    "<!-- sq:goal:GO2:discussion -->\n<!-- sq:goal:GO2:discussion:end -->\n"
    "<!-- sq:goal:GO2:end -->\n<!-- sq:goals:end -->\n"
)
RENAMED_INITIATIVE_SHOW = (
    "╭───────────────────────────────────────────────╮\n"
    "│ INI-5  (initiative)                           │\n"
    "│ title: Open the beta                          │\n"
    "│ status: Draft                                 │\n"
    "│ urgency: 🔴 now                               │\n"
    "│ horizon: 2026-12-01                           │\n"
    "│ themes: growth                                │\n"
    "│ author: manager                               │\n"
    "│ file: initiatives/INI-000005-open-the-beta.md │\n"
    "╰───────────────────────────────────────────────╯\n\n"
    "## Description\n\n_TODO: describe this initiative._\n\n"
    "Desired outcome  Status  Assignee  Title              \n"
    "GO1              Todo              Fifty active teams \n"
    "GO2              Todo              A published roadmap\n"
)


@pytest.mark.covers("migrate rename-kind", "old")
@pytest.mark.covers("migrate rename-kind", "new")
async def test_rename_kind_keeps_the_prefix_and_the_bodies_stay_reachable(
    override_project, invoke
) -> None:
    await _map_the_first_action_to_the_first_outcome(override_project, invoke)
    _redeclare_outcome_as_goal(override_project)

    result = await invoke(["migrate", "rename-kind", "outcome", "goal"])

    assert (result.exit_code, result.output) == (
        0,
        "rename-kind done: outcome → goal, 1 item(s) rewritten\n" + CHECK_HINT,
    )
    shown = await invoke(["initiative", "5", "goal", "1", "show"])
    assert shown.output.splitlines()[:5] == [
        "OC1 — Fifty active teams  (goal)",
        "  status: Todo",
        "",
        "Measured weekly.",
        "",
    ]
    mapped = await invoke(["job", "6", "action", "1", "show"])
    assert mapped.output.splitlines()[1] == "  status: Todo   Impact: large   Desired outcome: OC1"
    checked = await invoke(["check", "--json"])
    assert (checked.exit_code, checked.output) == (0, "[]\n")


@pytest.mark.covers("migrate rename-kind", "new")
async def test_rename_kind_moves_the_prefix_the_plural_and_the_mappings(
    override_project, invoke
) -> None:
    await _map_the_first_action_to_the_first_outcome(override_project, invoke)
    _redeclare_outcome_as_goal(override_project, prefix="GO", plural="goals")

    result = await invoke(["migrate", "rename-kind", "outcome", "goal"])

    assert (result.exit_code, result.output) == (
        0,
        "rename-kind done: outcome → goal, 2 item(s) rewritten\n" + CHECK_HINT,
    )
    initiative = _item_file(override_project, "initiatives", 5).read_text(encoding="utf-8")
    assert initiative == RENAMED_INITIATIVE
    shown = await invoke(["initiative", "5", "goal", "1", "show"])
    assert shown.output.splitlines()[:4] == [
        "GO1 — Fifty active teams  (goal)",
        "  status: Todo",
        "",
        "Measured weekly.",
    ]
    mapped = await invoke(["job", "6", "action", "1", "show"])
    assert mapped.output.splitlines()[1] == "  status: Todo   Impact: large   Desired outcome: GO1"
    table = await invoke(["initiative", "5", "show"])
    assert table.output == RENAMED_INITIATIVE_SHOW
    checked = await invoke(["check", "--json"])
    assert (checked.exit_code, checked.output) == (0, "[]\n")


@pytest.mark.covers("migrate rename-kind", "new")
async def test_rename_kind_refuses_a_kind_the_spec_does_not_declare(
    override_project, invoke
) -> None:
    before = _squad_bytes(override_project)

    result = await invoke(["migrate", "rename-kind", "outcome", "nosuch"])

    assert (result.exit_code, result.output) == (
        1,
        "error: 'nosuch' is not a sub-entity kind the active spec declares\n",
    )
    assert _squad_bytes(override_project) == before


@pytest.mark.covers("migrate rename-kind", "new")
async def test_rename_kind_refuses_a_type_that_does_not_host_the_kind(
    override_project, invoke
) -> None:
    before = _squad_bytes(override_project)

    result = await invoke(["migrate", "rename-kind", "outcome", "action"])

    assert (result.exit_code, result.output) == (
        1,
        "error: cannot rename kind 'outcome' to 'action': INI-5: initiative does not host "
        "'action'\n",
    )
    assert _squad_bytes(override_project) == before


def _rewrite_in(path: Path, old: str, new: str) -> None:
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


@pytest.mark.covers("migrate rename-kind", "old")
async def test_rename_kind_refuses_two_ids_that_would_become_the_same_id(
    override_project, invoke
) -> None:
    _rewrite_in(_item_file(override_project, "initiatives", 5), "OC2", "GO1")
    await invoke(["repair"])
    _redeclare_outcome_as_goal(override_project, prefix="GO")
    before = _squad_bytes(override_project)

    result = await invoke(["migrate", "rename-kind", "outcome", "goal"])

    assert (result.exit_code, result.output) == (
        1,
        "error: cannot rename kind 'outcome' to 'goal': INI-5: OC1 and GO1 would both become GO1\n",
    )
    assert _squad_bytes(override_project) == before


@pytest.mark.covers("migrate rename-kind", "old")
async def test_rename_kind_brings_a_stray_prefix_among_declared_ones_to_the_declaration(
    override_project, invoke
) -> None:
    _rewrite_in(_item_file(override_project, "initiatives", 5), "OC2", "XX2")
    await invoke(["repair"])
    mismatch = {
        "level": "warn",
        "item": "INI-5",
        "message": "XX2 does not start with prefix 'OC' of kind 'outcome'; "
        "`sq migrate rename-kind outcome outcome` brings it to the declaration",
        "rule": "subentity_kind_mismatch",
    }
    reported = await invoke(["check", "--json"])
    assert (reported.exit_code, json.loads(reported.output)) == (0, [mismatch])

    result = await invoke(["migrate", "rename-kind", "outcome", "outcome"])

    assert (result.exit_code, result.output) == (
        0,
        "rename-kind done: outcome → outcome, 1 item(s) rewritten\n" + CHECK_HINT,
    )
    fixed = await invoke(["check", "--json"])
    assert (fixed.exit_code, fixed.output) == (0, "[]\n")
    shown = await invoke(["initiative", "5", "outcome", "2", "show"])
    assert shown.output.splitlines()[0] == "OC2 — A published roadmap  (outcome)"


@pytest.mark.covers("migrate rename-kind", "new")
async def test_a_prefix_change_then_add_then_rename_gives_distinct_ids_and_a_clean_check(
    override_project, invoke
) -> None:
    await invoke(["create", "initiative", "Second", "--author", "manager"])
    await invoke(["initiative", "8", "add-outcome", "First", "-m", "One."])
    _rewrite_in(
        override_project.squad_dir / ".overrides" / "workflow.toml",
        'local_prefix = "OC"',
        'local_prefix = "GO"',
    )
    added = await invoke(["initiative", "8", "add-outcome", "Next", "-m", "Two."])
    assert added.exit_code == 0, added.output

    reported = await invoke(["check", "--json"])
    assert sorted(
        (i["item"], i["message"].split(" does")[0]) for i in json.loads(reported.output)
    ) == [
        ("INI-5", "OC1"),
        ("INI-5", "OC2"),
        ("INI-8", "OC1"),
    ]

    result = await invoke(["migrate", "rename-kind", "outcome", "outcome"])

    assert (result.exit_code, result.output) == (
        0,
        "rename-kind done: outcome → outcome, 2 item(s) rewritten\n" + CHECK_HINT,
    )
    fixed = await invoke(["check", "--json"])
    assert (fixed.exit_code, fixed.output) == (0, "[]\n")
    second = await invoke(["initiative", "8", "outcome", "2", "show"])
    assert second.output.splitlines()[0] == "GO2 — Next  (outcome)"


@pytest.mark.covers("migrate rename-kind", "old")
async def test_rename_kind_refuses_an_item_with_a_missing_marker_pair(
    override_project, invoke
) -> None:
    initiative = _item_file(override_project, "initiatives", 5)
    initiative.write_text(
        initiative.read_text(encoding="utf-8").replace("<!-- sq:outcome:OC2:end -->\n", ""),
        encoding="utf-8",
    )
    _redeclare_outcome_as_goal(override_project, prefix="GO")
    before = _squad_bytes(override_project)

    result = await invoke(["migrate", "rename-kind", "outcome", "goal"])

    assert (result.exit_code, result.output) == (
        1,
        "error: cannot rename kind 'outcome' to 'goal': INI-5: no marker pair for OC2\n",
    )
    assert _squad_bytes(override_project) == before


@pytest.mark.covers("migrate rename-kind", "--json")
async def test_rename_kind_writes_nothing_when_the_spellings_already_match(
    override_project, invoke
) -> None:
    before = _squad_bytes(override_project)

    result = await invoke(["migrate", "rename-kind", "outcome", "outcome", "--json"])

    assert (result.exit_code, result.output) == (
        0,
        json_text({"old": "outcome", "new": "outcome", "items": 0}),
    )
    assert _squad_bytes(override_project) == before


@pytest.mark.covers("migrate rename-kind", "old")
async def test_rename_kind_logs_and_comments_on_each_item_it_rewrites(
    override_project, invoke
) -> None:
    await _map_the_first_action_to_the_first_outcome(override_project, invoke)
    _redeclare_outcome_as_goal(override_project, prefix="GO", plural="goals")
    await invoke(["migrate", "rename-kind", "outcome", "goal"])

    logged = await invoke(["reflog", "--json", "--op", "rename-kind"])
    shown = await invoke(["initiative", "5", "show", "--comments"])

    assert [(e["target"], e["delta"]) for e in json.loads(logged.output)] == [
        ("INI-5", {"old": "outcome", "new": "goal"}),
        ("JOB-6", {"old": "outcome", "new": "goal"}),
    ]
    header, bullet = shown.output.strip().splitlines()[-2:]
    assert re.fullmatch(r"--- \w+ \[2026-06-07T10:00:00Z\] squads ---", header)
    assert bullet == "- kind spellings brought from outcome to goal"


JOB_FRONTMATTER = (
    "id: JOB-6\nsequence_id: 6\ntype: job\ntitle: Write the onboarding guide\n"
    "status: Draft\nparent: INI-5\nauthor: manager\n"
    "subentities:\n- local_id: AC1\n  title: Draft the outline\n  status: Todo\n"
    "  {entry_key}: large\n"
    "- local_id: AC2\n  title: Record the walkthrough\n  status: Deferred\n"
    "  deferred_to: REC-7\n"
    "created_at: '2026-06-07T10:00:00Z'\nupdated_at: '2026-06-07T10:00:00Z'\n"
    "owner_team: docs\nneeds_review: true\nwork_size: m\n{item_tail}: large\n"
)


def _frontmatter(path: Path) -> str:
    """The frontmatter block of the item file at *path*."""
    return path.read_text(encoding="utf-8").split("---\n")[1]


@pytest.mark.covers("migrate rename-field", "--kind")
async def test_rename_field_limited_to_a_kind_leaves_the_item_key_in_place(
    override_project, invoke
) -> None:
    job = await _store_job_values_under_an_old_key(override_project, invoke)

    result = await invoke(["migrate", "rename-field", "weight", "impact", "--kind", "action"])

    assert (result.exit_code, result.output) == (
        0,
        "rename-field done: weight → impact, 0 item(s) and 1 sub-entity entry(ies) moved\n"
        + CHECK_HINT,
    )
    assert _frontmatter(job) == JOB_FRONTMATTER.format(entry_key="impact", item_tail="weight")


@pytest.mark.covers("migrate rename-field", "--type")
async def test_rename_field_limited_to_a_type_leaves_the_entries_in_place(
    override_project, invoke
) -> None:
    _declare_impact_on_jobs(override_project)
    job = await _store_job_values_under_an_old_key(override_project, invoke)

    result = await invoke(["migrate", "rename-field", "weight", "impact", "--type", "job"])

    assert (result.exit_code, result.output) == (
        0,
        "rename-field done: weight → impact, 1 item(s) and 0 sub-entity entry(ies) moved\n"
        + CHECK_HINT,
    )
    assert _frontmatter(job) == JOB_FRONTMATTER.format(entry_key="weight", item_tail="impact")


@pytest.mark.covers("migrate rename-field", "--kind")
async def test_rename_field_refuses_a_scope_the_spec_does_not_declare(
    override_project, invoke
) -> None:
    before = _squad_bytes(override_project)

    kind = await invoke(["migrate", "rename-field", "weight", "impact", "--kind", "nosuch"])
    item_type = await invoke(["migrate", "rename-field", "weight", "impact", "--type", "nosuch"])

    assert [(r.exit_code, r.output) for r in (kind, item_type)] == [
        (1, "error: --kind 'nosuch' is not a sub-entity kind the active spec declares\n"),
        (1, "error: --type 'nosuch' is not an item type the active spec declares\n"),
    ]
    assert _squad_bytes(override_project) == before


@pytest.mark.covers("check", "--json")
async def test_check_reports_a_changed_local_prefix_without_any_selection(
    override_project, invoke
) -> None:
    override = override_project.squad_dir / ".overrides" / "workflow.toml"
    override.write_text(
        override.read_text(encoding="utf-8").replace('local_prefix = "OC"', 'local_prefix = "GO"'),
        encoding="utf-8",
    )

    checked = await invoke(["check", "--json"])

    verb = "`sq migrate rename-kind outcome outcome` brings it to the declaration"
    assert (checked.exit_code, json.loads(checked.output)) == (
        0,
        [
            {
                "level": "warn",
                "item": "INI-5",
                "message": f"{local} does not start with prefix 'GO' of kind 'outcome'; {verb}",
                "rule": "subentity_kind_mismatch",
            }
            for local in ("OC1", "OC2")
        ],
    )
    await invoke(["migrate", "rename-kind", "outcome", "outcome"])
    fixed = await invoke(["check", "--json"])
    assert (fixed.exit_code, fixed.output) == (0, "[]\n")


@pytest.mark.covers("migrate rename-field", "--type")
async def test_rename_field_refusal_under_a_scope_does_not_suggest_a_scope(
    override_project, invoke
) -> None:
    await _store_job_values_under_an_old_key(override_project, invoke)
    before = _squad_bytes(override_project)

    result = await invoke(["migrate", "rename-field", "weight", "urgency", "--type", "job"])

    assert (result.exit_code, result.output) == (
        1,
        "error: cannot rename field 'weight' to 'urgency': JOB-6: 'job' does not declare "
        "'urgency'\n",
    )
    assert _squad_bytes(override_project) == before
