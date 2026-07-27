"""`_aio.atomic_write_text`'s contract: after it returns, the target holds either the
complete new text or its complete previous bytes -- never a prefix of either -- and no
temp file survives a successful write.
"""

import pathlib

import pytest

from squads import _aio

pytestmark = pytest.mark.anyio


async def test_writing_over_an_existing_file_yields_exactly_the_new_content(tmp_path):
    path = tmp_path / "item.md"
    path.write_text("old content", encoding="utf-8")

    await _aio.atomic_write_text(path, "brand new content")

    assert path.read_text(encoding="utf-8") == "brand new content"


async def test_no_temp_file_survives_a_successful_write(tmp_path):
    path = tmp_path / "item.md"

    await _aio.atomic_write_text(path, "hello")

    leftovers = [p for p in tmp_path.iterdir() if p != path]
    assert leftovers == []


async def test_a_failure_between_the_temp_write_and_the_replace_leaves_previous_bytes_exactly(
    tmp_path, monkeypatch
):
    """Patches the writer to fail right after the temp file is fully written (flushed and
    fsynced) but before `Path.replace` ever runs -- the exact window the primitive exists to
    make harmless."""
    path = tmp_path / "item.md"
    path.write_text("previous bytes", encoding="utf-8")

    original_replace = pathlib.Path.replace

    def _replace_then_raise(self, target):
        raise OSError("simulated crash after the temp write, before the replace")

    monkeypatch.setattr(pathlib.Path, "replace", _replace_then_raise)

    with pytest.raises(OSError, match="simulated crash"):
        await _aio.atomic_write_text(path, "new bytes that should never land")

    monkeypatch.setattr(pathlib.Path, "replace", original_replace)

    # The target -- the file every reader/repair actually looks at -- was never touched.
    assert path.read_text(encoding="utf-8") == "previous bytes"
    # The half-committed temp file is left behind (a failed write is not itself cleaned up;
    # it is gitignored -- see `*.tmp` -- and orphaned only on this out-of-model failure path).
    tmp_leftovers = list(tmp_path.glob("*.tmp"))
    assert len(tmp_leftovers) == 1


async def test_the_temp_name_carries_pid_and_thread_id_so_concurrent_writers_never_collide(
    tmp_path, monkeypatch
):
    import os
    import re

    path = tmp_path / "item.md"
    seen: list[str] = []
    original_replace = pathlib.Path.replace

    def _spy_replace(self, target):
        seen.append(self.name)
        return original_replace(self, target)

    monkeypatch.setattr(pathlib.Path, "replace", _spy_replace)

    await _aio.atomic_write_text(path, "content")

    assert len(seen) == 1
    # pid is this process's; the thread id belongs to whichever worker thread `to_thread`
    # ran the write on -- just needs to be present and numeric, not equal to the test's own.
    assert re.fullmatch(rf"item\.md\.{os.getpid()}\.\d+\.tmp", seen[0])
