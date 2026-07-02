"""Custom-status regression coverage for FEAT-000211 AC#1/AC#2 (TASK-000278).

Proves that a project-declared custom lifecycle (via ``.overrides/workflow.toml``) flows
correctly through every query/filter surface that classifies items by status:

- ``parse_status`` (`_cli/_common.py`) accepts custom statuses and rejects unknown ones with
  an actionable "known values: …" error.
- ``sq list --status <custom>`` returns items in that status.
- ``sq list`` (default, no ``--all``) hides items in a custom **terminal** status and shows
  items in a custom **non-terminal** status.
- ``sq blocked`` treats a blocker in a custom non-terminal status as still-blocking, and one
  in a custom terminal status as cleared.
- ``sq inbox`` suppresses ``@mention``s in items whose status is a custom terminal status, and
  surfaces mentions in items whose status is a custom non-terminal status.

Per the codebase investigation for this task, every one of these surfaces
(`_services/_base.py`, `_services/_refs.py`, `_services/_collab.py`, `_services/_roster.py`,
`_cli/_main.py`) already reads `spec.is_open(status)` / `spec.statuses` rather than the
built-in `Status` enum or a `TERMINAL` frozenset — this module is a **characterization +
regression** test proving that end-to-end with a real override spec, not a rewire. No
production hardcode was found or changed for this task (see TASK-278 comment).

Uses a custom type (``incident``) with a custom lifecycle (``Triage -> Mitigating -> Resolved``,
mirroring FEAT-000211's worked example) so real items can be created, transitioned, and queried
through the CLI exactly as a project with this override would use it.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from squads._cli import app

pytestmark = pytest.mark.anyio

_INCIDENT_OVERRIDE = """
[statuses.Triage]
terminal = false

[statuses.Mitigating]
terminal = false

[statuses.Resolved]
terminal = true

[lifecycles.incident_lc]
initial = "Triage"

[lifecycles.incident_lc.transitions]
Triage = ["Mitigating", "Resolved"]
Mitigating = ["Resolved"]
Resolved = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
"""


@pytest.fixture
def custom_squad(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_time: Any) -> CliRunner:
    """A minimal-roster squad with the incident override installed (roster/clock pinned)."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    r = runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    assert r.exit_code == 0, r.output
    override_dir = tmp_path / "squads" / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_INCIDENT_OVERRIDE, encoding="utf-8")
    return runner


def _inv(runner: CliRunner, args: list[str]) -> Any:
    r = runner.invoke(app, args)
    assert r.exit_code == 0, f"{args!r} failed (exit {r.exit_code}):\n{r.output}"
    return r


class TestParseStatusAcceptsCustomAndRejectsUnknown:
    """``parse_status`` validates against the loaded spec's vocabulary (AC#1)."""

    def test_list_status_custom_value_accepted(self, custom_squad: CliRunner) -> None:
        _inv(custom_squad, ["create", "incident", "First incident", "--author", "manager"])
        r = custom_squad.invoke(app, ["list", "--status", "Triage"])
        assert r.exit_code == 0, r.output
        assert "INC-000002" in r.output

    def test_list_status_unknown_value_gives_actionable_error(
        self, custom_squad: CliRunner
    ) -> None:
        r = custom_squad.invoke(app, ["list", "--status", "Bogus"])
        assert r.exit_code == 1
        assert "unknown status" in r.output
        assert "Bogus" in r.output
        # The custom statuses appear among the listed known values.
        assert "Triage" in r.output
        assert "Mitigating" in r.output
        assert "Resolved" in r.output

    def test_list_status_loose_match_still_works_for_custom_value(
        self, custom_squad: CliRunner
    ) -> None:
        """Loose matching (case/underscore-insensitive) applies to custom statuses too."""
        _inv(custom_squad, ["create", "incident", "Loose match test", "--author", "manager"])
        r = custom_squad.invoke(app, ["list", "--status", "triage"])
        assert r.exit_code == 0, r.output
        assert "INC-000002" in r.output


class TestListStatusFilterReturnsCustomStatusItems:
    """``sq list --status <custom>`` returns exactly the items in that status (AC#1/US1)."""

    def test_list_status_triage_returns_only_triage_items(self, custom_squad: CliRunner) -> None:
        _inv(custom_squad, ["create", "incident", "Incident A", "--author", "manager"])  # INC-2
        _inv(custom_squad, ["create", "incident", "Incident B", "--author", "manager"])  # INC-3
        _inv(custom_squad, ["incident", "3", "update", "--status", "Resolved"])
        r = custom_squad.invoke(app, ["list", "--status", "Triage"])
        assert r.exit_code == 0, r.output
        assert "INC-000002" in r.output
        assert "INC-000003" not in r.output


class TestListDefaultFilterHonorsCustomTerminality:
    """``sq list`` (default, no ``--all``) hides custom-terminal items, shows custom-open ones
    (AC#1/US1)."""

    @pytest.mark.parametrize(
        ("status_value", "expected_hidden"),
        [
            ("Triage", False),
            ("Mitigating", False),
            ("Resolved", True),
        ],
    )
    def test_list_default_filter_by_custom_status(
        self, custom_squad: CliRunner, status_value: str, expected_hidden: bool
    ) -> None:
        _inv(custom_squad, ["create", "incident", "Incident", "--author", "manager"])  # INC-2
        _inv(custom_squad, ["incident", "2", "update", "--status", status_value])
        r = custom_squad.invoke(app, ["list"])
        assert r.exit_code == 0, r.output
        is_hidden = "INC-000002" not in r.output
        assert is_hidden == expected_hidden, (
            f"status {status_value!r}: expected hidden={expected_hidden}, "
            f"actual hidden={is_hidden}.\n{r.output}"
        )
        # --all always shows it regardless of status.
        r_all = custom_squad.invoke(app, ["list", "--all"])
        assert "INC-000002" in r_all.output


class TestBlockedHonorsCustomTerminality:
    """``sq blocked`` treats a custom non-terminal status as open, a custom terminal status as
    cleared (AC#2/US1)."""

    def test_blocked_by_non_terminal_custom_status_still_blocks(
        self, custom_squad: CliRunner
    ) -> None:
        _inv(custom_squad, ["create", "incident", "Blocker", "--author", "manager"])  # INC-2
        _inv(custom_squad, ["create", "incident", "Dependent", "--author", "manager"])  # INC-3
        _inv(
            custom_squad,
            ["incident", "3", "ref", "add", "INC-000002", "--kind", "depends-on"],
        )
        # Blocker stays at Triage (non-terminal) — still counts as blocking.
        r = custom_squad.invoke(app, ["blocked"])
        assert r.exit_code == 0, r.output
        assert "INC-000003" in r.output
        assert "blocked by" in r.output
        assert "INC-000002" in r.output

    def test_blocked_cleared_once_blocker_reaches_custom_terminal_status(
        self, custom_squad: CliRunner
    ) -> None:
        _inv(custom_squad, ["create", "incident", "Blocker", "--author", "manager"])  # INC-2
        _inv(custom_squad, ["create", "incident", "Dependent", "--author", "manager"])  # INC-3
        _inv(
            custom_squad,
            ["incident", "3", "ref", "add", "INC-000002", "--kind", "depends-on"],
        )
        _inv(custom_squad, ["incident", "2", "update", "--status", "Resolved"])
        r = custom_squad.invoke(app, ["blocked"])
        assert r.exit_code == 0, r.output
        assert "nothing blocked" in r.output

    def test_blocked_json_shape_reports_custom_status_string(self, custom_squad: CliRunner) -> None:
        _inv(custom_squad, ["create", "incident", "Blocker", "--author", "manager"])  # INC-2
        _inv(custom_squad, ["create", "incident", "Dependent", "--author", "manager"])  # INC-3
        _inv(
            custom_squad,
            ["incident", "3", "ref", "add", "INC-000002", "--kind", "depends-on"],
        )
        r = custom_squad.invoke(app, ["blocked", "--json"])
        assert r.exit_code == 0, r.output
        data = json.loads(r.output)
        assert data == [
            {
                "id": "INC-000003",
                "title": "Dependent",
                "blockers": [{"id": "INC-000002", "title": "Blocker", "status": "Triage"}],
            }
        ]


class TestInboxHonorsCustomTerminality:
    """``sq inbox`` suppresses mentions in items with a custom terminal status (AC#2/US1)."""

    def test_inbox_shows_mention_in_custom_non_terminal_item(self, custom_squad: CliRunner) -> None:
        _inv(custom_squad, ["create", "incident", "Open incident", "--author", "manager"])  # INC-2
        _inv(
            custom_squad,
            ["incident", "2", "comment", "--as", "manager", "-m", "please look @manager"],
        )
        r = custom_squad.invoke(app, ["inbox", "manager"])
        assert r.exit_code == 0, r.output
        assert "INC-000002" in r.output

    def test_inbox_suppresses_mention_in_custom_terminal_item(
        self, custom_squad: CliRunner
    ) -> None:
        _inv(
            custom_squad, ["create", "incident", "Resolved incident", "--author", "manager"]
        )  # INC-2
        _inv(custom_squad, ["incident", "2", "update", "--status", "Resolved"])
        _inv(
            custom_squad,
            ["incident", "2", "comment", "--as", "manager", "-m", "please look @manager"],
        )
        r = custom_squad.invoke(app, ["inbox", "manager"])
        assert r.exit_code == 0, r.output
        assert "INC-000002" not in r.output

    def test_inbox_mixed_open_and_closed_only_reports_open(self, custom_squad: CliRunner) -> None:
        _inv(custom_squad, ["create", "incident", "Open incident", "--author", "manager"])  # INC-2
        _inv(
            custom_squad, ["create", "incident", "Resolved incident", "--author", "manager"]
        )  # INC-3
        _inv(custom_squad, ["incident", "3", "update", "--status", "Resolved"])
        _inv(
            custom_squad,
            ["incident", "2", "comment", "--as", "manager", "-m", "look here @manager"],
        )
        _inv(
            custom_squad,
            ["incident", "3", "comment", "--as", "manager", "-m", "and here too @manager"],
        )
        r = custom_squad.invoke(app, ["inbox", "manager"])
        assert r.exit_code == 0, r.output
        assert "INC-000002" in r.output
        assert "INC-000003" not in r.output
