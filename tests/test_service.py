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


def test_repair_carries_padding_forward(svc):
    """repair() preserves stored padding as a floor (ADR-000104); default squads get 6."""
    import json

    svc.create(ItemType.TASK, "t")
    # Default padding is 6.
    assert svc.store.load().padding == 6
    # repair on an unmodified squad keeps padding at 6.
    result = svc.repair()
    assert result.db.padding == 6

    # Manually set padding to 7 in the index to simulate a post-repad squad.
    raw = json.loads(svc.paths.index_path.read_text(encoding="utf-8"))
    raw["padding"] = 7
    svc.paths.index_path.write_text(json.dumps(raw), encoding="utf-8")

    # repair carries the stored floor forward (no files are at width 7, but stored > 6).
    result = svc.repair()
    assert result.db.padding == 7  # floor preserved


def test_repair_writes_padding_for_pre_existing_index(svc):
    """repair() materialises padding=6 into an index that predates the padding field."""
    import json

    svc.create(ItemType.TASK, "t")
    # Remove padding from the index as if it were a pre-FEAT-000027 index.
    raw = json.loads(svc.paths.index_path.read_text(encoding="utf-8"))
    del raw["padding"]
    svc.paths.index_path.write_text(json.dumps(raw), encoding="utf-8")

    # The model defaults missing padding to 6 on read, and repair writes it back.
    result = svc.repair()
    assert result.db.padding == 6
    # Confirm it's physically in the file.
    on_disk = json.loads(svc.paths.index_path.read_text(encoding="utf-8"))
    assert on_disk["padding"] == 6


def test_create_at_capacity_raises_index_full_error(svc):
    """create raises SquadsError naming sq migrate repad when the counter hits capacity."""
    import json

    # Force the counter to the last valid slot for padding=6.
    raw = json.loads(svc.paths.index_path.read_text(encoding="utf-8"))
    raw["counter"] = 10**6 - 1  # 999_999
    svc.paths.index_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(SquadsError, match="sq migrate repad"):
        svc.create(ItemType.TASK, "overflow")


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
    pointer = svc.paths.root / ".claude" / "agents" / "rust-dev.md"
    assert pointer.exists()
    assert "Rust" in pointer.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- skills


def test_skill_add_generates_pointer(svc):
    skill = svc.add_skill(
        "PDF extract", description="Pull text", when_to_use="when a pdf is attached"
    )
    assert skill.type is ItemType.SKILL
    assert skill.status is Status.ACTIVE
    pointer = svc.paths.root / ".claude" / "skills" / "pdf-extract" / "SKILL.md"
    assert pointer.exists()
    assert skill.path in pointer.read_text(encoding="utf-8")


def test_skill_rm_purge_removes_pointer_and_file(svc):
    skill = svc.add_skill("Temp skill")
    path = svc.paths.abspath(skill.path)
    pointer_dir = svc.paths.root / ".claude" / "skills" / "temp-skill"
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
    pointer = (project.root / ".claude" / "agents" / "manager.md").read_text(encoding="utf-8")
    assert "color: magenta" in pointer  # the pointer was regenerated from the edited config


def test_role_body_active_contains_working_agreements(svc):
    """role_body(slug) returns the item body including working agreements when active."""
    # minimal init activates `manager` — its body is generated from the role template.
    body = svc.role_body("manager")
    assert body is not None
    assert "Working agreements" in body


def test_role_body_bundled_only_returns_none(svc):
    """role_body(slug) returns None for a bundled-but-not-activated role."""
    # `qa` is bundled but not activated under the minimal spec.
    body = svc.role_body("qa")
    assert body is None


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


# ----------------------------------------------------------------- repair: F2 (REV-000105)


def test_repair_raises_padding_from_filename_width(svc):
    """repair() raises padding when an item file's digit-run is wider than the stored padding.

    F2 (REV-000105): the filename-recompute arm of repair was untested.  Scenario: stored padding
    is 6 but an item file was renamed to a width-7 name (as repad would do).  repair() must
    detect the wider filename and raise padding to 7.
    """
    import json

    from squads._models._enums import ItemType

    task = svc.create(ItemType.TASK, "task").item
    # Confirm default padding.
    assert svc.store.load().padding == 6

    # Rename the task file to a width-7 name to simulate a partial or completed repad.
    old_path = svc.paths.abspath(task.path)
    new_name = old_path.name.replace("TASK-000", "TASK-0000")  # e.g. TASK-0000002-task.md
    new_path = old_path.parent / new_name
    old_path.rename(new_path)

    # Repair should detect the wider filename and raise padding to 7.
    result = svc.repair()
    assert result.db.padding == 7, "repair must raise padding to match the widest filename"

    # The stored value must also be 7 on disk.
    on_disk = json.loads(svc.paths.index_path.read_text(encoding="utf-8"))
    assert on_disk["padding"] == 7


# --------------------------------------------------------------------------- repad


def test_repad_renames_files_and_bumps_padding(svc):
    """repad(7) renames all item files to width-7 and stores padding=7."""
    feat = svc.create(ItemType.FEATURE, "feat").item  # FEAT-000002
    task = svc.create(ItemType.TASK, "task").item  # TASK-000003

    renamed = svc.repad(7)

    # All item files should now have width-7 digit runs.
    for _, md in svc._iter_item_files():  # pyright: ignore[reportPrivateUsage]
        stem = md.stem
        _, _, digits_slug = stem.partition("-")
        digit_run = digits_slug.split("-", 1)[0]
        assert len(digit_run) == 7, f"expected width-7 digit run, got {digit_run!r} in {md.name}"

    # The index must record the new padding.
    db = svc.store.load()
    assert db.padding == 7

    # Items are keyed by sequence_id — all three items present.
    assert feat.sequence_id in db.items
    assert task.sequence_id in db.items

    # renamed count: every item file (role + feat + task = 3)
    assert renamed == 3


def test_repad_refuses_to_lower(svc):
    """repad raises SquadsError when the requested width is <= the current padding."""
    svc.create(ItemType.TASK, "t")
    assert svc.store.load().padding == 6

    with pytest.raises(SquadsError, match="must be greater than"):
        svc.repad(6)

    with pytest.raises(SquadsError, match="must be greater than"):
        svc.repad(5)


def test_repad_leaves_file_contents_byte_identical(svc):
    """repad only renames files; the bytes inside each file are unchanged."""
    task = svc.create(ItemType.TASK, "byte check task").item

    # Capture the file contents before repad.
    old_path = svc.paths.abspath(task.path)
    original_bytes = old_path.read_bytes()

    svc.repad(7)

    # The old path no longer exists.
    assert not old_path.exists()

    # Find the renamed file and check that its bytes are identical.
    task_folder = svc.paths.folder_for(ItemType.TASK)
    new_files = list(task_folder.glob("TASK-*.md"))
    assert len(new_files) == 1, "expected exactly one task file after repad"
    new_bytes = new_files[0].read_bytes()
    assert new_bytes == original_bytes, "file contents must be byte-identical after repad"


def test_repad_sq_check_clean_afterwards(svc):
    """sq check must pass on a repadded squad."""
    svc.create(ItemType.TASK, "t")
    svc.repad(7)
    issues = svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors, f"sq check errors after repad: {errors}"


def test_repad_is_idempotent_on_already_wide_files(svc):
    """repad(8) on a width-7 squad: files that are already width-8 are not re-renamed."""
    svc.create(ItemType.TASK, "t")
    svc.repad(7)
    db7 = svc.store.load()
    assert db7.padding == 7

    renamed8 = svc.repad(8)
    db8 = svc.store.load()
    assert db8.padding == 8
    # All files renamed from width-7 to width-8.
    assert renamed8 > 0


def test_renumber_plan_uses_supplied_padding(svc):
    """_renumber_plan mints IDs at the supplied padding, not the hard-coded default.

    F1 (REV-000105): simulate a width-7 squad by calling _renumber_plan with padding=7
    and verifying that the minted collision-resolved IDs use 7-digit formatting.
    """
    from pathlib import Path

    from squads._models._enums import ItemType
    from squads._services._maintenance import MaintenanceMixin

    # Build two synthetic _FileRec tuples that collide on sequence 3.
    fid_a = "TASK-000003"
    fid_b = "FEAT-000003"
    fake_path = Path("/fake/path.md")
    records = [
        (fid_a, fake_path, ItemType.TASK, "task", 3),
        (fid_b, fake_path, ItemType.FEATURE, "feat", 3),
    ]
    _, renames = MaintenanceMixin._renumber_plan(records, padding=7)  # pyright: ignore[reportPrivateUsage]
    # The reassigned ID must use 7-digit formatting.
    for _path, _item_type, _slug, new_id in renames:
        _, digits_part = new_id.rsplit("-", 1)
        assert len(digits_part) == 7, f"expected 7-digit id, got {new_id!r}"


# --------------------------------------------------------------------------- width-tolerant IDs


def test_display_uses_current_padding_after_repad(svc):
    """After repad, item.id uses the new padding width (display always uses current padding).

    The _propagate_padding model validator sets id_padding on all loaded items from
    db.padding so item.id returns the current-width ID everywhere (FEAT-000027 / TASK-000103).
    """
    task = svc.create(ItemType.TASK, "t").item
    assert task.id == "TASK-000002"  # width-6 before repad

    svc.repad(7)

    # After repad the stored padding is 7 and items loaded from the index must reflect it.
    db = svc.store.load()
    assert db.padding == 7
    loaded_task = db.items[task.sequence_id]
    assert loaded_task.id_padding == 7, "_propagate_padding must set id_padding from db.padding"
    assert loaded_task.id == "TASK-0000002", "display must use the current (new) padding width"


def test_refs_in_width_tolerant_after_repad(svc):
    """refs_in() returns backrefs correctly when the stored ref uses the old padding.

    Scenario: item A is created at width-6 and refs item B. Squad is then repadded to
    width-7. refs_in(B's new-width ID) must still find A.
    """
    feat = svc.create(ItemType.FEATURE, "feat").item  # FEAT-000002
    task = svc.create(ItemType.TASK, "task").item  # TASK-000003
    svc.add_ref(task.id, feat.id)  # TASK-000003 → FEAT-000002 (width-6 stored ref)

    svc.repad(7)

    # After repad, feat's canonical ID becomes FEAT-0000002.
    db = svc.store.load()
    feat_new_id = db.items[feat.sequence_id].id
    assert feat_new_id == "FEAT-0000002"

    # refs_in must still find TASK-0000003 using the new-width ID.
    backrefs = svc.refs_in(feat_new_id)
    assert len(backrefs) == 1
    task_new_id, kind = backrefs[0]
    assert task_new_id == "TASK-0000003"
    assert kind == "related"


def test_backrefs_width_tolerant_after_repad(svc):
    """SquadsDB.backrefs() works with old-width refs after a repad."""
    feat = svc.create(ItemType.FEATURE, "feat").item
    task = svc.create(ItemType.TASK, "task").item
    svc.add_ref(task.id, feat.id)

    svc.repad(7)
    db = svc.store.load()

    feat_new_id = db.items[feat.sequence_id].id  # "FEAT-0000002"
    task_new_id = db.items[task.sequence_id].id  # "TASK-0000003"

    result = db.backrefs(feat_new_id)
    assert result == [task_new_id]


def test_parent_lookup_width_tolerant_after_repad(svc):
    """Parent stored with old-width ID still resolves correctly after repad.

    index.get(item.parent) is width-tolerant via _seq; _check_items must not report a
    dangling-parent error when parent holds an old-width string.
    """
    feat = svc.create(ItemType.FEATURE, "feat").item
    task = svc.create(ItemType.TASK, "task", parent=feat.id).item
    assert task.parent == "FEAT-000002"  # stored at width-6

    svc.repad(7)

    # The parent field in frontmatter still reads "FEAT-000002" (contents never rewritten).
    db = svc.store.load()
    loaded_task = db.items[task.sequence_id]
    assert loaded_task.parent == "FEAT-000002"  # old width in frontmatter

    # index.get resolves it correctly (width-tolerant via _seq).
    parent_item = db.get(loaded_task.parent)
    assert parent_item is not None
    assert parent_item.sequence_id == feat.sequence_id

    # sq check must be clean — no dangling-parent errors.
    issues = svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors, f"errors after repad with old-width parent: {errors}"


def test_add_ref_dedup_width_tolerant(svc):
    """add_ref() does not duplicate a ref when re-adding across a repad boundary.

    Before repad: item A refs item B ("FEAT-000002").
    After repad:  add_ref(A, "FEAT-0000002") must replace the old ref, not add a second one.
    """
    feat = svc.create(ItemType.FEATURE, "feat").item
    task = svc.create(ItemType.TASK, "task").item
    svc.add_ref(task.id, feat.id)  # stores "FEAT-000002" in task's refs

    svc.repad(7)

    db = svc.store.load()
    feat_new_id = db.items[feat.sequence_id].id  # "FEAT-0000002"
    task_new_id = db.items[task.sequence_id].id

    # Re-add the ref using the new-width ID.
    updated_task = svc.add_ref(task_new_id, feat_new_id, kind="implements")

    # Only one ref should exist, with the new-width ID and updated kind.
    assert len(updated_task.refs) == 1
    raw_ref = updated_task.refs[0]
    ref_id, _, ref_kind_raw = raw_ref.partition(":")
    ref_kind = ref_kind_raw or "related"
    assert "FEAT" in ref_id  # canonical form
    assert ref_kind == "implements"


def test_rm_ref_width_tolerant(svc):
    """rm_ref() removes a ref stored with old-width ID when addressed with new-width ID."""
    feat = svc.create(ItemType.FEATURE, "feat").item
    task = svc.create(ItemType.TASK, "task").item
    svc.add_ref(task.id, feat.id)  # stores "FEAT-000002"

    svc.repad(7)
    db = svc.store.load()
    feat_new_id = db.items[feat.sequence_id].id
    task_new_id = db.items[task.sequence_id].id

    # Remove using the new-width ID — must find and remove the old-width stored ref.
    result = svc.rm_ref(task_new_id, feat_new_id)
    assert result.refs == []


def test_check_decisions_width_tolerant_after_repad(svc):
    """_check_decisions does not false-warn when the supersedes ref uses the old width."""
    adr1 = svc.create(ItemType.DECISION, "old decision").item
    adr2 = svc.create(ItemType.DECISION, "new decision").item
    svc.add_ref(adr2.id, adr1.id, kind="supersedes")
    svc.set_status(adr1.id, Status.SUPERSEDED, force=True)

    svc.repad(7)

    # After repad, _check_decisions must not warn about the old-width supersedes ref.
    issues = svc.check()
    superseded_warns = [i for i in issues if "Superseded" in i.message and i.item == adr1.id]
    assert not superseded_warns, f"spurious Superseded warning after repad: {superseded_warns}"


def test_end_to_end_repad_resolution(svc):
    """Full acceptance test: repad to width-7, every old-width ref/parent/mention still resolves.

    This is the joint acceptance seam with TASK-000102: after sq migrate repad(7),
    all old-width stored refs/parent/CLI addressing must work and sq check must be clean.
    """
    # Build a squad with cross-references and parent links (all width-6).
    feat = svc.create(ItemType.FEATURE, "feat").item  # FEAT-000002
    task = svc.create(ItemType.TASK, "task", parent=feat.id).item  # TASK-000003, parent FEAT-000002
    bug = svc.create(ItemType.BUG, "bug").item  # BUG-000004
    svc.add_ref(task.id, bug.id, kind="fixes")  # TASK-000003 fixes BUG-000004
    svc.add_ref(feat.id, task.id, kind="related")  # FEAT-000002 refs TASK-000003

    # Confirm width-6 state.
    assert task.parent == "FEAT-000002"
    assert svc.refs_in(bug.id) == [(task.id, "fixes")]

    # --- Repad to width 7 ---
    renamed = svc.repad(7)
    assert renamed > 0

    # After repad, the squad is at width-7.
    db = svc.store.load()
    assert db.padding == 7

    # All items display at the new width.
    feat7 = db.items[feat.sequence_id]
    task7 = db.items[task.sequence_id]
    bug7 = db.items[bug.sequence_id]
    assert feat7.id == "FEAT-0000002"
    assert task7.id == "TASK-0000003"
    assert bug7.id == "BUG-0000004"

    # Old-width parent ("FEAT-000002") resolves to the correct item.
    parent_item = db.get(task7.parent)  # task7.parent is still "FEAT-000002"
    assert parent_item is not None
    assert parent_item.sequence_id == feat.sequence_id

    # refs_in with new-width ID finds the old-width stored ref.
    bug_backrefs = svc.refs_in(bug7.id)
    assert any(seq_id == task7.id for seq_id, _ in bug_backrefs), (
        f"TASK-0000003 must appear in BUG-0000004 backrefs; got {bug_backrefs}"
    )

    # backrefs on the DB level.
    assert task7.id in db.backrefs(bug7.id)

    # CLI addressing with the old-width ID resolves to the item (db.get is width-tolerant).
    assert db.get("FEAT-000002") is feat7
    assert db.get("TASK-000003") is task7
    assert db.get("BUG-000004") is bug7

    # CLI addressing with the new-width ID also resolves.
    assert db.get("FEAT-0000002") is feat7
    assert db.get("TASK-0000003") is task7

    # sq check is clean (no dangling refs, no dangling parents, no reconciliation errors).
    issues = svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors, f"sq check errors after repad: {errors}"


def test_repair_after_repad_no_spurious_missing(svc):
    """F3 (REV-000106): repair() after repad must not report any items as missing.

    Before the F1 fix, _propagate_padding widens item.id strings in the prev snapshot
    (width-7) while from_frontmatter rebuilds at the default width-6, so
    previous_ids - found_ids equals the entire corpus.  This test must FAIL against that
    bug and pass only after repair() computes missing_ids by sequence_id (int).
    """
    feat = svc.create(ItemType.FEATURE, "feat").item
    task = svc.create(ItemType.TASK, "task", parent=feat.id).item
    bug = svc.create(ItemType.BUG, "bug").item
    svc.add_ref(task.id, bug.id, kind="fixes")

    # Repad to width 7 — renames files, leaves frontmatter IDs at width 6.
    renamed = svc.repad(7)
    assert renamed > 0

    # Running repair() again after repad must not report any spurious missing items.
    rr = svc.repair()
    assert rr.missing_ids == [], (
        f"repair() reported spurious missing items after repad: {rr.missing_ids}"
    )
