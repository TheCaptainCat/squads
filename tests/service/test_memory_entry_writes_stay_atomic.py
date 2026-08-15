"""Memory entries are squad data (hand-authored, no regeneration path), not a regenerable
artifact: adding one must go through the atomic primitive, never the bare truncate-in-place
`_aio.write_text` -- so a killed process can't leave a truncated entry, and a future reach-in
that bypasses the primitive is caught rather than silently reintroducing the hazard.
"""

import pathlib

import pytest

from squads import _aio

pytestmark = pytest.mark.anyio

_ROLE = "python-dev"


def _entry_path(svc, entry) -> pathlib.Path:
    return svc.paths.squad_dir / "agents" / "memory" / _ROLE / f"{entry.slug}.md"


async def test_adding_a_memory_goes_through_the_atomic_primitive(svc, monkeypatch):
    calls: list[tuple[pathlib.Path, str]] = []
    original = _aio.atomic_write_text

    async def _spy(path, text):
        calls.append((path, text))
        await original(path, text)

    async def _fail_if_reached(path, text):
        raise AssertionError(f"non-atomic _aio.write_text was called for {path}")

    monkeypatch.setattr(_aio, "atomic_write_text", _spy)
    monkeypatch.setattr(_aio, "write_text", _fail_if_reached)

    entry = await svc.memory_add(_ROLE, "a fact worth remembering")

    assert len(calls) == 1
    assert calls[0][0] == _entry_path(svc, entry)


async def test_a_failure_between_the_temp_write_and_the_replace_leaves_no_entry_file(svc):
    def _raise(self, target):
        raise OSError("simulated crash after the temp write, before the replace")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pathlib.Path, "replace", _raise)
        with pytest.raises(OSError, match="simulated crash"):
            await svc.memory_add(_ROLE, "a fact that never lands")

    # The create direction: no entry existed at this slug before, so an interrupted write
    # must leave nothing there -- never a half-written orphan.
    role_folder = svc.paths.squad_dir / "agents" / "memory" / _ROLE
    on_disk = list(role_folder.glob("*.md")) if role_folder.is_dir() else []
    assert on_disk == []

    # A normal (uninterrupted) add afterwards still works fine.
    entry = await svc.memory_add(_ROLE, "a fact that lands cleanly")
    assert _entry_path(svc, entry).read_text(encoding="utf-8")


async def test_an_interrupted_add_never_disturbs_an_existing_entry(svc):
    existing = await svc.memory_add(_ROLE, "an existing fact, untouched by later adds")
    existing_bytes = _entry_path(svc, existing).read_bytes()

    def _raise(self, target):
        raise OSError("simulated crash after the temp write, before the replace")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(pathlib.Path, "replace", _raise)
        with pytest.raises(OSError, match="simulated crash"):
            await svc.memory_add(_ROLE, "a second fact that never lands")

    assert _entry_path(svc, existing).read_bytes() == existing_bytes
    listed, _unreadable = await svc.memory_list(_ROLE)
    assert [e.slug for e in listed] == [existing.slug]
