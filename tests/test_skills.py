from squads import _interactions as interactions
from squads._cli import app
from squads._models._enums import ItemType
from squads._sections import split_frontmatter

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
    ).read_text(encoding="utf-8")


def test_item_skills_generated_with_active_role_sections(project):
    skills_dir = project.claude_dir / "skills"
    for it in interactions.managed_item_types():
        # thin pointer in .claude → real body under the squad folder
        pointer = (skills_dir / interactions.item_skill_name(it) / "SKILL.md").read_text(
            encoding="utf-8"
        )
        fm, _ = split_frontmatter(pointer)
        assert fm["name"] == interactions.item_skill_name(it)
        assert (project.squad_dir / "agents" / "skills" / f"{fm['name']}.md").is_file()
    feature = _item_skill_body(project, ItemType.FEATURE)
    # 'minimal' roster = manager only, who does not interact with features → no role sections
    assert "## For " not in feature
    # but the generic command block is always present
    assert "add-story" in feature


def test_item_skill_shows_only_active_roles(svc, project):
    svc.activate_role("product-owner")
    svc.activate_role("qa")
    svc.refresh_managed()
    feature = _item_skill_body(project, ItemType.FEATURE)
    assert "Nina Product" in feature  # active PO section present
    assert "Olivia Lead" not in feature  # tech-lead not activated → no section


def test_item_skill_actor_guidance_is_structured(svc, project):
    svc.add_dev("python")  # the developers section is gated on an active dev (see below)
    svc.refresh_managed()
    task = _item_skill_body(project, ItemType.TASK)
    assert "## For developers" in task
    for label in ("**Enter**", "**Do:**", "**Hand off:**", "**Watch for:**"):
        assert label in task
    assert "acceptance criteria" in task  # enter: read the feature's stories
    assert "@reviewer" in task  # hand off
    assert "don't author features/tasks" in task  # watch: scope discipline


def test_dev_section_gated_on_active_dev(svc, project):
    # no dev in the roster → no developers section anywhere
    assert "## For developers" not in _item_skill_body(project, ItemType.TASK)
    svc.add_dev("rust")
    svc.refresh_managed()
    assert "## For developers" in _item_skill_body(project, ItemType.TASK)


def test_item_skill_watch_for_reviewer(svc, project):
    svc.activate_role("reviewer")
    svc.refresh_managed()
    task = _item_skill_body(project, ItemType.TASK)
    assert "Paul Reviewer" in task
    assert "don't fix the code yourself" in task  # reviewer scope discipline


def test_squads_skill_has_direct_operator_rule(project):
    body = (project.squad_dir / "agents" / "skills" / "squads.md").read_text(encoding="utf-8")
    assert "Working directly with the operator" in body
    assert "never your chat" in body


def test_pointer_lists_skills_frontmatter(svc, project):
    svc.activate_role("product-owner")
    svc.refresh_managed()
    fm, _ = split_frontmatter(
        (project.claude_dir / "agents" / "product-owner.md").read_text(encoding="utf-8")
    )
    assert fm["skills"] == ["squads", "sq-epic", "sq-feature"]
    # manager (default, no managed item type) lists only the squads skill
    mfm, _ = split_frontmatter(
        (project.claude_dir / "agents" / "manager.md").read_text(encoding="utf-8")
    )
    assert mfm["skills"] == ["squads"]


def test_role_body_lists_skills(svc):
    item = svc.activate_role("tech-writer")
    body = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    assert "## Skills" in body
    assert "`sq-guide`" in body


def test_role_body_has_operating_contract(svc):
    item = svc.activate_role("tech-writer")
    body = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    # the entry point reinforces: keep sq current, hand back, and follow the per-item skill section
    assert "read `sq`, not your chat" in body
    assert "follow your `sq-<type>` skill" in body


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
