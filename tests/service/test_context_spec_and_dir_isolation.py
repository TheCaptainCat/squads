"""``RequestContext.active_spec``/``active_dir``: two logically-concurrent requests resolving
two differently-customized squads each see their own spec and dir through the CLI's ambient
accessors (``get_active_spec``/``get_service``) — neither observes the other's.
"""

from pathlib import Path

import anyio
import anyio.lowlevel
import pytest

from squads._cli._common import get_active_spec, get_service
from squads._context import RequestContext, bind_context
from squads._services import _service as service
from squads._workflow import bundled_spec
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME, load_workflow_spec
from squads._workflow._models import WorkflowSpec

pytestmark = pytest.mark.anyio

_INCIDENT_OVERRIDE = """
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


def _ensure_dir(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)


async def _init_squad(root: Path) -> Path:
    _ensure_dir(root)
    result = await service.init(root=root, roles_spec="", no_claude=True)
    return result.paths.squad_dir


def _customized_squad(squad_dir: Path) -> WorkflowSpec:
    override_path = squad_dir / WORKFLOW_OVERRIDE_FILENAME
    override_path.parent.mkdir(parents=True, exist_ok=True)
    override_path.write_text(_INCIDENT_OVERRIDE, encoding="utf-8")
    return load_workflow_spec(squad_dir=squad_dir)


async def test_two_bound_contexts_see_their_own_spec_and_dir_not_each_others(tmp_path):
    squad_dir_a = await _init_squad(tmp_path / "squad-a")
    squad_dir_b = await _init_squad(tmp_path / "squad-b")
    spec_b = _customized_squad(squad_dir_b)

    bind_context(RequestContext(active_dir=str(squad_dir_a), active_spec=bundled_spec()))
    assert get_active_spec() is bundled_spec()
    assert "incident" not in get_active_spec().items
    assert get_service().paths.squad_dir == squad_dir_a

    bind_context(RequestContext(active_dir=str(squad_dir_b), active_spec=spec_b))
    assert "incident" in get_active_spec().items
    assert get_service().paths.squad_dir == squad_dir_b

    # the customization never touched the shared bundled singleton
    assert "incident" not in bundled_spec().items


async def test_get_active_spec_falls_back_to_bundled_when_nothing_is_bound() -> None:
    bind_context(RequestContext())
    assert get_active_spec() is bundled_spec()


async def test_concurrent_contexts_do_not_observe_each_others_active_spec_or_dir(tmp_path):
    """Two sibling asyncio tasks, each a stand-in for a concurrent request against a
    differently-customized squad, must each read back only their own binding."""
    squad_dir_a = await _init_squad(tmp_path / "squad-a")
    squad_dir_b = await _init_squad(tmp_path / "squad-b")
    spec_b = _customized_squad(squad_dir_b)

    seen: dict[str, tuple[bool, Path]] = {}

    async def _run(label: str, squad_dir: Path, spec: WorkflowSpec) -> None:
        bind_context(RequestContext(active_dir=str(squad_dir), active_spec=spec))
        await anyio.lowlevel.checkpoint()  # yield so the sibling task interleaves on this thread
        seen[label] = ("incident" in get_active_spec().items, get_service().paths.squad_dir)

    async with anyio.create_task_group() as tg:
        tg.start_soon(_run, "a", squad_dir_a, bundled_spec())
        tg.start_soon(_run, "b", squad_dir_b, spec_b)

    assert seen["a"] == (False, squad_dir_a)
    assert seen["b"] == (True, squad_dir_b)
