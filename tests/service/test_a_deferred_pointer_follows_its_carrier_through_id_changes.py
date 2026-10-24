"""A finding's `deferred_to` is rewritten wherever the carrier's id changes (retype, type rename,
`renumber`, `repair --renumber`), severed when the carrier is removed, and rebuilt from the
file by `repair`.
"""

import pytest

from _helpers import create_item
from squads._errors import SquadsError
from squads._itemfile import read_frontmatter
from squads._sections import replace_frontmatter, split_frontmatter
from squads._services._service import Service

pytestmark = pytest.mark.anyio


async def _deferred(svc: Service) -> tuple[str, str]:
    """A review whose only finding is deferred to a task; returns (review id, task id)."""
    review = (await create_item(svc, "review", "r")).item
    await svc.add_finding(review.id, "f")
    carrier = (await create_item(svc, "task", "carrier")).item
    await svc.update_finding(review.id, "F1", status="Deferred", deferred_to=carrier.id)
    return review.id, carrier.id


async def _pointer(svc: Service, review_id: str) -> tuple[str | None, str | None]:
    """The pointer as the index holds it and as the review's file holds it."""
    item = await svc.get(review_id)
    stored = read_frontmatter(svc.paths.abspath(item.path))["subentities"][0].get("deferred_to")
    return item.subentities[0].deferred_to, stored


async def test_retype_rewrites_the_pointer(svc) -> None:
    review, carrier = await _deferred(svc)
    retyped = (await svc.retype(carrier, "bug")).item
    assert retyped.id != carrier
    assert await _pointer(svc, review) == (retyped.id, retyped.id)


async def test_a_type_rename_rewrites_the_pointer(svc) -> None:
    review, carrier = await _deferred(svc)
    renamed = dict((await svc.rename_type("task", "epic")).ids)
    assert await _pointer(svc, review) == (renamed[carrier], renamed[carrier])


async def test_renumber_rewrites_the_pointer(svc) -> None:
    review, carrier = await _deferred(svc)
    result = await svc.renumber(from_seq=(await svc.get(carrier)).sequence_id, by=10)
    assert result.remap[carrier] != carrier
    assert await _pointer(svc, review) == (result.remap[carrier],) * 2


async def test_repair_renumber_rewrites_the_pointer(svc) -> None:
    review, carrier = await _deferred(svc)
    task = await svc.get(carrier)
    bug = await svc.create("bug", "Beta", author="manager")
    fm = split_frontmatter(bug.path.read_text(encoding="utf-8"))[0]
    fm["sequence_id"] = task.sequence_id
    fm["id"] = f"BUG-{task.sequence_id}"
    bug.path.write_text(
        replace_frontmatter(bug.path.read_text(encoding="utf-8"), fm), encoding="utf-8", newline=""
    )

    result = await svc.repair(renumber=True)

    moved = next(i for i in result.db.items.values() if i.title == "carrier")
    assert moved.id != carrier
    assert await _pointer(svc, review) == (moved.id, moved.id)


async def test_removing_the_carrier_needs_force_and_severs_the_pointer(svc) -> None:
    review, carrier = await _deferred(svc)
    with pytest.raises(SquadsError, match=review):
        await svc.remove_work_item(carrier)
    assert (await _pointer(svc, review))[0] == carrier

    result = await svc.remove_work_item(carrier, force=True)

    assert result.severed_refs == [review]
    assert await _pointer(svc, review) == (None, None)
    assert (await svc.list_findings(review))[0].status == "Deferred"


async def test_repair_rebuilds_the_pointer_from_the_file(svc) -> None:
    review, carrier = await _deferred(svc)
    await _drop_index_pointer(svc, review)
    assert (await _pointer(svc, review))[0] is None

    await svc.repair()

    assert await _pointer(svc, review) == (carrier, carrier)


async def _drop_index_pointer(svc: Service, review_id: str) -> None:
    async with svc.store.transaction() as db:
        db.items[(await svc.get(review_id)).sequence_id].subentities[0].deferred_to = None
