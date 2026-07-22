"""Every surface that writes agent-supplied text into a marker-delimited body — an item comment,
a sub-entity-targeted comment, a story/subtask/finding title (at add or update time), and a set
body — rejects text containing a well-formed `sq:` marker tag, in either bracket or backtick
form, and leaves the file completely untouched on rejection (CLAUDE.md invariant #3).
"""

import pytest

from squads._errors import SquadsError

pytestmark = pytest.mark.anyio

# Built at runtime so this source file itself contains no literal marker tag.
_MARKER_TAG = "<!-- sq:body -->"
_BACKTICK_MARKER_TAG = f"`{_MARKER_TAG}`"


async def test_comment_with_marker_tag_rejected_bracket_and_backtick_form(svc):
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="marker"):
        await svc.comment(task.id, [f"see the {_MARKER_TAG} region"], as_slug="manager")
    with pytest.raises(SquadsError, match="marker"):
        await svc.comment(task.id, [f"see {_BACKTICK_MARKER_TAG}"], as_slug="manager")


async def test_comment_marker_in_any_message_position_rejects_and_leaves_file_untouched(svc):
    task = (await svc.create("task", "t")).item
    path = svc.paths.abspath((await svc.get(task.id)).path)
    text_before = path.read_text(encoding="utf-8")
    with pytest.raises(SquadsError, match="marker"):
        await svc.comment(
            task.id, ["safe first line", f"bad {_MARKER_TAG} line"], as_slug="manager"
        )
    assert path.read_text(encoding="utf-8") == text_before  # no partial write
    assert await svc.check() == []


async def test_subentity_targeted_comment_with_marker_rejected(svc):
    feat = (await svc.create("feature", "f")).item
    await svc.add_story(feat.id, "A story")
    with pytest.raises(SquadsError, match="marker"):
        await svc.comment(feat.id, [f"inject {_MARKER_TAG}"], as_slug="product-owner", story="US1")


@pytest.mark.parametrize(
    ("kind", "add"),
    [
        ("story", lambda svc, parent: svc.add_story(parent, f"title {_MARKER_TAG} here")),
        ("subtask", lambda svc, parent: svc.add_subtask(parent, f"subtask {_MARKER_TAG}")),
        ("finding", lambda svc, parent: svc.add_finding(parent, f"finding {_MARKER_TAG}")),
    ],
    ids=["story", "subtask", "finding"],
)
async def test_add_sub_entity_title_with_marker_rejected_for_every_kind(svc, kind, add):
    """Every add-<kind> surface calls the same guard — each is its own wiring point."""
    parent_type = {"story": "feature", "subtask": "task", "finding": "review"}[kind]
    parent = (await svc.create(parent_type, "p")).item
    with pytest.raises(SquadsError, match="marker"):
        await add(svc, parent.id)


async def test_update_subentity_title_with_marker_rejected_and_title_unchanged(svc):
    task = (await svc.create("task", "t")).item
    await svc.add_subtask(task.id, "clean title")
    with pytest.raises(SquadsError, match="marker"):
        await svc.update_subtask(task.id, "ST1", title=f"inject {_MARKER_TAG}")
    assert (await svc.list_subtasks(task.id))[0].title == "clean title"


async def test_set_body_with_marker_rejected_message_unchanged(svc):
    """Regression guard: the exact body-guard message is preserved."""
    task = (await svc.create("task", "t")).item
    with pytest.raises(SquadsError, match="body must not contain sq marker comments"):
        await svc.set_body(task.id, f"bad body {_MARKER_TAG}")


async def test_item_level_title_and_description_with_non_marker_brackets_are_allowed(svc):
    """Bracket/backtick content that is NOT a well-formed marker tag passes through fine."""
    task = (await svc.create("task", "t")).item
    ok = await svc.update(task.id, title="[x] done label")
    assert ok.title == "[x] done label"
    ok2 = await svc.update(task.id, description="Use `sq:body` syntax (plain text)")
    assert "sq:body" in ok2.description
