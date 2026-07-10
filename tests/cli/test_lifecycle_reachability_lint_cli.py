"""``sq workflow lint`` CLI exit codes for the reachability-lint family (the algorithm itself
is proven at tests/unit/test_lifecycle_reachability_lint.py) — an off-vocab transition target
and a terminal-unreachable lifecycle both exit 1 with the offending name in the output; a
valid custom override and the bundled spec with no override both exit 0; a custom sub-entity
kind's off-vocab completion status exits 1 too.
"""

import pytest

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
terminal = false

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
terminal = false
[statuses.Mitigating]
terminal = false

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
terminal = false
[statuses.Resolved]
terminal = true

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
