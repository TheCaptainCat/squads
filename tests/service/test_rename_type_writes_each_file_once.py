"""``Service.rename_type()`` composes every renamed file in memory and writes each file it
changes once, before the index commit, whatever the cross-references among the renamed items and
from the rest of the board. A failed write restores the board; a failed index commit leaves a
repairable squad.
"""

from pathlib import Path
from typing import Any

import pytest

from _helpers import create_item
from squads import _aio
from squads._itemfile import read_frontmatter

pytestmark = pytest.mark.anyio


async def _board(svc: Any, *, several: bool, among: str, from_others: bool) -> list[Any]:
    """Tasks to rename (one or several) wired to each other as *among* says, plus a review
    that refs and mentions every one of them when *from_others*."""
    tasks = [(await create_item(svc, "task", "First")).item]
    if several:
        tasks.append((await create_item(svc, "task", "Second")).item)
    first = tasks[0]
    if several:
        second = tasks[1]
        if among in {"refs", "both"}:
            await svc.add_ref(first.id, second.id, kind="blocks")
        if among in {"mentions", "both"}:
            await svc.set_body(first.id, f"waits on {second.id}")
    elif among in {"mentions", "both"}:
        await svc.set_body(first.id, f"I am {first.id}")
    if from_others:
        other = (await create_item(svc, "review", "Referrer")).item
        for t in tasks:
            await svc.add_ref(other.id, t.id, kind="blocks")
        await svc.set_body(other.id, " ".join(t.id for t in tasks))
    return tasks


@pytest.mark.parametrize("several", [False, True], ids=["one", "several"])
@pytest.mark.parametrize("among", ["none", "refs", "mentions", "both"])
@pytest.mark.parametrize("from_others", [False, True], ids=["no-referrers", "referrers"])
async def test_a_rename_writes_each_file_it_changes_once(
    svc, write_ledger, several, among, from_others
):
    tasks = await _board(svc, several=several, among=among, from_others=from_others)
    old_ids = [t.id for t in tasks]

    res = await svc.rename_type("task", "epic")

    unit = next(u for u in reversed(write_ledger.finished) if u.method == "rename_type")
    assert set(unit.counts.values()) == {1}
    assert len(unit.counts) == len(tasks) + (1 if from_others else 0)
    assert res.renamed == len(tasks)
    assert [old for old, _new in res.ids] == old_ids
    new_ids = dict(res.ids)
    for old_id, new_id in res.ids:
        item = await svc.get(new_id)
        path = svc.paths.abspath(item.path)
        assert read_frontmatter(path)["type"] == "epic"
        assert f"renamed {old_id} → {new_id}" in path.read_text(encoding="utf-8")
    first = await svc.get(new_ids[old_ids[0]])
    if several and among in {"refs", "both"}:
        assert first.refs == [f"{new_ids[old_ids[1]]}:blocks"]
    if among in {"mentions", "both"}:
        mentioned = new_ids[old_ids[1]] if several else first.id
        assert mentioned in await svc.read_body(first.id)
    if from_others:
        other = next(i for i in await svc.list_items(item_type="review"))
        assert sorted(other.refs) == sorted(f"{new}:blocks" for new in new_ids.values())
        assert await svc.read_body(other.id) == " ".join(new_ids.values())


async def test_a_rename_cli_smoke(svc, invoke):
    await create_item(svc, "task", "Subject")

    result = await invoke(["migrate", "rename-type", "task", "epic"])

    assert result.exit_code == 0


# ----------------------------------------------------------------- faults
def _snapshot(svc: Any) -> dict[Path, str]:
    return {
        p: p.read_text(encoding="utf-8")
        for p in sorted(svc.paths.squad_dir.rglob("*.md"))
        if not any(part.startswith(".") for part in p.relative_to(svc.paths.squad_dir).parts)
    }


@pytest.mark.parametrize("where", ["first-write", "second-write", "commit"])
async def test_a_fault_restores_the_board_or_leaves_it_repairable(
    svc, monkeypatch, write_ledger, where
):
    await _board(svc, several=True, among="both", from_others=True)
    before = _snapshot(svc)
    real_replace = _aio.atomic_replace_sync
    seen: list[str] = []

    def replace_(path: Path, text: str) -> None:
        is_renamed = path.name.startswith("EPIC-")
        if where != "commit" and is_renamed and ".tmp" not in path.name:
            seen.append(path.name)
            if len(seen) == (1 if where == "first-write" else 2):
                raise OSError("injected at a write")
        if where == "commit" and path.name == ".squads.json":
            raise OSError("injected at the commit")
        real_replace(path, text)

    with monkeypatch.context() as faulty:
        faulty.setattr(_aio, "atomic_replace_sync", replace_)
        with pytest.raises(OSError, match="injected"):
            await svc.rename_type("task", "epic")

    if where != "commit":
        assert _snapshot(svc) == before
    await svc.repair()
    assert [i for i in await svc.check() if i.level == "error"] == []
