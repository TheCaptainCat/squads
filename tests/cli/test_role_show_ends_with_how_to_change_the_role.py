"""`sq role <slug> show` ends with how to change the role, in text output only."""

import json

import pytest

from squads import __version__
from squads._rendering._engine import invalidate_squad_dir

pytestmark = pytest.mark.anyio


def _scaffold_line(slug: str) -> str:
    return (
        "To change its mission, responsibilities or model: "
        f"`sq override scaffold --role {slug}`, edit the file, then `sq sync`."
    )


_OWN_FILE_LINE = "To change it: edit `.overrides/roles/auditor.toml`, then `sq sync`."


async def test_an_activated_bundled_role_ends_with_the_scaffold_line(svc, invoke) -> None:
    await svc.activate_role("reviewer")
    result = await invoke(["role", "reviewer", "show"])
    assert result.exit_code == 0, result.output
    assert result.output.rstrip().splitlines()[-1] == _scaffold_line("reviewer")


async def test_a_bundled_role_that_is_not_activated_ends_with_the_scaffold_line(
    project, invoke
) -> None:
    result = await invoke(["role", "reviewer", "show"])
    assert result.exit_code == 0, result.output
    assert result.output.rstrip().splitlines()[-1] == _scaffold_line("reviewer")


async def test_a_templated_developer_ends_with_the_scaffold_line(svc, invoke) -> None:
    await svc.add_dev("python")
    result = await invoke(["role", "python-dev", "show"])
    assert result.exit_code == 0, result.output
    assert result.output.rstrip().splitlines()[-1] == _scaffold_line("python-dev")


async def test_a_project_defined_role_points_at_its_own_override_file(project, svc, invoke) -> None:
    roles_dir = project.squad_dir / ".overrides" / "roles"
    roles_dir.mkdir(parents=True, exist_ok=True)
    (roles_dir / "auditor.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        'full_name = "Alma Auditor"\ntitle = "auditor"\n'
        'description = "Audits."\nmission = "Audit the work."\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(project.squad_dir)
    await svc.activate_role("auditor")
    result = await invoke(["role", "auditor", "show"])
    assert result.exit_code == 0, result.output
    assert result.output.rstrip().splitlines()[-1] == _OWN_FILE_LINE


async def test_json_output_carries_no_change_hint(svc, invoke) -> None:
    await svc.activate_role("reviewer")
    result = await invoke(["role", "reviewer", "show", "--json"])
    assert result.exit_code == 0, result.output
    assert "sq override scaffold" not in result.output
    assert json.loads(result.output)["slug"] == "reviewer"
