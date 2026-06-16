from squads import _interactions as interactions
from squads._cli import app
from squads._models._enums import ItemType
from squads._sections import split_frontmatter

# --------------------------------------------------------------------------- matrix


def test_skills_for_role_mapping():
    # every role preloads the always-on skills (squads + greeting); managers add nothing else
    assert interactions.skills_for_role("manager") == ["squads", "greeting"]
    assert interactions.skills_for_role("devops") == ["squads", "greeting"]
    # specialists get exactly the item skills they interact with, after the always-on pair
    assert interactions.skills_for_role("product-owner") == [
        "squads",
        "greeting",
        "sq-epic",
        "sq-feature",
    ]
    assert "sq-guide" in interactions.skills_for_role("tech-writer")
    assert interactions.skills_for_role("tech-writer") == ["squads", "greeting", "sq-guide"]


def test_dev_sentinel_expands_to_any_dev_slug():
    skills = interactions.skills_for_role("python-dev")
    assert skills == ["squads", "greeting", "sq-task", "sq-bug", "sq-review"]


# --------------------------------------------------------------------------- generation


def _item_skill_body(project, item_type):
    return (
        project.squad_dir / "agents" / "skills" / f"{interactions.item_skill_name(item_type)}.md"
    ).read_text(encoding="utf-8")


def test_item_skills_generated_with_active_role_sections(project):
    skills_dir = project.root / ".claude" / "skills"
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


def test_squads_skill_teaches_full_comments_briefing(project):
    # US6: the squads skill must teach show --full --comments as the standard briefing move so
    # agents don't silently miss decisions captured only in discussion comments.
    body = (project.squad_dir / "agents" / "skills" / "squads.md").read_text(encoding="utf-8")
    assert "--full --comments" in body
    # appears in the Anchor-to-an-item guidance (Working directly with the operator)
    assert "show --full --comments" in body


def test_item_skills_teach_full_comments_briefing(svc, project):
    # US6: every per-type sq-<type> skill's Enter section must instruct reading with
    # --full --comments. The guidance is injected by item_skill.md.j2 as the first Enter bullet.
    svc.add_dev("python")
    svc.refresh_managed()
    for it in interactions.managed_item_types():
        body = _item_skill_body(project, it)
        assert "--full --comments" in body, (
            f"sq-{it.value} skill is missing --full --comments briefing guidance"
        )
        # The Enter section specifically should carry the dossier instruction
        assert "show --full --comments" in body, (
            f"sq-{it.value} Enter section missing 'show --full --comments'"
        )


def test_greeting_skill_is_generated_and_preloaded(project):
    # the always-on greeting skill: real body under the squad folder, thin pointer in .claude
    pointer = (project.root / ".claude" / "skills" / "greeting" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "@squads/agents/skills/greeting.md" in pointer
    body = (project.squad_dir / "agents" / "skills" / "greeting.md").read_text(encoding="utf-8")
    # operator-facing only, and the three greeting beats (tone, who/help, project read)
    assert "spawned as a subagent" in body  # subagents skip the greeting
    assert "sq list -t operator" in body and "git config user.name" in body  # detect + register
    assert "Match their tone" in body
    # every role pointer preloads it
    fm, _ = split_frontmatter(
        (project.root / ".claude" / "agents" / "manager.md").read_text(encoding="utf-8")
    )
    assert "greeting" in fm["skills"]


def test_pointer_lists_skills_frontmatter(svc, project):
    svc.activate_role("product-owner")
    svc.refresh_managed()
    fm, _ = split_frontmatter(
        (project.root / ".claude" / "agents" / "product-owner.md").read_text(encoding="utf-8")
    )
    assert fm["skills"] == ["squads", "greeting", "sq-epic", "sq-feature"]
    # manager (default, no managed item type) lists just the always-on skills
    mfm, _ = split_frontmatter(
        (project.root / ".claude" / "agents" / "manager.md").read_text(encoding="utf-8")
    )
    assert mfm["skills"] == ["squads", "greeting"]


def test_role_body_lists_skills(svc):
    item = svc.activate_role("tech-writer")
    body = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    assert "## Skills" in body
    assert "`sq-guide`" in body


def test_role_body_has_operating_contract(svc):
    item = svc.activate_role("tech-writer")
    body = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    # the entry point reinforces: follow the per-item skill section
    assert "follow your `sq-<type>` skill" in body
    # both regime headings must be present
    assert "### Spawned as a subagent" in body
    assert "### Live with the operator" in body
    # the shared principle appears in the live regime
    assert "Record what the next reader needs, when it becomes true" in body
    # subagent regime: full record requirement before returning
    assert "full record" in body
    # live regime: handoffs only when work actually moves
    assert "when work actually moves" in body


def test_reviewer_role_body_carries_findings_agreement(svc):
    # TASK-000068: the reviewer's working agreements must include the findings-as-sub-entities line
    item = svc.activate_role("reviewer")
    body = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    assert "add-finding" in body
    assert "never as body prose" in body


def test_non_reviewer_role_body_has_no_findings_agreement(svc):
    # TASK-000068: roles without per-role agreements must not carry the findings line
    item = svc.activate_role("tech-writer")
    body = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    assert "add-finding" not in body
    assert "never as body prose" not in body


def test_squads_skill_teaches_comment_scoping_convention(project):
    # FEAT-000062 US1: the squads skill must name the sub-entity comment command and give
    # a concrete example for each sub-entity kind (finding, story, subtask).
    body = (project.squad_dir / "agents" / "skills" / "squads.md").read_text(encoding="utf-8")
    # the canonical convention is present (single source)
    assert "Scope your comment to the right discussion" in body
    # all three sub-entity command shapes appear as examples
    assert "story <k> comment" in body
    assert "subtask <k> comment" in body
    assert "finding <k> comment" in body
    # the inbox rule is explained (no gap when using sub-entity discussions)
    assert "sq inbox" in body


def test_per_type_skills_carry_scoped_comment_guidance(svc, project):
    # FEAT-000062 US1: sq-review, sq-feature, sq-task each carry role-specific scoped-comment
    # guidance that points at the squads skill convention (no restatement of the full text).
    svc.activate_role("reviewer")
    svc.activate_role("product-owner")
    svc.activate_role("tech-lead")
    svc.add_dev("python")
    svc.refresh_managed()

    review = _item_skill_body(project, ItemType.REVIEW)
    # reviewer: finding-scoped comment when closing/responding
    assert "finding <k> comment" in review
    assert "comment-scoping convention" in review

    feature = _item_skill_body(project, ItemType.FEATURE)
    # product-owner and tech-lead: story-scoped comments for acceptance clarifications
    assert "story <k> comment" in feature
    assert "comment-scoping convention" in feature

    task = _item_skill_body(project, ItemType.TASK)
    # dev: subtask-scoped comments for implementation notes
    assert "subtask <k> comment" in task
    assert "comment-scoping convention" in task


def test_role_body_has_comment_scoping_pointer(svc):
    # FEAT-000062 US1: every activated role's working agreements name the scoping principle
    # and point at the squads skill — a brief sentence, not a restatement of the full convention.
    item = svc.activate_role("tech-writer")
    body = svc.paths.abspath(item.path).read_text(encoding="utf-8")
    assert "comment-scoping" in body
    assert "squads" in body  # points at the squads skill by name


def test_sync_regenerates_role_bodies(svc, project):
    # activate a role, manually corrupt its body region, then verify sync restores both regimes
    item = svc.activate_role("qa")
    path = svc.paths.abspath(item.path)
    from squads import _sections as sections
    from squads._models import _markers as markers

    corrupted = sections.replace_section(
        path.read_text(encoding="utf-8"), markers.BODY, "\n_corrupted_\n"
    )
    path.write_text(corrupted, encoding="utf-8")
    assert "Spawned as a subagent" not in path.read_text(encoding="utf-8")
    # sync should re-render the body
    svc.sync()
    restored = path.read_text(encoding="utf-8")
    assert "### Spawned as a subagent" in restored
    assert "### Live with the operator" in restored
    assert "Record what the next reader needs, when it becomes true" in restored


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
