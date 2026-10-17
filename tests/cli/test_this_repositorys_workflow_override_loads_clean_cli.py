"""A squad carrying this repository's workflow override lints clean, lists the override as
current, and passes `sq check` -- and a fresh squad carries no such override and selects
neither catalog-only check. Bare exit codes throughout.
"""

from pathlib import Path

import pytest

from squads._services import _service as service
from squads._workflow._models import effective_validator_names, parse_validator_entry

pytestmark = pytest.mark.anyio

REPO_OVERRIDE = Path(__file__).resolve().parents[2] / "squads" / ".overrides" / "workflow.toml"


def _install_repo_override(squad_dir: Path) -> None:
    (squad_dir / ".overrides").mkdir(exist_ok=True)
    (squad_dir / ".overrides" / "workflow.toml").write_text(
        REPO_OVERRIDE.read_text(encoding="utf-8"), encoding="utf-8"
    )


async def test_workflow_lint_exits_0_with_no_error_or_warning(project, invoke) -> None:
    _install_repo_override(project.squad_dir)
    result = await invoke(["workflow", "lint"])
    assert result.exit_code == 0, result.output
    assert "no errors or warnings" in result.output.lower()


async def test_override_list_shows_workflow_as_current(project, invoke) -> None:
    _install_repo_override(project.squad_dir)
    result = await invoke(["override", "list"])
    assert result.exit_code == 0, result.output
    workflow_line = next(ln for ln in result.output.splitlines() if "workflow" in ln)
    assert "current" in workflow_line


async def test_check_exits_0_on_a_squad_carrying_the_override(project, invoke) -> None:
    _install_repo_override(project.squad_dir)
    result = await invoke(["check"])
    assert result.exit_code == 0, result.output


async def test_a_fresh_squad_has_no_workflow_override_and_selects_neither_check(project) -> None:
    assert not (project.squad_dir / ".overrides" / "workflow.toml").exists()
    spec = service.open_service().spec
    assert len(spec.items) == 12
    for item_type, ts in spec.items.items():
        effective = {
            parse_validator_entry(n)[0]
            for n in effective_validator_names(ts.category, extra=tuple(ts.validators))
        }
        assert not effective & {"no_status_banner", "subentity_title_max"}, item_type
        assert spec.item_subentity_title_max(item_type) is None
