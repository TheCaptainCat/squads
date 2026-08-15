"""Every surface that writes agent-supplied text into a marker-delimited body — an item comment,
a sub-entity-targeted comment, a story/subtask/finding title (at add or update time), and a set
body — rejects text containing a well-formed `sq:` marker tag, in either bracket or backtick
form, and leaves the file completely untouched on rejection (CLAUDE.md invariant #3).

The guard covers *sub-entity* region tags as much as top-level ones. Those are the dangerous
ones: a forged `<kind>:<local_id>:body` tag inside an agent-authored item body sits earlier in
the file than the genuine region, so the next sub-entity body write resolves to the forgery and
rewrites whatever the forged pair spans, leaving the real region stale. The same recognition
gap also blinded `check`'s marker linter to a duplicated or unclosed sub-entity marker.
"""

import re

import pytest

from _helpers import create_item
from squads import _sections as sections
from squads._errors import SquadsError
from squads._models import _markers as markers

pytestmark = pytest.mark.anyio

# Built at runtime so this source file itself contains no literal marker tag.
_MARKER_TAG = "<!-- sq:body -->"
_BACKTICK_MARKER_TAG = f"`{_MARKER_TAG}`"

#: Every ``<!-- sq:... -->``-shaped comment, however malformed its tag.
_ANY_SQ_COMMENT = re.compile(r"<!--\s*sq:[^>]*-->")


async def test_comment_with_marker_tag_rejected_bracket_and_backtick_form(svc):
    task = (await create_item(svc, "task", "t")).item
    with pytest.raises(SquadsError, match="marker"):
        await svc.comment(task.id, [f"see the {_MARKER_TAG} region"], as_slug="manager")
    with pytest.raises(SquadsError, match="marker"):
        await svc.comment(task.id, [f"see {_BACKTICK_MARKER_TAG}"], as_slug="manager")


async def test_comment_marker_in_any_message_position_rejects_and_leaves_file_untouched(svc):
    task = (await create_item(svc, "task", "t")).item
    path = svc.paths.abspath((await svc.get(task.id)).path)
    text_before = path.read_text(encoding="utf-8")
    with pytest.raises(SquadsError, match="marker"):
        await svc.comment(
            task.id, ["safe first line", f"bad {_MARKER_TAG} line"], as_slug="manager"
        )
    assert path.read_text(encoding="utf-8") == text_before  # no partial write
    assert await svc.check() == []


async def test_subentity_targeted_comment_with_marker_rejected(svc):
    feat = (await create_item(svc, "feature", "f")).item
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
    parent = (await create_item(svc, parent_type, "p")).item
    with pytest.raises(SquadsError, match="marker"):
        await add(svc, parent.id)


async def test_update_subentity_title_with_marker_rejected_and_title_unchanged(svc):
    task = (await create_item(svc, "task", "t")).item
    await svc.add_subtask(task.id, "clean title")
    with pytest.raises(SquadsError, match="marker"):
        await svc.update_subtask(task.id, "ST1", title=f"inject {_MARKER_TAG}")
    assert (await svc.list_subtasks(task.id))[0].title == "clean title"


#: The sentence that turns the refusal into instructions. It is the whole reason the guard's
#: strictness is defensible rather than merely obstructive, so every seam must carry it.
_REMEDIATION = "backtick-wrapping does not neutralize a well-formed tag"


async def _seam_body(svc, text):
    task = (await create_item(svc, "task", "t")).item
    await svc.set_body(task.id, text)


async def _seam_subentity_body(svc, text):
    task = (await create_item(svc, "task", "t")).item
    await svc.add_subtask(task.id, "clean")
    await svc.set_subtask_body(task.id, "ST1", text, append=False)


async def _seam_comment(svc, text):
    task = (await create_item(svc, "task", "t")).item
    await svc.comment(task.id, [text], as_slug="manager")


async def _seam_title(svc, text):
    task = (await create_item(svc, "task", "t")).item
    await svc.add_subtask(task.id, text)


@pytest.mark.parametrize(
    ("label", "seam"),
    [
        ("item body", _seam_body),
        ("sub-entity body", _seam_subentity_body),
        ("comment", _seam_comment),
        ("sub-entity title", _seam_title),
    ],
    ids=["item-body", "subentity-body", "comment", "subentity-title"],
)
async def test_every_prose_seam_tells_the_author_what_to_write_instead(svc, label, seam):
    """The refusal has to be instructions, on every seam — not just the ones that happened to
    get the longer string.

    The `body` label (the default, and therefore the busiest path: the item body, both
    sub-entity body writers and the shared section-edit core all take it) used to get a terse
    variant with no guidance, kept that way purely so existing tests stayed unchanged. Widening
    the tag class is what makes this matter: the likeliest way to trip the guard now is quoting
    a sub-entity region tag while writing *about* the marker system, and the first thing an
    author reaches for is backticks, which do not help.
    """
    with pytest.raises(SquadsError, match=_REMEDIATION):
        await seam(svc, f"text with {_MARKER_TAG} in it")


async def test_the_refusal_still_names_which_input_was_rejected(svc):
    """Adding the guidance must not cost the label that says *what* was rejected — with four
    seams sharing one sentence, the label is the only thing locating the problem."""
    task = (await create_item(svc, "task", "t")).item
    with pytest.raises(SquadsError, match="body must not contain sq marker comments"):
        await svc.set_body(task.id, f"bad body {_MARKER_TAG}")
    with pytest.raises(SquadsError, match="comment message must not contain sq marker comments"):
        await svc.comment(task.id, [f"bad {_MARKER_TAG}"], as_slug="manager")


async def test_item_level_title_and_description_with_non_marker_brackets_are_allowed(svc):
    """Bracket/backtick content that is NOT a well-formed marker tag passes through fine."""
    task = (await create_item(svc, "task", "t")).item
    ok = await svc.update(task.id, title="[x] done label")
    assert ok.title == "[x] done label"
    ok2 = await svc.update(task.id, description="Use `sq:body` syntax (plain text)")
    assert "sq:body" in ok2.description


# ─── sub-entity region tags ────────────────────────────────────────────────────


def _forged(kind: str, local_id: str) -> tuple[str, str]:
    """The open/close comment pair for a sub-entity's ``:body`` region, built at runtime."""
    tag = f"{kind}:{local_id}:body"
    return markers.open_marker(tag), markers.close_marker(tag)


@pytest.mark.parametrize(
    ("kind", "local_id", "parent_type", "add"),
    [
        ("story", "US1", "feature", lambda svc, p: svc.add_story(p, "a story")),
        ("subtask", "ST1", "task", lambda svc, p: svc.add_subtask(p, "a subtask")),
        ("finding", "F1", "review", lambda svc, p: svc.add_finding(p, "a finding")),
    ],
    ids=["story", "subtask", "finding"],
)
async def test_a_forged_sub_entity_region_pair_in_an_item_body_is_rejected_for_every_kind(
    svc, kind, local_id, parent_type, add
):
    """The span-destroying shape: the forged pair brackets real prose, so accepting it hands the
    next sub-entity body write a region that spans (and replaces) that prose."""
    parent = (await create_item(svc, parent_type, "p")).item
    await add(svc, parent.id)
    open_tag, close_tag = _forged(kind, local_id)
    with pytest.raises(SquadsError, match="body must not contain sq marker comments"):
        await svc.set_body(parent.id, f"{open_tag}\nreal scope prose\n{close_tag}")


async def test_rejecting_a_forged_sub_entity_marker_leaves_the_file_and_the_real_region_intact(
    svc,
):
    review = (await create_item(svc, "review", "r")).item
    await svc.add_finding(review.id, "a finding", body="the genuine finding body")
    await svc.set_body(review.id, "scope prose worth keeping")
    path = svc.paths.abspath((await svc.get(review.id)).path)
    before = path.read_text(encoding="utf-8")

    open_tag, close_tag = _forged("finding", "F1")
    with pytest.raises(SquadsError, match="marker"):
        await svc.set_body(review.id, f"{open_tag}\nhijacked\n{close_tag}")

    assert path.read_text(encoding="utf-8") == before  # no partial write
    # And the real region is still the one a sub-entity body write resolves to (force, because
    # the finding was created with a body and replacing authored prose is guarded).
    await svc.set_block_body(review.id, "finding", "F1", "rewritten body", append=False, force=True)
    after = path.read_text(encoding="utf-8")
    assert "scope prose worth keeping" in after
    assert (await svc.get_block(review.id, "finding", "F1")).body.strip() == "rewritten body"
    assert await svc.check() == []


async def test_check_reports_a_duplicated_sub_entity_marker(svc):
    """``_marker_issues`` reads the same primitive: a duplicated sub-entity region pair planted
    directly on disk (bypassing the write guard, as a hand-edit or a bad merge would) must be
    reported, not silently tolerated the way a duplicated top-level one never was."""
    review = (await create_item(svc, "review", "r")).item
    await svc.add_finding(review.id, "a finding")
    path = svc.paths.abspath((await svc.get(review.id)).path)
    open_tag, close_tag = _forged("finding", "F1")
    path.write_text(
        path.read_text(encoding="utf-8") + f"\n{open_tag}\n{close_tag}\n", encoding="utf-8"
    )

    messages = [i.message for i in await svc.check()]
    assert any("duplicate marker" in m and "finding:F1:body" in m for m in messages), messages


async def test_check_reports_an_unclosed_sub_entity_marker(svc):
    feat = (await create_item(svc, "feature", "f")).item
    await svc.add_story(feat.id, "a story")
    path = svc.paths.abspath((await svc.get(feat.id)).path)
    tag = markers.discussion_tag("story:US1")
    path.write_text(
        path.read_text(encoding="utf-8") + f"\n{markers.open_marker(tag)}\n", encoding="utf-8"
    )

    messages = [i.message for i in await svc.check()]
    assert any("unclosed marker" in m and "story:US1:discussion" in m for m in messages), messages


async def test_a_service_written_item_file_has_every_one_of_its_markers_recognised(svc):
    """Whole-file property on a file sq itself wrote, across all three sub-entity kinds: the
    tag count the primitive reports equals the count physically present. This is the shape of
    assertion the original blind spot needed — every per-branch test it had still passed."""
    for parent_type, add in (
        ("feature", lambda p: svc.add_story(p, "s")),
        ("task", lambda p: svc.add_subtask(p, "s")),
        ("review", lambda p: svc.add_finding(p, "f")),
    ):
        parent = (await create_item(svc, parent_type, "p")).item
        await add(parent.id)
        await add(parent.id)
        text = svc.paths.abspath((await svc.get(parent.id)).path).read_text(encoding="utf-8")
        present = _ANY_SQ_COMMENT.findall(text)
        assert len(present) >= 20, f"{parent_type}: fixture must carry sub-entity markers"
        assert len(sections.find_markers(text)) == len(present), parent_type
