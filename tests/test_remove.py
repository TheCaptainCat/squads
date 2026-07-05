"""Tests for ``Service.remove_work_item()`` and the ``sq <type> <n> remove`` CLI verb.

Covers ADR-000114:
- Hard delete (file + index entry atomically); counter high-water mark never shrinks.
- Default refuses on incoming refs or children; --force severs refs; children always block.
- Sequence gap is sanctioned: sq repair does not reissue the number.
- Interactive confirm respected; --yes skips it.
- --json output.
- REV-000115 F1/F2 retype cleanup tested implicitly via the retype tests (no new test needed
  here; the type-annotation corrections do not change observable behaviour).
"""

import json

import pytest

from squads._cli import app
from squads._errors import SquadsError
from squads._models._enums import ItemType

pytestmark = pytest.mark.anyio

# =========================================================================== service-level tests


async def test_remove_work_item_deletes_file_and_index_entry(svc):
    """Hard delete: file gone, index entry gone, counter unchanged."""
    task = (await svc.create(ItemType.TASK, "Oops")).item
    seq = task.sequence_id
    path = svc.paths.abspath(task.path)
    counter_before = (await svc.store.load()).counter

    assert path.exists()
    assert seq in (await svc.store.load()).items

    res = await svc.remove_work_item(task.id, force=False)

    assert res.removed_id == task.id
    assert res.severed_refs == []
    assert not path.exists()
    db = await svc.store.load()
    assert seq not in db.items
    # Counter is preserved (ADR-000114 §4)
    assert db.counter == counter_before


async def test_remove_work_item_counter_never_shrinks_and_repair_respects_gap(svc):
    """The freed sequence number is never reissued after remove + repair (ADR-000114 §4)."""
    task = (await svc.create(ItemType.TASK, "Gone")).item
    removed_seq = task.sequence_id
    counter_after_create = (await svc.store.load()).counter

    await svc.remove_work_item(task.id)

    # counter unchanged
    assert (await svc.store.load()).counter == counter_after_create

    # repair must not reissue the freed number
    await svc.repair()
    db_after = await svc.store.load()
    assert db_after.counter == counter_after_create
    assert removed_seq not in db_after.items

    # a new item gets the *next* number, not the freed one
    new_task = (await svc.create(ItemType.TASK, "New")).item
    assert new_task.sequence_id > removed_seq
    assert new_task.sequence_id not in {removed_seq}


async def test_remove_refuses_on_incoming_refs_without_force(svc):
    """Default (no --force): refuses and lists the referrer."""
    task = (await svc.create(ItemType.TASK, "Target")).item
    other = (await svc.create(ItemType.TASK, "Referrer")).item
    await svc.add_ref(other.id, task.id)

    with pytest.raises(SquadsError, match=other.id):
        await svc.remove_work_item(task.id)

    # item still in index
    assert (await svc.store.load()).get(task.id) is not None


async def test_remove_force_severs_incoming_refs(svc):
    """--force: severs the incoming ref from the referrer and removes the item."""
    task = (await svc.create(ItemType.TASK, "Target")).item
    other = (await svc.create(ItemType.TASK, "Referrer")).item
    await svc.add_ref(other.id, task.id, kind="related")

    res = await svc.remove_work_item(task.id, force=True)

    assert res.severed_refs == [other.id]
    # item gone
    assert (await svc.store.load()).get(task.id) is None
    # referrer's ref list is empty
    referrer_after = await svc.get(other.id)
    assert referrer_after.refs == []
    # sq check is clean (no dangling ref)
    issues = await svc.check()
    assert not any("dangling" in i.message.lower() for i in issues)


async def test_remove_force_severs_multiple_referrers(svc):
    """--force severs all incoming refs (multiple referrers)."""
    target = (await svc.create(ItemType.TASK, "T")).item
    a = (await svc.create(ItemType.TASK, "A")).item
    b = (await svc.create(ItemType.BUG, "B")).item
    await svc.add_ref(a.id, target.id, kind="related")
    await svc.add_ref(b.id, target.id, kind="blocks")

    res = await svc.remove_work_item(target.id, force=True)

    assert sorted(res.severed_refs) == sorted([a.id, b.id])
    assert (await svc.get(a.id)).refs == []
    assert (await svc.get(b.id)).refs == []


async def test_remove_refuses_when_children_exist_even_with_force(svc):
    """Children block removal even with --force; the hint lists them."""
    feat = (await svc.create(ItemType.FEATURE, "Parent feat")).item
    task = (await svc.create(ItemType.TASK, "Child task")).item
    await svc.link(task.id, feat.id)

    with pytest.raises(SquadsError, match=task.id):
        await svc.remove_work_item(feat.id, force=True)

    # feature still present
    assert (await svc.store.load()).get(feat.id) is not None


async def test_remove_succeeds_after_child_removed(svc):
    """After removing the child, the parent can be removed."""
    feat = (await svc.create(ItemType.FEATURE, "F")).item
    task = (await svc.create(ItemType.TASK, "T")).item
    await svc.link(task.id, feat.id)

    await svc.remove_work_item(task.id)
    res = await svc.remove_work_item(feat.id)

    assert res.removed_id == feat.id
    assert not svc.paths.abspath(feat.path).exists()


async def test_remove_no_refs_or_children_passes_without_force(svc):
    """A bare item (no refs, no children) is removed without --force."""
    bug = (await svc.create(ItemType.BUG, "Small bug")).item
    res = await svc.remove_work_item(bug.id)
    assert res.removed_id == bug.id


async def test_remove_check_clean_after_forced_removal(svc):
    """sq check is clean after a forced removal that severs refs."""
    a = (await svc.create(ItemType.TASK, "A")).item
    b = (await svc.create(ItemType.TASK, "B")).item
    await svc.add_ref(a.id, b.id, kind="depends-on")

    await svc.remove_work_item(b.id, force=True)

    issues = await svc.check()
    dangling = [i for i in issues if "dangling" in i.message.lower()]
    assert dangling == []


async def test_remove_width_tolerant_ref_severing(svc):
    """Ref severing is width-tolerant: a ref stored at the old width is still found."""
    from squads._models._item import make_ref

    target = (await svc.create(ItemType.BUG, "Bug")).item
    referrer = (await svc.create(ItemType.TASK, "Task")).item

    # Manually inject a ref at a narrower width (simulates pre-repad ref text)
    old_width_id = f"BUG-{target.sequence_id:04d}"  # 4-digit, current default is 6
    async with svc.store.transaction() as db:
        r_item = db.get(referrer.id)
        assert r_item is not None
        r_item.refs = [make_ref(old_width_id, "related")]
        from squads._index._resolver import item_file
        from squads._itemfile import update_frontmatter

        await update_frontmatter(item_file(svc.paths, r_item), r_item)

    # --force must still sever the narrower-width ref
    res = await svc.remove_work_item(target.id, force=True)
    assert referrer.id in res.severed_refs
    assert (await svc.get(referrer.id)).refs == []


async def test_remove_children_helper_returns_correct_list(svc):
    """SquadsDB.children() returns direct children by parent field."""
    feat = (await svc.create(ItemType.FEATURE, "F")).item
    task1 = (await svc.create(ItemType.TASK, "T1")).item
    task2 = (await svc.create(ItemType.TASK, "T2")).item
    await svc.link(task1.id, feat.id)
    await svc.link(task2.id, feat.id)

    db = await svc.store.load()
    children = db.children(feat.id)
    assert sorted(children) == sorted([task1.id, task2.id])

    # unrelated item not in children
    other = (await svc.create(ItemType.TASK, "Other")).item
    assert other.id not in db.children(feat.id)


# =========================================================================== CLI tests


def test_cli_remove_basic(runner, tmp_path, monkeypatch, frozen_time):
    """sq <type> <n> remove --yes removes the item without a prompt."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Oops", "--author", "manager"])  # TASK-000002

    r = runner.invoke(app, ["task", "2", "remove", "--yes"])

    assert r.exit_code == 0, r.output
    assert "TASK-2" in r.output
    assert "removed" in r.output


def test_cli_remove_requires_confirm(runner, tmp_path, monkeypatch, frozen_time):
    """Without --yes, the command asks for confirmation; 'n' aborts."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Oops", "--author", "manager"])  # TASK-000002

    # typer.confirm with abort=True raises SystemExit when input is 'n'
    r = runner.invoke(app, ["task", "2", "remove"], input="n\n")

    assert r.exit_code != 0


def test_cli_remove_json_output(runner, tmp_path, monkeypatch, frozen_time):
    """sq <type> <n> remove --yes --json returns structured JSON."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Gone", "--author", "manager"])  # TASK-000002

    r = runner.invoke(app, ["task", "2", "remove", "--yes", "--json"])

    assert r.exit_code == 0, r.output
    data = json.loads(r.output)
    assert data["removed_id"] == "TASK-2"
    assert data["severed_refs"] == []


def test_cli_remove_refuses_on_incoming_refs(runner, tmp_path, monkeypatch, frozen_time):
    """CLI remove without --force exits 1 and names the referrer."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Target", "--author", "manager"])  # TASK-000002
    runner.invoke(app, ["create", "task", "Referrer", "--author", "manager"])  # TASK-000003
    runner.invoke(app, ["task", "3", "ref", "add", "TASK-000002"])

    r = runner.invoke(app, ["task", "2", "remove", "--yes"])

    assert r.exit_code == 1
    assert "TASK-3" in r.output


def test_cli_remove_force_severs_refs(runner, tmp_path, monkeypatch, frozen_time):
    """CLI remove --force severs refs and prints the severed list."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Target", "--author", "manager"])  # TASK-000002
    runner.invoke(app, ["create", "task", "Referrer", "--author", "manager"])  # TASK-000003
    runner.invoke(app, ["task", "3", "ref", "add", "TASK-000002"])

    r = runner.invoke(app, ["task", "2", "remove", "--yes", "--force"])

    assert r.exit_code == 0, r.output
    assert "TASK-2" in r.output
    assert "TASK-3" in r.output


def test_cli_remove_refuses_children_even_with_force(runner, tmp_path, monkeypatch, frozen_time):
    """Children block removal even with --force."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "feature", "Feat", "--author", "manager"])  # FEAT-000002
    runner.invoke(  # TASK-000003
        app, ["create", "task", "Task", "--author", "manager", "--parent", "FEAT-000002"]
    )

    r = runner.invoke(app, ["feature", "2", "remove", "--yes", "--force"])

    assert r.exit_code == 1
    assert "TASK-3" in r.output


async def test_remove_unlink_happens_before_index_commit_no_resurrection(svc, monkeypatch):
    """Atomicity / no-resurrection property (REV-000116 F1).

    The .md unlink must happen *inside* the transaction body — before the index commit.

    Simulate a crash at commit time: patch _atomic_write to raise so the index is never
    updated on disk.  After the exception:

    - The .md must already be gone (unlink ran before the commit → safe failure direction).
    - The on-disk index still has the item (commit never landed).
    - sq repair rebuilds from .md files: no .md found → seq is absent from the rebuilt
      index.  The item is NOT resurrected.

    Contrast: if unlink ran *after* the commit (old code), a crash between commit and unlink
    would leave the index-entry gone but the .md surviving.  repair would re-adopt the .md
    and resurrect the removed item with its old sequence number.
    """
    from squads._index._store import IndexStore

    task = (await svc.create(ItemType.TASK, "AtomicCheck")).item
    seq = task.sequence_id
    path = svc.paths.abspath(task.path)

    assert path.exists()
    assert seq in (await svc.store.load()).items

    # Capture the original _atomic_write before patching so we can restore it later.
    original_atomic_write = IndexStore._atomic_write  # type: ignore[attr-defined]

    def _crash_on_write(self, db):  # type: ignore[no-untyped-def]
        """Raise to simulate the process dying before the atomic os.replace."""
        raise OSError("simulated crash during index commit")

    monkeypatch.setattr(IndexStore, "_atomic_write", _crash_on_write)

    with pytest.raises(OSError, match="simulated crash"):
        await svc.remove_work_item(task.id)

    # The .md must be gone — unlink ran before the failed commit.
    assert not path.exists(), (
        "file still exists after simulated commit crash; "
        "unlink ran after the index commit (F1 regression: "
        "resurrection via repair is now possible)"
    )

    # The on-disk index was not updated (commit raised); seq still present.
    assert seq in (await svc.store.load()).items

    # Restore _atomic_write so repair can write the rebuilt index.
    monkeypatch.setattr(IndexStore, "_atomic_write", original_atomic_write)

    # repair scans .md files → no .md for seq → seq absent from rebuilt index.
    # The item is NOT resurrected.
    await svc.repair()
    db_after = await svc.store.load()
    assert seq not in db_after.items, (
        "repair resurrected the removed item — the orphaned .md must not survive the crash"
    )


def test_cli_remove_counter_and_repair(runner, tmp_path, monkeypatch, frozen_time):
    """After remove + repair the counter is stable and number is not reissued."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    runner.invoke(app, ["create", "task", "Removed", "--author", "manager"])  # TASK-000002
    runner.invoke(app, ["create", "task", "Kept", "--author", "manager"])  # TASK-000003

    r = runner.invoke(app, ["task", "2", "remove", "--yes"])
    assert r.exit_code == 0, r.output

    # repair must not error and must not reissue seq 2
    r2 = runner.invoke(app, ["repair"])
    assert r2.exit_code == 0, r2.output

    # create a new item — it must NOT get sequence 2
    r3 = runner.invoke(app, ["create", "task", "New", "--author", "manager", "--json"])
    assert r3.exit_code == 0, r3.output
    data = json.loads(r3.output)
    suffix = int(data["id"].rsplit("-", 1)[1])
    assert suffix > 3  # must be beyond the last allocated number (3), not the gap (2)
