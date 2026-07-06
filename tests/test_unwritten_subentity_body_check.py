"""Tests for the `sq check` advisory that flags an unwritten sub-entity body.

A freshly-scaffolded story/subtask/finding body starts as its kind's placeholder stub
(`_discussion.py::_PLACEHOLDER`). `sq check` should flag any sub-entity whose body is still
exactly that placeholder, and stop flagging it once real content is written — even content
that only starts to diverge from the placeholder text.
"""

import json

import pytest

from squads import _discussion as discussion
from squads._models._enums import ItemType

pytestmark = pytest.mark.anyio


def _warn_body_issues(issues):
    return [i for i in issues if "body is unwritten" in i.message]


# ---------------------------------------------------------------------------
# Service-level
# ---------------------------------------------------------------------------


class TestServiceUnwrittenBodyCheck:
    async def test_fresh_story_placeholder_is_flagged(self, svc):
        feat = (await svc.create(ItemType.FEATURE, "My feature")).item
        await svc.add_story(feat.id, "A story")
        issues = _warn_body_issues(await svc.check())
        assert len(issues) == 1

    async def test_flagged_issue_is_warn_level(self, svc):
        feat = (await svc.create(ItemType.FEATURE, "My feature")).item
        await svc.add_story(feat.id, "A story")
        issue = _warn_body_issues(await svc.check())[0]
        assert issue.level == "warn"

    async def test_flagged_issue_names_parent_item(self, svc):
        feat = (await svc.create(ItemType.FEATURE, "My feature")).item
        await svc.add_story(feat.id, "A story")
        issue = _warn_body_issues(await svc.check())[0]
        assert issue.item == feat.id

    async def test_flagged_issue_names_local_id(self, svc):
        feat = (await svc.create(ItemType.FEATURE, "My feature")).item
        res = await svc.add_story(feat.id, "A story")
        issue = _warn_body_issues(await svc.check())[0]
        assert res.local_id in issue.message

    async def test_writing_real_body_clears_the_flag(self, svc):
        feat = (await svc.create(ItemType.FEATURE, "My feature")).item
        res = await svc.add_story(feat.id, "A story")
        await svc.set_story_body(feat.id, res.local_id, "As a user, I want X so that Y.")
        issues = _warn_body_issues(await svc.check())
        assert not issues

    async def test_body_merely_diverging_from_placeholder_is_not_flagged(self, svc):
        """Even a single edited character counts as written — no heuristics."""
        feat = (await svc.create(ItemType.FEATURE, "My feature")).item
        res = await svc.add_story(feat.id, "A story")
        placeholder = discussion.body_placeholder("story")
        divergent = placeholder[:-1] + "!"
        await svc.set_story_body(feat.id, res.local_id, divergent)
        issues = _warn_body_issues(await svc.check())
        assert not issues

    async def test_unwritten_subtask_body_is_flagged(self, svc):
        task = (await svc.create(ItemType.TASK, "My task")).item
        await svc.add_subtask(task.id, "A subtask")
        issues = _warn_body_issues(await svc.check())
        assert len(issues) == 1

    async def test_unwritten_finding_body_is_flagged(self, svc):
        review = (await svc.create(ItemType.REVIEW, "My review")).item
        await svc.add_finding(review.id, "A finding")
        issues = _warn_body_issues(await svc.check())
        assert len(issues) == 1

    async def test_multiple_unwritten_bodies_each_produce_own_issue(self, svc):
        feat = (await svc.create(ItemType.FEATURE, "My feature")).item
        await svc.add_story(feat.id, "Story one")
        await svc.add_story(feat.id, "Story two")
        issues = _warn_body_issues(await svc.check())
        assert len(issues) == 2

    async def test_mixed_written_and_unwritten_only_flags_unwritten(self, svc):
        feat = (await svc.create(ItemType.FEATURE, "My feature")).item
        written = await svc.add_story(feat.id, "Story one")
        await svc.set_story_body(feat.id, written.local_id, "Real acceptance criteria.")
        await svc.add_story(feat.id, "Story two")
        issues = _warn_body_issues(await svc.check())
        assert len(issues) == 1

    async def test_item_with_no_subentities_produces_no_issue(self, svc):
        await svc.create(ItemType.FEATURE, "My feature")
        issues = _warn_body_issues(await svc.check())
        assert not issues

    async def test_warn_level_does_not_affect_other_issue_levels(self, svc):
        feat = (await svc.create(ItemType.FEATURE, "My feature")).item
        await svc.add_story(feat.id, "A story")
        issues = await svc.check()
        for issue in _warn_body_issues(issues):
            assert issue.level == "warn"


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------


class TestCLIUnwrittenBodyCheck:
    async def test_check_reports_unwritten_story_body(self, project, invoke):
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "add-story", "A story"])
        result = await invoke(["check"])
        assert result.exit_code == 0, result.output
        assert "body is unwritten" in result.output

    async def test_check_exits_0_when_only_advisory(self, project, invoke):
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "add-story", "A story"])
        result = await invoke(["check"])
        assert result.exit_code == 0, result.output

    async def test_check_clears_once_body_is_written(self, project, invoke):
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "add-story", "A story"])
        await invoke(["feature", "2", "story", "1", "body", "-m", "Real acceptance criteria."])
        result = await invoke(["check"])
        assert "body is unwritten" not in result.output

    async def test_check_json_includes_unwritten_body_issue(self, project, invoke):
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "add-story", "A story"])
        result = await invoke(["check", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        matches = [i for i in data if "body is unwritten" in i.get("message", "")]
        assert matches
        assert matches[0]["level"] == "warn"
