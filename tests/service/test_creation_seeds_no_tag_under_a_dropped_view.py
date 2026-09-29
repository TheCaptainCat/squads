"""A view dropped from ``[selected]`` seeds nothing anywhere, creation included: a bundled
scaffold's hardcoded tag is stripped before the placement routine ever sees it, table-driven
over host kind (role, milestone) x creation verb x whether the view is declared or dropped."""

from pathlib import Path

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import get_section
from squads._services import _service as service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

#: Drops `role_definition` — every other bundled view stays selected.
_DROP_ROLE_DEFINITION = """\
[selected]
views = ["milestone_rollup", "squads_skill", "greeting_skill", "memory_skill", "item_skill"]
"""

#: Drops `milestone_rollup` — every other bundled view stays selected.
_DROP_MILESTONE_ROLLUP = """\
[selected]
views = ["role_definition", "squads_skill", "greeting_skill", "memory_skill", "item_skill"]
"""


def _write_override(squad_dir: Path, content: str) -> None:
    from squads import __version__

    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


def _body(svc, item) -> str:
    path = item_file(svc.paths, item)
    return (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()


def _declared(svc, content: str) -> service.Service:
    _write_override(svc.paths.squad_dir, content)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    return service.Service(svc.paths, spec=spec)


# --------------------------------------------------------------------------------------- role


async def test_activating_a_role_under_a_dropped_view_seeds_no_tag(svc) -> None:
    declared = _declared(svc, _DROP_ROLE_DEFINITION)

    role = await declared.activate_role("reviewer")

    assert _body(declared, role) == "", (
        "a view dropped from [selected] seeds nothing anywhere, creation included"
    )
    role_filename = Path(role.path).name
    issues = await declared.check()
    assert not any("role_definition" in i.message and i.item == role_filename for i in issues), [
        i.message for i in issues
    ]


async def test_activating_a_role_under_a_declared_view_still_seeds_the_tag(svc) -> None:
    """The untouched path, with no override at all, still seeds the tag as before."""
    role = await svc.activate_role("reviewer")

    assert _body(svc, role) == markers.open_marker(markers.view_tag("role_definition"))


async def test_importing_a_role_under_a_dropped_view_seeds_no_tag(svc) -> None:
    """The bulk importer's ``create`` op, a separate call site, also seeds no tag for a
    dropped view."""
    import json

    declared = _declared(svc, _DROP_ROLE_DEFINITION)
    event = json.dumps({"op": "create", "as": "manager", "type": "role", "title": "Imported Role"})

    result = await declared.import_events(event, default_as="manager")

    assert not result.plan.issues, result.plan.issues
    roles = await declared.list_items(item_type="role")
    (role,) = [r for r in roles if r.title == "Imported Role"]
    assert _body(declared, role) == ""
    role_filename = Path(role.path).name
    issues = await declared.check()
    assert not any("role_definition" in i.message and i.item == role_filename for i in issues), [
        i.message for i in issues
    ]


# ---------------------------------------------------------------------------------- milestone


async def test_creating_a_milestone_under_a_dropped_view_seeds_no_tag(svc) -> None:
    declared = _declared(svc, _DROP_MILESTONE_ROLLUP)

    result = await declared.create("milestone", "M", author="manager")

    body = _body(declared, result.item)
    assert "sq:view:milestone_rollup" not in body, body
    assert await declared.read_body(result.item.id) == body.strip(), (
        "no literal tag left for a reader to see either"
    )
    issues = await declared.check()
    assert not any("milestone_rollup" in i.message for i in issues), [i.message for i in issues]


async def test_creating_a_milestone_under_a_declared_view_still_seeds_the_tag(svc) -> None:
    """The untouched path must still seed the tag exactly as before."""
    result = await svc.create("milestone", "M", author="manager")

    assert markers.open_marker(markers.view_tag("milestone_rollup")) in _body(svc, result.item)


async def test_importing_a_milestone_under_a_dropped_view_seeds_no_tag(svc) -> None:
    import json

    declared = _declared(svc, _DROP_MILESTONE_ROLLUP)
    event = json.dumps(
        {"op": "create", "as": "manager", "type": "milestone", "title": "Imported Milestone"}
    )

    result = await declared.import_events(event, default_as="manager")

    assert not result.plan.issues, result.plan.issues
    milestones = await declared.list_items(item_type="milestone")
    assert len(milestones) == 1
    body = _body(declared, milestones[0])
    assert "sq:view:milestone_rollup" not in body, body
