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
    result = svc.repair()
    db = result.db
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
    result = svc.repair()
    (sub,) = result.db.get(task.id).subentities
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

    result = svc.repair(renumber=True)
    db = result.db

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


# --------------------------------------------------------------------------- counter monotonicity


def test_repair_keeps_counter_after_top_item_deleted(svc):
    """Repair must not regress the counter when the highest-numbered item's file is deleted."""
    svc.create(ItemType.FEATURE, "alpha")  # FEAT-000002
    top = svc.create(ItemType.TASK, "beta").item  # TASK-000003; counter → 3
    assert svc.store.load().counter == 3

    # Delete the top item's markdown file — simulates accidental or manual removal.
    svc.paths.abspath(top.path).unlink()

    result = svc.repair()
    # Counter must stay at 3 (the previous high-water mark), not drop to 2.
    assert result.db.counter == 3, "counter must not regress after top-item file loss"
    # The missing id is reported.
    assert top.id in result.missing_ids


def test_allocate_after_repair_never_reuses(svc):
    """Next create after a repair-after-file-loss must yield max+1, not a reused number."""
    svc.create(ItemType.FEATURE, "alpha")  # FEAT-000002
    top = svc.create(ItemType.TASK, "beta").item  # TASK-000003; counter → 3

    svc.paths.abspath(top.path).unlink()
    svc.repair()

    # The next allocation must be 4, never 3.
    new_item = svc.create(ItemType.BUG, "new bug").item
    assert new_item.sequence_id == 4, f"expected sequence 4, got {new_item.sequence_id}"
    assert new_item.id == "BUG-000004"


def test_load_corrects_regressed_counter(svc):
    """load() corrects a regressed counter in memory but leaves the file untouched.

    The corrected counter is then persisted by the next transaction (e.g. create),
    which must allocate max+1 and write the corrected value to disk.
    """
    import json

    svc.create(ItemType.FEATURE, "f1")  # FEAT-000002
    svc.create(ItemType.TASK, "t1")  # TASK-000003; counter → 3

    # Simulate a hand-edit that regressed the counter to 1.
    with svc.store.transaction() as db:
        db.counter = 1

    # File must still have the regressed value of 1 on disk.
    raw_before = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    assert raw_before["counter"] == 1, "file should be unchanged before load()"

    # load() must raise the in-memory counter to max(sequence_ids) = 3 …
    loaded = svc.store.load()
    assert loaded.counter == 3, f"expected in-memory counter=3 after load, got {loaded.counter}"

    # … but the file must remain untouched (counter still 1 on disk).
    raw_after = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    assert raw_after["counter"] == 1, "load() must not write back to the file"

    # The next create (a transaction) allocates max+1 = 4 and persists counter=4 to disk.
    new_item = svc.create(ItemType.BUG, "should be 4").item
    assert new_item.sequence_id == 4, f"expected sequence 4, got {new_item.sequence_id}"
    raw_persisted = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    assert raw_persisted["counter"] == 4, "transaction must persist the corrected counter"


def test_repair_reports_missing_ids(svc):
    """Repair surfaces the IDs of items that were indexed but whose files disappeared."""
    feat = svc.create(ItemType.FEATURE, "feature a").item  # FEAT-000002
    task = svc.create(ItemType.TASK, "task b").item  # TASK-000003

    # Delete one file.
    svc.paths.abspath(task.path).unlink()

    result = svc.repair()
    assert task.id in result.missing_ids
    assert feat.id not in result.missing_ids  # feat is still on disk; not reported


def test_check_flags_index_item_with_no_file(svc):
    """check() reports an error for items present in the index but missing from disk."""
    task = svc.create(ItemType.TASK, "t").item
    # Artificially add a ghost item to the index (no file on disk).
    import json

    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    raw["items"]["99"] = {
        "id": "TASK-000099",
        "sequence_id": 99,
        "type": "task",
        "title": "ghost",
        "slug": "ghost",
        "status": "Draft",
        "path": "tasks/TASK-000099-ghost.md",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    raw["counter"] = 99
    svc.store.index_path.write_text(json.dumps(raw), encoding="utf-8")

    issues = svc.check()
    assert any(i.item == "TASK-000099" and "no markdown" in i.message for i in issues)
    # The real task has no issue.
    assert not any(i.item == task.id and "no markdown" in i.message for i in issues)


# --------------------------------------------------------------------------- ref-kind vocabulary


def test_add_ref_rejects_unknown_kind(svc):
    """add_ref with an unknown kind raises SquadsError listing the valid kinds."""
    a = svc.create(ItemType.TASK, "a").item
    b = svc.create(ItemType.TASK, "b").item
    with pytest.raises(SquadsError) as exc_info:
        svc.add_ref(a.id, b.id, kind="banana")
    msg = str(exc_info.value)
    assert "banana" in msg
    # valid kinds are listed in the error
    for kind in ("related", "blocks", "fixes", "addresses", "supersedes", "duplicates"):
        assert kind in msg


def test_add_ref_accepts_all_valid_kinds(svc):
    """add_ref accepts each of the eight vocabulary kinds."""
    from squads._models._item import VALID_REF_KINDS

    items = [svc.create(ItemType.TASK, f"item-{i}").item for i in range(len(VALID_REF_KINDS))]
    target = svc.create(ItemType.TASK, "target").item
    for i, kind in enumerate(sorted(VALID_REF_KINDS)):
        svc.add_ref(items[i].id, target.id, kind=kind)
        pairs = svc.refs_out(items[i].id)
        assert pairs == [(target.id, kind)]


def test_add_ref_bare_defaults_related(svc):
    """add_ref without a kind defaults to 'related' — no nudge, no friction."""
    a = svc.create(ItemType.TASK, "a").item
    b = svc.create(ItemType.TASK, "b").item
    svc.add_ref(a.id, b.id)
    fm = read_frontmatter(svc.paths.abspath(svc.get(a.id).path))
    assert fm["refs"] == [b.id]  # stored bare (no ':related' suffix)
    assert svc.refs_out(a.id) == [(b.id, "related")]


def test_add_ref_three_new_kinds_persist(svc):
    """supersedes, depends-on, duplicates are accepted and round-trip through frontmatter."""
    dec_a = svc.create(ItemType.DECISION, "old decision").item
    dec_b = svc.create(ItemType.DECISION, "new decision").item
    task_a = svc.create(ItemType.TASK, "blocker").item
    task_b = svc.create(ItemType.TASK, "dependent").item
    bug_a = svc.create(ItemType.BUG, "original").item
    bug_b = svc.create(ItemType.BUG, "duplicate").item

    svc.add_ref(dec_b.id, dec_a.id, kind="supersedes")
    svc.add_ref(task_b.id, task_a.id, kind="depends-on")
    svc.add_ref(bug_b.id, bug_a.id, kind="duplicates")

    assert svc.refs_out(dec_b.id) == [(dec_a.id, "supersedes")]
    assert svc.refs_out(task_b.id) == [(task_a.id, "depends-on")]
    assert svc.refs_out(bug_b.id) == [(bug_a.id, "duplicates")]

    # verify frontmatter round-trip
    fm_dec = read_frontmatter(svc.paths.abspath(svc.get(dec_b.id).path))
    fm_task = read_frontmatter(svc.paths.abspath(svc.get(task_b.id).path))
    fm_bug = read_frontmatter(svc.paths.abspath(svc.get(bug_b.id).path))
    assert fm_dec["refs"] == [f"{dec_a.id}:supersedes"]
    assert fm_task["refs"] == [f"{task_a.id}:depends-on"]
    assert fm_bug["refs"] == [f"{bug_a.id}:duplicates"]


def test_create_with_ref_rejects_unknown_kind(svc):
    """svc.create with refs containing an unknown kind raises SquadsError."""
    from squads._models._item import make_ref

    a = svc.create(ItemType.TASK, "a").item
    with pytest.raises(SquadsError) as exc_info:
        svc.create(ItemType.TASK, "b", refs=[make_ref(a.id, "bogus")])
    assert "bogus" in str(exc_info.value)


# --------------------------------------------------------------------------- blocked (depends-on)


def test_blocked_depends_on_equivalent_to_blocks(svc):
    """depends-on produces the same (blocked, [blocker]) pair as the equivalent blocks edge."""
    blocker = svc.create(ItemType.TASK, "blocker").item
    dependent = svc.create(ItemType.TASK, "dependent").item

    # A depends-on B means A is blocked by B — same as B blocks A
    svc.add_ref(dependent.id, blocker.id, kind="depends-on")

    pairs = svc.blocked()
    assert len(pairs) == 1
    blocked_item, blockers = pairs[0]
    assert blocked_item.id == dependent.id
    assert len(blockers) == 1 and blockers[0].id == blocker.id


def test_blocked_mixed_edges_no_duplicates(svc):
    """An item blocked via both blocks and depends-on appears once with all blockers."""
    blocker_a = svc.create(ItemType.TASK, "blocker-a").item
    blocker_b = svc.create(ItemType.TASK, "blocker-b").item
    dependent = svc.create(ItemType.TASK, "dependent").item

    # blocker_a blocks dependent (edge on blocker_a)
    svc.add_ref(blocker_a.id, dependent.id, kind="blocks")
    # dependent depends-on blocker_b (edge on dependent)
    svc.add_ref(dependent.id, blocker_b.id, kind="depends-on")

    pairs = svc.blocked()
    assert len(pairs) == 1
    blocked_item, blockers = pairs[0]
    assert blocked_item.id == dependent.id
    blocker_ids = {b.id for b in blockers}
    assert blocker_ids == {blocker_a.id, blocker_b.id}


def test_blocked_closed_blocker_not_included(svc):
    """A closed blocker is not counted; if all blockers are closed the item is not listed."""
    blocker = svc.create(ItemType.TASK, "blocker").item
    dependent = svc.create(ItemType.TASK, "dependent").item

    svc.add_ref(dependent.id, blocker.id, kind="depends-on")
    # close the blocker
    svc.set_status(blocker.id, Status.IN_PROGRESS)
    svc.set_status(blocker.id, Status.DONE)

    assert svc.blocked() == []


# --------------------------------------------------------------------------- check warnings


def test_check_warns_on_unknown_ref_kind(svc):
    """check() emits a warn-level issue when a ref has an unknown kind."""
    import squads._sections as sections
    from squads._itemfile import read_frontmatter

    a = svc.create(ItemType.TASK, "a").item
    b = svc.create(ItemType.TASK, "b").item

    # Inject a junk kind directly into the frontmatter, bypassing add_ref validation.
    path = svc.paths.abspath(svc.get(a.id).path)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["refs"] = [f"{b.id}:banana"]
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    svc.repair()  # sync index with the rewritten frontmatter

    issues = svc.check()
    warn_issues = [i for i in issues if i.level == "warn" and "banana" in i.message]
    assert len(warn_issues) == 1
    assert warn_issues[0].item == a.id


def test_check_warns_superseded_decision_without_edge(svc):
    """check() warns when a Superseded decision has no incoming supersedes edge."""
    old_adr = svc.create(ItemType.DECISION, "old decision").item
    # Force it to Superseded status
    svc.set_status(old_adr.id, Status.PROPOSED)
    svc.set_status(old_adr.id, Status.SUPERSEDED, force=True)

    issues = svc.check()
    warn_issues = [
        i
        for i in issues
        if i.level == "warn" and "supersedes" in i.message and i.item == old_adr.id
    ]
    assert len(warn_issues) == 1


def test_check_no_warn_superseded_decision_with_edge(svc):
    """check() does NOT warn when a Superseded decision has an incoming supersedes edge."""
    old_adr = svc.create(ItemType.DECISION, "old decision").item
    new_adr = svc.create(ItemType.DECISION, "new decision").item

    svc.set_status(old_adr.id, Status.PROPOSED)
    svc.set_status(old_adr.id, Status.SUPERSEDED, force=True)
    # new supersedes old — edge lives on new_adr
    svc.add_ref(new_adr.id, old_adr.id, kind="supersedes")

    issues = svc.check()
    superseded_warns = [
        i
        for i in issues
        if i.level == "warn" and "supersedes" in i.message and i.item == old_adr.id
    ]
    assert len(superseded_warns) == 0
