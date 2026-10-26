"""A file retyped between the scan's read and the directory listing that follows it is one
file, not two carrying one number; a real shared number and a real duplicate whose copy is
renamed in that window are still reported."""

import pytest

from squads import _aio
from squads._services._results import CheckIssue

pytestmark = pytest.mark.anyio


def _rule(issues: list[CheckIssue], rule: str) -> list[CheckIssue]:
    return [i for i in issues if i.rule == rule]


async def test_a_retype_between_the_scan_and_the_listing_is_not_a_shared_number(svc, monkeypatch):
    created = await svc.create("task", "alpha", author="manager")
    listed = svc._id_carriers

    async def retype_then_list(log=None):
        await svc.retype(created.item.id, "bug")
        return await listed(log)

    monkeypatch.setattr(svc, "_id_carriers", retype_then_list)
    issues = await svc.check()
    assert _rule(issues, "numbers_unique") == []
    assert _rule(issues, "ids_unique") == []


async def test_a_real_shared_number_is_still_reported(svc):
    created = await svc.create("task", "alpha", author="manager")
    other = created.path.parent.parent / "bugs" / created.path.name.replace("TASK", "BUG")
    text = (await _aio.read_text(created.path)).replace(
        created.item.id, "BUG-" + created.item.id[5:]
    )
    await _aio.write_text(other, text)
    issues = _rule(await svc.check(), "numbers_unique")
    assert len(issues) == 1
    assert "under different ids" in issues[0].message


async def test_a_real_duplicate_whose_copy_is_renamed_after_the_listing_is_reported(
    svc, monkeypatch
):
    created = await svc.create("task", "alpha", author="manager")
    old = created.path
    copy = old.with_name(old.name.replace("alpha", "copy"))
    await _aio.write_text(copy, await _aio.read_text(old))
    renamed = old.with_name(old.name.replace("alpha", "gamma"))
    listed = svc._id_carriers

    async def list_then_rename(log=None):
        carriers = await listed(log)
        await _aio.path_rename(old, renamed)
        return carriers

    monkeypatch.setattr(svc, "_id_carriers", list_then_rename)
    issues = _rule(await svc.check(), "ids_unique")
    assert len(issues) == 1
    assert "2 files carry this id" in issues[0].message
