"""Board notices are squad data (posted content with no regeneration path), not a regenerable
artifact: posting one must go through the atomic primitive, never the bare truncate-in-place
`_aio.write_text` -- so a killed process can't leave a truncated notice, and a future reach-in
that bypasses the primitive is caught rather than silently reintroducing the hazard.
"""

import pathlib

import pytest

from squads import _aio

pytestmark = pytest.mark.anyio


def _notice_path(svc, notice) -> pathlib.Path:
    return svc.paths.squad_dir / "board" / f"{notice.id}.md"


async def test_posting_a_notice_goes_through_the_atomic_primitive(svc, monkeypatch):
    calls: list[tuple[pathlib.Path, str]] = []
    original = _aio.atomic_write_text

    async def _spy(path, text):
        calls.append((path, text))
        await original(path, text)

    async def _fail_if_reached(path, text):
        raise AssertionError(f"non-atomic _aio.write_text was called for {path}")

    monkeypatch.setattr(_aio, "atomic_write_text", _spy)
    monkeypatch.setattr(_aio, "write_text", _fail_if_reached)

    notice = await svc.board_post("op-pierre", "a notice for the board")

    assert len(calls) == 1
    assert calls[0][0] == _notice_path(svc, notice)


async def test_a_failure_between_the_temp_write_and_the_replace_leaves_no_notice_file(svc):
    def _raise(self, target):
        raise OSError("simulated crash after the temp write, before the replace")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pathlib.Path, "replace", _raise)
        with pytest.raises(OSError, match="simulated crash"):
            await svc.board_post("op-pierre", "a notice that never lands")

    # The create direction: no notice existed at this content-derived path before, so an
    # interrupted write must leave nothing there -- never a half-written orphan.
    board_folder = svc.paths.squad_dir / "board"
    on_disk = list(board_folder.glob("*.md")) if board_folder.is_dir() else []
    assert on_disk == []

    # A normal (uninterrupted) post afterwards still works fine.
    notice = await svc.board_post("op-pierre", "a notice that lands cleanly")
    assert _notice_path(svc, notice).read_text(encoding="utf-8")


async def test_an_interrupted_post_never_disturbs_an_existing_notice(svc):
    existing = await svc.board_post("op-pierre", "an existing notice, untouched by later posts")
    existing_bytes = _notice_path(svc, existing).read_bytes()

    def _raise(self, target):
        raise OSError("simulated crash after the temp write, before the replace")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pathlib.Path, "replace", _raise)
        with pytest.raises(OSError, match="simulated crash"):
            await svc.board_post("op-pierre", "a second notice that never lands")

    assert _notice_path(svc, existing).read_bytes() == existing_bytes
    listed = await svc.board_list()
    assert [n.id for n in listed] == [existing.id]
