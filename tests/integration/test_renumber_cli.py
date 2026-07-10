"""`sq renumber` — the pre-merge block-shift command: reassigns one branch's local IDs into a
range disjoint from another branch's, rewriting refs/parents and renaming files so referential
intent survives the shift, driven through the real CLI end to end.
"""

import pytest

from squads._services._service import Service

pytestmark = pytest.mark.anyio


async def test_renumber_shifts_a_block_and_rewrites_refs_and_files(project, invoke):
    svc = Service(project)
    feat = (await svc.create("feature", "keep")).item  # below --from: never shifted
    task = (await svc.create("task", "shift-task", parent=feat.id)).item
    bug = (await svc.create("bug", "shift-bug")).item
    await svc.add_ref(task.id, bug.id)

    result = await invoke(["renumber", "--from", str(task.sequence_id), "--onto", "10"])
    assert result.exit_code == 0, result.output
    assert "renumbered 2 item(s)" in result.output
    assert f"{feat.id} ->" not in result.output

    db = await svc.store.load()
    # the counter lands above both the other branch's counter (10) and this branch's own max
    assert db.counter > 10
    old_bug_path = svc.paths.abspath(bug.path)
    assert not old_bug_path.exists()
    new_bug = next(it for it in db.items.values() if it.title == "shift-bug")
    assert svc.paths.abspath(new_bug.path).exists()
    # the task's ref now points at the same (renumbered) bug — referential intent preserved
    new_task = next(it for it in db.items.values() if it.title == "shift-task")
    assert new_task.refs == [new_bug.id]
    assert new_task.parent == feat.id  # a link crossing the shift boundary still resolves


async def test_renumber_rejects_specifying_both_onto_and_by(project, invoke):
    result = await invoke(["renumber", "--from", "2", "--onto", "5", "--by", "3"])
    assert result.exit_code != 0
    assert "exactly one" in result.output.lower()


async def test_renumber_refuses_an_unsafe_by_offset_with_zero_mutation(project, invoke):
    svc = Service(project)
    index_path = svc.store.index_path
    before = index_path.read_text(encoding="utf-8")

    result = await invoke(["renumber", "--from", "1", "--by", "0"])
    assert result.exit_code == 1, result.output
    assert "minimum safe offset" in result.output

    assert index_path.read_text(encoding="utf-8") == before


def test_renumber_is_listed_in_root_help_with_the_onto_recipe(runner, tmp_path, monkeypatch):
    import re

    monkeypatch.chdir(tmp_path)
    from squads._cli import app

    _ansi = re.compile(r"\x1b\[[0-9;]*m")

    root = runner.invoke(app, ["--help"])
    assert root.exit_code == 0, root.output
    assert "renumber" in root.output

    sub = runner.invoke(app, ["renumber", "--help"])
    assert sub.exit_code == 0, sub.output
    help_text = _ansi.sub("", sub.output)  # tolerate a color-forcing help console
    assert "--onto" in help_text and "--by" in help_text
    assert "squads.json" in help_text and "jq .counter" in help_text
