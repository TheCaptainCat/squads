"""``Service.comments()`` — parses an item's top-level discussion into ordered ``Comment``
entries, composing ``read_discussion`` + ``discussion.split_discussion`` for the dedicated
``sq <type> <n> comments`` read-back verb.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_returns_comments_in_file_order_with_author_and_timestamp(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.comment(feat.id, ["first point"], as_slug="manager")
    await svc.comment(feat.id, ["second point"], as_slug="manager")

    comments = await svc.comments(feat.id)
    assert [c.body for c in comments] == ["- first point", "- second point"]
    assert all(c.author == "Catherine Manager" for c in comments)
    assert all(c.timestamp for c in comments)


async def test_an_item_with_no_comments_returns_an_empty_list(svc):
    feat = (await svc.create("feature", "f")).item
    assert await svc.comments(feat.id) == []


async def test_a_multiline_fenced_code_comment_round_trips_intact(svc):
    feat = (await svc.create("feature", "f")).item
    body = "before\n```\ncode line\n```\nafter"
    await svc.comment(feat.id, [body], as_slug="manager")

    (comment,) = await svc.comments(feat.id)
    assert "```" in comment.body
    assert "code line" in comment.body
