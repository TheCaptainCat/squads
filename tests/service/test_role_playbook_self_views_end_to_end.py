"""The ``role``/``playbook``/``self`` source kinds through the real service seams — placement
(``insert_view``), read-time tag expansion (``read_body``), and the direct question
(``render_view``) — not just the module-level resolver/predicate functions in isolation. Also
covers ``--json`` resolution for all three: each reuses the shape its own kind already has a
serializer for (``_view_json_payload``), never a shared envelope.

Also covers ``playbook``'s emptiness case end to end: a type genuinely declared in ``[items]``
but outside every guide's lane domain is a real, supported case, not a defect — placement
accepts the tag, the read expands it to the source's "no lane" value rather than raising, and
``--json`` reports ``lane: None`` rather than refusing.

Also covers the roster's laziness on a tagged body read: ``read_body`` threads a
zero-argument, memoized roster provider through expansion, so a body carrying a ``role``/
``self`` (or ``ref``/``subtree``/``subentity``) tag never forces it, and a body carrying more
than one ``playbook`` tag forces it once, not once per tag.
"""

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
    """A fresh ``Service`` bound to the just-written workflow override — ``self.spec`` is
    fixed at construction, so a view declared after ``svc`` was built needs a new instance."""
    return Service(project, spec=load_workflow_spec(squad_dir=project.squad_dir))


async def test_a_role_sourced_view_places_expands_at_read_time_and_renders(project, svc) -> None:
    _write_workflow_override(project.squad_dir, '[views.role_card]\nsource = { kind = "role" }\n')
    _place_view_template(project.squad_dir, "role_card", "Role: {{ source.slug }}\n")
    reopened = _reopen(project)
    role_item = await reopened.activate_role("tech-writer")

    assert await reopened.insert_view(role_item.id, "role_card") is True
    body = await reopened.read_body(role_item.id)
    assert "Role: tech-writer" in body
    assert "sq:view:role_card" not in body  # the tag itself is gone, replaced by its render

    rendered = await reopened.render_view("role_card", role_item.id)
    assert rendered.strip() == "Role: tech-writer"


async def test_an_orphaned_project_role_under_a_placed_tag_still_reads(project, svc) -> None:
    """A project-declared custom role — a slug with no bundled catalog entry, only its own
    ``.overrides/roles/<slug>.toml`` — resolves normally while that file is present. Deleting
    it (an ordinary edit, and a corpus state the codebase explicitly tolerates elsewhere) must
    not turn a read into a crash: the role source resolves through the same seam every other
    role reader degrades through, so the item keeps reading."""
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

    assert await reopened.insert_view(role_item.id, "role_card") is True
    body = await reopened.read_body(role_item.id)
    assert "Role: sre" in body

    override_path.unlink()

    degraded_body = await reopened.read_body(role_item.id)
    assert "Role: sre" in degraded_body  # degraded, not RoleNotFoundError out of read_body


async def test_a_role_sourced_views_json_resolution_reuses_the_role_show_json_shape(
    project, svc
) -> None:
    """No projection envelope survives for a ``role`` source's ``--json`` either — it joins
    the per-source dispatch every other kind uses, reusing ``sq role <slug> show --json``'s own
    builder rather than being refused or forced through a flattened record shape."""
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
    """Shadows the bundled ``guide`` type with an equally-shaped custom type ``doc`` that
    carries no playbook entry, and declares a ``playbook``-sourced view naming it —
    coverage is required only for bundled type names still active in the spec, so a renamed
    type owes nothing until a project writes one, and ``doc`` is genuinely declared
    (``"doc" in spec.items``) yet genuinely unlaned (``playbook.types.get("doc") is None``)."""
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

    assert await reopened.insert_view(doc_item.id, "lane_card") is True

    body = await reopened.read_body(doc_item.id)
    assert "No lane." in body
    assert "sq:view:lane_card" not in body  # the tag itself is gone, replaced by its render

    payload = await _view_json_payload(reopened, reopened.spec, "lane_card", doc_item.id)
    assert isinstance(payload, dict)
    assert payload["type"] == "doc"
    assert payload["lane"] is None  # the well-formed empty case, not a raise
    assert isinstance(payload["roster"], list) and payload["roster"]

    issues = await reopened.check()
    assert not any("lane_card" in issue.message for issue in issues)


async def test_read_body_never_computes_the_roster_for_a_self_sourced_tag(project, svc) -> None:
    _write_workflow_override(project.squad_dir, '[views.self_card]\nsource = { kind = "self" }\n')
    _place_view_template(project.squad_dir, "self_card", "{{ source.id }}\n")
    reopened = _reopen(project)
    task = (await create_item(reopened, "task", "T")).item
    assert await reopened.insert_view(task.id, "self_card") is True

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
    assert await reopened.insert_view(task.id, "lane_a") is True
    assert await reopened.insert_view(task.id, "lane_b") is True

    with patch.object(reopened, "roster_from_db", wraps=reopened.roster_from_db) as spy:
        body = await reopened.read_body(task.id)

    assert "A:task" in body
    assert "B:bug" in body
    spy.assert_called_once()
