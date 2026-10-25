"""A write that cannot get the index lock exits 1 with a one-line error on stderr and no traceback,
and stdout stays empty."""

import functools

import pytest

from _helpers import create_item, hold_lock
from squads._index._store import IndexStore

pytestmark = pytest.mark.anyio


async def test_write_held_past_the_timeout_exits_one_with_a_clean_stderr(
    project, svc, invoke, monkeypatch
):
    created = await create_item(svc, "task", "Held")
    monkeypatch.setattr(
        "squads._services._service.IndexStore", functools.partial(IndexStore, lock_timeout=2)
    )
    holder = hold_lock(project.lock_path, 4)
    try:
        result = await invoke(
            ["task", str(created.item.sequence_id), "comment", "--as", "manager", "-m", "probe"]
        )
    finally:
        holder.wait()
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert "nothing was written" in result.stderr
    assert str(project.lock_path) in result.stderr.replace("\n", "")
