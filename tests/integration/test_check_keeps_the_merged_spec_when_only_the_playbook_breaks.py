"""``sq check`` must not throw away a workflow spec that loaded fine just because the
playbook, a separate document, failed to load. Before this fix, the ``PlaybookConfigError``
branch rebuilt its fallback ``Service`` on the BUNDLED spec — so a squad with a custom
workflow-declared type and a playbook-only breakage got a false, unrelated "type no longer
declared" corpus error instead of the real playbook finding, and the real finding never
printed at all.
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio


def _write_workflow_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


def _write_playbook_override(squad_dir: Path, content: str) -> None:
    from squads import __version__

    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "playbook.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


_CUSTOM_INCIDENT_TYPE = (
    '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "work"\n'
)
_BROKEN_PLAYBOOK_OVERVIEW = '[types.task]\noverview = ""\n'


async def test_check_reports_the_playbook_issue_and_no_phantom_type_error(
    project, svc, invoke
) -> None:
    _write_workflow_override(project.squad_dir, _CUSTOM_INCIDENT_TYPE)
    # Sanity: the workflow spec alone is fine.
    lint = await invoke(["workflow", "lint"])
    assert "workflow spec OK" in lint.output

    create = await invoke(["create", "incident", "db outage", "--author", "manager"])
    assert create.exit_code == 0, create.output

    _write_playbook_override(project.squad_dir, _BROKEN_PLAYBOOK_OVERVIEW)

    result = await invoke(["check"])
    assert "playbook config invalid" in result.output
    assert "overview is empty" in result.output
    # The regression this pins: no phantom "type no longer declares" / migrate-or-retype
    # error, and no corpus error masking the real finding.
    assert "no longer declares" not in result.output
    assert "migrate or re-type" not in result.output
    assert result.exit_code == 3


async def test_check_json_carries_only_the_playbook_issue_not_a_phantom_type_error(
    project, svc, invoke
) -> None:
    _write_workflow_override(project.squad_dir, _CUSTOM_INCIDENT_TYPE)
    create = await invoke(["create", "incident", "db outage", "--author", "manager"])
    assert create.exit_code == 0, create.output

    _write_playbook_override(project.squad_dir, _BROKEN_PLAYBOOK_OVERVIEW)

    result = await invoke(["check", "--json"])
    import json

    issues = json.loads(result.output)
    assert any(i["item"] == "playbook" and "overview is empty" in i["message"] for i in issues)
    assert not any("no longer declares" in i["message"] for i in issues)


async def test_check_exit_code_is_the_issue_level_path_not_a_hard_crash(
    project, svc, invoke
) -> None:
    """Before the fix this died with exit 1 (an uncaught error escaping svc.check()), which a
    wrapper cannot distinguish from any other hard failure. It must be 3 — the normal
    issue-level path — same as every other reported ``sq check`` error."""
    _write_workflow_override(project.squad_dir, _CUSTOM_INCIDENT_TYPE)
    create = await invoke(["create", "incident", "db outage", "--author", "manager"])
    assert create.exit_code == 0, create.output

    _write_playbook_override(project.squad_dir, _BROKEN_PLAYBOOK_OVERVIEW)

    result = await invoke(["check"])
    assert result.exit_code == 3
