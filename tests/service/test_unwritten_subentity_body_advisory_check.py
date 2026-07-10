"""The `sq check` advisory that flags a sub-entity body still equal to its kind's placeholder
stub: fires for a fresh story/subtask/finding, clears the moment the body diverges by even one
character, produces one issue per unwritten body, and never fires on an item with no
sub-entities. Warn-level only. CLI surfacing lives in
tests/cli/test_unwritten_subentity_body_advisory_check_cli.py.
"""

import pytest

from squads import _discussion as discussion

pytestmark = pytest.mark.anyio


def _unwritten_body_issues(issues):
    return [i for i in issues if "body is unwritten" in i.message]


async def test_a_fresh_placeholder_body_is_flagged_warn_naming_the_parent_and_local_id(
    svc,
) -> None:
    feat = (await svc.create("feature", "My feature")).item
    res = await svc.add_story(feat.id, "A story")
    issues = _unwritten_body_issues(await svc.check())
    assert len(issues) == 1
    assert issues[0].level == "warn"
    assert issues[0].item == feat.id
    assert res.local_id in issues[0].message


async def test_subtask_and_finding_placeholders_are_flagged_the_same_way(svc) -> None:
    task = (await svc.create("task", "My task")).item
    await svc.add_subtask(task.id, "A subtask")
    review = (await svc.create("review", "My review")).item
    await svc.add_finding(review.id, "A finding")

    issues = _unwritten_body_issues(await svc.check())
    assert len([i for i in issues if i.item == task.id]) == 1
    assert len([i for i in issues if i.item == review.id]) == 1


async def test_writing_a_real_body_clears_the_flag(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    res = await svc.add_story(feat.id, "A story")
    await svc.set_story_body(feat.id, res.local_id, "As a user, I want X so that Y.")
    assert not _unwritten_body_issues(await svc.check())


async def test_a_body_diverging_from_the_placeholder_by_one_character_is_not_flagged(
    svc,
) -> None:
    feat = (await svc.create("feature", "My feature")).item
    res = await svc.add_story(feat.id, "A story")
    placeholder = discussion.body_placeholder("story")
    await svc.set_story_body(feat.id, res.local_id, placeholder[:-1] + "!")
    assert not _unwritten_body_issues(await svc.check())


async def test_multiple_unwritten_bodies_each_produce_their_own_issue(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    await svc.add_story(feat.id, "Story one")
    await svc.add_story(feat.id, "Story two")
    assert len(_unwritten_body_issues(await svc.check())) == 2


async def test_a_mix_of_written_and_unwritten_bodies_flags_only_the_unwritten_one(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    written = await svc.add_story(feat.id, "Story one")
    await svc.set_story_body(feat.id, written.local_id, "Real acceptance criteria.")
    await svc.add_story(feat.id, "Story two")
    assert len(_unwritten_body_issues(await svc.check())) == 1


async def test_an_item_with_no_subentities_produces_no_issue(svc) -> None:
    await svc.create("feature", "My feature")
    assert not _unwritten_body_issues(await svc.check())


async def test_the_warn_level_never_affects_other_issue_levels(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    await svc.add_story(feat.id, "A story")
    for issue in _unwritten_body_issues(await svc.check()):
        assert issue.level == "warn"
