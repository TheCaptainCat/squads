"""``sq check`` must name the override kind that actually failed to load: a broken
``.overrides/workflow.toml`` reports "workflow config invalid" and points at
``sq workflow lint`` (which reads that file); a broken ``.overrides/playbook.toml`` reports
"playbook config invalid" with the loader's own violation and the file path — never the
workflow message, and never a pointer to ``sq workflow lint``, which does not read
``.overrides/playbook.toml`` at all and would report the workflow spec clean while leaving the
real problem unreported.

``open_service`` is the ground truth both directions rest on: it raises
:class:`~squads._errors.PlaybookConfigError` (a distinct ``SquadsError`` subclass) for a
playbook failure and a plain ``SquadsError`` for a workflow-spec failure — ``sq check`` catches
the more specific subclass first.
"""

from pathlib import Path

import pytest

from squads._errors import PlaybookConfigError, SquadsError
from squads._services._service import open_service, resolve_playbook
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio


def _write_playbook_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "playbook.toml").write_text(content, encoding="utf-8")


def _write_workflow_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


_BROKEN_PLAYBOOK = '[types.task]\nroles = [{ slug = "no-such-role" }]\n'
_BROKEN_WORKFLOW = '[bogus_section.task]\nprefix = "X"\n'


# --------------------------------------------------------------------------- resolve_playbook:
# the one place the distinct exception type is raised


def test_resolve_playbook_raises_playbook_config_error_not_a_plain_squads_error(
    tmp_path: Path,
) -> None:
    _write_playbook_override(tmp_path, _BROKEN_PLAYBOOK)
    with pytest.raises(PlaybookConfigError) as exc_info:
        resolve_playbook(bundled_spec(), tmp_path)
    message = str(exc_info.value)
    assert "role slug 'no-such-role' not in role catalog" in message
    assert str(tmp_path / ".overrides" / "playbook.toml") in message  # names *where*
    assert "sq workflow lint" not in message  # never a non-diagnosing pointer
    assert "sq override diff playbook" not in message  # diff doesn't validate; not invented


def test_playbook_config_error_is_a_squads_error_subclass_so_broad_catches_still_work(
    tmp_path: Path,
) -> None:
    _write_playbook_override(tmp_path, _BROKEN_PLAYBOOK)
    with pytest.raises(SquadsError):
        resolve_playbook(bundled_spec(), tmp_path)


# --------------------------------------------------------------------------- open_service: both
# call sites (the no-workflow-override fast path, and the merged path) raise it


async def test_open_service_raises_playbook_config_error_with_no_workflow_override_at_all(
    project,
) -> None:
    """The fast path (``.overrides/workflow.toml`` absent) still resolves the playbook
    unconditionally — a broken ``.overrides/playbook.toml`` alone, with no workflow override
    anywhere, must still raise the distinct exception, not a plain ``SquadsError``."""
    _write_playbook_override(project.squad_dir, _BROKEN_PLAYBOOK)
    with pytest.raises(PlaybookConfigError):
        open_service(dir_override=str(project.squad_dir))


async def test_open_service_raises_playbook_config_error_alongside_a_valid_workflow_override(
    project,
) -> None:
    _write_workflow_override(
        project.squad_dir,
        '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "work"\n',
    )
    _write_playbook_override(project.squad_dir, _BROKEN_PLAYBOOK)
    with pytest.raises(PlaybookConfigError):
        open_service(dir_override=str(project.squad_dir))


async def test_open_service_never_raises_playbook_config_error_for_a_broken_workflow_override(
    project,
) -> None:
    _write_workflow_override(project.squad_dir, _BROKEN_WORKFLOW)
    with pytest.raises(SquadsError) as exc_info:
        open_service(dir_override=str(project.squad_dir))
    assert not isinstance(exc_info.value, PlaybookConfigError)
    assert "sq workflow lint" in str(exc_info.value)


# --------------------------------------------------------------------------- sq check: message
# and suggested command match the override kind that actually failed


async def test_check_reports_workflow_config_invalid_for_a_broken_workflow_override(
    project, svc, invoke
) -> None:
    _write_workflow_override(project.squad_dir, _BROKEN_WORKFLOW)
    result = await invoke(["check"])
    assert "workflow config invalid" in result.output
    assert "sq workflow lint" in result.output
    assert "playbook config invalid" not in result.output
    assert result.exit_code == 3


async def test_check_reports_playbook_config_invalid_for_a_broken_playbook_override(
    project, svc, invoke
) -> None:
    _write_playbook_override(project.squad_dir, _BROKEN_PLAYBOOK)
    result = await invoke(["check"])
    assert "playbook config invalid" in result.output
    assert "role slug" in result.output and "no-such-role" in result.output
    assert "workflow config invalid" not in result.output
    # No non-diagnosing pointer: nothing lints a playbook override today.
    assert "sq workflow lint" not in result.output
    assert result.exit_code == 3


async def test_workflow_lint_reports_clean_when_only_the_playbook_override_is_broken(
    project, svc, invoke
) -> None:
    """The other half of the misattribution this fix closes: with only the playbook broken,
    ``sq workflow lint`` — which never reads ``.overrides/playbook.toml`` — correctly reports
    the workflow spec itself is fine. It is ``sq check`` that must not send the adopter here."""
    _write_playbook_override(project.squad_dir, _BROKEN_PLAYBOOK)
    result = await invoke(["workflow", "lint"])
    assert "workflow spec OK" in result.output
    assert result.exit_code == 0


async def test_check_json_carries_the_playbook_item_label_not_workflow(
    project, svc, invoke
) -> None:
    _write_playbook_override(project.squad_dir, _BROKEN_PLAYBOOK)
    result = await invoke(["check", "--json"])
    import json

    issues = json.loads(result.output)
    playbook_issues = [i for i in issues if i["item"] == "playbook"]
    assert len(playbook_issues) == 1
    assert "playbook config invalid" in playbook_issues[0]["message"]
    assert not any(i["item"] == "workflow" for i in issues)
