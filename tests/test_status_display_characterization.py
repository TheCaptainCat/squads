"""Characterization baseline for status display, filtering, and blocking — pinned against HEAD.

**GATING TEST — must stay green through any rework of status handling.**

This module locks in, byte-for-byte, how built-in item/sub-entity statuses are displayed and
queried today, so that generalizing status handling to support custom (project-defined)
statuses cannot silently change built-in behavior. It is deliberately written and made green
*before* any such rework begins, so the rework runs under a passing guard rather than trusting
a trailing test that could be skipped or watered down.

Scope note: custom-status work is expected to fix a real crash — badge lookup today resolves
a status by parsing it back into the built-in ``Status`` enum, which raises on any status
value outside that enum — and to give badge-less statuses a graceful default. But it must NOT
introduce a *new* display surface: today, top-level item status (``sq show``'s ``status:``
line, ``sq list``'s Status column) is rendered as a plain string with no badge at all, and this
module pins that absence as intentional. Only sub-entity "head" regions (subtasks/stories/
findings) show a badge today; that's the one surface where badge-resolution logic runs, and
it's the one this baseline pins in full.

What is pinned here (see class docstrings for detail):

1. ``sq workflow`` cheatsheet — already gated by ``tests/test_workflow_renderer_261.py``
   (``TestByteIdenticalForBundledSpec.test_workflow_cheatsheet_matches_golden``, backed by
   ``tests/goldens/workflow_cheatsheet.txt``). Not duplicated here; this module only adds a
   cross-check that the golden file is exercised as expected, and documents the dependency.
2. Status badges — every one of the 9 sub-entity statuses (``EXPECTED_BUILTIN_STATUS_BADGES``'s
   domain, in ``tests/_helpers.py``: Todo/InProgress/Blocked/Done/Cancelled for subtask+story,
   Open/Fixed/WontFix/Verified for finding) resolves to its exact ``_discussion._status_badge``
   text, and that exact text
   appears verbatim in a sub-entity's rendered ``:head`` region on disk. Also pins that
   top-level item statuses (``sq <type> show`` panel line, ``sq list`` Status column) render
   with NO badge — plain status string — today.
3. ``sq list`` default closed-item filter + ``sq blocked`` open/terminal classification for
   every built-in top-level status, via a small fixture squad with a ``blocks``/``depends-on``
   edge.

Pinning discipline (see the "pin the roster when diffing generated output" project lesson,
and CLAUDE.md's testing section):

- **Roster held constant.** Every fixture below inits with ``--roles minimal`` (the same
  roster the shared ``project``/``svc`` fixtures use) so no test here can produce a false
  diff from a roster mismatch. None of the surfaces pinned in this module are roster-
  dependent (``workflow.md.j2`` renders from the spec only; badges/list/blocked are pure
  status-machine surfaces) — the roster is pinned anyway, for documentation and so a future
  edit that accidentally makes one of them roster-sensitive is caught by drift, not by luck.
- **Clock frozen** via the ``frozen_time`` fixture (never ``datetime.now()``) — the fixture
  squad's ``created_at``/``updated_at`` timestamps are asserted below so the freeze is
  load-bearing, not decorative, and nothing here can become wall-clock-sensitive later.
- **Flags explicit** — every CLI invocation below passes ``--author``/``--status``/``--force``
  explicitly; nothing relies on ambient defaults that could shift.

Nothing in this module could be made deterministic and was skipped — flag if that changes.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from _helpers import EXPECTED_BUILTIN_STATUS_BADGES
from squads import _discussion as discussion
from squads._cli import app

pytestmark = pytest.mark.anyio

# The wall-clock timestamp frozen_time pins — asserted on the fixture squad's first item
# below so the freeze is exercised rather than merely present.
_FROZEN_ISO = "2026-06-07T10:00:00Z"


# ---------------------------------------------------------------------------
# Shared deterministic fixture squad (roster + clock pinned)
# ---------------------------------------------------------------------------


@pytest.fixture
def pinned_squad(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_time: Any) -> CliRunner:
    """A minimal-roster, frozen-clock squad — pinned inputs for every test in this module."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    r = runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    assert r.exit_code == 0, r.output
    # Confirm the clock freeze actually took (load-bearing use of frozen_time, not decorative).
    role_json = json.loads(runner.invoke(app, ["show", "ROLE-000001", "--json"]).output)
    assert role_json["created_at"] == _FROZEN_ISO, (
        f"frozen_time fixture did not pin the clock as expected: {role_json['created_at']!r} "
        f"!= {_FROZEN_ISO!r}"
    )
    return runner


def _inv(runner: CliRunner, args: list[str]) -> Any:
    r = runner.invoke(app, args)
    assert r.exit_code == 0, f"{args!r} failed (exit {r.exit_code}):\n{r.output}"
    return r


# ---------------------------------------------------------------------------
# 1. sq workflow cheatsheet — cross-check the existing byte-identical golden is load-bearing
# ---------------------------------------------------------------------------


class TestWorkflowCheatsheetGoldenIsGating:
    """The `sq workflow` byte-identical golden already exists — confirm it holds.

    ``tests/test_workflow_renderer_261.py::TestByteIdenticalForBundledSpec
    .test_workflow_cheatsheet_matches_golden`` compares ``render("workflow.md.j2",
    spec=bundled_spec())`` against ``tests/goldens/workflow_cheatsheet.txt``. That test has
    no roster/clock dependency (the template only consumes the WorkflowSpec), so it already
    gates the cheatsheet output for any status-handling rework. This test re-asserts the same
    fact from this module so a reviewer scanning this file sees the coverage without having
    to cross-reference another module, and so CI failure attribution is unambiguous.
    """

    def test_bundled_workflow_cheatsheet_golden_exists_and_matches(self) -> None:
        from squads._rendering._engine import render
        from squads._workflow import bundled_spec

        golden_path = Path(__file__).parent / "goldens" / "workflow_cheatsheet.txt"
        assert golden_path.exists(), (
            f"Golden file missing: {golden_path} — this golden must exist so status-handling "
            "changes run under a byte-identical guard."
        )
        expected = golden_path.read_text(encoding="utf-8")
        actual = render("workflow.md.j2", spec=bundled_spec())
        assert actual == expected, (
            "sq workflow cheatsheet drifted from the HEAD golden — the bundled (non-custom) "
            "spec's cheatsheet text must stay byte-identical."
        )


# ---------------------------------------------------------------------------
# 2. Status badges — every built-in sub-entity status + top-level no-badge invariant
# ---------------------------------------------------------------------------

# The exact badge text _status_badge produces today for all 9 sub-entity statuses
# (EXPECTED_BUILTIN_STATUS_BADGES's full domain, see tests/_helpers.py). This is the exact
# function that crashes on a status value outside the built-in enum — built-in values must
# keep producing exactly this text once that crash is fixed for non-built-in values.
_EXPECTED_BADGES: dict[str, str] = {
    "Todo": "⚪ Todo",
    "InProgress": "🟡 In Progress",
    "Blocked": "🔴 Blocked",
    "Done": "🟢 Done",
    "Cancelled": "⚫ Cancelled",
    "Open": "🔴 Open",
    "Fixed": "🟡 Fixed",
    "Verified": "🟢 Verified",
    "WontFix": "⚫ Wont Fix",
}

# Statuses reachable on a review finding (subset of _EXPECTED_BADGES's domain).
_FINDING_STATUSES = ("Fixed", "Verified", "WontFix")


class TestStatusBadgeFunction:
    """Pin `_discussion._status_badge` for every one of the 9 sub-entity statuses.

    EXPECTED_BUILTIN_STATUS_BADGES (tests/_helpers.py) covers exactly these 9 values today. A
    change that alters any of these mappings, or the "InProgress" -> "In Progress" spacing rule,
    would regress built-in badge display.
    """

    def test_status_emoji_domain_is_exactly_the_nine_subentity_statuses(self) -> None:
        assert set(EXPECTED_BUILTIN_STATUS_BADGES) == set(_EXPECTED_BADGES), (
            "EXPECTED_BUILTIN_STATUS_BADGES's domain changed from the 9 sub-entity statuses "
            "known today; extend _EXPECTED_BADGES deliberately if this is correct."
        )

    @pytest.mark.parametrize("status_value", sorted(_EXPECTED_BADGES))
    def test_status_badge_exact_text(self, status_value: str) -> None:
        assert discussion._status_badge(status_value) == _EXPECTED_BADGES[status_value]  # pyright: ignore[reportPrivateUsage]


class TestSubEntityHeadBadgeOnDisk:
    """The exact `_status_badge` text appears verbatim in a sub-entity's rendered :head region.

    Drives every status via `update --force` (bypassing transition validation) so all 9
    values are reachable deterministically regardless of the machine's transition graph.
    """

    @pytest.mark.parametrize(
        ("status_value", "expected_line"),
        [(s, f"**Status:** {b}") for s, b in _EXPECTED_BADGES.items() if s != "Todo"],
    )
    def test_subtask_head_badge(
        self, pinned_squad: CliRunner, status_value: str, expected_line: str
    ) -> None:
        _inv(pinned_squad, ["create", "task", "T", "--author", "manager"])  # TASK-000002
        _inv(pinned_squad, ["task", "2", "add-subtask", "A subtask"])  # ST1, Todo
        _inv(
            pinned_squad,
            ["task", "2", "subtask", "1", "update", "--status", status_value, "--force"],
        )
        text = Path("squads/tasks/TASK-000002-t.md").read_text(encoding="utf-8")
        assert expected_line in text, (
            f"Expected sub-entity head badge line {expected_line!r} for status "
            f"{status_value!r} not found verbatim in the rendered file.\n{text}"
        )

    def test_subtask_head_badge_initial_status(self, pinned_squad: CliRunner) -> None:
        """A freshly-created subtask (Todo, the initial status) already carries a head badge.

        A new sub-entity always has a status (the machine's initial state), so set_head
        renders a badge from the moment the block is created — pins the exact text for the
        default/initial case, not just for explicitly-transitioned statuses.
        """
        _inv(pinned_squad, ["create", "task", "T", "--author", "manager"])
        _inv(pinned_squad, ["task", "2", "add-subtask", "A subtask"])
        text = Path("squads/tasks/TASK-000002-t.md").read_text(encoding="utf-8")
        assert "**Status:** ⚪ Todo" in text, (
            "Initial (Todo) sub-entity status must render its badge exactly as today."
        )

    @pytest.mark.parametrize(
        ("status_value", "expected_line"),
        [(s, f"**Status:** {b}") for s, b in _EXPECTED_BADGES.items() if s in _FINDING_STATUSES],
    )
    def test_finding_head_badge(
        self, pinned_squad: CliRunner, status_value: str, expected_line: str
    ) -> None:
        _inv(pinned_squad, ["create", "review", "R", "--author", "manager"])  # REV-000002
        _inv(pinned_squad, ["review", "2", "add-finding", "A finding", "--severity", "high"])
        _inv(
            pinned_squad,
            ["review", "2", "finding", "1", "update", "--status", status_value, "--force"],
        )
        text = Path("squads/reviews/REV-000002-r.md").read_text(encoding="utf-8")
        assert expected_line in text, (
            f"Expected sub-entity head badge line {expected_line!r} for status "
            f"{status_value!r} not found verbatim in the rendered file.\n{text}"
        )


class TestTopLevelStatusHasNoBadgeToday:
    """Pin that top-level item status display stays badge-free (byte-identical) today.

    Badge resolution (and its crash on non-built-in values) only runs for sub-entity
    displays today. Top-level `sq show` and `sq list` render the raw status string with no
    badge at all — generalizing badge support to non-built-in statuses must not introduce a
    *new* badge display on these surfaces. These tests fail the moment one is introduced.
    """

    def test_show_panel_status_line_has_no_badge(self, pinned_squad: CliRunner) -> None:
        _inv(pinned_squad, ["create", "task", "Plain task", "--author", "manager"])
        r = pinned_squad.invoke(app, ["task", "2", "show"])
        assert r.exit_code == 0, r.output
        assert "status: Draft" in r.output
        for emoji in EXPECTED_BUILTIN_STATUS_BADGES.values():
            assert emoji not in r.output, (
                f"Badge emoji {emoji!r} found in top-level `sq show` output — this is a new "
                "display surface that must not appear (top-level status has no badge today)."
            )

    def test_list_status_column_has_no_badge(self, pinned_squad: CliRunner) -> None:
        _inv(pinned_squad, ["create", "task", "Plain task", "--author", "manager"])
        r = pinned_squad.invoke(app, ["list"])
        assert r.exit_code == 0, r.output
        assert "Draft" in r.output
        for emoji in EXPECTED_BUILTIN_STATUS_BADGES.values():
            assert emoji not in r.output, (
                f"Badge emoji {emoji!r} found in `sq list` output — this is a new display "
                "surface that must not appear (top-level status has no badge today)."
            )

    def test_list_json_status_is_plain_string(self, pinned_squad: CliRunner) -> None:
        _inv(pinned_squad, ["create", "task", "Plain task", "--author", "manager"])
        r = pinned_squad.invoke(app, ["list", "--json"])
        assert r.exit_code == 0, r.output
        data = json.loads(r.output)
        by_id = {row["id"]: row for row in data}
        assert by_id["TASK-000002"]["status"] == "Draft"


# ---------------------------------------------------------------------------
# 3. sq list default filter + sq blocked open/terminal classification
# ---------------------------------------------------------------------------


class TestListDefaultFilterAndBlocked:
    """Pin the default-closed-item filter (`sq list`) and `sq blocked` classification.

    Exercises every built-in top-level status via `--force` transitions on a task, so the
    open/terminal boundary is pinned status-by-status, not just for one representative value.
    Also pins the `blocks`/`depends-on` edge semantics `sq blocked` reports on.
    """

    @pytest.mark.parametrize(
        ("status_value", "expected_hidden"),
        [
            ("Draft", False),
            ("Ready", False),
            ("InProgress", False),
            ("InReview", False),
            ("Blocked", False),
            ("Done", True),
            ("Cancelled", True),
        ],
    )
    def test_list_default_filter_by_status(
        self, pinned_squad: CliRunner, status_value: str, expected_hidden: bool
    ) -> None:
        _inv(pinned_squad, ["create", "task", "T", "--author", "manager"])  # TASK-000002
        _inv(pinned_squad, ["task", "2", "update", "--status", status_value, "--force"])
        r = pinned_squad.invoke(app, ["list"])
        assert r.exit_code == 0, r.output
        is_hidden = "TASK-000002" not in r.output
        assert is_hidden == expected_hidden, (
            f"status {status_value!r}: expected hidden={expected_hidden}, "
            f"actual hidden={is_hidden}.\n{r.output}"
        )
        # --all always shows it regardless of status.
        r_all = pinned_squad.invoke(app, ["list", "--all"])
        assert "TASK-000002" in r_all.output

    def test_blocked_open_dependent_on_open_blocker(self, pinned_squad: CliRunner) -> None:
        """An open item depends-on an open blocker: reported by `sq blocked`."""
        _inv(pinned_squad, ["create", "task", "Blocker", "--author", "manager"])  # TASK-000002
        _inv(pinned_squad, ["create", "task", "Dependent", "--author", "manager"])  # TASK-000003
        _inv(pinned_squad, ["task", "3", "ref", "add", "TASK-000002", "--kind", "depends-on"])
        r = pinned_squad.invoke(app, ["blocked"])
        assert r.exit_code == 0, r.output
        assert "TASK-000003" in r.output
        assert "blocked by" in r.output
        assert "TASK-000002" in r.output

    def test_blocked_hides_dependent_once_blocker_closed(self, pinned_squad: CliRunner) -> None:
        """Once the blocker reaches a terminal status, `sq blocked` no longer reports it."""
        _inv(pinned_squad, ["create", "task", "Blocker", "--author", "manager"])  # TASK-000002
        _inv(pinned_squad, ["create", "task", "Dependent", "--author", "manager"])  # TASK-000003
        _inv(pinned_squad, ["task", "3", "ref", "add", "TASK-000002", "--kind", "depends-on"])
        _inv(pinned_squad, ["task", "2", "update", "--status", "Done", "--force"])
        r = pinned_squad.invoke(app, ["blocked"])
        assert r.exit_code == 0, r.output
        assert "nothing blocked" in r.output

    def test_blocked_hides_dependent_once_dependent_closed(self, pinned_squad: CliRunner) -> None:
        """Once the dependent itself is closed, `sq blocked` doesn't report it as open."""
        _inv(pinned_squad, ["create", "task", "Blocker", "--author", "manager"])  # TASK-000002
        _inv(pinned_squad, ["create", "task", "Dependent", "--author", "manager"])  # TASK-000003
        _inv(pinned_squad, ["task", "3", "ref", "add", "TASK-000002", "--kind", "depends-on"])
        _inv(pinned_squad, ["task", "3", "update", "--status", "Cancelled", "--force"])
        r = pinned_squad.invoke(app, ["blocked"])
        assert r.exit_code == 0, r.output
        assert "nothing blocked" in r.output

    def test_blocked_json_shape(self, pinned_squad: CliRunner) -> None:
        _inv(pinned_squad, ["create", "task", "Blocker", "--author", "manager"])  # TASK-000002
        _inv(pinned_squad, ["create", "task", "Dependent", "--author", "manager"])  # TASK-000003
        _inv(pinned_squad, ["task", "3", "ref", "add", "TASK-000002", "--kind", "depends-on"])
        r = pinned_squad.invoke(app, ["blocked", "--json"])
        assert r.exit_code == 0, r.output
        data = json.loads(r.output)
        assert data == [
            {
                "id": "TASK-000003",
                "title": "Dependent",
                "blockers": [{"id": "TASK-000002", "title": "Blocker", "status": "Draft"}],
            }
        ]
