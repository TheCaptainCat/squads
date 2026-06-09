import pytest

from squads._errors import InvalidTransitionError, ItemNotFoundError, SquadsError
from squads._itemfile import read_frontmatter
from squads._models._enums import ItemType, Status

# --------------------------------------------------------------------------- create / lifecycle


def test_create_allocates_id_and_writes_file(svc):
    res = svc.create(ItemType.FEATURE, "User authentication", description="Login")
    assert res.item.id == "FEAT-000002"  # ROLE-000001 took the first number
    assert res.path.exists()
    assert res.path.name == "FEAT-000002-user-authentication.md"
    fm = read_frontmatter(res.path)
    assert fm["status"] == "Draft"
    assert fm["id"] == "FEAT-000002"


def test_create_rejects_missing_parent(svc):
    with pytest.raises(ItemNotFoundError):
        svc.create(ItemType.TASK, "x", parent="FEAT-999999")


def test_status_transition_and_validation(svc):
    res = svc.create(ItemType.TASK, "t")
    with pytest.raises(InvalidTransitionError):
        svc.set_status(res.item.id, Status.DONE)  # Draft -> Done illegal
    svc.set_status(res.item.id, Status.IN_PROGRESS)
    forced = svc.set_status(res.item.id, Status.DONE, force=False)  # InProgress -> Done legal
    assert forced.status is Status.DONE
    # frontmatter mirrors the index
    assert read_frontmatter(svc.paths.abspath(forced.path))["status"] == "Done"


def test_update_title_renames_file(svc):
    res = svc.create(ItemType.TASK, "Fix login")
    old = res.path
    updated = svc.update(res.item.id, title="Fix login loop")
    assert updated.slug == "fix-login-loop"
    assert not old.exists()
    assert svc.paths.abspath(updated.path).exists()
    assert updated.path.endswith("TASK-000002-fix-login-loop.md")


def test_link_unlink(svc):
    feat = svc.create(ItemType.FEATURE, "f").item
    task = svc.create(ItemType.TASK, "t").item
    svc.link(task.id, feat.id)
    assert svc.get(task.id).parent == feat.id
    svc.unlink(task.id)
    assert svc.get(task.id).parent is None


def test_set_body_replaces_appends_and_rejects(svc):
    task = svc.create(ItemType.TASK, "t", description="summary stays in frontmatter").item
    # the description is a frontmatter summary, NOT rendered into the body
    assert "summary stays in frontmatter" not in svc.read_body(task.id)
    svc.set_body(task.id, "## Description\n\nFull body content.")
    assert svc.read_body(task.id) == "## Description\n\nFull body content."
    # the frontmatter summary is untouched by a body change
    assert svc.get(task.id).description == "summary stays in frontmatter"
    # append adds a paragraph
    svc.set_body(task.id, "More detail.", append=True)
    assert svc.read_body(task.id).endswith("Full body content.\n\nMore detail.")
    # a body with an sq marker is rejected
    with pytest.raises(SquadsError, match="marker"):
        svc.set_body(task.id, "oops <!-- sq:body:end --> oops")
    # roles/skills bodies are generated, not free-form
    with pytest.raises(SquadsError, match="generated from its fields"):
        svc.set_body("ROLE-000001", "x")


def test_create_with_body(svc):
    res = svc.create(ItemType.FEATURE, "Login", body="## Summary\n\nEmail + password.")
    assert svc.read_body(res.item.id) == "## Summary\n\nEmail + password."


def test_repair_rebuilds_index_from_frontmatter(svc):
    svc.create(ItemType.FEATURE, "f")
    svc.create(ItemType.TASK, "t")
    # frontmatter is the durable truth: nuke the index and rebuild
    svc.paths.index_path.unlink()
    db = svc.repair()
    # the index now keys items by their int sequence number; ids live on the items
    assert set(db.items) == {1, 2, 3}
    assert {it.id for it in db.items.values()} == {"ROLE-000001", "FEAT-000002", "TASK-000003"}
    assert db.counter == 3


def test_subentity_state_lives_in_frontmatter_not_markers(svc):
    feat = svc.create(ItemType.FEATURE, "Login").item
    svc.add_story(feat.id, "Reset password")  # US1
    task = svc.create(ItemType.TASK, "Auth", parent=feat.id).item
    svc.add_subtask(task.id, "Validate", story="US1")
    svc.set_subtask_status(task.id, "ST1", Status.IN_PROGRESS)

    text = svc.paths.abspath(svc.get(task.id).path).read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    # state is in frontmatter …
    assert fm["subentities"] == [
        {"local_id": "ST1", "title": "Validate", "status": "InProgress", "story": "US1"}
    ]
    # … not in the body markers (no :meta), while prose + presentation regions stay
    assert ":meta" not in text
    assert "<!-- sq:subtask:ST1:head -->" in text and "<!-- sq:subtask:ST1:body -->" in text


def test_repair_reconstructs_subentities_from_frontmatter(svc):
    task = svc.create(ItemType.TASK, "Auth").item
    svc.add_subtask(task.id, "Validate", assignee=None)
    svc.paths.index_path.unlink()
    db = svc.repair()
    (sub,) = db.get(task.id).subentities
    assert (sub.local_id, sub.title, sub.status) == ("ST1", "Validate", Status.TODO)


# --------------------------------------------------------------------------- refs (forward edges)


def test_refs_out_and_computed_backrefs(svc):
    task = svc.create(ItemType.TASK, "t").item
    guide = svc.create(ItemType.GUIDE, "g").item
    svc.add_ref(task.id, guide.id, kind="implements")
    assert svc.refs_out(task.id) == [(guide.id, "implements")]
    assert svc.refs_in(guide.id) == [(task.id, "implements")]
    # the kind rides inline with the edge — no separate ref_kinds extra
    fm = read_frontmatter(svc.paths.abspath(svc.get(task.id).path))
    assert fm["refs"] == [f"{guide.id}:implements"]
    assert "ref_kinds" not in fm.get("extra", {})
    assert "backrefs" not in svc.store.load().to_json()


def test_default_kind_stored_bare(svc):
    a = svc.create(ItemType.TASK, "a").item
    b = svc.create(ItemType.GUIDE, "b").item
    svc.add_ref(a.id, b.id)  # default kind 'related'
    fm = read_frontmatter(svc.paths.abspath(svc.get(a.id).path))
    assert fm["refs"] == [b.id]  # no ':related' suffix
    assert svc.refs_out(a.id) == [(b.id, "related")]


def test_readd_updates_kind(svc):
    a = svc.create(ItemType.TASK, "a").item
    b = svc.create(ItemType.BUG, "b").item
    svc.add_ref(a.id, b.id, kind="related")
    svc.add_ref(a.id, b.id, kind="fixes")  # re-add updates, not duplicates
    assert svc.refs_out(a.id) == [(b.id, "fixes")]


def test_ref_rm_and_self_ref_rejected(svc):
    a = svc.create(ItemType.TASK, "a").item
    b = svc.create(ItemType.TASK, "b").item
    svc.add_ref(a.id, b.id, kind="blocks")
    svc.rm_ref(a.id, b.id)  # removed by ID regardless of kind
    assert svc.refs_out(a.id) == []
    with pytest.raises(SquadsError):
        svc.add_ref(a.id, a.id)


# --------------------------------------------------------------------------- repair --renumber


def test_repair_renumber_resolves_collision(svc):
    # build a collision like a git merge would: two items sharing number 000003
    svc.create(ItemType.TASK, "real task")  # TASK-000002
    bug = svc.create(ItemType.BUG, "real bug").item  # BUG-000003
    # forge a feature file that also claims number 000003, referenced by the bug
    feat_dir = svc.paths.folder_for(ItemType.FEATURE)
    forged = feat_dir / "FEAT-000003-forged.md"
    forged.write_text(
        "---\nid: FEAT-000003\nsequence_id: 3\ntype: feature\ntitle: forged\nstatus: Draft\n"
        "created_at: '2026-01-01T00:00:00Z'\nupdated_at: '2026-01-01T00:00:00Z'\n---\n"
        "<!-- sq:body -->\n<!-- sq:body:end -->\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n",
        encoding="utf-8",
    )
    # rebuild so the forged item enters the index, then have the bug reference it
    svc.repair()
    svc.add_ref(bug.id, "FEAT-000003")

    db = svc.repair(renumber=True)

    numbers = list(db.items)  # the index keys ARE the sequence numbers
    assert len(numbers) == len(set(numbers)), "no duplicate numbers remain"
    # BUG-000003 kept its number (sorts before FEAT-000003); FEAT got a fresh one
    assert bug.sequence_id in db.items
    new_feat = next(it.id for it in db.items.values() if it.id.startswith("FEAT-"))
    assert new_feat != "FEAT-000003"
    # the bug's forward ref was rewritten to the new feature id
    assert db.items[bug.sequence_id].refs == [new_feat]
    # counter advanced past the reassigned number
    assert db.counter == max(numbers)


# --------------------------------------------------------------------------- developers


def test_dev_add_auto_name_and_slug(svc):
    d1 = svc.add_dev("dotnet")
    assert d1.extra["slug"] == "dotnet-dev"
    assert d1.extra["full_name"].endswith("Dotnet")
    assert d1.extra["is_dev"] is True
    assert d1.author == "dotnet-dev"  # a dev role authors itself
    d2 = svc.add_dev("python", name="Grace Hopper")
    assert d2.extra["full_name"] == "Grace Hopper"
    assert d2.extra["slug"] == "python-dev"
    with pytest.raises(SquadsError):
        svc.add_dev("dotnet")  # duplicate slug


def test_dev_pointer_generated(svc):
    svc.add_dev("rust")
    pointer = svc.paths.claude_dir / "agents" / "rust-dev.md"
    assert pointer.exists()
    assert "Rust" in pointer.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- skills


def test_skill_add_generates_pointer(svc):
    skill = svc.add_skill(
        "PDF extract", description="Pull text", when_to_use="when a pdf is attached"
    )
    assert skill.type is ItemType.SKILL
    assert skill.status is Status.ACTIVE
    pointer = svc.paths.claude_dir / "skills" / "pdf-extract" / "SKILL.md"
    assert pointer.exists()
    assert skill.path in pointer.read_text(encoding="utf-8")


def test_skill_rm_purge_removes_pointer_and_file(svc):
    skill = svc.add_skill("Temp skill")
    path = svc.paths.abspath(skill.path)
    pointer_dir = svc.paths.claude_dir / "skills" / "temp-skill"
    assert path.exists() and pointer_dir.exists()
    svc.remove_item(skill.id, purge=True)
    assert skill.sequence_id not in svc.store.load().items
    assert not path.exists()
    assert not pointer_dir.exists()


# --------------------------------------------------------------------------- author & update


def test_author_defaults_to_registered_role_and_validates(svc):
    # the svc fixture's minimal roster registers `manager`; create defaults author to it
    task = svc.create(ItemType.TASK, "t").item
    assert task.author == "manager"
    # the bundled manager role self-authored at init
    assert svc.get("ROLE-000001").author == "manager"
    # an explicit unregistered author is rejected
    with pytest.raises(SquadsError, match="not a registered agent"):
        svc.create(ItemType.TASK, "x", author="ghost")


def test_check_flags_author_whose_role_was_removed(svc):
    task = svc.create(ItemType.TASK, "t", author="manager").item
    svc.remove_item(svc.get("ROLE-000001").id)  # drop the manager role
    issues = svc.check()
    assert any(i.item == task.id and "author" in i.message for i in issues)


def test_assignee_validated_against_roster(svc):
    svc.add_dev("python")  # registers python-dev as an agent
    task = svc.create(ItemType.TASK, "t", assignee="python-dev").item
    assert task.assignee == "python-dev"
    # an unregistered assignee is rejected at create and at update
    with pytest.raises(SquadsError, match="not a registered agent"):
        svc.create(ItemType.TASK, "x", assignee="ghost")
    svc.update(task.id, assignee="manager")
    assert svc.get(task.id).assignee == "manager"
    with pytest.raises(SquadsError, match="not a registered agent"):
        svc.update(task.id, assignee="ghost")
    # an empty assignee clears it (no validation)
    svc.update(task.id, assignee="")
    assert svc.get(task.id).assignee is None


def test_check_flags_assignee_whose_role_was_removed(svc):
    svc.add_dev("rust")  # registers rust-dev
    task = svc.create(ItemType.TASK, "t", assignee="rust-dev").item
    role = next(
        r for r in svc.list_items(item_type=ItemType.ROLE) if r.extra.get("slug") == "rust-dev"
    )
    svc.remove_item(role.id)
    issues = svc.check()
    assert any(i.item == task.id and "assignee" in i.message for i in issues)


def test_update_role_extra_regenerates_pointer(svc, project):
    # minimal roster registers `manager` as ROLE-000001 with a generated .claude pointer
    svc.update("ROLE-000001", set_extra={"color": "magenta"})
    assert svc.get("ROLE-000001").extra["color"] == "magenta"
    pointer = (project.claude_dir / "agents" / "manager.md").read_text(encoding="utf-8")
    assert "color: magenta" in pointer  # the pointer was regenerated from the edited config


# --------------------------------------------------------------------------- sync / version


def test_sync_stamps_version(svc, monkeypatch):
    import squads

    monkeypatch.setattr(squads, "__version__", "9.9.9", raising=False)
    monkeypatch.setattr("squads._services._maintenance.__version__", "9.9.9", raising=False)
    svc.sync()
    import tomllib

    cfg = tomllib.loads(svc.paths.config_path.read_text(encoding="utf-8"))
    assert cfg["squads_version"] == "9.9.9"


def test_version_notice_triggers_when_newer(capsys, project, monkeypatch):
    from squads._cli import _common as common

    monkeypatch.setattr(common, "__version__", "9.9.9", raising=False)
    common.set_active_dir(None)
    monkeypatch.chdir(project.root)
    common.version_notice()
    err = capsys.readouterr().err
    assert "sq sync" in err
