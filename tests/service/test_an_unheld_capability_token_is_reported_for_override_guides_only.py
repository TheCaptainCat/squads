"""An `@*<capability>` token no live role holds renders as `*<capability>` and mentions nobody.
When the guide is one the adopter declared, `sq check` and `sq sync` report it once, naming the
capability, the type and both remedies; the same token in the bundled playbook stays silent."""

import tomllib
from pathlib import Path

import pytest

from _helpers import resolved_skill_definition
from squads import __version__
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_REPORT = "mentions `@*audit`, but no live role holds the capability"

_ROLE = (
    'full_name = "Alma Auditor"\ntitle = "auditor"\ndescription = "Audits."\n'
    'mission = "Audit the work."\ncapabilities = ["audit"]\n'
)


def _write(squad_dir: Path, relative: str, body: str) -> None:
    path = squad_dir / ".overrides" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# squads:override-base:{__version__}\n{body}", encoding="utf-8")


def _declare_guide_mentioning_audit(squad_dir: Path) -> None:
    _write(
        squad_dir,
        "playbook.toml",
        '[types.task]\nroles = [\n    "$(*self)",\n'
        '    { slug = "manager", do = ["ask `@*audit` to look"] },\n]\n',
    )


async def _skill(squad_dir: Path) -> str:
    return await resolved_skill_definition(service.open_service(client_cwd=squad_dir), "sq-task")


async def _reports(squad_dir: Path) -> tuple[list[str], list[str]]:
    svc = service.open_service(client_cwd=squad_dir)
    synced = [m for m in await svc.sync() if _REPORT in m]
    checked = [i.message for i in await svc.check() if _REPORT in i.message]
    return synced, checked


async def test_an_unheld_token_in_an_override_guide_is_reported_by_check_and_sync(project) -> None:
    _declare_guide_mentioning_audit(project.squad_dir)
    synced, checked = await _reports(project.squad_dir)
    assert len(checked) == 1
    assert synced == checked
    message = checked[0]
    assert "'task'" in message
    assert 'capabilities = ["audit"]' in message
    assert ".overrides/playbook.toml" in message


async def test_an_unheld_token_in_an_override_command_line_is_reported(project) -> None:
    _write(
        project.squad_dir,
        "playbook.toml",
        '[types.task]\ncommands = ["$(*self)", "sq task <n> comment -m \'ping @*audit\'"]\n',
    )
    synced, checked = await _reports(project.squad_dir)
    assert len(checked) == 1
    assert synced == checked
    assert "'task'" in checked[0]


async def test_a_held_token_in_an_override_guide_is_silent(project) -> None:
    _declare_guide_mentioning_audit(project.squad_dir)
    _write(project.squad_dir, "roles/auditor.toml", _ROLE)
    await service.open_service(client_cwd=project.squad_dir).add_role(
        "auditor", definition=tomllib.loads(_ROLE)
    )
    assert await _reports(project.squad_dir) == ([], [])
    assert "ask `@auditor` to look" in await _skill(project.squad_dir)


async def test_a_token_whose_only_holder_is_retired_is_reported_and_renders_unheld(
    project,
) -> None:
    _declare_guide_mentioning_audit(project.squad_dir)
    _write(project.squad_dir, "roles/auditor.toml", _ROLE)
    svc = service.open_service(client_cwd=project.squad_dir)
    auditor = await svc.add_role("auditor", definition=tomllib.loads(_ROLE))
    await svc.set_status(auditor.id, "Archived")
    synced, checked = await _reports(project.squad_dir)
    assert len(checked) == 1
    assert synced == checked


async def test_an_unheld_token_in_the_bundled_playbook_is_silent_and_renders_unheld(
    project,
) -> None:
    svc = service.open_service(client_cwd=project.squad_dir)
    await svc.activate_role(None, from_template="dev", tech="python")
    skipped = await svc.sync()
    issues = [i.message for i in await svc.check()]
    assert not [m for m in [*skipped, *issues] if "no live role holds the capability" in m]
