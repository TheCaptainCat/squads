"""The bulk-import engine returns its post-commit integrity findings **with their level**.

The apply pass runs the integrity catalog over the items it touched once the transaction has
committed, and that catalog answers at two levels. Flattening them into one string list at this
boundary is unrecoverable: nothing above the engine can restore a level the engine did not
return, so the exit code, the human rendering and the JSON payload all lose it at once.

Nothing is filtered by level on the way out either. Which catalog members can reach this point
is a property of the effective spec — a type naming an error-level rule in an override reaches
it — so the engine reports what the reporter returned rather than a list of the members that
happen to reach it in a bundled squad.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._services import _service as service

pytestmark = pytest.mark.anyio

#: Renaming a sub-entity kind's container plural leaves an existing corpus carrying the old
#: container marker, which the catalog reports at error level. Stamped like any hand-written
#: override so the squad's only finding is the one these tests are about.
_RENAMED_PLURAL = (
    f'# squads:override-base:{__version__}\n[subentity_kinds.subtask]\nplural = "worksteps"\n'
)


def _renamed_container_service(squad_dir: Path) -> service.Service:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_RENAMED_PLURAL, encoding="utf-8")
    svc = service.open_service()
    assert svc.spec.subentity_plural("subtask") == "worksteps"
    return svc


def _comment_event(target: str) -> str:
    return f'{{"op":"comment","target":"{target}","message":"Imported.","as":"manager"}}\n'


async def test_an_error_level_finding_survives_the_apply_pass_with_its_level(project, svc):
    task = (await create_item(svc, "task", "Alpha task")).item
    await svc.add_subtask(task.id, "A subtask")

    renamed = _renamed_container_service(project.squad_dir)
    result = await renamed.import_events(_comment_event(task.id), default_as="manager")

    assert result.applied is not None
    levels = {(f.level, f.item) for f in result.applied.findings}
    assert ("error", task.id) in levels
    assert ("warn", task.id) in levels
    (error,) = result.applied.error_findings
    assert "worksteps" in error.message

    # The warn-level stream keeps its own lines in the wording it has always used, and does
    # not smuggle the error-level one in beside them at the same visual weight.
    assert result.applied.warnings == [
        f"{task.id}: ST1 body is unwritten (still the placeholder stub)"
    ]


async def test_a_warn_only_apply_reports_no_error_level_finding(svc):
    review = (await create_item(svc, "review", "A review")).item
    text = (
        f'{{"op":"add-finding","target":"{review.id}","title":"{"x" * 200}","severity":"high"}}\n'
    )

    result = await svc.import_events(text, default_as="manager")

    assert result.applied is not None
    assert result.applied.findings
    assert result.applied.error_findings == []
    assert {f.level for f in result.applied.findings} == {"warn"}
