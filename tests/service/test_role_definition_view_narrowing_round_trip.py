"""The whole drop -> author -> re-add -> converge round trip for a role's ``role_definition``
view: dropping the view admits an ordinary authored write, and marker-free authored prose
survives both ``sq repair`` and a version-drift backfill untouched."""

from pathlib import Path

import pytest

from squads import __version__
from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section
from squads._services import _service as service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_DROP_ROLE_DEFINITION = """\
[selected]
views = ["milestone_rollup", "squads_skill", "greeting_skill", "memory_skill", "item_skill"]
"""

_AUTHORED_PROSE = "A hand-authored role definition, written while the view was dropped."


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


def _region(path: Path) -> str:
    return (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()


#: A role activated by the ``svc`` fixture already carries its enabled ``role_definition`` tag,
#: which dropping the view does not strip, so the round trip's prose sits beside it.
_PRE_EXISTING_TAG = markers.open_marker(markers.view_tag("role_definition"))


async def _drop_author_re_add(svc) -> tuple[str, Path]:
    """Drop ``role_definition``, author plain prose while it is dropped, then re-declare the
    view. Returns the role's id and file path."""
    role = await svc.roster_item("role", "manager") or await svc.activate_role("manager")
    path = item_file(svc.paths, role)

    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)
    dropped = service.Service(svc.paths, spec=load_workflow_spec(squad_dir=svc.paths.squad_dir))
    await dropped.set_body(role.id, _AUTHORED_PROSE)
    region = _region(path)
    assert region.startswith(_AUTHORED_PROSE)
    assert region.endswith(_PRE_EXISTING_TAG)

    (svc.paths.squad_dir / ".overrides" / "workflow.toml").unlink()
    return role.id, path


async def test_the_write_is_admitted_while_the_view_is_dropped(svc) -> None:
    """A write is admitted, not refused, while the view is dropped."""
    _role_id, path = await _drop_author_re_add(svc)
    assert _region(path).startswith(_AUTHORED_PROSE)


async def test_repair_preserves_the_marker_free_prose(svc) -> None:
    """``sq repair`` must not add the tag on its own and must not touch the prose."""
    _role_id, path = await _drop_author_re_add(svc)

    before = _region(path)
    await svc.repair()

    assert _region(path) == before, "the region was rewritten"


async def test_a_version_drift_backfill_preserves_the_marker_free_prose(svc) -> None:
    """``sq sync``'s version-drift backfill also preserves the marker-free prose."""
    _role_id, path = await _drop_author_re_add(svc)
    cfg_path = svc.paths.config_path
    text = cfg_path.read_text(encoding="utf-8")
    cfg_path.write_text(
        text.replace(f'squads_version = "{__version__}"', 'squads_version = "0.1.0"'),
        encoding="utf-8",
    )

    before = _region(path)
    await service.Service(svc.paths).sync()

    assert _region(path) == before, "the region was rewritten"


async def test_adding_the_tag_again_restores_it_enabled_at_its_position(svc) -> None:
    """``view add`` re-enables the already-present tag in place, never duplicating it."""
    role_id, path = await _drop_author_re_add(svc)
    before = _region(path)

    placed = await svc.add_view(role_id, "role_definition")

    assert not placed, "the tag was already enabled; add_view reports a no-op, not a fresh place"
    region = _region(path)
    assert region.startswith(_AUTHORED_PROSE)
    assert region.endswith(markers.open_marker(markers.view_tag("role_definition")))
    assert region == before, "the tag was already present enabled; add_view must not duplicate it"


async def test_a_repeated_convergence_pass_keeps_the_prose_and_tag_stable(svc) -> None:
    """Once both prose and tag are on disk together, a further repair/sync pass is idempotent."""
    role_id, path = await _drop_author_re_add(svc)
    await svc.add_view(role_id, "role_definition")
    placed = path.read_text(encoding="utf-8")

    await svc.repair()
    await service.Service(svc.paths).sync()

    assert path.read_text(encoding="utf-8") == placed
