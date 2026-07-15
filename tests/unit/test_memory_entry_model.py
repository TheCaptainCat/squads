"""The memory-entry model — pure frontmatter round-trip, no filesystem.

Deliberately NOT the ``Item`` model: no schema-version/status/workflow fields to assert on,
just the light frontmatter (summary, created_at, optional tags) over a freeform body.
"""

from squads._memory._model import MemoryEntry


def test_to_frontmatter_dict_carries_summary_and_created_at_only_when_there_are_no_tags():
    entry = MemoryEntry(
        slug="scale-tests-slow",
        summary="the scale suite is slow",
        created_at="2026-06-07T10:00:00Z",
        body="details here",
    )
    assert entry.to_frontmatter_dict() == {
        "summary": "the scale suite is slow",
        "created_at": "2026-06-07T10:00:00Z",
    }


def test_to_frontmatter_dict_includes_tags_when_present():
    entry = MemoryEntry(
        slug="pyright-strict",
        summary="pyright runs in strict mode",
        created_at="2026-06-07T10:00:00Z",
        body="body",
        tags=("testing", "typing"),
    )
    assert entry.to_frontmatter_dict()["tags"] == ["testing", "typing"]


def test_from_frontmatter_round_trips_to_frontmatter_dict():
    original = MemoryEntry(
        slug="a-fact",
        summary="a fact",
        created_at="2026-06-07T10:00:00Z",
        body="the freeform body",
        tags=("one", "two"),
    )
    rebuilt = MemoryEntry.from_frontmatter(
        original.slug, original.to_frontmatter_dict(), original.body
    )
    assert rebuilt == original


def test_from_frontmatter_tolerates_a_missing_tags_key():
    rebuilt = MemoryEntry.from_frontmatter(
        "slug", {"summary": "s", "created_at": "2026-06-07T10:00:00Z"}, "body"
    )
    assert rebuilt.tags == ()
