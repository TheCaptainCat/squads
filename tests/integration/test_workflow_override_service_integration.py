"""``open_service`` threads a squad's (possibly overridden) spec into the ``Service`` it
returns: it picks up a valid override, fails closed with a lint pointer on a structurally
invalid one, and — the AC5 guarantee — fails closed when an override drops a status/type still
referenced by a *live* item, rather than silently orphaning that item's data. With no override
at all it uses the pre-validated bundled singleton (no re-parse). ``sq check`` surfaces the same
class of problem instead of crashing.
"""

from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._index._store import IndexStore
from squads._services import _service as service
from squads._workflow import bundled_spec, load_workflow_spec
from squads._workflow._loader import validate_against_index

pytestmark = pytest.mark.anyio

_INCIDENT_V1 = """
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
"""

# v2 redeclares the SAME custom type with a lifecycle that no longer mentions "Triage" at all —
# structurally valid on its own, but a live incident item is still sitting at status "Triage".
_INCIDENT_V2_DROPS_TRIAGE = """
[statuses.Triage2]
terminal = false
[statuses.Resolved]
terminal = true

[lifecycles.incident_lc]
initial = "Triage2"
[lifecycles.incident_lc.transitions]
Triage2 = ["Resolved"]
Resolved = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "incident_lc"
"""


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


# --------------------------------------------------------------------------- open_service basics


async def test_open_service_picks_up_a_valid_override(project) -> None:
    _write_override(project.squad_dir, _INCIDENT_V1)
    svc = service.open_service()
    assert "incident" in svc.spec.items


async def test_open_service_raises_with_a_lint_pointer_on_a_structurally_invalid_override(
    project,
) -> None:
    _write_override(
        project.squad_dir,
        '[items.broken]\nprefix = "BRK"\nfolder = "brokens"\nlifecycle = "nonexistent_lifecycle"\n',
    )
    with pytest.raises(SquadsError, match="sq workflow lint"):
        service.open_service()


async def test_open_service_with_no_override_uses_the_bundled_singleton_fast_path(project) -> None:
    """No override → svc.spec IS the cached bundled singleton, not a freshly re-parsed copy."""
    svc = service.open_service()
    assert svc.spec is bundled_spec()


# --------------------------------------------------------------------------- AC5: fail closed
# when a live item's status/type would be orphaned by the (possibly-overridden) spec


async def test_validate_against_index_flags_a_live_items_status_dropped_from_the_spec(
    project, svc
) -> None:
    result = await svc.create("task", "Test task", author="manager")
    task_id = result.item.id

    bundled = load_workflow_spec()
    statuses_no_draft = {k: v for k, v in bundled.statuses.items() if k != "Draft"}
    mock_spec = type("_MockSpec", (), {"items": bundled.items, "statuses": statuses_no_draft})()

    store = IndexStore(project.index_path, project.lock_path)
    async with store.transaction() as db:
        errors = validate_against_index(mock_spec, db)  # type: ignore[arg-type]

    assert any("Draft" in e and task_id in e for e in errors)


async def test_validate_against_index_flags_a_live_items_type_dropped_from_the_spec(
    project, svc
) -> None:
    result = await svc.create("bug", "Test bug", author="manager")

    bundled = load_workflow_spec()
    items_without_bug = {k: v for k, v in bundled.items.items() if k != "bug"}
    mock_spec = type("_MockSpec", (), {"items": items_without_bug, "statuses": bundled.statuses})()

    store = IndexStore(project.index_path, project.lock_path)
    async with store.transaction() as db:
        errors = validate_against_index(mock_spec, db)  # type: ignore[arg-type]

    assert any("bug" in e for e in errors)
    assert any(result.item.id in e for e in errors)


async def test_validate_against_index_flags_a_subentitys_status_dropped_from_the_spec(
    project, svc
) -> None:
    result = await svc.create("task", "Task with subtask", author="manager")
    await svc.add_subtask(result.item.id, "My subtask")

    bundled = load_workflow_spec()
    statuses_no_todo = {k: v for k, v in bundled.statuses.items() if k != "Todo"}
    mock_spec = type("_MockSpec", (), {"items": bundled.items, "statuses": statuses_no_todo})()

    store = IndexStore(project.index_path, project.lock_path)
    async with store.transaction() as db:
        errors = validate_against_index(mock_spec, db)  # type: ignore[arg-type]

    assert any("Todo" in e and result.item.id in e for e in errors)


async def test_open_service_fails_closed_end_to_end_when_a_new_override_orphans_a_live_status(
    project,
) -> None:
    """The full AC5 path through ``open_service`` itself (not just the lower-level cross-check
    function): a squad with a live custom-type item at a custom status, then an override
    revision that drops that exact status — reopening the service must refuse, naming the
    offending item and the dropped status, and pointing at ``sq workflow lint``."""
    _write_override(project.squad_dir, _INCIDENT_V1)
    svc = service.open_service()
    result = await svc.create("incident", "Live incident", author="manager")
    assert result.item.status == "Triage"

    _write_override(project.squad_dir, _INCIDENT_V2_DROPS_TRIAGE)
    with pytest.raises(SquadsError) as exc_info:
        service.open_service()
    message = str(exc_info.value)
    assert "Triage" in message
    assert result.item.id in message
    assert "sq workflow lint" in message


# --------------------------------------------------------------------------- sq check surfaces
# (not crashes on) a workflow-spec problem


async def test_check_reports_no_workflow_issue_when_the_spec_is_valid(project, svc, invoke) -> None:
    result = await invoke(["check"])
    assert "workflow config invalid" not in result.output


async def test_check_surfaces_a_one_line_workflow_warning_for_an_invalid_spec(
    project, svc, invoke
) -> None:
    _write_override(
        project.squad_dir,
        '[items.check_broken]\nprefix = "CHK"\nfolder = "check_brokens"\n'
        'lifecycle = "no_such_lifecycle_check"\n',
    )
    result = await invoke(["check"])
    assert "workflow config invalid" in result.output
    assert "sq workflow lint" in result.output
    assert result.exit_code in (1, 3)


# --------------------------------------------------------------------------- lint is not
# self-blocked by the same AC5 check open_service enforces


async def test_lint_reports_but_does_not_crash_even_after_open_service_would_hard_stop(
    project,
) -> None:
    from squads._workflow._loader import lint_workflow_spec

    _write_override(project.squad_dir, _INCIDENT_V1)
    svc = service.open_service()
    await svc.create("incident", "Live incident", author="manager")

    _write_override(project.squad_dir, _INCIDENT_V2_DROPS_TRIAGE)
    # open_service now hard-stops (proven above); lint must still run and report cleanly.
    findings = lint_workflow_spec(project.squad_dir)
    errors = [f for f in findings if f[0] == "error"]
    assert errors
    assert any("Triage" in f[2] for f in errors)
