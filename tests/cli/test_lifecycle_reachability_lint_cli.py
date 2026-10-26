"""``sq workflow lint`` CLI exit codes for the reachability-lint family (the algorithm itself
is proven at tests/unit/test_lifecycle_reachability_lint.py) — an off-vocab transition target
and a terminal-unreachable lifecycle both exit 1 with the offending name in the output; a
valid custom override and the bundled spec with no override both exit 0; a custom sub-entity
kind's off-vocab completion status exits 1 too.
"""

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio


def _write_override(squad_dir, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


async def test_exits_1_on_an_off_vocabulary_transition_target(project, invoke):
    _write_override(
        project.squad_dir,
        """
[statuses.Triage]

[lifecycles.incident_lc]
initial = "Triage"
[lifecycles.incident_lc.transitions]
Triage = ["Nowhere"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
""",
    )
    result = await invoke(["workflow", "lint"])
    assert result.exit_code == 1
    assert "Nowhere" in result.output


async def test_exits_1_when_a_custom_lifecycle_can_never_reach_a_terminal_state(project, invoke):
    _write_override(
        project.squad_dir,
        """
[statuses.Triage]
[statuses.Mitigating]

[lifecycles.incident_lc]
initial = "Triage"
[lifecycles.incident_lc.transitions]
Triage = ["Mitigating"]
Mitigating = ["Triage"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
""",
    )
    result = await invoke(["workflow", "lint"])
    assert result.exit_code == 1
    assert "incident_lc" in result.output


async def test_exits_0_on_a_valid_custom_override_and_on_the_bundled_spec_with_no_override(
    project, invoke
):
    clean = await invoke(["workflow", "lint"])
    assert clean.exit_code == 0

    _write_override(
        project.squad_dir,
        """
[statuses.Triage]
[statuses.Resolved]
role = "done"

[lifecycles.incident_lc]
initial = "Triage"
[lifecycles.incident_lc.transitions]
Triage = ["Resolved"]
Resolved = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
""",
    )
    valid_custom = await invoke(["workflow", "lint"])
    assert valid_custom.exit_code == 0


async def test_exits_1_on_a_custom_subentity_kinds_off_vocabulary_completion_status(
    project, invoke
):
    _write_override(
        project.squad_dir,
        """
[lifecycles.action]
initial = "Open"
[lifecycles.action.transitions]
Open = ["InProgress", "Done"]
InProgress = ["Done"]
Done = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "action"
subentity_kind = "action"

[subentity_kinds.action]
lifecycle = "action"
completion = "Verified"
plural = "actions"
local_prefix = "AC"
""",
    )
    result = await invoke(["workflow", "lint"])
    assert result.exit_code == 1
    assert "action" in result.output


async def test_an_override_that_redeclares_open_without_noted_still_lints_clean_and_loads(
    project, invoke
):
    _write_override(
        project.squad_dir,
        f"""# squads:override-base:{__version__}
[lifecycles.finding.transitions]
Open = ["Fixed", "WontFix"]
""",
    )

    lint = await invoke(["workflow", "lint"])
    assert lint.exit_code == 0, lint.output
    assert "unreachable" not in lint.output
    assert (await invoke(["workflow", "lifecycles"])).exit_code == 0


_OWN_STATE_ROWS = {
    "an own state whose entry edge was forgotten": """
[statuses.Parked]
[lifecycles.work.transitions]
Parked = ["Ready"]
""",
    "a chain from an own entry-less state": """
[statuses.Parked]
[statuses.Shelved]
[lifecycles.work.transitions]
Parked = ["Shelved"]
Shelved = ["Ready"]
""",
    "an orphan of a new lifecycle": """
[statuses.Triage]
[statuses.Escalated]
[statuses.Resolved]
role = "done"
[lifecycles.incident_lc]
initial = "Triage"
[lifecycles.incident_lc.transitions]
Triage = ["Resolved"]
Escalated = ["Resolved"]
Resolved = []
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
""",
}


@pytest.mark.parametrize("row", list(_OWN_STATE_ROWS))
async def test_an_adopters_own_unreachable_state_is_still_reported(project, invoke, row: str):
    _write_override(
        project.squad_dir, f"# squads:override-base:{__version__}\n{_OWN_STATE_ROWS[row]}"
    )

    result = await invoke(["workflow", "lint"])

    assert result.exit_code == 1, result.output
    assert "unreachable" in result.output


async def test_an_inherited_state_the_override_stops_entering_lints_clean(project, invoke):
    _write_override(
        project.squad_dir,
        f"""# squads:override-base:{__version__}
[lifecycles.work.transitions]
Ready = ["InProgress", "Cancelled"]
InProgress = ["InReview", "Done", "Cancelled"]
InReview = ["InProgress", "Done", "Cancelled"]
""",
    )

    result = await invoke(["workflow", "lint"])

    assert result.exit_code == 0, result.output
