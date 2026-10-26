"""A file renamed between the scan's read and the directory listing that follows it is one
file, not two carrying the same id; a real second copy is still reported."""

from pathlib import Path

import pytest

from squads import _aio
from squads._services._results import CheckIssue

pytestmark = pytest.mark.anyio


def _duplicates(issues: list[CheckIssue]) -> list[CheckIssue]:
    return [i for i in issues if i.rule == "ids_unique"]


async def test_a_rename_between_the_scan_and_the_listing_is_not_a_duplicate(svc, monkeypatch):
    created = await svc.create("task", "alpha", author="manager")
    old: Path = created.path
    new = old.with_name(old.name.replace("alpha", "beta"))
    listed = svc._id_carriers

    async def rename_then_list(log=None):
        await _aio.path_rename(old, new)
        return await listed(log)

    monkeypatch.setattr(svc, "_id_carriers", rename_then_list)
    issues = await svc.check()
    assert new.exists()
    assert _duplicates(issues) == []


async def test_two_files_carrying_one_id_are_still_reported(svc):
    created = await svc.create("task", "alpha", author="manager")
    old: Path = created.path
    copy = old.with_name(old.name.replace("alpha", "beta"))
    await _aio.write_text(copy, await _aio.read_text(old))
    issues = _duplicates(await svc.check())
    assert len(issues) == 1
    assert "2 files carry this id" in issues[0].message
