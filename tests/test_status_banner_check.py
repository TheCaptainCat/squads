"""Tests for the `sq check` advisory that flags a leading status/lifecycle banner.

A body or description that *opens* with a self-declared state ("STATUS: Proposed", a
hand-written "## Status" heading) is a maintenance smell: the frontmatter `status` field is the
single source of truth, and prose like this drifts the moment the real status changes. `sq check`
should flag only that leading-banner shape — never a mid-body mention of lifecycle as a topic, a
cross-reference to another item's status, an example inside fenced code, or anything living in the
discussion region (dated comments recording state-at-a-point-in-time are the sanctioned channel).
"""

import json

import pytest

pytestmark = pytest.mark.anyio


def _banner_issues(issues):
    return [i for i in issues if "status/lifecycle banner" in i.message]


# ---------------------------------------------------------------------------
# Service-level — positive (the detector fires on a banner)
# ---------------------------------------------------------------------------


class TestServiceStatusBannerCheckPositive:
    async def test_body_opening_with_status_colon_is_flagged(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        await svc.set_body(feat.id, "STATUS: Proposed — drafting is not a greenlight yet.")
        issues = _banner_issues(await svc.check())
        assert len(issues) == 1
        assert issues[0].item == feat.id
        assert issues[0].level == "warn"

    async def test_body_with_leading_status_heading_is_flagged(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        await svc.set_body(feat.id, "## Status\n\nThis is still being drafted.")
        issues = _banner_issues(await svc.check())
        assert len(issues) == 1
        assert issues[0].item == feat.id

    async def test_bold_status_banner_is_flagged(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        await svc.set_body(feat.id, "**STATUS: Proposed / assessment** — do not merge yet.")
        issues = _banner_issues(await svc.check())
        assert len(issues) == 1

    async def test_description_opening_with_status_banner_is_flagged(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        await svc.update(feat.id, description="STATUS: Draft, not ready for review")
        issues = _banner_issues(await svc.check())
        assert len(issues) == 1
        assert issues[0].item == feat.id

    async def test_message_names_the_offending_item_and_the_fix(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        await svc.set_body(feat.id, "STATUS: Proposed")
        issue = _banner_issues(await svc.check())[0]
        assert "frontmatter" in issue.message
        assert "comment" in issue.message


# ---------------------------------------------------------------------------
# Service-level — negative (topical/contextual lifecycle mentions never fire)
# ---------------------------------------------------------------------------


class TestServiceStatusBannerCheckNegative:
    async def test_topical_lifecycle_mention_mid_body_is_not_flagged(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        await svc.set_body(
            feat.id,
            "This feature builds the Draft→Ready transition for the review workflow, so"
            " that teams can promote a review once its findings are settled.",
        )
        issues = _banner_issues(await svc.check())
        assert not issues

    async def test_cross_reference_to_another_items_status_is_not_flagged(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        await svc.set_body(
            feat.id,
            "This work blocks the payments migration task until that lands, since it"
            " depends on the new schema being in place first.",
        )
        issues = _banner_issues(await svc.check())
        assert not issues

    async def test_status_word_inside_fenced_code_is_not_flagged(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        await svc.set_body(
            feat.id,
            "Example CLI output:\n\n```\nSTATUS: Draft\n```\n\nThat is the shape of the"
            " field, not a claim about this item.",
        )
        issues = _banner_issues(await svc.check())
        assert not issues

    async def test_status_banner_in_discussion_is_not_flagged(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        await svc.set_body(feat.id, "Plain, state-free acceptance criteria.")
        await svc.comment(feat.id, ["STATUS: Proposed — moved here on 2026-01-01."])
        issues = _banner_issues(await svc.check())
        assert not issues

    async def test_item_with_no_body_produces_no_issue(self, svc):
        await svc.create("feature", "My feature")
        issues = _banner_issues(await svc.check())
        assert not issues

    async def test_warn_level_does_not_affect_other_issue_levels(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        await svc.set_body(feat.id, "STATUS: Proposed")
        issues = await svc.check()
        for issue in _banner_issues(issues):
            assert issue.level == "warn"


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------


class TestCLIStatusBannerCheck:
    async def test_check_reports_status_banner(self, project, invoke):
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "body", "-m", "STATUS: Proposed"])
        result = await invoke(["check"])
        assert result.exit_code == 0, result.output
        assert "status/lifecycle banner" in result.output

    async def test_check_exits_0_when_only_advisory(self, project, invoke):
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "body", "-m", "STATUS: Proposed"])
        result = await invoke(["check"])
        assert result.exit_code == 0, result.output

    async def test_check_stays_silent_on_topical_lifecycle_mention(self, project, invoke):
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(
            [
                "feature",
                "2",
                "body",
                "-m",
                "Describes the Draft→Ready transition this feature builds.",
            ]
        )
        result = await invoke(["check"])
        assert "status/lifecycle banner" not in result.output

    async def test_check_json_includes_status_banner_issue(self, project, invoke):
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "body", "-m", "STATUS: Proposed"])
        result = await invoke(["check", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        matches = [i for i in data if "status/lifecycle banner" in i.get("message", "")]
        assert matches
        assert matches[0]["level"] == "warn"
