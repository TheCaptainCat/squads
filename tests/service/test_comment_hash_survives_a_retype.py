"""A comment's hash is anchored on the item's sequence number, so a retype keeps it."""

from _helpers import create_item


async def test_a_comment_keeps_its_hash_when_the_item_changes_type(svc) -> None:
    task = (await create_item(svc, "task", "task")).item
    await svc.comment(task.id, ["kept across the retype"], as_slug="operator")
    (before,) = await svc.comments(task.id)

    res = await svc.retype(task.id, "bug")

    after = [c for c in await svc.comments(res.item.id) if c.author_slug == "operator"]
    assert [c.hash for c in after] == [before.hash]
    assert res.item.id != task.id
