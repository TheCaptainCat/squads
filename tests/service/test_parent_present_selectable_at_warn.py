"""``parent_present`` — the requires-a-parent check, in no ``CATEGORY_BUNDLES`` entry — is
selectable at warn once level is declarable: the cliff that kept it unbundled was its level,
not its rule. A project opts a type into it at warn without erroring on parentless items
already on disk; selected at error (bare, or explicitly), it still refuses a parentless
create/update outright. This project's own bundled spec selects it nowhere — the point is what
an adopter *can* choose, not a new bundled default.
"""

from pathlib import Path

import pytest

from _helpers import create_item
from squads import __version__
from squads._errors import SquadsError
from squads._services import _service as service
from squads._workflow import bundled_spec

pytestmark = pytest.mark.anyio


def _service_with_override(squad_dir: Path, override_body: str) -> service.Service:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{override_body}", encoding="utf-8"
    )
    return service.open_service()


def test_the_bundled_spec_selects_parent_present_nowhere() -> None:
    spec = bundled_spec()
    assert all("parent_present" not in ts.validators for ts in spec.items.values())


async def test_selecting_it_at_warn_loads_clean_over_an_existing_parentless_item(project):
    """A parentless task already on disk, created before the override existed — the spec load
    that follows must not error, and the item must not become unmutatable."""
    plain_svc = service.open_service()
    parentless = (await create_item(plain_svc, "task", "t")).item

    svc = _service_with_override(
        project.squad_dir, '[items.task]\nvalidators = ["parent_present@warn"]\n'
    )
    assert svc.spec.items["task"].validators == ["parent_present@warn"]

    # An ordinary update on the pre-existing parentless item is not refused.
    await svc.set_status(parentless.id, "Ready")
    updated = await svc.store.load()
    refreshed = updated.get(parentless.id)
    assert refreshed is not None
    assert refreshed.status == "Ready"


async def test_selecting_it_at_warn_reports_a_warning_with_exit_code_zero(project):
    svc = _service_with_override(
        project.squad_dir, '[items.task]\nvalidators = ["parent_present@warn"]\n'
    )
    task = (await create_item(svc, "task", "t")).item

    issues = await svc.check()
    matching = [i for i in issues if i.item == task.id and "requires a parent" in i.message]
    assert len(matching) == 1
    assert matching[0].level == "warn"
    # sq check's exit code is error-only — a warn-only finding does not fail the gate proper.
    assert not any(i.level == "error" for i in matching)


@pytest.mark.parametrize("entry", ["parent_present", "parent_present@error"])
async def test_selecting_it_at_error_still_refuses_a_parentless_create(project, entry):
    """Bare (no suffix) resolves to the same bundled default level as an explicit ``@error``,
    so both refuse a parentless create."""
    svc = _service_with_override(project.squad_dir, f'[items.task]\nvalidators = ["{entry}"]\n')
    with pytest.raises(SquadsError, match="requires a parent"):
        await create_item(svc, "task", "t")
