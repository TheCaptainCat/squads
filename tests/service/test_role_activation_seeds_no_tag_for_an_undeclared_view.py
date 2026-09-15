"""``ServiceCore._create_core``'s role branch, gated on ``self.spec.views`` the same way
``MaintenanceMixin._repair_body_tag``'s classifier already gates the repair sweep.

The repair-time gate stops a dangling tag from being *re-seeded* onto an already-empty body,
but the creation path is a second, independent writer: the bundled creation scaffold
(``agents/role.md.j2``) carries the ``sq:view:role_definition`` tag as static text, and
``_create_core`` used to overwrite the rendered body with that same tag unconditionally,
regardless of whether the active spec still declares the view. Every activation under a
dropped view therefore minted a fresh dangling tag — the harm the repair-time gate stops from
being *produced* is still being produced by this second writer, on a corpus the repair gate
never touches (a role that does not exist yet).

The fix makes the creation path agree with the repair path: under a declared view the body is
seeded with the tag exactly as before (the template's own static content, reasserted); under a
dropped view the body is overwritten with nothing, matching the empty, untagged state
``_repair_body_tag`` already treats as the accepted quiet state for a dropped view.
"""

from pathlib import Path

import pytest

from squads._models import _markers as markers
from squads._sections import get_section
from squads._services import _service as service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

#: Drops `role_definition` from the declared view set. Every other bundled view stays selected
#: (including the freestanding `milestone_rollup`, which no bundled type attaches, so nothing
#: about dropping a different view could ever orphan it).
_DROP_ROLE_DEFINITION = """\
[selected]
views = ["milestone_rollup", "squads_skill", "greeting_skill", "memory_skill", "item_skill"]
"""


def _write_override(squad_dir: Path, content: str) -> None:
    from squads import __version__

    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


def _role_body(svc, item) -> str:
    from squads._index._resolver import item_file

    path = item_file(svc.paths, item)
    return (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()


@pytest.mark.gate_for("squads/_services/_base.py::_create_core")
async def test_activating_a_role_under_a_dropped_view_leaves_the_body_empty(svc) -> None:
    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    declared = service.Service(svc.paths, spec=spec)

    role = await declared.activate_role("reviewer")

    assert _role_body(declared, role) == "", (
        "the creation path seeded a tag naming a view the spec no longer declares"
    )


async def test_activating_a_role_under_a_declared_view_still_seeds_the_tag(svc) -> None:
    """Regression control: the untouched path — no override at all — must still seed the tag
    exactly as before. Proves the gate only *subtracts* behaviour under a dropped view rather
    than changing anything for the ordinary case."""
    role = await svc.activate_role("reviewer")

    assert _role_body(svc, role) == markers.open_marker(markers.view_tag("role_definition"))


async def test_repeated_activation_under_a_dropped_view_adds_no_check_findings(svc) -> None:
    """The reviewer's own repro, driven at the service layer: a role activated under a dropped
    view must not add a fresh `sq check` finding, and activating a second role must not add a
    second one — the count stays flat, not growing by one per activation."""
    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    declared = service.Service(svc.paths, spec=spec)

    before = await declared.check()
    dangling_before = [i for i in before if "role_definition" in i.message]

    await declared.activate_role("reviewer")
    after_one = await declared.check()
    dangling_after_one = [i for i in after_one if "role_definition" in i.message]
    assert len(dangling_after_one) == len(dangling_before)

    await declared.activate_role("qa")
    after_two = await declared.check()
    dangling_after_two = [i for i in after_two if "role_definition" in i.message]
    assert len(dangling_after_two) == len(dangling_before)
