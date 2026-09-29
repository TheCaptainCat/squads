"""The ``role``/``playbook``/``self`` source kinds through the real service seams: placement,
read-time expansion, direct render, and ``--json`` resolution, including a declared-but-unlaned
type's empty case and the roster's lazy, once-per-read computation on a tagged body."""

from pathlib import Path
from typing import cast
from unittest.mock import patch

import pytest

from _helpers import create_item
from squads import __version__
from squads._cli._workflow_cmd import _view_json_payload
from squads._rendering._engine import invalidate_squad_dir
from squads._services._service import Service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio


def _write_workflow_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


def _place_view_template(squad_dir: Path, name: str, content: str) -> None:
    target = squad_dir / ".overrides" / "templates" / "views" / f"{name}.md.j2"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


def _reopen(project) -> Service:
    """A fresh ``Service`` bound to the just-written workflow override."""
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


async def test_a_role_sourced_view_places_expands_at_read_time_and_renders(project, svc) -> None:
    _write_workflow_override(project.squad_dir, '[views.role_card]\nsource = { kind = "role" }\n')
    _place_view_template(project.squad_dir, "role_card", "Role: {{ source.slug }}\n")
    reopened = _reopen(project)
    role_item = await reopened.activate_role("tech-writer")

    assert await reopened.add_view(role_item.id, "role_card") is True
    body = await reopened.read_body(role_item.id)
    assert "Role: tech-writer" in body
    assert "sq:view:role_card" not in body

    rendered = await reopened.render_view("role_card", role_item.id)
    assert rendered.strip() == "Role: tech-writer"


async def test_an_orphaned_project_role_under_a_placed_tag_still_reads(project, svc) -> None:
    """Deleting a project-declared role's own override file degrades the read, not a crash."""
    override_dir = project.squad_dir / ".overrides" / "roles"
    override_dir.mkdir(parents=True, exist_ok=True)
    override_path = override_dir / "sre.toml"
    override_path.write_text(
        f"# squads:override-base:{__version__}\n"
        'full_name = "Sam Reliability"\n'
        'title = "site reliability engineer"\n'
        'description = "Keeps production reliable."\n'
        'mission = "Keep production reliable."\n',
        encoding="utf-8",
    )
    _write_workflow_override(project.squad_dir, '[views.role_card]\nsource = { kind = "role" }\n')
    _place_view_template(project.squad_dir, "role_card", "Role: {{ source.slug }}\n")
    reopened = _reopen(project)
    role_item = await reopened.activate_role("sre")

    assert await reopened.add_view(role_item.id, "role_card") is True
    body = await reopened.read_body(role_item.id)
    assert "Role: sre" in body

    override_path.unlink()

    degraded_body = await reopened.read_body(role_item.id)
    assert "Role: sre" in degraded_body


async def test_a_role_sourced_views_json_resolution_reuses_the_role_show_json_shape(
    project, svc
) -> None:
    """A role-sourced view's ``--json`` reuses ``sq role <slug> show --json``'s own builder."""
    _write_workflow_override(project.squad_dir, '[views.role_card]\nsource = { kind = "role" }\n')
    _place_view_template(project.squad_dir, "role_card", "Role: {{ source.slug }}\n")
    reopened = _reopen(project)
    role_item = await reopened.activate_role("tech-writer")

    payload = cast(
        "dict[str, object]",
        await _view_json_payload(reopened, reopened.spec, "role_card", role_item.id),
    )
    assert payload["slug"] == "tech-writer"


async def test_a_playbook_sourced_view_with_no_name_resolves_the_hosts_own_type(
    project, svc
) -> None:
    _write_workflow_override(
        project.squad_dir, '[views.lane_card]\nsource = { kind = "playbook" }\n'
    )
    _place_view_template(project.squad_dir, "lane_card", "Type: {{ source.item_type }}\n")
    reopened = _reopen(project)
    task = (await create_item(reopened, "task", "T")).item

    rendered = await reopened.render_view("lane_card", task.id)

    assert rendered.strip() == "Type: task"


async def test_a_self_sourced_view_renders_the_host_and_carries_squad_dir(project, svc) -> None:
    _write_workflow_override(project.squad_dir, '[views.self_card]\nsource = { kind = "self" }\n')
    _place_view_template(project.squad_dir, "self_card", "{{ source.id }} at {{ squad_dir }}\n")
    reopened = _reopen(project)
    task = (await create_item(reopened, "task", "T")).item

    rendered = await reopened.render_view("self_card", task.id)

    assert rendered.strip() == f"{task.id} at {project.config.squad_dir}"


def _write_unlaned_type_and_view_override(squad_dir: Path, view_name: str) -> None:
    """Shadow the bundled ``guide`` type with a custom type ``doc`` that carries no playbook
    entry, and declare a ``playbook``-sourced view naming it."""
    bundled = load_workflow_spec()
    kept = sorted([t for t in bundled.items if t != "guide"] + ["doc"])
    _write_workflow_override(
        squad_dir,
        f"[selected]\nitems = {kept!r}\n\n"
        "[items.doc]\n"
        'prefix = "$(items.guide.prefix)"\n'
        'folder = "$(items.guide.folder)"\n'
        'lifecycle = "$(items.guide.lifecycle)"\n\n'
        f'[views.{view_name}]\nsource = {{ kind = "playbook", name = "doc" }}\n',
    )


async def test_a_playbook_sourced_view_on_a_declared_but_unlaned_type_resolves_empty(
    project, svc
) -> None:
    _write_unlaned_type_and_view_override(project.squad_dir, "lane_card")
    _place_view_template(
        project.squad_dir,
        "lane_card",
        "{% if source.lane %}{{ source.lane.overview }}{% else %}No lane.{% endif %}\n",
    )
    reopened = _reopen(project)
    doc_item = (await create_item(reopened, "doc", "D")).item

    assert await reopened.add_view(doc_item.id, "lane_card") is True

    body = await reopened.read_body(doc_item.id)
    assert "No lane." in body
    assert "sq:view:lane_card" not in body

    payload = await _view_json_payload(reopened, reopened.spec, "lane_card", doc_item.id)
    assert isinstance(payload, dict)
    assert payload["type"] == "doc"
    assert payload["lane"] is None
    assert isinstance(payload["roster"], list) and payload["roster"]

    issues = await reopened.check()
    assert not any("lane_card" in issue.message for issue in issues)


async def test_read_body_never_computes_the_roster_for_a_self_sourced_tag(project, svc) -> None:
    _write_workflow_override(project.squad_dir, '[views.self_card]\nsource = { kind = "self" }\n')
    _place_view_template(project.squad_dir, "self_card", "{{ source.id }}\n")
    reopened = _reopen(project)
    task = (await create_item(reopened, "task", "T")).item
    assert await reopened.add_view(task.id, "self_card") is True

    with patch.object(reopened, "roster_from_db", wraps=reopened.roster_from_db) as spy:
        body = await reopened.read_body(task.id)

    assert task.id in body
    spy.assert_not_called()


async def test_read_body_computes_the_roster_once_for_two_playbook_tags(project, svc) -> None:
    _write_workflow_override(
        project.squad_dir,
        '[views.lane_a]\nsource = { kind = "playbook", name = "task" }\n\n'
        '[views.lane_b]\nsource = { kind = "playbook", name = "bug" }\n',
    )
    _place_view_template(project.squad_dir, "lane_a", "A:{{ source.item_type }}\n")
    _place_view_template(project.squad_dir, "lane_b", "B:{{ source.item_type }}\n")
    reopened = _reopen(project)
    task = (await create_item(reopened, "task", "T")).item
    assert await reopened.add_view(task.id, "lane_a") is True
    assert await reopened.add_view(task.id, "lane_b") is True

    with patch.object(reopened, "roster_from_db", wraps=reopened.roster_from_db) as spy:
        body = await reopened.read_body(task.id)

    assert "A:task" in body
    assert "B:bug" in body
    spy.assert_called_once()
