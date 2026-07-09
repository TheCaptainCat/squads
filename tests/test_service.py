from pathlib import Path

import pytest

from squads._errors import InvalidTransitionError, ItemNotFoundError, SquadsError
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio

# --------------------------------------------------------------------------- create / lifecycle


async def test_create_allocates_id_and_writes_file(svc):
    res = await svc.create("feature", "User authentication", description="Login")
    assert res.item.id == "FEAT-2"  # ROLE-1 took the first number; display is unpadded
    assert res.path.exists()
    # Filename stays padded (ADR-000282) even though the displayed id is unpadded.
    assert res.path.name == "FEAT-000002-user-authentication.md"
    fm = read_frontmatter(res.path)
    assert fm["status"] == "Draft"
    assert fm["id"] == "FEAT-2"


async def test_create_rejects_missing_parent(svc):
    with pytest.raises(ItemNotFoundError):
        await svc.create("task", "x", parent="FEAT-999999")


async def test_status_transition_and_validation(svc):
    res = await svc.create("task", "t")
    with pytest.raises(InvalidTransitionError):
        await svc.set_status(res.item.id, "Done")  # Draft -> Done illegal
    await svc.set_status(res.item.id, "InProgress")
    forced = await svc.set_status(res.item.id, "Done", force=False)  # InProgress -> Done legal
    assert forced.status == "Done"
    # frontmatter mirrors the index
    assert read_frontmatter(svc.paths.abspath(forced.path))["status"] == "Done"


async def test_update_title_renames_file(svc):
    res = await svc.create("task", "Fix login")
    old = res.path
    updated = await svc.update(res.item.id, title="Fix login loop")
    assert updated.slug == "fix-login-loop"
    assert not old.exists()
    new_path = svc.paths.abspath(updated.path)
    assert new_path.exists()
    # Filename stem stays padded (ADR-000282) even though the displayed id is unpadded.
    assert updated.path.endswith("TASK-000002-fix-login-loop.md")
    assert read_frontmatter(new_path)["id"] == "TASK-2"


async def test_rename_and_retype_keep_filename_padded_while_id_unpadded(svc):
    """Invariant (ADR-000282): the on-disk stem stays padded while frontmatter id: is unpadded.

    Covers the two seams that concatenate a formatted id into a filename — rename (via
    update --title) and retype — in addition to create (test_create_allocates_id_and_writes_file).
    """
    # Rename seam.
    task = (await svc.create("task", "Original title")).item
    renamed = await svc.update(task.id, title="Renamed title")
    renamed_path = svc.paths.abspath(renamed.path)
    assert renamed_path.name == "TASK-000002-renamed-title.md"
    assert read_frontmatter(renamed_path)["id"] == "TASK-2"

    # Retype seam.
    retyped = (await svc.retype(task.id, "bug")).item
    retyped_path = svc.paths.abspath(retyped.path)
    assert retyped_path.name == "BUG-000002-renamed-title.md"
    assert read_frontmatter(retyped_path)["id"] == "BUG-2"


async def test_link_unlink(svc):
    feat = (await svc.create("feature", "f")).item
    task = (await svc.create("task", "t")).item
    await svc.link(task.id, feat.id)
    assert (await svc.get(task.id)).parent == feat.id
    await svc.unlink(task.id)
    assert (await svc.get(task.id)).parent is None


async def test_set_body_replaces_appends_and_rejects(svc):
    task = (await svc.create("task", "t", description="summary stays in frontmatter")).item
    # the description is a frontmatter summary, NOT rendered into the body
    assert "summary stays in frontmatter" not in await svc.read_body(task.id)
    await svc.set_body(task.id, "## Description\n\nFull body content.")
    assert await svc.read_body(task.id) == "## Description\n\nFull body content."
    # the frontmatter summary is untouched by a body change
    assert (await svc.get(task.id)).description == "summary stays in frontmatter"
    # append adds a paragraph
    await svc.set_body(task.id, "More detail.", append=True)
    assert (await svc.read_body(task.id)).endswith("Full body content.\n\nMore detail.")
    # a body with an sq marker is rejected
    with pytest.raises(SquadsError, match="marker"):
        await svc.set_body(task.id, "oops <!-- sq:body:end --> oops")
    # roles/skills bodies are generated, not free-form
    with pytest.raises(SquadsError, match="generated from its fields"):
        await svc.set_body("ROLE-000001", "x")


async def test_create_with_body(svc):
    res = await svc.create("feature", "Login", body="## Summary\n\nEmail + password.")
    assert await svc.read_body(res.item.id) == "## Summary\n\nEmail + password."


async def test_repair_rebuilds_index_from_frontmatter(svc):
    await svc.create("feature", "f")
    await svc.create("task", "t")
    # frontmatter is the durable truth: nuke the index and rebuild
    svc.paths.index_path.unlink()
    result = await svc.repair()
    db = result.db
    # the index now keys items by their int sequence number; ids live on the items
    assert set(db.items) == {1, 2, 3}
    assert {it.id for it in db.items.values()} == {"ROLE-1", "FEAT-2", "TASK-3"}
    assert db.counter == 3


async def test_repair_carries_padding_forward(svc):
    """repair() preserves stored padding as a floor (ADR-000104); default squads get 6."""
    import json

    await svc.create("task", "t")
    # Default padding is 6.
    assert (await svc.store.load()).padding == 6
    # repair on an unmodified squad keeps padding at 6.
    result = await svc.repair()
    assert result.db.padding == 6

    # Manually set padding to 7 in the index to simulate a post-repad squad.
    raw = json.loads(svc.paths.index_path.read_text(encoding="utf-8"))
    raw["padding"] = 7
    svc.paths.index_path.write_text(json.dumps(raw), encoding="utf-8")

    # repair carries the stored floor forward (no files are at width 7, but stored > 6).
    result = await svc.repair()
    assert result.db.padding == 7  # floor preserved


async def test_repair_writes_padding_for_pre_existing_index(svc):
    """repair() materialises padding=6 into an index that predates the padding field."""
    import json

    await svc.create("task", "t")
    # Remove padding from the index as if it were a pre-FEAT-000027 index.
    raw = json.loads(svc.paths.index_path.read_text(encoding="utf-8"))
    del raw["padding"]
    svc.paths.index_path.write_text(json.dumps(raw), encoding="utf-8")

    # The model defaults missing padding to 6 on read, and repair writes it back.
    result = await svc.repair()
    assert result.db.padding == 6
    # Confirm it's physically in the file.
    on_disk = json.loads(svc.paths.index_path.read_text(encoding="utf-8"))
    assert on_disk["padding"] == 6


async def test_create_at_capacity_raises_index_full_error(svc):
    """create raises SquadsError naming sq migrate repad when the counter hits capacity."""
    import json

    # Force the counter to the last valid slot for padding=6.
    raw = json.loads(svc.paths.index_path.read_text(encoding="utf-8"))
    raw["counter"] = 10**6 - 1  # 999_999
    svc.paths.index_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(SquadsError, match="sq migrate repad"):
        await svc.create("task", "overflow")


async def test_subentity_state_lives_in_frontmatter_not_markers(svc):
    feat = (await svc.create("feature", "Login")).item
    await svc.add_story(feat.id, "Reset password")  # US1
    task = (await svc.create("task", "Auth", parent=feat.id)).item
    await svc.add_subtask(task.id, "Validate", story="US1")
    await svc.set_subtask_status(task.id, "ST1", "InProgress")

    text = svc.paths.abspath((await svc.get(task.id)).path).read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    # state is in frontmatter …
    assert fm["subentities"] == [
        {"local_id": "ST1", "title": "Validate", "status": "InProgress", "story": "US1"}
    ]
    # … not in the body markers (no :meta), while prose + presentation regions stay
    assert ":meta" not in text
    assert "<!-- sq:subtask:ST1:head -->" in text and "<!-- sq:subtask:ST1:body -->" in text


async def test_repair_reconstructs_subentities_from_frontmatter(svc):
    task = (await svc.create("task", "Auth")).item
    await svc.add_subtask(task.id, "Validate", assignee=None)
    svc.paths.index_path.unlink()
    result = await svc.repair()
    (sub,) = result.db.get(task.id).subentities
    assert (sub.local_id, sub.title, sub.status) == ("ST1", "Validate", "Todo")


# --------------------------------------------------------------------------- refs (forward edges)


async def test_refs_out_and_computed_backrefs(svc):
    task = (await svc.create("task", "t")).item
    guide = (await svc.create("guide", "g")).item
    await svc.add_ref(task.id, guide.id, kind="implements")
    assert await svc.refs_out(task.id) == [(guide.id, "implements")]
    assert await svc.refs_in(guide.id) == [(task.id, "implements")]
    # the kind rides inline with the edge — no separate ref_kinds extra
    fm = read_frontmatter(svc.paths.abspath((await svc.get(task.id)).path))
    assert fm["refs"] == [f"{guide.id}:implements"]
    assert "ref_kinds" not in fm.get("extra", {})
    assert "backrefs" not in (await svc.store.load()).to_json()


async def test_default_kind_stored_bare(svc):
    a = (await svc.create("task", "a")).item
    b = (await svc.create("guide", "b")).item
    await svc.add_ref(a.id, b.id)  # default kind 'related'
    fm = read_frontmatter(svc.paths.abspath((await svc.get(a.id)).path))
    assert fm["refs"] == [b.id]  # no ':related' suffix
    assert await svc.refs_out(a.id) == [(b.id, "related")]


async def test_readd_updates_kind(svc):
    a = (await svc.create("task", "a")).item
    b = (await svc.create("bug", "b")).item
    await svc.add_ref(a.id, b.id, kind="related")
    await svc.add_ref(a.id, b.id, kind="fixes")  # re-add updates, not duplicates
    assert await svc.refs_out(a.id) == [(b.id, "fixes")]


async def test_ref_rm_and_self_ref_rejected(svc):
    a = (await svc.create("task", "a")).item
    b = (await svc.create("task", "b")).item
    await svc.add_ref(a.id, b.id, kind="blocks")
    await svc.rm_ref(a.id, b.id)  # removed by ID regardless of kind
    assert await svc.refs_out(a.id) == []
    with pytest.raises(SquadsError):
        await svc.add_ref(a.id, a.id)


# --------------------------------------------------------------------------- repair --renumber


async def test_repair_renumber_resolves_collision(svc):
    # build a collision like a git merge would: two items sharing number 000003
    await svc.create("task", "real task")  # TASK-000002
    bug = (await svc.create("bug", "real bug")).item  # BUG-000003
    # forge a feature file that also claims number 000003, referenced by the bug
    feat_dir = svc.paths.folder_for("feature", spec=svc.spec)
    forged = feat_dir / "FEAT-000003-forged.md"
    forged.write_text(
        "---\nid: FEAT-000003\nsequence_id: 3\ntype: feature\ntitle: forged\nstatus: Draft\n"
        "created_at: '2026-01-01T00:00:00Z'\nupdated_at: '2026-01-01T00:00:00Z'\n---\n"
        "<!-- sq:body -->\n<!-- sq:body:end -->\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n",
        encoding="utf-8",
    )
    # rebuild so the forged item enters the index, then have the bug reference it
    await svc.repair()
    await svc.add_ref(bug.id, "FEAT-000003")

    result = await svc.repair(renumber=True)
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


# --------------------------------------------------------------------------- sq renumber


def _fake_records(*seqs: int, prefix: str = "TASK") -> list[tuple[str, Path, str, str, int]]:
    return [(f"{prefix}-{seq}", Path(f"/fake/{prefix}-{seq}.md"), "task", "x", seq) for seq in seqs]


def _seqs_from(remap: dict[str, str]) -> dict[int, int]:
    return {int(k.rsplit("-", 1)[-1]): int(v.rsplit("-", 1)[-1]) for k, v in remap.items()}


def test_offset_plan_onto_lands_strictly_above_both_ranges():
    """--onto auto-computes the minimal safe offset for M > C, M < C, and M == C."""
    from squads._services._maintenance import MaintenanceMixin

    records = _fake_records(3, 4, 5)
    for onto, counter in [(10, 5), (2, 5), (5, 5)]:
        remap, renames, warning = MaintenanceMixin._offset_plan(  # pyright: ignore[reportPrivateUsage]
            records, from_seq=3, counter=counter, onto=onto, by=None, padding=6
        )
        assert warning is None  # --onto never warns — it fully certifies disjointness
        delta = max(onto, counter) + 1 - 3
        got = _seqs_from(remap)
        assert got == {3: 3 + delta, 4: 4 + delta, 5: 5 + delta}, (onto, counter, got)
        assert min(got.values()) > max(onto, counter)
        assert len(renames) == 3


def test_offset_plan_by_refuses_unsafe_offset_reports_minimum():
    """An unsafe --by refuses with SquadsError and reports the minimum safe offset."""
    from squads._services._maintenance import MaintenanceMixin

    records = _fake_records(3, 4, 5)
    with pytest.raises(SquadsError, match="minimum safe offset is 3"):
        MaintenanceMixin._offset_plan(  # pyright: ignore[reportPrivateUsage]
            records, from_seq=3, counter=5, onto=None, by=1, padding=6
        )


def test_offset_plan_by_safe_produces_remap_and_warns():
    """A safe --by shifts correctly but still warns it cannot certify the other branch clears."""
    from squads._services._maintenance import MaintenanceMixin

    records = _fake_records(3, 4, 5)
    remap, renames, warning = MaintenanceMixin._offset_plan(  # pyright: ignore[reportPrivateUsage]
        records, from_seq=3, counter=5, onto=None, by=3, padding=6
    )
    assert warning is not None and "onto" in warning.lower()
    assert _seqs_from(remap) == {3: 6, 4: 7, 5: 8}
    assert len(renames) == 3


def test_offset_plan_requires_exactly_one_of_onto_or_by():
    from squads._services._maintenance import MaintenanceMixin

    records = _fake_records(3)
    with pytest.raises(SquadsError, match="exactly one"):
        MaintenanceMixin._offset_plan(  # pyright: ignore[reportPrivateUsage]
            records, from_seq=3, counter=5, onto=None, by=None, padding=6
        )
    with pytest.raises(SquadsError, match="exactly one"):
        MaintenanceMixin._offset_plan(  # pyright: ignore[reportPrivateUsage]
            records, from_seq=3, counter=5, onto=10, by=3, padding=6
        )


async def test_renumber_shifts_block_and_preserves_referential_intent(svc):
    """The pre-merge shift rewrites a ref to a shifted item so it still points at that SAME
    item afterward — the referential-intent guarantee the post-merge collision fixer cannot
    make (contrast test_repair_renumber_resolves_collision, whose ref gets repointed to the
    *other* collided item)."""
    feat = (await svc.create("feature", "keep")).item  # FEAT-2, below --from
    task = (await svc.create("task", "shift-task", parent=feat.id)).item  # TASK-3
    bug = (await svc.create("bug", "shift-bug")).item  # BUG-4
    await svc.add_ref(task.id, bug.id)

    result = await svc.renumber(from_seq=3, onto=10)

    assert task.id in result.remap
    assert bug.id in result.remap
    assert feat.id not in result.remap  # below --from: untouched

    db = result.db
    new_task_id = result.remap[task.id]
    new_bug_id = result.remap[bug.id]
    new_task = db.get(new_task_id)
    assert new_task is not None
    assert new_task.refs == [new_bug_id]  # ref rewritten to the SAME (shifted) item
    assert new_task.parent == feat.id  # untouched parent link still resolves

    kept_feat = db.get(feat.id)
    assert kept_feat is not None
    assert kept_feat.title == "keep"

    # counter bumped to the true post-shift maximum
    assert db.counter == max(_seqs_from(result.remap).values())

    # files actually renamed on disk at the squad's filename padding (not the unpadded
    # content id) — a padding regression (e.g. a stray DISPLAY_ID_PADDING leak) would show
    # up here as a digit run shorter than db.padding.
    new_bug_item = db.get(new_bug_id)
    assert new_bug_item is not None
    new_bug_path = svc.paths.abspath(new_bug_item.path)
    assert new_bug_path.exists()
    assert not svc.paths.abspath(bug.path).exists()
    digit_run = new_bug_path.name.split("-")[1]
    assert digit_run.isdigit()
    assert len(digit_run) == db.padding, f"expected {db.padding}-digit filename, got {digit_run!r}"


async def test_renumber_rewrites_an_unshifted_items_ref_to_a_shifted_item(svc):
    """A referrer that is itself BELOW --from (never shifted) still has its ref to a shifted
    item rewritten to the new id — the reverse of the shifted-referrer case above, and the
    other half of the referential-intent guarantee: resolvability holds from both directions.
    """
    referrer = (await svc.create("task", "stay-put")).item  # TASK-2, will NOT be shifted
    bug = (await svc.create("bug", "shift-me")).item  # BUG-3
    await svc.add_ref(referrer.id, bug.id)

    result = await svc.renumber(from_seq=bug.sequence_id, onto=10)

    assert bug.id in result.remap
    assert referrer.id not in result.remap  # the referrer itself is below --from

    db = result.db
    new_bug_id = result.remap[bug.id]
    kept_referrer = db.get(referrer.id)
    assert kept_referrer is not None
    assert kept_referrer.refs == [new_bug_id]  # rewritten to point at the SAME (shifted) item
    assert db.get(new_bug_id) is not None


async def test_renumber_does_not_misreport_shifted_items_as_missing_in_reflog(svc):
    """`renumber` must NOT route its index commit through `repair`: repair's missing-file
    detector only sees an old sequence number vanish, not that it moved, and would otherwise
    log a false "missing" entry for every item this operation deliberately renumbered."""
    import json

    bug = (await svc.create("bug", "shift-me")).item  # BUG-2

    await svc.renumber(from_seq=bug.sequence_id, onto=10)

    reflog_path = svc.paths.squad_dir / ".reflog.jsonl"
    lines = [json.loads(ln) for ln in reflog_path.read_text(encoding="utf-8").splitlines() if ln]
    repair_entries = [ln for ln in lines if ln["op"] == "repair"]
    assert not repair_entries, f"renumber must not emit a repair op: {repair_entries}"
    assert all(bug.id not in ln.get("delta", {}).get("missing", []) for ln in lines)
    # sq check must see no dangling/missing state after the shift.
    issues = await svc.check()
    assert not any(i.level == "error" for i in issues), issues


def _read_reflog_lines(squad_dir: Path) -> list[str]:
    """Raw text lines (still JSON strings) of the reflog file, in file order."""
    path = squad_dir / ".reflog.jsonl"
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln]


async def test_renumber_appends_a_single_event_summarizing_the_shift(svc):
    """A shift appends exactly one new event whose delta carries the boundary, whichever of
    onto/by the operator actually supplied (the other stays null), and the full remap."""
    import json

    before = _read_reflog_lines(svc.paths.squad_dir)

    task = (await svc.create("task", "shift-me")).item
    bug = (await svc.create("bug", "shift-me-too")).item
    result = await svc.renumber(from_seq=task.sequence_id, onto=10)

    after = _read_reflog_lines(svc.paths.squad_dir)
    new_lines = after[len(before) :]
    # exactly one new line was appended for the two "create" ops plus the shift itself
    shift_lines = [json.loads(ln) for ln in new_lines if json.loads(ln)["op"] not in ("create",)]
    assert len(shift_lines) == 1, f"expected exactly one shift event, got {shift_lines}"
    entry = shift_lines[0]
    assert entry["target"] == ""
    delta = entry["delta"]
    assert delta["from"] == task.sequence_id
    assert delta["onto"] == 10
    assert delta["by"] is None  # the operator used --onto, not --by
    assert delta["remap"] == result.remap
    assert set(delta["remap"]) == {task.id, bug.id}


async def test_renumber_by_form_records_by_and_leaves_onto_null(svc):
    """The mirror case: a --by shift records `by` and leaves `onto` null in the summary."""
    import json

    task = (await svc.create("task", "shift-me")).item  # counter reaches 2

    result = await svc.renumber(from_seq=task.sequence_id, by=5)

    lines = [json.loads(ln) for ln in _read_reflog_lines(svc.paths.squad_dir)]
    entry = next(ln for ln in lines if ln["op"] == "renumber")
    assert entry["delta"]["onto"] is None
    assert entry["delta"]["by"] == 5
    assert entry["delta"]["remap"] == result.remap


async def test_renumber_leaves_prior_reflog_lines_byte_for_byte_unchanged(svc):
    """The append is a pure append: every line written before the shift is untouched — no
    in-place rewrite of a historical target/delta to the item's new (post-shift) id."""
    bug = (await svc.create("bug", "shift-me")).item

    before = _read_reflog_lines(svc.paths.squad_dir)
    assert before  # sanity: something was already logged (the create above)

    await svc.renumber(from_seq=bug.sequence_id, onto=10)

    after = _read_reflog_lines(svc.paths.squad_dir)
    assert after[: len(before)] == before, "a historical reflog line was rewritten in place"
    assert len(after) == len(before) + 1  # exactly the one appended renumber event
    # the historical line still names the item by its PRE-shift id — a truthful record of
    # what was true when it was written, not silently updated to the new id.
    assert any(bug.id in ln for ln in before)


async def test_renumber_rewrites_a_prose_mention_of_a_shifted_id_in_a_body(svc):
    """A shifted item's id, mentioned in another item's body prose (not a structured ref/
    parent field), is still rewritten — the content-side half of intent preservation."""
    note = (await svc.create("task", "keep-a-note")).item  # stays below --from
    bug = (await svc.create("bug", "shift-me")).item
    await svc.set_body(note.id, f"See {bug.id} for context.")

    result = await svc.renumber(from_seq=bug.sequence_id, onto=10)

    new_bug_id = result.remap[bug.id]
    body = await svc.read_body(note.id)
    assert new_bug_id in body
    assert bug.id not in body


async def test_renumber_nothing_to_shift_is_a_noop(svc):
    result = await svc.renumber(from_seq=999, onto=5)
    assert result.remap == {}


async def test_renumber_unsafe_by_leaves_filesystem_untouched(svc):
    """The refuse-path (unsafe --by) exits before touching a single file."""
    task = (await svc.create("task", "t")).item  # TASK-2, counter=2

    squad_dir = svc.paths.squad_dir
    before_files = sorted(p.name for p in squad_dir.rglob("*.md"))
    before_index = (squad_dir / ".squads.json").read_text(encoding="utf-8")

    with pytest.raises(SquadsError, match="unsafe"):
        await svc.renumber(from_seq=task.sequence_id, by=0)

    after_files = sorted(p.name for p in squad_dir.rglob("*.md"))
    after_index = (squad_dir / ".squads.json").read_text(encoding="utf-8")
    assert before_files == after_files
    assert before_index == after_index


async def test_renumber_requires_exactly_one_of_onto_or_by(svc):
    with pytest.raises(SquadsError, match="exactly one"):
        await svc.renumber(from_seq=1)
    with pytest.raises(SquadsError, match="exactly one"):
        await svc.renumber(from_seq=1, onto=5, by=3)


# --------------------------------------------------------------------------- developers


async def test_dev_add_auto_name_and_slug(svc):
    d1 = await svc.add_dev("dotnet")
    assert d1.extra["slug"] == "dotnet-dev"
    assert d1.extra["full_name"].endswith("Dotnet")
    assert d1.extra["is_dev"] is True
    assert d1.author == "dotnet-dev"  # a dev role authors itself
    d2 = await svc.add_dev("python", name="Grace Hopper")
    assert d2.extra["full_name"] == "Grace Hopper"
    assert d2.extra["slug"] == "python-dev"
    with pytest.raises(SquadsError):
        await svc.add_dev("dotnet")  # duplicate slug


async def test_dev_pointer_generated(svc):
    await svc.add_dev("rust")
    pointer = svc.paths.root / ".claude" / "agents" / "rust-dev.md"
    assert pointer.exists()
    assert "Rust" in pointer.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- skills


async def test_skill_add_generates_pointer(svc):
    skill = await svc.add_skill(
        "PDF extract", description="Pull text", when_to_use="when a pdf is attached"
    )
    assert skill.type == "skill"
    assert skill.status == "Active"
    pointer = svc.paths.root / ".claude" / "skills" / "pdf-extract" / "SKILL.md"
    assert pointer.exists()
    assert skill.path in pointer.read_text(encoding="utf-8")


async def test_skill_rm_purge_removes_pointer_and_file(svc):
    skill = await svc.add_skill("Temp skill")
    path = svc.paths.abspath(skill.path)
    pointer_dir = svc.paths.root / ".claude" / "skills" / "temp-skill"
    assert path.exists() and pointer_dir.exists()
    await svc.remove_item(skill.id, purge=True)
    assert skill.sequence_id not in (await svc.store.load()).items
    assert not path.exists()
    assert not pointer_dir.exists()


# --------------------------------------------------------------------------- author & update


async def test_author_defaults_to_registered_role_and_validates(svc):
    # the svc fixture's minimal roster registers `manager`; create defaults author to it
    task = (await svc.create("task", "t")).item
    assert task.author == "manager"
    # the bundled manager role self-authored at init
    assert (await svc.get("ROLE-000001")).author == "manager"
    # an explicit unregistered author is rejected
    with pytest.raises(SquadsError, match="not a registered agent"):
        await svc.create("task", "x", author="ghost")


async def test_check_flags_author_whose_role_was_removed(svc):
    task = (await svc.create("task", "t", author="manager")).item
    await svc.remove_item((await svc.get("ROLE-000001")).id)  # drop the manager role
    issues = await svc.check()
    assert any(i.item == task.id and "author" in i.message for i in issues)


async def test_assignee_validated_against_roster(svc):
    await svc.add_dev("python")  # registers python-dev as an agent
    task = (await svc.create("task", "t", assignee="python-dev")).item
    assert task.assignee == "python-dev"
    # an unregistered assignee is rejected at create and at update
    with pytest.raises(SquadsError, match="not a registered agent"):
        await svc.create("task", "x", assignee="ghost")
    await svc.update(task.id, assignee="manager")
    assert (await svc.get(task.id)).assignee == "manager"
    with pytest.raises(SquadsError, match="not a registered agent"):
        await svc.update(task.id, assignee="ghost")
    # an empty assignee clears it (no validation)
    await svc.update(task.id, assignee="")
    assert (await svc.get(task.id)).assignee is None


async def test_check_flags_assignee_whose_role_was_removed(svc):
    await svc.add_dev("rust")  # registers rust-dev
    task = (await svc.create("task", "t", assignee="rust-dev")).item
    role = next(
        r for r in await svc.list_items(item_type="role") if r.extra.get("slug") == "rust-dev"
    )
    await svc.remove_item(role.id)
    issues = await svc.check()
    assert any(i.item == task.id and "assignee" in i.message for i in issues)


async def test_update_role_extra_regenerates_pointer(svc, project):
    # minimal roster registers `manager` as ROLE-000001 with a generated .claude pointer
    await svc.update("ROLE-000001", set_extra={"color": "magenta"})
    assert (await svc.get("ROLE-000001")).extra["color"] == "magenta"
    pointer = (project.root / ".claude" / "agents" / "manager.md").read_text(encoding="utf-8")
    assert "color: magenta" in pointer  # the pointer was regenerated from the edited config


async def test_role_body_active_contains_working_agreements(svc):
    """role_body(slug) returns the item body including working agreements when active."""
    # minimal init activates `manager` — its body is generated from the role template.
    body = await svc.role_body("manager")
    assert body is not None
    assert "Working agreements" in body


async def test_role_body_bundled_only_returns_none(svc):
    """role_body(slug) returns None for a bundled-but-not-activated role."""
    # `qa` is bundled but not activated under the minimal spec.
    body = await svc.role_body("qa")
    assert body is None


# --------------------------------------------------------------------------- sync / version


async def test_sync_stamps_version(svc, monkeypatch):
    import squads

    monkeypatch.setattr(squads, "__version__", "9.9.9", raising=False)
    monkeypatch.setattr("squads._services._maintenance.__version__", "9.9.9", raising=False)
    await svc.sync()
    import tomllib

    cfg = tomllib.loads(svc.paths.config_path.read_text(encoding="utf-8"))
    assert cfg["squads_version"] == "9.9.9"


async def test_version_notice_triggers_when_newer(capsys, project, monkeypatch):
    from squads._cli import _common as common

    monkeypatch.setattr(common, "__version__", "9.9.9", raising=False)
    common.set_active_dir(None)
    monkeypatch.chdir(project.root)
    common.version_notice()
    err = capsys.readouterr().err
    assert "sq sync" in err


# --------------------------------------------------------------------------- counter monotonicity


async def test_repair_keeps_counter_after_top_item_deleted(svc):
    """Repair must not regress the counter when the highest-numbered item's file is deleted."""
    await svc.create("feature", "alpha")  # FEAT-000002
    top = (await svc.create("task", "beta")).item  # TASK-000003; counter → 3
    assert (await svc.store.load()).counter == 3

    # Delete the top item's markdown file — simulates accidental or manual removal.
    svc.paths.abspath(top.path).unlink()

    result = await svc.repair()
    # Counter must stay at 3 (the previous high-water mark), not drop to 2.
    assert result.db.counter == 3, "counter must not regress after top-item file loss"
    # The missing id is reported.
    assert top.id in result.missing_ids


async def test_allocate_after_repair_never_reuses(svc):
    """Next create after a repair-after-file-loss must yield max+1, not a reused number."""
    await svc.create("feature", "alpha")  # FEAT-000002
    top = (await svc.create("task", "beta")).item  # TASK-000003; counter → 3

    svc.paths.abspath(top.path).unlink()
    await svc.repair()

    # The next allocation must be 4, never 3.
    new_item = (await svc.create("bug", "new bug")).item
    assert new_item.sequence_id == 4, f"expected sequence 4, got {new_item.sequence_id}"
    assert new_item.id == "BUG-4"


async def test_load_corrects_regressed_counter(svc):
    """load() corrects a regressed counter in memory but leaves the file untouched.

    The corrected counter is then persisted by the next transaction (e.g. create),
    which must allocate max+1 and write the corrected value to disk.
    """
    import json

    await svc.create("feature", "f1")  # FEAT-000002
    await svc.create("task", "t1")  # TASK-000003; counter → 3

    # Simulate a hand-edit that regressed the counter to 1.
    async with svc.store.transaction() as db:
        db.counter = 1

    # File must still have the regressed value of 1 on disk.
    raw_before = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    assert raw_before["counter"] == 1, "file should be unchanged before load()"

    # load() must raise the in-memory counter to max(sequence_ids) = 3 …
    loaded = await svc.store.load()
    assert loaded.counter == 3, f"expected in-memory counter=3 after load, got {loaded.counter}"

    # … but the file must remain untouched (counter still 1 on disk).
    raw_after = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    assert raw_after["counter"] == 1, "load() must not write back to the file"

    # The next create (a transaction) allocates max+1 = 4 and persists counter=4 to disk.
    new_item = (await svc.create("bug", "should be 4")).item
    assert new_item.sequence_id == 4, f"expected sequence 4, got {new_item.sequence_id}"
    raw_persisted = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    assert raw_persisted["counter"] == 4, "transaction must persist the corrected counter"


async def test_repair_reports_missing_ids(svc):
    """Repair surfaces the IDs of items that were indexed but whose files disappeared."""
    feat = (await svc.create("feature", "feature a")).item  # FEAT-000002
    task = (await svc.create("task", "task b")).item  # TASK-000003

    # Delete one file.
    svc.paths.abspath(task.path).unlink()

    result = await svc.repair()
    assert task.id in result.missing_ids
    assert feat.id not in result.missing_ids  # feat is still on disk; not reported


async def test_check_flags_index_item_with_no_file(svc):
    """check() reports an error for items present in the index but missing from disk."""
    task = (await svc.create("task", "t")).item
    # Artificially add a ghost item to the index (no file on disk).
    import json

    raw = json.loads(svc.store.index_path.read_text(encoding="utf-8"))
    raw["items"]["99"] = {
        "id": "TASK-99",
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

    issues = await svc.check()
    assert any(i.item == "TASK-99" and "no markdown" in i.message for i in issues)
    # The real task has no issue.
    assert not any(i.item == task.id and "no markdown" in i.message for i in issues)


# --------------------------------------------------------------------------- ref-kind vocabulary


async def test_add_ref_rejects_unknown_kind(svc):
    """add_ref with an unknown kind raises SquadsError listing the valid kinds."""
    a = (await svc.create("task", "a")).item
    b = (await svc.create("task", "b")).item
    with pytest.raises(SquadsError) as exc_info:
        await svc.add_ref(a.id, b.id, kind="banana")
    msg = str(exc_info.value)
    assert "banana" in msg
    # valid kinds are listed in the error
    for kind in ("related", "blocks", "fixes", "addresses", "supersedes", "duplicates"):
        assert kind in msg


async def test_add_ref_accepts_all_valid_kinds(svc):
    """add_ref accepts each of the eight vocabulary kinds."""
    from squads._models._item import VALID_REF_KINDS

    items = [(await svc.create("task", f"item-{i}")).item for i in range(len(VALID_REF_KINDS))]
    target = (await svc.create("task", "target")).item
    for i, kind in enumerate(sorted(VALID_REF_KINDS)):
        await svc.add_ref(items[i].id, target.id, kind=kind)
        pairs = await svc.refs_out(items[i].id)
        assert pairs == [(target.id, kind)]


async def test_add_ref_bare_defaults_related(svc):
    """add_ref without a kind defaults to 'related' — no nudge, no friction."""
    a = (await svc.create("task", "a")).item
    b = (await svc.create("task", "b")).item
    await svc.add_ref(a.id, b.id)
    fm = read_frontmatter(svc.paths.abspath((await svc.get(a.id)).path))
    assert fm["refs"] == [b.id]  # stored bare (no ':related' suffix)
    assert await svc.refs_out(a.id) == [(b.id, "related")]


async def test_add_ref_three_new_kinds_persist(svc):
    """supersedes, depends-on, duplicates are accepted and round-trip through frontmatter."""
    dec_a = (await svc.create("decision", "old decision")).item
    dec_b = (await svc.create("decision", "new decision")).item
    task_a = (await svc.create("task", "blocker")).item
    task_b = (await svc.create("task", "dependent")).item
    bug_a = (await svc.create("bug", "original")).item
    bug_b = (await svc.create("bug", "duplicate")).item

    await svc.add_ref(dec_b.id, dec_a.id, kind="supersedes")
    await svc.add_ref(task_b.id, task_a.id, kind="depends-on")
    await svc.add_ref(bug_b.id, bug_a.id, kind="duplicates")

    assert await svc.refs_out(dec_b.id) == [(dec_a.id, "supersedes")]
    assert await svc.refs_out(task_b.id) == [(task_a.id, "depends-on")]
    assert await svc.refs_out(bug_b.id) == [(bug_a.id, "duplicates")]

    # verify frontmatter round-trip
    fm_dec = read_frontmatter(svc.paths.abspath((await svc.get(dec_b.id)).path))
    fm_task = read_frontmatter(svc.paths.abspath((await svc.get(task_b.id)).path))
    fm_bug = read_frontmatter(svc.paths.abspath((await svc.get(bug_b.id)).path))
    assert fm_dec["refs"] == [f"{dec_a.id}:supersedes"]
    assert fm_task["refs"] == [f"{task_a.id}:depends-on"]
    assert fm_bug["refs"] == [f"{bug_a.id}:duplicates"]


async def test_create_with_ref_rejects_unknown_kind(svc):
    """svc.create with refs containing an unknown kind raises SquadsError."""
    from squads._models._item import make_ref

    a = (await svc.create("task", "a")).item
    with pytest.raises(SquadsError) as exc_info:
        await svc.create("task", "b", refs=[make_ref(a.id, "bogus")])
    assert "bogus" in str(exc_info.value)


# --------------------------------------------------------------------------- blocked (depends-on)


async def test_blocked_depends_on_equivalent_to_blocks(svc):
    """depends-on produces the same (blocked, [blocker]) pair as the equivalent blocks edge."""
    blocker = (await svc.create("task", "blocker")).item
    dependent = (await svc.create("task", "dependent")).item

    # A depends-on B means A is blocked by B — same as B blocks A
    await svc.add_ref(dependent.id, blocker.id, kind="depends-on")

    pairs = await svc.blocked()
    assert len(pairs) == 1
    blocked_item, blockers = pairs[0]
    assert blocked_item.id == dependent.id
    assert len(blockers) == 1 and blockers[0].id == blocker.id


async def test_blocked_mixed_edges_no_duplicates(svc):
    """An item blocked via both blocks and depends-on appears once with all blockers."""
    blocker_a = (await svc.create("task", "blocker-a")).item
    blocker_b = (await svc.create("task", "blocker-b")).item
    dependent = (await svc.create("task", "dependent")).item

    # blocker_a blocks dependent (edge on blocker_a)
    await svc.add_ref(blocker_a.id, dependent.id, kind="blocks")
    # dependent depends-on blocker_b (edge on dependent)
    await svc.add_ref(dependent.id, blocker_b.id, kind="depends-on")

    pairs = await svc.blocked()
    assert len(pairs) == 1
    blocked_item, blockers = pairs[0]
    assert blocked_item.id == dependent.id
    blocker_ids = {b.id for b in blockers}
    assert blocker_ids == {blocker_a.id, blocker_b.id}


async def test_blocked_closed_blocker_not_included(svc):
    """A closed blocker is not counted; if all blockers are closed the item is not listed."""
    blocker = (await svc.create("task", "blocker")).item
    dependent = (await svc.create("task", "dependent")).item

    await svc.add_ref(dependent.id, blocker.id, kind="depends-on")
    # close the blocker
    await svc.set_status(blocker.id, "InProgress")
    await svc.set_status(blocker.id, "Done")

    assert await svc.blocked() == []


# --------------------------------------------------------------------------- check warnings


async def test_check_warns_on_unknown_ref_kind(svc):
    """check() emits a warn-level issue when a ref has an unknown kind."""
    import squads._sections as sections
    from squads._itemfile import read_frontmatter

    a = (await svc.create("task", "a")).item
    b = (await svc.create("task", "b")).item

    # Inject a junk kind directly into the frontmatter, bypassing add_ref validation.
    path = svc.paths.abspath((await svc.get(a.id)).path)
    text = path.read_text(encoding="utf-8")
    fm = read_frontmatter(text=text)
    fm["refs"] = [f"{b.id}:banana"]
    path.write_text(sections.replace_frontmatter(text, fm), encoding="utf-8")
    await svc.repair()  # sync index with the rewritten frontmatter

    issues = await svc.check()
    warn_issues = [i for i in issues if i.level == "warn" and "banana" in i.message]
    assert len(warn_issues) == 1
    assert warn_issues[0].item == a.id


async def test_check_warns_superseded_decision_without_edge(svc):
    """check() warns when a Superseded decision has no incoming supersedes edge."""
    old_adr = (await svc.create("decision", "old decision")).item
    # Force it to Superseded status
    await svc.set_status(old_adr.id, "Proposed")
    await svc.set_status(old_adr.id, "Superseded", force=True)

    issues = await svc.check()
    warn_issues = [
        i
        for i in issues
        if i.level == "warn" and "supersedes" in i.message and i.item == old_adr.id
    ]
    assert len(warn_issues) == 1


async def test_check_no_warn_superseded_decision_with_edge(svc):
    """check() does NOT warn when a Superseded decision has an incoming supersedes edge."""
    old_adr = (await svc.create("decision", "old decision")).item
    new_adr = (await svc.create("decision", "new decision")).item

    await svc.set_status(old_adr.id, "Proposed")
    await svc.set_status(old_adr.id, "Superseded", force=True)
    # new supersedes old — edge lives on new_adr
    await svc.add_ref(new_adr.id, old_adr.id, kind="supersedes")

    issues = await svc.check()
    superseded_warns = [
        i
        for i in issues
        if i.level == "warn" and "supersedes" in i.message and i.item == old_adr.id
    ]
    assert len(superseded_warns) == 0


# ----------------------------------------------------------------- repair: F2 (REV-000105)


async def test_repair_raises_padding_from_filename_width(svc):
    """repair() raises padding when an item file's digit-run is wider than the stored padding.

    F2 (REV-000105): the filename-recompute arm of repair was untested.  Scenario: stored padding
    is 6 but an item file was renamed to a width-7 name (as repad would do).  repair() must
    detect the wider filename and raise padding to 7.
    """
    import json

    task = (await svc.create("task", "task")).item
    # Confirm default padding.
    assert (await svc.store.load()).padding == 6

    # Rename the task file to a width-7 name to simulate a partial or completed repad.
    old_path = svc.paths.abspath(task.path)
    new_name = old_path.name.replace("TASK-000", "TASK-0000")  # e.g. TASK-0000002-task.md
    new_path = old_path.parent / new_name
    old_path.rename(new_path)

    # Repair should detect the wider filename and raise padding to 7.
    result = await svc.repair()
    assert result.db.padding == 7, "repair must raise padding to match the widest filename"

    # The stored value must also be 7 on disk.
    on_disk = json.loads(svc.paths.index_path.read_text(encoding="utf-8"))
    assert on_disk["padding"] == 7


# --------------------------------------------------------------------------- repad


async def test_repad_renames_files_and_bumps_padding(svc):
    """repad(7) renames all item files to width-7 and stores padding=7."""
    feat = (await svc.create("feature", "feat")).item  # FEAT-000002
    task = (await svc.create("task", "task")).item  # TASK-000003

    renamed = await svc.repad(7)

    # All ID-prefixed item files should now have width-7 digit runs.
    # Skill files use slug-only names (e.g. squads.md, sq-bug.md) and are not repadded — skip them.
    for _, md in svc._iter_item_files():  # pyright: ignore[reportPrivateUsage]
        stem = md.stem
        _, sep, digits_slug = stem.partition("-")
        digit_run = digits_slug.split("-", 1)[0] if sep else ""
        if not digit_run.isdigit():
            continue  # slug-only or non-ID filename (skill files like squads.md) — not repadded
        assert len(digit_run) == 7, f"expected width-7 digit run, got {digit_run!r} in {md.name}"

    # The index must record the new padding.
    db = await svc.store.load()
    assert db.padding == 7

    # Items are keyed by sequence_id — all three items present.
    assert feat.sequence_id in db.items
    assert task.sequence_id in db.items

    # renamed count: every item file (role + feat + task = 3)
    assert renamed == 3


async def test_repad_refuses_to_lower(svc):
    """repad raises SquadsError when the requested width is <= the current padding."""
    await svc.create("task", "t")
    assert (await svc.store.load()).padding == 6

    with pytest.raises(SquadsError, match="must be greater than"):
        await svc.repad(6)

    with pytest.raises(SquadsError, match="must be greater than"):
        await svc.repad(5)


async def test_repad_leaves_file_contents_byte_identical(svc):
    """repad only renames files; the bytes inside each file are unchanged."""
    task = (await svc.create("task", "byte check task")).item

    # Capture the file contents before repad.
    old_path = svc.paths.abspath(task.path)
    original_bytes = old_path.read_bytes()

    await svc.repad(7)

    # The old path no longer exists.
    assert not old_path.exists()

    # Find the renamed file and check that its bytes are identical.
    task_folder = svc.paths.folder_for("task", spec=svc.spec)
    new_files = list(task_folder.glob("TASK-*.md"))
    assert len(new_files) == 1, "expected exactly one task file after repad"
    new_bytes = new_files[0].read_bytes()
    assert new_bytes == original_bytes, "file contents must be byte-identical after repad"


async def test_repad_sq_check_clean_afterwards(svc):
    """sq check must pass on a repadded squad."""
    await svc.create("task", "t")
    await svc.repad(7)
    issues = await svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors, f"sq check errors after repad: {errors}"


async def test_repad_is_idempotent_on_already_wide_files(svc):
    """repad(8) on a width-7 squad: files that are already width-8 are not re-renamed."""
    await svc.create("task", "t")
    await svc.repad(7)
    db7 = await svc.store.load()
    assert db7.padding == 7

    renamed8 = await svc.repad(8)
    db8 = await svc.store.load()
    assert db8.padding == 8
    # All files renamed from width-7 to width-8.
    assert renamed8 > 0


async def test_renumber_plan_uses_supplied_padding(svc):
    """_renumber_plan mints IDs at the supplied padding, not the hard-coded default.

    F1 (REV-000105): simulate a width-7 squad by calling _renumber_plan with padding=7
    and verifying that the minted collision-resolved IDs use 7-digit formatting.
    """
    from pathlib import Path

    from squads._services._maintenance import MaintenanceMixin

    # Build two synthetic _FileRec tuples that collide on sequence 3.
    fid_a = "TASK-000003"
    fid_b = "FEAT-000003"
    fake_path = Path("/fake/path.md")
    records = [
        (fid_a, fake_path, "task", "task", 3),
        (fid_b, fake_path, "feature", "feat", 3),
    ]
    _, renames = MaintenanceMixin._renumber_plan(records, padding=7)  # pyright: ignore[reportPrivateUsage]
    # The reassigned ID must use 7-digit formatting.
    for _path, _item_type, _slug, new_id in renames:
        _, digits_part = new_id.rsplit("-", 1)
        assert len(digits_part) == 7, f"expected 7-digit id, got {new_id!r}"


# --------------------------------------------------------------------------- width-tolerant IDs


async def test_display_stays_unpadded_after_repad(svc):
    """repad() only changes filename width — the displayed id stays unpadded (ADR-000282).

    Display padding is a fixed constant (DISPLAY_ID_PADDING=0); SquadsDB.padding governs
    filenames only and never affects item.id, before or after a repad.
    """
    task = (await svc.create("task", "t")).item
    assert task.id == "TASK-2"

    await svc.repad(7)

    # After repad the stored (filename) padding is 7, but the displayed id is unchanged.
    db = await svc.store.load()
    assert db.padding == 7
    loaded_task = db.items[task.sequence_id]
    assert loaded_task.id == "TASK-2", "display stays unpadded regardless of filename width"


async def test_refs_in_width_tolerant_after_repad(svc):
    """refs_in() is width-tolerant on its query, and its returned id is always unpadded.

    repad() only widens filenames — the stored ref, the displayed id, and refs_in's query
    are all matched/rendered by (prefix, sequence_id), never literal string width
    (ADR-000282). A query at the (now-irrelevant) old or new filename width still resolves.
    """
    feat = (await svc.create("feature", "feat")).item  # FEAT-2
    task = (await svc.create("task", "task")).item  # TASK-3
    await svc.add_ref(task.id, feat.id)  # stores the unpadded ref "FEAT-2"

    await svc.repad(7)

    # feat's displayed id is unchanged by repad; refs_in also tolerates a padded query.
    db = await svc.store.load()
    feat_id = db.items[feat.sequence_id].id
    assert feat_id == "FEAT-2"

    for query in (feat_id, "FEAT-000002", "FEAT-0000002"):
        backrefs = await svc.refs_in(query)
        assert len(backrefs) == 1
        task_id, kind = backrefs[0]
        assert task_id == "TASK-3"
        assert kind == "related"


async def test_backrefs_width_tolerant_after_repad(svc):
    """SquadsDB.backrefs() works with old-width refs after a repad."""
    feat = (await svc.create("feature", "feat")).item
    task = (await svc.create("task", "task")).item
    await svc.add_ref(task.id, feat.id)

    await svc.repad(7)
    db = await svc.store.load()

    feat_new_id = db.items[feat.sequence_id].id  # "FEAT-0000002"
    task_new_id = db.items[task.sequence_id].id  # "TASK-0000003"

    result = db.backrefs(feat_new_id)
    assert result == [task_new_id]


async def test_parent_lookup_width_tolerant_after_repad(svc):
    """Parent stored unpadded still resolves correctly after a filename-only repad.

    index.get(item.parent) is width-tolerant via _seq; _check_items must not report a
    dangling-parent error regardless of the squad's current filename padding.
    """
    feat = (await svc.create("feature", "feat")).item
    task = (await svc.create("task", "task", parent=feat.id)).item
    assert task.parent == "FEAT-2"  # stored unpadded — display is always unpadded

    await svc.repad(7)

    # The parent field in frontmatter is untouched by repad (content is never rewritten).
    db = await svc.store.load()
    loaded_task = db.items[task.sequence_id]
    assert loaded_task.parent == "FEAT-2"

    # index.get resolves it correctly (width-tolerant via _seq) — including a padded query.
    parent_item = db.get(loaded_task.parent)
    assert parent_item is not None
    assert parent_item.sequence_id == feat.sequence_id
    assert db.get("FEAT-000002") is parent_item
    assert db.get("FEAT-0000002") is parent_item

    # sq check must be clean — no dangling-parent errors.
    issues = await svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors, f"errors after repad with old-width parent: {errors}"


async def test_add_ref_dedup_width_tolerant(svc):
    """add_ref() does not duplicate a ref when re-adding across a repad boundary.

    Before repad: item A refs item B ("FEAT-000002").
    After repad:  add_ref(A, "FEAT-0000002") must replace the old ref, not add a second one.
    """
    feat = (await svc.create("feature", "feat")).item
    task = (await svc.create("task", "task")).item
    await svc.add_ref(task.id, feat.id)  # stores "FEAT-000002" in task's refs

    await svc.repad(7)

    db = await svc.store.load()
    feat_new_id = db.items[feat.sequence_id].id  # "FEAT-0000002"
    task_new_id = db.items[task.sequence_id].id

    # Re-add the ref using the new-width ID.
    updated_task = await svc.add_ref(task_new_id, feat_new_id, kind="implements")

    # Only one ref should exist, with the new-width ID and updated kind.
    assert len(updated_task.refs) == 1
    raw_ref = updated_task.refs[0]
    ref_id, _, ref_kind_raw = raw_ref.partition(":")
    ref_kind = ref_kind_raw or "related"
    assert "FEAT" in ref_id  # canonical form
    assert ref_kind == "implements"


async def test_rm_ref_width_tolerant(svc):
    """rm_ref() removes a ref stored with old-width ID when addressed with new-width ID."""
    feat = (await svc.create("feature", "feat")).item
    task = (await svc.create("task", "task")).item
    await svc.add_ref(task.id, feat.id)  # stores "FEAT-000002"

    await svc.repad(7)
    db = await svc.store.load()
    feat_new_id = db.items[feat.sequence_id].id
    task_new_id = db.items[task.sequence_id].id

    # Remove using the new-width ID — must find and remove the old-width stored ref.
    result = await svc.rm_ref(task_new_id, feat_new_id)
    assert result.refs == []


async def test_check_decisions_width_tolerant_after_repad(svc):
    """_check_decisions does not false-warn when the supersedes ref uses the old width."""
    adr1 = (await svc.create("decision", "old decision")).item
    adr2 = (await svc.create("decision", "new decision")).item
    await svc.add_ref(adr2.id, adr1.id, kind="supersedes")
    await svc.set_status(adr1.id, "Superseded", force=True)

    await svc.repad(7)

    # After repad, _check_decisions must not warn about the old-width supersedes ref.
    issues = await svc.check()
    superseded_warns = [i for i in issues if "Superseded" in i.message and i.item == adr1.id]
    assert not superseded_warns, f"spurious Superseded warning after repad: {superseded_warns}"


async def test_end_to_end_repad_resolution(svc):
    """Full acceptance test: repad to width-7, every ref/parent/mention still resolves.

    This is the joint acceptance seam with FEAT-000027: after sq migrate repad(7), the
    displayed id stays unpadded (ADR-000282), all stored refs/parent/CLI addressing keep
    working at any queried width, and sq check must be clean.
    """
    # Build a squad with cross-references and parent links (all stored unpadded).
    feat = (await svc.create("feature", "feat")).item  # FEAT-2
    task = (await svc.create("task", "task", parent=feat.id)).item  # TASK-3, parent FEAT-2
    bug = (await svc.create("bug", "bug")).item  # BUG-4
    await svc.add_ref(task.id, bug.id, kind="fixes")  # TASK-3 fixes BUG-4
    await svc.add_ref(feat.id, task.id, kind="related")  # FEAT-2 refs TASK-3

    # Confirm unpadded state.
    assert task.parent == "FEAT-2"
    assert await svc.refs_in(bug.id) == [(task.id, "fixes")]

    # --- Repad to width 7 (filenames only) ---
    renamed = await svc.repad(7)
    assert renamed > 0

    # After repad, the squad's filename width is 7.
    db = await svc.store.load()
    assert db.padding == 7

    # Display is unaffected by repad — still unpadded.
    feat7 = db.items[feat.sequence_id]
    task7 = db.items[task.sequence_id]
    bug7 = db.items[bug.sequence_id]
    assert feat7.id == "FEAT-2"
    assert task7.id == "TASK-3"
    assert bug7.id == "BUG-4"

    # Parent ("FEAT-2") resolves to the correct item.
    parent_item = db.get(task7.parent)  # task7.parent is still "FEAT-2"
    assert parent_item is not None
    assert parent_item.sequence_id == feat.sequence_id

    # refs_in finds the stored ref.
    bug_backrefs = await svc.refs_in(bug7.id)
    assert any(seq_id == task7.id for seq_id, _ in bug_backrefs), (
        f"TASK-3 must appear in BUG-4 backrefs; got {bug_backrefs}"
    )

    # backrefs on the DB level.
    assert task7.id in db.backrefs(bug7.id)

    # CLI addressing with the unpadded id resolves to the item.
    assert db.get("FEAT-2") is feat7
    assert db.get("TASK-3") is task7
    assert db.get("BUG-4") is bug7

    # CLI addressing with a padded variant (old or new filename width) also resolves
    # (db.get is width-tolerant regardless of what's actually stored/displayed).
    assert db.get("FEAT-000002") is feat7
    assert db.get("FEAT-0000002") is feat7
    assert db.get("TASK-000003") is task7
    assert db.get("TASK-0000003") is task7

    # sq check is clean (no dangling refs, no dangling parents, no reconciliation errors).
    issues = await svc.check()
    errors = [i for i in issues if i.level == "error"]
    assert not errors, f"sq check errors after repad: {errors}"


async def test_repair_after_repad_no_spurious_missing(svc):
    """F3 (REV-000106): repair() after repad must not report any items as missing.

    Before the F1 fix, _propagate_padding widens item.id strings in the prev snapshot
    (width-7) while from_frontmatter rebuilds at the default width-6, so
    previous_ids - found_ids equals the entire corpus.  This test must FAIL against that
    bug and pass only after repair() computes missing_ids by sequence_id (int).
    """
    feat = (await svc.create("feature", "feat")).item
    task = (await svc.create("task", "task", parent=feat.id)).item
    bug = (await svc.create("bug", "bug")).item
    await svc.add_ref(task.id, bug.id, kind="fixes")

    # Repad to width 7 — renames files, leaves frontmatter IDs at width 6.
    renamed = await svc.repad(7)
    assert renamed > 0

    # Running repair() again after repad must not report any spurious missing items.
    rr = await svc.repair()
    assert rr.missing_ids == [], (
        f"repair() reported spurious missing items after repad: {rr.missing_ids}"
    )


# --------------------------------------------------------------------------- async consumer


async def test_async_consumer(project, frozen_time):
    """Async consumer drives the service with no anyio.run / to_thread in the consumer itself.

    The consumer exercises the write path (comment via async transaction) then the read path
    (get + read_body + read_discussion via async IO).  Migrated from tests/test_async_spike.py
    (US1 acceptance demo, C8 / F6, REV-000154).
    """
    from squads._services import _service as service

    svc = service.Service(project)

    res = await svc.create("task", "Async consumer demo", author="manager")
    task_id = res.item.id

    item = await svc.comment(task_id, ["hello from async world"], as_slug="manager")
    assert item.id == task_id

    it = await svc.get(task_id)
    assert it.id == task_id

    body = await svc.read_body(task_id)
    assert isinstance(body, str)

    disc = await svc.read_discussion(task_id)
    assert "hello from async world" in disc
