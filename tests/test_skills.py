from squads import interactions
from squads.cli import app
from squads.models import ItemType
from squads.sections import split_frontmatter

# --------------------------------------------------------------------------- matrix


def test_skills_for_role_mapping():
    # roles that don't manage an item type get only the general squads skill
    assert interactions.skills_for_role("manager") == ["squads"]
    assert interactions.skills_for_role("devops") == ["squads"]
    # specialists get exactly the item skills they interact with
    assert interactions.skills_for_role("product-owner") == ["squads", "sq-epic", "sq-feature"]
    assert "sq-guide" in interactions.skills_for_role("tech-writer")
    assert interactions.skills_for_role("tech-writer") == ["squads", "sq-guide"]


def test_dev_sentinel_expands_to_any_dev_slug():
    skills = interactions.skills_for_role("python-dev")
    assert skills == ["squads", "sq-task", "sq-bug", "sq-review"]


# --------------------------------------------------------------------------- generation


def _item_skill_body(project, item_type):
    return (
        project.squad_dir / "agents" / "skills" / f"{interactions.item_skill_name(item_type)}.md"
    ).read_text()


def test_item_skills_generated_with_active_role_sections(project):
    skills_dir = project.claude_dir / "skills"
    for it in interactions.managed_item_types():
        # thin pointer in .claude → real body under the squad folder
        pointer = (skills_dir / interactions.item_skill_name(it) / "SKILL.md").read_text()
        fm, _ = split_frontmatter(pointer)
        assert fm["name"] == interactions.item_skill_name(it)
        assert (project.squad_dir / "agents" / "skills" / f"{fm['name']}.md").is_file()
    feature = _item_skill_body(project, ItemType.FEATURE)
    # 'minimal' roster = manager only, who does not interact with features → no role sections
    assert "## For " not in feature
    # but the generic command block is always present
    assert "sq story add" in feature


def test_item_skill_shows_only_active_roles(svc, project):
    svc.activate_role("product-owner")
    svc.activate_role("qa")
    svc.refresh_managed()
    feature = _item_skill_body(project, ItemType.FEATURE)
    assert "Nina Product" in feature  # active PO section present
    assert "Olivia Lead" not in feature  # tech-lead not activated → no section


def test_pointer_lists_skills_frontmatter(svc, project):
    svc.activate_role("product-owner")
    svc.refresh_managed()
    fm, _ = split_frontmatter((project.claude_dir / "agents" / "product-owner.md").read_text())
    assert fm["skills"] == ["squads", "sq-epic", "sq-feature"]
    # manager (default, no managed item type) lists only the squads skill
    mfm, _ = split_frontmatter((project.claude_dir / "agents" / "manager.md").read_text())
    assert mfm["skills"] == ["squads"]


def test_role_body_lists_skills(svc):
    item = svc.activate_role("tech-writer")
    body = svc.paths.abspath(item.path).read_text()
    assert "## Skills" in body
    assert "`sq-guide`" in body


# --------------------------------------------------------------------------- sq workflow / help


def test_workflow_command(runner, project, monkeypatch):
    monkeypatch.chdir(project.root)
    r = runner.invoke(app, ["workflow"])
    assert r.exit_code == 0, r.output
    assert "Team workflow" in r.output
    assert "parent" in r.output and "feature" in r.output


def test_help_points_to_workflow(runner):
    r = runner.invoke(app, ["--help"])
    assert "sq workflow" in r.output
