"""The `sq check` advisory that flags a leading status/lifecycle banner in a body or
description: STATUS: lines, a leading '## Status' heading, and a bold banner all fire;
a topical lifecycle mention, a cross-reference to another item's status, fenced-code
text, and discussion content never do. Warn-level only — never affects other issue
levels. CLI surfacing lives in tests/cli/test_status_banner_advisory_check_cli.py.
"""

import pytest

pytestmark = pytest.mark.anyio


def _banner_issues(issues):
    return [i for i in issues if "status/lifecycle banner" in i.message]


async def test_a_leading_status_colon_line_is_flagged_warn_and_names_the_item(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    await svc.set_body(feat.id, "STATUS: Proposed — drafting is not a greenlight yet.")
    issues = _banner_issues(await svc.check())
    assert len(issues) == 1
    assert issues[0].item == feat.id
    assert issues[0].level == "warn"


async def test_a_leading_status_heading_and_a_bold_banner_are_both_flagged(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    await svc.set_body(feat.id, "## Status\n\nThis is still being drafted.")
    feat2 = (await svc.create("feature", "Another feature")).item
    await svc.set_body(feat2.id, "**STATUS: Proposed / assessment** — do not merge yet.")

    issues = _banner_issues(await svc.check())
    assert len([i for i in issues if i.item == feat.id]) == 1
    assert len([i for i in issues if i.item == feat2.id]) == 1


async def test_a_description_opening_with_a_status_banner_is_flagged(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    await svc.update(feat.id, description="STATUS: Draft, not ready for review")
    issues = _banner_issues(await svc.check())
    assert len(issues) == 1
    assert issues[0].item == feat.id


async def test_the_message_names_the_frontmatter_field_and_the_comment_fix(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    await svc.set_body(feat.id, "STATUS: Proposed")
    issue = _banner_issues(await svc.check())[0]
    assert "frontmatter" in issue.message
    assert "comment" in issue.message


async def test_a_topical_lifecycle_mention_mid_body_is_never_flagged(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    await svc.set_body(
        feat.id,
        "This feature builds the Draft→Ready transition for the review workflow, so"
        " that teams can promote a review once its findings are settled.",
    )
    assert not _banner_issues(await svc.check())


async def test_a_cross_reference_to_another_items_status_is_never_flagged(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    await svc.set_body(
        feat.id,
        "This work blocks the payments migration task until that lands, since it"
        " depends on the new schema being in place first.",
    )
    assert not _banner_issues(await svc.check())


async def test_a_status_word_inside_fenced_code_is_never_flagged(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    await svc.set_body(
        feat.id,
        "Example CLI output:\n\n```\nSTATUS: Draft\n```\n\nThat is the shape of the"
        " field, not a claim about this item.",
    )
    assert not _banner_issues(await svc.check())


async def test_a_status_banner_written_into_discussion_is_never_flagged(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    await svc.set_body(feat.id, "Plain, state-free acceptance criteria.")
    await svc.comment(feat.id, ["STATUS: Proposed — moved here on 2026-01-01."])
    assert not _banner_issues(await svc.check())


async def test_an_item_with_no_body_produces_no_issue(svc) -> None:
    await svc.create("feature", "My feature")
    assert not _banner_issues(await svc.check())


async def test_the_warn_level_never_affects_other_issue_levels(svc) -> None:
    feat = (await svc.create("feature", "My feature")).item
    await svc.set_body(feat.id, "STATUS: Proposed")
    for issue in _banner_issues(await svc.check()):
        assert issue.level == "warn"
