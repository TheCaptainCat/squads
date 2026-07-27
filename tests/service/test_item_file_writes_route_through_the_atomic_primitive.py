"""The item-file layer (`_itemfile.py`) exposes only the atomic primitive: every one of its
writers goes through `_aio.atomic_write_text`, never the bare truncate-in-place `_aio.write_text`
-- so a future mutation site that imports from this module cannot silently reintroduce a
truncating write.
"""

from pathlib import Path

import pytest

from squads import _aio
from squads import _itemfile as itemfile
from squads._index._resolver import item_file

pytestmark = pytest.mark.anyio


def _install_spy(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, str]]:
    """Installs the spy AFTER any setup I/O (item creation) has already happened, so only the
    call under test is recorded. Fails outright if the non-atomic `_aio.write_text` is ever
    reached instead of the atomic primitive."""
    calls: list[tuple[Path, str]] = []
    original = _aio.atomic_write_text

    async def _spy(path, text):
        calls.append((path, text))
        await original(path, text)

    async def _fail_if_reached(path, text):
        raise AssertionError(f"non-atomic _aio.write_text was called for {path}")

    monkeypatch.setattr(_aio, "atomic_write_text", _spy)
    monkeypatch.setattr(_aio, "write_text", _fail_if_reached)
    return calls


async def test_write_new_uses_the_atomic_primitive(svc, monkeypatch):
    item = (await svc.create("task", "Fresh")).item
    path = item_file(svc.paths, item)
    path.unlink()  # write_new is exercised standalone below, on a clean target
    calls = _install_spy(monkeypatch)

    await itemfile.write_new(path, item, "<!-- sq:body -->\n<!-- sq:body:end -->\n")

    assert len(calls) == 1
    assert calls[0][0] == path


async def test_update_frontmatter_uses_the_atomic_primitive(svc, monkeypatch):
    item = (await svc.create("task", "Existing")).item
    path = item_file(svc.paths, item)
    base = item.model_copy(deep=True)
    calls = _install_spy(monkeypatch)

    await itemfile.update_frontmatter(path, item, base)

    assert len(calls) == 1
    assert calls[0][0] == path


async def test_write_text_uses_the_atomic_primitive(svc, monkeypatch):
    item = (await svc.create("task", "Sectioned")).item
    path = item_file(svc.paths, item)
    new_text = path.read_text(encoding="utf-8")
    calls = _install_spy(monkeypatch)

    await itemfile.write_text(path, new_text)

    assert calls == [(path, new_text)]


async def test_rewrite_ids_uses_the_atomic_primitive_only_for_files_it_actually_changes(
    svc, monkeypatch
):
    a = (await svc.create("task", "A")).item
    b = (await svc.create("task", "B mentions " + a.id)).item
    c = (await svc.create("task", "C, unrelated")).item
    a_path, b_path, c_path = (item_file(svc.paths, it) for it in (a, b, c))
    calls = _install_spy(monkeypatch)

    touched = await itemfile.rewrite_ids([a_path, b_path, c_path], {a.id: "TASK-999999"})

    # a_path changes too -- its own frontmatter `id:` field is a match -- but c_path, which
    # never mentions a.id anywhere, must not be touched or written at all.
    assert set(touched) == {a_path, b_path}
    assert c_path not in touched
    assert {p for p, _ in calls} == {a_path, b_path}
