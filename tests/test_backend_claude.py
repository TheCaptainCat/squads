import json

import yaml

from squads.sections import split_frontmatter


def _read_pointer(project, slug):
    return (project.claude_dir / "agents" / f"{slug}.md").read_text()


def test_init_creates_claude_pointers_and_managed_files(project):
    # minimal roster => manager only
    text = _read_pointer(project, "manager")
    fm, body = split_frontmatter(text)
    assert fm["name"] == "manager"  # lowercase-hyphen, Claude requirement
    assert isinstance(fm["description"], str)
    # body points at the real definition under the squad folder
    assert "squads/agents/roles/ROLE-000001-manager.md" in body
    assert "Catherine Manager" in body

    skill = (project.claude_dir / "skills" / "squads" / "SKILL.md").read_text()
    assert "sq create" in skill
    assert "squads:version:" in skill

    claude_md = project.claude_md.read_text()
    assert "<!-- squads:start -->" in claude_md
    assert "Catherine Manager" in claude_md  # default role on greeting


def test_pointer_frontmatter_is_valid_yaml(project):
    fm, _ = split_frontmatter(_read_pointer(project, "manager"))
    # round-trips through a real YAML parser
    assert yaml.safe_load(yaml.safe_dump(fm)) == fm
    assert fm["name"] == fm["name"].lower()


def test_settings_merge_does_not_clobber(project, svc):
    settings = project.claude_dir / "settings.json"
    data = json.loads(settings.read_text())
    data["permissions"]["allow"].append("Bash(git status)")
    data["customKey"] = 123
    settings.write_text(json.dumps(data))
    # re-run scaffold (idempotent merge)
    svc._backend().ensure_scaffold(svc._ctx)
    merged = json.loads(settings.read_text())
    assert merged["customKey"] == 123  # preserved
    assert "Bash(git status)" in merged["permissions"]["allow"]  # preserved
    assert "Bash(sq:*)" in merged["permissions"]["allow"]  # still present


def test_claude_md_injection_idempotent(project, svc):
    before = project.claude_md.read_text()
    svc.refresh_managed()
    after = project.claude_md.read_text()
    assert before.count("<!-- squads:start -->") == 1
    assert after.count("<!-- squads:start -->") == 1
