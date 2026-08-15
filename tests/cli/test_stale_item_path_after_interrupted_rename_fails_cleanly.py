"""An interrupted title-changing update physically moves an item's file before the index
commits, leaving the index naming a path the file no longer lives at. That skew is sanctioned
(`sq repair` always resolves it) -- what must not happen is a raw, uncaught `FileNotFoundError`
reaching the terminal on every verb that reads the file's content in the meantime.

Pins the user-visible outcome (what reaches the terminal), not just the exception type -- a
test asserting only that a `SquadsError` was raised would pass even if the CLI still printed a
traceback around it.
"""

import pytest

from _helpers import create_item
from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio

#: Frames that must never reach the terminal once the stale-path seam is guarded.
_FORBIDDEN_SNIPPETS = ("Traceback", "site-packages", ".venv", "FileNotFoundError")


def _assert_clean_failure(output: str, *, item_id: str) -> None:
    for snippet in _FORBIDDEN_SNIPPETS:
        assert snippet not in output, f"{snippet!r} leaked into output:\n{output}"
    assert "error:" in output
    assert item_id in output
    assert "sq repair" in output.replace("\n", " ")


async def _interrupt_a_title_changing_update(svc, monkeypatch, item_id: str) -> None:
    """Crash the index commit right after the physical rename + frontmatter rewrite land --
    the file is at its new path; the index still names the old one."""
    real_atomic_write = IndexStore._atomic_write

    async def _boom(self, db):
        raise OSError("simulated crash during the index commit")

    monkeypatch.setattr(IndexStore, "_atomic_write", _boom)
    try:
        with pytest.raises(OSError):
            await svc.update(item_id, title="renamed mid crash")
    finally:
        monkeypatch.setattr(IndexStore, "_atomic_write", real_atomic_write)


async def test_show_full_fails_cleanly_after_an_interrupted_rename(svc, invoke, monkeypatch):
    task = (await create_item(svc, "task", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, task.id)

    result = await invoke(["task", str(task.sequence_id), "show", "--full"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, item_id=task.id)


async def test_comment_fails_cleanly_after_an_interrupted_rename(svc, invoke, monkeypatch):
    task = (await create_item(svc, "task", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, task.id)

    result = await invoke(["task", str(task.sequence_id), "comment", "--as", "manager", "-m", "hi"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, item_id=task.id)


async def test_the_comments_readback_verb_fails_cleanly_after_an_interrupted_rename(
    svc, invoke, monkeypatch
):
    task = (await create_item(svc, "task", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, task.id)

    result = await invoke(["task", str(task.sequence_id), "comments"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, item_id=task.id)


async def test_a_subtask_body_read_fails_cleanly_after_an_interrupted_rename(
    svc, invoke, monkeypatch
):
    task = (await create_item(svc, "task", "Original title")).item
    added = await svc.add_subtask(task.id, "A subtask")
    await _interrupt_a_title_changing_update(svc, monkeypatch, task.id)

    result = await invoke(["task", str(task.sequence_id), "subtask", added.local_id, "show"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, item_id=task.id)


async def test_plain_show_also_fails_cleanly_since_it_reads_the_body_too(svc, invoke, monkeypatch):
    """Plain `show` (no `--full`) still renders the body region -- it is not purely
    index-derived -- so it hits the same stale-path seam and must fail the same clean way,
    not a raw traceback, even though it never asked for `--full`."""
    task = (await create_item(svc, "task", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, task.id)

    result = await invoke(["task", str(task.sequence_id), "show"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, item_id=task.id)


async def test_list_stays_index_only_and_unaffected_by_the_stale_path(svc, invoke, monkeypatch):
    task = (await create_item(svc, "task", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, task.id)

    result = await invoke(["list", "-a"])
    assert result.exit_code == 0, result.output
    assert task.id in result.output
    for snippet in _FORBIDDEN_SNIPPETS:
        assert snippet not in result.output


async def test_everything_works_again_after_repair(svc, invoke, monkeypatch):
    task = (await create_item(svc, "task", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, task.id)

    repaired = await invoke(["repair"])
    assert repaired.exit_code == 0, repaired.output

    shown = await invoke(["task", str(task.sequence_id), "show", "--full"])
    assert shown.exit_code == 0, shown.output

    commented = await invoke(
        ["task", str(task.sequence_id), "comment", "--as", "manager", "-m", "hi"]
    )
    assert commented.exit_code == 0, commented.output


# ---------------------------------------------------------------------------------------------
# The read verbs above were the first seams routed through the clean-failure conversion; these
# mutating ones were left crashing raw in the exact same state. Same fixture, same forbidden
# frames, same repairable outcome -- write verbs get no different a story than read ones.
# ---------------------------------------------------------------------------------------------


async def test_updating_the_description_fails_cleanly_after_an_interrupted_rename(
    svc, invoke, monkeypatch
):
    task = (await create_item(svc, "task", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, task.id)

    result = await invoke(["task", str(task.sequence_id), "update", "--desc", "new summary"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, item_id=task.id)


async def test_changing_status_fails_cleanly_after_an_interrupted_rename(svc, invoke, monkeypatch):
    task = (await create_item(svc, "task", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, task.id)

    result = await invoke(["task", str(task.sequence_id), "status", "InProgress"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, item_id=task.id)


async def test_adding_a_subtask_fails_cleanly_after_an_interrupted_rename(svc, invoke, monkeypatch):
    task = (await create_item(svc, "task", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, task.id)

    result = await invoke(["task", str(task.sequence_id), "add-subtask", "A new subtask"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, item_id=task.id)


async def test_the_mutating_verbs_all_work_again_after_repair(svc, invoke, monkeypatch):
    task = (await create_item(svc, "task", "Original title")).item
    await _interrupt_a_title_changing_update(svc, monkeypatch, task.id)

    repaired = await invoke(["repair"])
    assert repaired.exit_code == 0, repaired.output

    updated = await invoke(["task", str(task.sequence_id), "update", "--desc", "new summary"])
    assert updated.exit_code == 0, updated.output

    stated = await invoke(["task", str(task.sequence_id), "status", "InProgress"])
    assert stated.exit_code == 0, stated.output

    added = await invoke(["task", str(task.sequence_id), "add-subtask", "A new subtask"])
    assert added.exit_code == 0, added.output
