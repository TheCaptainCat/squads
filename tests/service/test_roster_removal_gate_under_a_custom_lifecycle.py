"""The removal gate does not depend on the lifecycle having a direct edge to a non-live status,
and a refused removal states the dependency and the step that clears it."""

from pathlib import Path

import anyio
import pytest

from squads._errors import ConfigIntegrityError
from squads._services import _service as service
from squads._services._service import Service
from squads._workflow._loader import load_workflow_spec

pytestmark = pytest.mark.anyio

# Active reaches Archived only through Standby: no live entry has a direct non-live edge.
_STANDBY_LIFECYCLE = """\
[lifecycles.agent.transitions]
Active = ["Standby"]
Standby = ["Archived", "Active"]
Archived = ["Active"]

[statuses.Standby]
role = "active"
"""


async def _squad(root: Path, monkeypatch: pytest.MonkeyPatch, *, standby: bool) -> Service:
    await anyio.Path(root).mkdir()
    monkeypatch.chdir(root)
    paths = (await service.init(root=root, roles_spec="minimal")).paths
    if not standby:
        return Service(paths)
    overrides = anyio.Path(paths.squad_dir / ".overrides")
    await overrides.mkdir()
    await (overrides / "workflow.toml").write_text(_STANDBY_LIFECYCLE)
    return Service(paths, spec=load_workflow_spec(squad_dir=paths.squad_dir))


async def _target(svc: Service, name: str) -> str:
    if name == "last-live-role":
        return (await svc.get("ROLE-000001")).id
    if name == "type-implied-skill":
        await svc.activate_role("tech-lead")
        slug = "sq-task"
    else:
        slug = "squads"
    item = await svc.roster_item("skill", slug)
    assert item is not None
    return item.id


_NAMES = ["last-live-role", "seeded-skill", "type-implied-skill"]


@pytest.mark.parametrize("purge", [True, False])
@pytest.mark.parametrize("name", _NAMES)
async def test_a_lifecycle_without_a_direct_retiring_edge_is_still_gated(
    name: str, purge: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc = await _squad(tmp_path / "squad", monkeypatch, standby=True)
    item_id = await _target(svc, name)

    with pytest.raises(ConfigIntegrityError, match=f"cannot remove {item_id}"):
        await svc.remove_item(item_id, purge=purge)


@pytest.mark.parametrize(
    ("name", "expected", "absent"),
    [
        ("seeded-skill", "permanent floor", ("not live", "live again", "reactivate")),
        ("type-implied-skill", "implied by declared type(s)", ("not live", "live again")),
        ("last-live-role", "activate another role first", ("not live", "live again")),
    ],
)
async def test_a_refused_removal_states_the_dependency_and_the_step(
    name: str,
    expected: str,
    absent: tuple[str, ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = await _squad(tmp_path / "squad", monkeypatch, standby=False)
    item_id = await _target(svc, name)

    with pytest.raises(ConfigIntegrityError) as exc:
        await svc.remove_item(item_id, purge=True)

    text = str(exc.value)
    assert text.startswith(f"cannot remove {item_id}: other entries depend on it:")
    assert expected in text
    assert not [a for a in absent if a in text]
