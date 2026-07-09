"""Tests for TASK-000168 and TASK-000169: sub-entity title-length advisories.

TASK-000168 (authoring-time advisory):
- TITLE_ADVISORY_MAX = 120 constant lives in _interactions.py
- add-finding / add-subtask / add-story carry a title_advisory on BlockResult when
  len(title) > 120; None at/below 120
- Sub-entity is always created (warn-and-proceed; exit 0 on the CLI)
- Advisory is recorded in the reflog delta (title_advisory key)
- CLI renders it (human path) and includes it in --json

TASK-000169 (sq check advisory rule):
- _check_subentity_title_lengths emits warn-level CheckIssue per over-long title
- Fires strictly above 120; silent at/below
- sq check exits 0 with only advisory warnings (no errors)
- --json includes the advisory entries
"""

import json

import pytest

from squads._index._reflog import read_lines, reflog_path
from squads._interactions import TITLE_ADVISORY_MAX

pytestmark = pytest.mark.anyio

# One character above the threshold — triggers the advisory.
LONG_TITLE = "A" * (TITLE_ADVISORY_MAX + 1)
# Exactly at the threshold — silent.
EXACT_TITLE = "A" * TITLE_ADVISORY_MAX
# Well under the threshold — silent.
SHORT_TITLE = "Short title"


# ---------------------------------------------------------------------------
# Constant sanity
# ---------------------------------------------------------------------------


class TestTitleAdvisoryMax:
    def test_constant_value(self):
        """TITLE_ADVISORY_MAX must be 120 (ADR-000167)."""
        assert TITLE_ADVISORY_MAX == 120

    def test_constant_is_int(self):
        assert isinstance(TITLE_ADVISORY_MAX, int)


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestServiceTitleAdvisory:
    """add-finding / add-subtask / add-story carry title_advisory above 120; None at/below."""

    # ------------------------------------------------------------------ add-story
    async def test_add_story_above_threshold_returns_advisory(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        res = await svc.add_story(feat.id, LONG_TITLE)
        assert res.title_advisory is not None

    async def test_add_story_advisory_names_length(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        res = await svc.add_story(feat.id, LONG_TITLE)
        assert str(len(LONG_TITLE)) in (res.title_advisory or "")

    async def test_add_story_advisory_names_body_command(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        res = await svc.add_story(feat.id, LONG_TITLE)
        advisory = res.title_advisory or ""
        assert "body" in advisory
        assert res.local_id in advisory

    async def test_add_story_at_threshold_no_advisory(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        res = await svc.add_story(feat.id, EXACT_TITLE)
        assert res.title_advisory is None

    async def test_add_story_below_threshold_no_advisory(self, svc):
        feat = (await svc.create("feature", "My feature")).item
        res = await svc.add_story(feat.id, SHORT_TITLE)
        assert res.title_advisory is None

    async def test_add_story_still_creates_sub_entity(self, svc):
        """Sub-entity is always created even when the advisory fires."""
        feat = (await svc.create("feature", "My feature")).item
        res = await svc.add_story(feat.id, LONG_TITLE)
        assert res.local_id is not None
        assert res.path.exists()

    # ------------------------------------------------------------------ add-subtask
    async def test_add_subtask_above_threshold_returns_advisory(self, svc):
        task = (await svc.create("task", "My task")).item
        res = await svc.add_subtask(task.id, LONG_TITLE)
        assert res.title_advisory is not None

    async def test_add_subtask_advisory_names_length(self, svc):
        task = (await svc.create("task", "My task")).item
        res = await svc.add_subtask(task.id, LONG_TITLE)
        assert str(len(LONG_TITLE)) in (res.title_advisory or "")

    async def test_add_subtask_advisory_names_body_command(self, svc):
        task = (await svc.create("task", "My task")).item
        res = await svc.add_subtask(task.id, LONG_TITLE)
        advisory = res.title_advisory or ""
        assert "body" in advisory
        assert res.local_id in advisory

    async def test_add_subtask_at_threshold_no_advisory(self, svc):
        task = (await svc.create("task", "My task")).item
        res = await svc.add_subtask(task.id, EXACT_TITLE)
        assert res.title_advisory is None

    async def test_add_subtask_below_threshold_no_advisory(self, svc):
        task = (await svc.create("task", "My task")).item
        res = await svc.add_subtask(task.id, SHORT_TITLE)
        assert res.title_advisory is None

    async def test_add_subtask_still_creates_sub_entity(self, svc):
        task = (await svc.create("task", "My task")).item
        res = await svc.add_subtask(task.id, LONG_TITLE)
        assert res.local_id is not None
        assert res.path.exists()

    # ------------------------------------------------------------------ add-finding
    async def test_add_finding_above_threshold_returns_advisory(self, svc):
        review = (await svc.create("review", "My review")).item
        res = await svc.add_finding(review.id, LONG_TITLE)
        assert res.title_advisory is not None

    async def test_add_finding_advisory_names_length(self, svc):
        review = (await svc.create("review", "My review")).item
        res = await svc.add_finding(review.id, LONG_TITLE)
        assert str(len(LONG_TITLE)) in (res.title_advisory or "")

    async def test_add_finding_advisory_names_body_command(self, svc):
        review = (await svc.create("review", "My review")).item
        res = await svc.add_finding(review.id, LONG_TITLE)
        advisory = res.title_advisory or ""
        assert "body" in advisory
        assert res.local_id in advisory

    async def test_add_finding_at_threshold_no_advisory(self, svc):
        review = (await svc.create("review", "My review")).item
        res = await svc.add_finding(review.id, EXACT_TITLE)
        assert res.title_advisory is None

    async def test_add_finding_below_threshold_no_advisory(self, svc):
        review = (await svc.create("review", "My review")).item
        res = await svc.add_finding(review.id, SHORT_TITLE)
        assert res.title_advisory is None

    async def test_add_finding_still_creates_sub_entity(self, svc):
        review = (await svc.create("review", "My review")).item
        res = await svc.add_finding(review.id, LONG_TITLE)
        assert res.local_id is not None
        assert res.path.exists()

    # ------------------------------------------------------------------ reflog
    async def test_add_story_advisory_recorded_in_reflog(self, svc, frozen_time):
        feat = (await svc.create("feature", "F")).item
        await svc.add_story(feat.id, LONG_TITLE)
        lines = await read_lines(reflog_path(svc.paths.squad_dir))
        sub_lines = [ln for ln in lines if ln.op == "subentity" and ln.target == feat.id]
        add_lines = [ln for ln in sub_lines if ln.delta.get("op") == "add"]
        assert add_lines, "no subentity add entry in reflog"
        delta = add_lines[-1].delta
        assert "title_advisory" in delta
        ta = delta["title_advisory"]
        assert isinstance(ta, dict)
        assert ta["advisory"] is True
        assert ta["title_len"] == len(LONG_TITLE)

    async def test_add_story_no_advisory_reflog_no_title_advisory_key(self, svc, frozen_time):
        feat = (await svc.create("feature", "F")).item
        await svc.add_story(feat.id, SHORT_TITLE)
        lines = await read_lines(reflog_path(svc.paths.squad_dir))
        sub_lines = [ln for ln in lines if ln.op == "subentity" and ln.target == feat.id]
        add_lines = [ln for ln in sub_lines if ln.delta.get("op") == "add"]
        assert add_lines
        assert "title_advisory" not in add_lines[-1].delta

    async def test_add_subtask_advisory_recorded_in_reflog(self, svc, frozen_time):
        task = (await svc.create("task", "T")).item
        await svc.add_subtask(task.id, LONG_TITLE)
        lines = await read_lines(reflog_path(svc.paths.squad_dir))
        sub_lines = [ln for ln in lines if ln.op == "subentity" and ln.target == task.id]
        add_lines = [ln for ln in sub_lines if ln.delta.get("op") == "add"]
        assert add_lines
        delta = add_lines[-1].delta
        assert "title_advisory" in delta
        assert delta["title_advisory"]["advisory"] is True  # type: ignore[index]

    async def test_add_finding_advisory_recorded_in_reflog(self, svc, frozen_time):
        review = (await svc.create("review", "R")).item
        await svc.add_finding(review.id, LONG_TITLE)
        lines = await read_lines(reflog_path(svc.paths.squad_dir))
        sub_lines = [ln for ln in lines if ln.op == "subentity" and ln.target == review.id]
        add_lines = [ln for ln in sub_lines if ln.delta.get("op") == "add"]
        assert add_lines
        assert "title_advisory" in add_lines[-1].delta

    # ------------------------------------------------------------------ advisory wording
    async def test_advisory_wording_no_enforcement_language(self, svc):
        """Warning text is advisory; no enforcement/gate/forbid language (ADR-000167)."""
        feat = (await svc.create("feature", "F")).item
        res = await svc.add_story(feat.id, LONG_TITLE)
        advisory = (res.title_advisory or "").lower()
        for forbidden in ("enforce", "guarantee", "secur", "forbid", "blocked", "prevented"):
            assert forbidden not in advisory, (
                f"advisory must not contain {forbidden!r}; got: {res.title_advisory!r}"
            )

    async def test_advisory_wording_advisory_language_present(self, svc):
        """Warning text mentions the char count and the body command."""
        feat = (await svc.create("feature", "F")).item
        res = await svc.add_story(feat.id, LONG_TITLE)
        advisory = res.title_advisory or ""
        assert str(len(LONG_TITLE)) in advisory
        assert "body" in advisory.lower()


# ---------------------------------------------------------------------------
# CLI smoke tests
# ---------------------------------------------------------------------------


class TestCLITitleAdvisory:
    """Warning renders on the human path; --json carries it; exit 0."""

    async def test_add_story_long_title_prints_advisory_exit_0(self, project, invoke):
        """sq feature N add-story LONG_TITLE warns and exits 0."""
        # Role takes seq 1; feature takes seq 2
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        result = await invoke(["feature", "2", "add-story", LONG_TITLE])
        assert result.exit_code == 0, result.output
        assert str(len(LONG_TITLE)) in result.output
        assert "body" in result.output.lower()

    async def test_add_story_long_title_still_creates(self, project, invoke):
        """Sub-entity is created even when the advisory fires."""
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        result = await invoke(["feature", "2", "add-story", LONG_TITLE])
        assert result.exit_code == 0, result.output
        # The 'added' confirmation line must also appear
        assert "added" in result.output or "US" in result.output

    async def test_add_story_short_title_no_advisory(self, project, invoke):
        """Short title produces no advisory output."""
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        result = await invoke(["feature", "2", "add-story", SHORT_TITLE])
        assert result.exit_code == 0, result.output
        assert str(len(SHORT_TITLE)) not in result.output or "chars" not in result.output

    async def test_add_story_long_title_json_carries_field(self, project, invoke):
        """--json output carries title_advisory for an over-long title."""
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        result = await invoke(["feature", "2", "add-story", LONG_TITLE, "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "title_advisory" in data
        assert data["title_advisory"] is not None
        assert str(len(LONG_TITLE)) in data["title_advisory"]

    async def test_add_story_short_title_json_no_advisory_field(self, project, invoke):
        """--json output has no title_advisory key (or None) for a short title."""
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        result = await invoke(["feature", "2", "add-story", SHORT_TITLE, "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data.get("title_advisory") is None

    async def test_add_subtask_long_title_prints_advisory_exit_0(self, project, invoke):
        """sq task N add-subtask LONG_TITLE warns and exits 0."""
        await invoke(["create", "task", "My task", "--author", "manager"])
        result = await invoke(["task", "2", "add-subtask", LONG_TITLE])
        assert result.exit_code == 0, result.output
        assert str(len(LONG_TITLE)) in result.output
        assert "body" in result.output.lower()

    async def test_add_subtask_short_title_no_advisory(self, project, invoke):
        await invoke(["create", "task", "My task", "--author", "manager"])
        result = await invoke(["task", "2", "add-subtask", SHORT_TITLE])
        assert result.exit_code == 0, result.output
        assert "chars" not in result.output

    async def test_add_subtask_long_title_json_carries_field(self, project, invoke):
        await invoke(["create", "task", "My task", "--author", "manager"])
        result = await invoke(["task", "2", "add-subtask", LONG_TITLE, "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "title_advisory" in data
        assert data["title_advisory"] is not None

    async def test_add_finding_long_title_prints_advisory_exit_0(self, project, invoke):
        """sq review N add-finding LONG_TITLE warns and exits 0."""
        await invoke(["create", "review", "My review", "--author", "manager"])
        result = await invoke(["review", "2", "add-finding", LONG_TITLE])
        assert result.exit_code == 0, result.output
        assert str(len(LONG_TITLE)) in result.output
        assert "body" in result.output.lower()

    async def test_add_finding_short_title_no_advisory(self, project, invoke):
        await invoke(["create", "review", "My review", "--author", "manager"])
        result = await invoke(["review", "2", "add-finding", SHORT_TITLE])
        assert result.exit_code == 0, result.output
        assert "chars" not in result.output

    async def test_add_finding_long_title_json_carries_field(self, project, invoke):
        await invoke(["create", "review", "My review", "--author", "manager"])
        result = await invoke(["review", "2", "add-finding", LONG_TITLE, "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "title_advisory" in data
        assert data["title_advisory"] is not None

    async def test_add_finding_at_threshold_no_advisory_cli(self, project, invoke):
        """Exactly 120 chars → silent (at-threshold boundary)."""
        await invoke(["create", "review", "My review", "--author", "manager"])
        result = await invoke(["review", "2", "add-finding", EXACT_TITLE])
        assert result.exit_code == 0, result.output
        assert "chars" not in result.output


# ---------------------------------------------------------------------------
# TASK-000169: sq check advisory rule for over-long sub-entity titles
# ---------------------------------------------------------------------------


class TestCheckSubentityTitleLengths:
    """_check_subentity_title_lengths fires warn-level issues for titles > 120 chars.

    sq check exits 0 with only advisory (warn) issues — errors are the only
    thing that triggers Exit(3).
    """

    # ------------------------------------------------------------------ service unit

    async def test_short_titles_no_advisory_issues(self, svc):
        """Items with short sub-entity titles produce no check advisory issues."""
        feat = (await svc.create("feature", "My feature")).item
        await svc.add_story(feat.id, SHORT_TITLE)
        issues = await svc.check()
        title_issues = [i for i in issues if "advisory" in i.message and "chars" in i.message]
        assert not title_issues

    async def test_long_story_title_emits_warn_issue(self, svc):
        """A story with title > 120 chars emits a warn-level check issue."""
        feat = (await svc.create("feature", "My feature")).item
        await svc.add_story(feat.id, LONG_TITLE)
        issues = await svc.check()
        title_issues = [i for i in issues if "advisory" in i.message and "chars" in i.message]
        assert len(title_issues) == 1
        assert title_issues[0].level == "warn"

    async def test_long_subtask_title_emits_warn_issue(self, svc):
        """A subtask with title > 120 chars emits a warn-level check issue."""
        task = (await svc.create("task", "My task")).item
        await svc.add_subtask(task.id, LONG_TITLE)
        issues = await svc.check()
        title_issues = [i for i in issues if "advisory" in i.message and "chars" in i.message]
        assert len(title_issues) == 1
        assert title_issues[0].level == "warn"

    async def test_long_finding_title_emits_warn_issue(self, svc):
        """A finding with title > 120 chars emits a warn-level check issue."""
        review = (await svc.create("review", "My review")).item
        await svc.add_finding(review.id, LONG_TITLE)
        issues = await svc.check()
        title_issues = [i for i in issues if "advisory" in i.message and "chars" in i.message]
        assert len(title_issues) == 1
        assert title_issues[0].level == "warn"

    async def test_issue_references_item_id(self, svc):
        """The check issue carries the parent item ID."""
        feat = (await svc.create("feature", "My feature")).item
        await svc.add_story(feat.id, LONG_TITLE)
        issues = await svc.check()
        title_issues = [i for i in issues if "advisory" in i.message and "chars" in i.message]
        assert title_issues[0].item == feat.id

    async def test_issue_message_contains_length(self, svc):
        """The check issue message includes the actual char count."""
        feat = (await svc.create("feature", "My feature")).item
        await svc.add_story(feat.id, LONG_TITLE)
        issues = await svc.check()
        title_issues = [i for i in issues if "advisory" in i.message and "chars" in i.message]
        assert str(len(LONG_TITLE)) in title_issues[0].message

    async def test_issue_message_references_threshold(self, svc):
        """The check issue message references the threshold value."""
        feat = (await svc.create("feature", "My feature")).item
        await svc.add_story(feat.id, LONG_TITLE)
        issues = await svc.check()
        title_issues = [i for i in issues if "advisory" in i.message and "chars" in i.message]
        assert str(TITLE_ADVISORY_MAX) in title_issues[0].message

    async def test_at_threshold_no_check_issue(self, svc):
        """Title exactly at threshold (120 chars) does not emit a check issue."""
        feat = (await svc.create("feature", "My feature")).item
        await svc.add_story(feat.id, EXACT_TITLE)
        issues = await svc.check()
        title_issues = [i for i in issues if "advisory" in i.message and "chars" in i.message]
        assert not title_issues

    async def test_multiple_long_titles_multiple_issues(self, svc):
        """Each over-long title produces its own warn issue."""
        feat = (await svc.create("feature", "My feature")).item
        await svc.add_story(feat.id, LONG_TITLE)
        await svc.add_story(feat.id, LONG_TITLE)
        issues = await svc.check()
        title_issues = [i for i in issues if "advisory" in i.message and "chars" in i.message]
        assert len(title_issues) == 2

    async def test_mixed_long_and_short_only_long_flagged(self, svc):
        """Only the over-long title is flagged; the short one is silent."""
        feat = (await svc.create("feature", "My feature")).item
        await svc.add_story(feat.id, LONG_TITLE)
        await svc.add_story(feat.id, SHORT_TITLE)
        issues = await svc.check()
        title_issues = [i for i in issues if "advisory" in i.message and "chars" in i.message]
        assert len(title_issues) == 1

    async def test_warn_only_does_not_flip_to_error_level(self, svc):
        """Advisory issues are always warn, never error."""
        feat = (await svc.create("feature", "My feature")).item
        await svc.add_story(feat.id, LONG_TITLE)
        issues = await svc.check()
        title_issues = [i for i in issues if "advisory" in i.message and "chars" in i.message]
        for issue in title_issues:
            assert issue.level == "warn", f"expected warn, got {issue.level!r}"

    # ------------------------------------------------------------------ CLI smoke

    async def test_check_long_title_exits_0(self, project, invoke):
        """sq check exits 0 when the only issues are advisory warn-level."""
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "add-story", LONG_TITLE])
        result = await invoke(["check"])
        assert result.exit_code == 0, f"expected exit 0, got {result.exit_code}: {result.output}"

    async def test_check_long_title_prints_warn(self, project, invoke):
        """sq check prints the advisory warn line for over-long titles."""
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "add-story", LONG_TITLE])
        result = await invoke(["check"])
        assert result.exit_code == 0
        assert "warn" in result.output.lower()
        assert "advisory" in result.output.lower()

    async def test_check_short_title_clean(self, project, invoke):
        """sq check is clean when all sub-entity titles are short."""
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "add-story", SHORT_TITLE])
        result = await invoke(["check"])
        assert result.exit_code == 0
        # "no issues" or the specific issue, but NOT a title-advisory warn line
        assert str(len(SHORT_TITLE)) not in result.output or "chars" not in result.output

    async def test_check_json_includes_advisory(self, project, invoke):
        """sq check --json includes the advisory issue and exits 0."""
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "add-story", LONG_TITLE])
        result = await invoke(["check", "--json"])
        assert result.exit_code == 0, f"expected exit 0, got {result.exit_code}: {result.output}"
        data = json.loads(result.output)
        assert isinstance(data, list)
        advisory_issues = [
            i for i in data if i.get("level") == "warn" and "advisory" in i.get("message", "")
        ]
        assert advisory_issues, f"expected advisory issue in JSON output: {data}"

    async def test_check_json_advisory_no_errors(self, project, invoke):
        """sq check --json: advisory issues have level 'warn', not 'error'."""
        await invoke(["create", "feature", "My feature", "--author", "manager"])
        await invoke(["feature", "2", "add-story", LONG_TITLE])
        result = await invoke(["check", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        error_issues = [i for i in data if i.get("level") == "error"]
        assert not error_issues, f"advisory must not produce error-level issues: {error_issues}"
