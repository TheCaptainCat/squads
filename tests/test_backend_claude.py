import json

import yaml

from squads._sections import split_frontmatter


def _read_pointer(project, slug):
    return (project.root / ".claude" / "agents" / f"{slug}.md").read_text(encoding="utf-8")


def test_init_creates_claude_pointers_and_managed_files(project):
    # minimal roster => manager only
    text = _read_pointer(project, "manager")
    fm, body = split_frontmatter(text)
    assert fm["name"] == "manager"  # lowercase-hyphen, Claude requirement
    assert isinstance(fm["description"], str)
    # body points at the real definition under the squad folder
    assert "squads/agents/roles/ROLE-000001-manager.md" in body
    assert "Catherine Manager" in body

    # the squads skill is a thin pointer in .claude → real body under the squad folder
    skill_pointer = (project.root / ".claude" / "skills" / "squads" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "@squads/agents/skills/squads.md" in skill_pointer
    skill_body = (project.squad_dir / "agents" / "skills" / "squads.md").read_text(encoding="utf-8")
    assert "sq create" in skill_body
    assert "squads:version:" in skill_body

    claude_md = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "<!-- squads:start -->" in claude_md
    assert "Catherine Manager" in claude_md  # default role on greeting
    # the orchestration loop is taught: delegate by spawning specialists via the Task tool
    assert "Orchestration loop" in claude_md
    assert "Task tool" in claude_md and "subagent_type" in claude_md


def test_claude_md_has_operators_section_and_session_start(project, svc):
    # the people roster + session-start ritual render even with no operators registered yet
    before = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Operators (people)" in before
    assert "_None registered yet._" in before
    assert "you MUST ask" in before and "sq list -t operator" in before
    # registering one lists them by name + op- slug
    svc.add_operator("Pierre Chat")
    after = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Pierre Chat" in after and "op-pierre" in after
    assert "_None registered yet._" not in after


def test_manager_role_describes_the_loop(project):
    # the manager's role body teaches delegating + driving features to done (backend-agnostic)
    body = (project.squad_dir / "agents" / "roles" / "ROLE-000001-manager.md").read_text(
        encoding="utf-8"
    )
    assert "Delegate" in body and "until done" in body


def test_pointer_frontmatter_is_valid_yaml(project):
    fm, _ = split_frontmatter(_read_pointer(project, "manager"))
    # round-trips through a real YAML parser
    assert yaml.safe_load(yaml.safe_dump(fm)) == fm
    assert fm["name"] == fm["name"].lower()


def test_settings_merge_does_not_clobber(project, svc):
    settings = project.root / ".claude" / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["permissions"]["allow"].append("Bash(git status)")
    data["customKey"] = 123
    settings.write_text(json.dumps(data), encoding="utf-8")
    # re-run scaffold (idempotent merge)
    svc._backend().ensure_scaffold(svc._ctx)
    merged = json.loads(settings.read_text(encoding="utf-8"))
    assert merged["customKey"] == 123  # preserved
    assert "Bash(git status)" in merged["permissions"]["allow"]  # preserved
    assert "Bash(sq:*)" in merged["permissions"]["allow"]  # still present


def test_claude_md_injection_idempotent(project, svc):
    before = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    svc.refresh_managed()
    after = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert before.count("<!-- squads:start -->") == 1
    assert after.count("<!-- squads:start -->") == 1


def test_claude_md_impersonation_uses_sq_command_not_path(project, svc):
    """Generated CLAUDE.md section teaches sq role <slug> show (item-first), not a path."""
    text = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    # The impersonation paragraph must reference the item-first CLI command.
    assert "sq role <slug> show" in text
    # The filesystem path must not appear as an agent-facing instruction.
    assert "agents/roles/" not in text

    # sq sync must propagate the same constraint.
    svc.sync()
    synced = (project.root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "sq role <slug> show" in synced
    assert "agents/roles/" not in synced
