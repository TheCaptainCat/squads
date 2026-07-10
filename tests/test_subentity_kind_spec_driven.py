"""Service-level proof that sub-entity kind<->type<->container maps are active-spec-driven
(ADR-348 §5, TASK-351): a project-declared type hosting a project-declared kind resolves with
no code change, and the bundled maps stay untouched for a service on the default spec.
"""

import pytest

from squads._rendering._engine import invalidate_squad_dir
from squads._services import _service as service
from squads._workflow import bundled_spec
from squads._workflow._models import ItemSpec, SubentityKindSpec

pytestmark = pytest.mark.anyio


def _spec_with_custom_kind():
    base = bundled_spec()
    new_items = {
        **base.items,
        "gadget": ItemSpec(
            prefix="GDG", folder="gadgets", lifecycle="work", subentity_kind="ticket"
        ),
    }
    new_kinds = {
        **base.subentity_kinds,
        "ticket": SubentityKindSpec(
            lifecycle="subentity", completion="Done", plural="tickets", local_prefix="TK"
        ),
    }
    new_prefix_to_type = {**base.prefix_to_type, "GDG": "gadget"}
    return base.model_copy(
        update={
            "items": new_items,
            "subentity_kinds": new_kinds,
            "prefix_to_type": new_prefix_to_type,
        }
    )


async def test_custom_subentity_kind_resolves_from_active_spec(project) -> None:
    """A project-declared type ('gadget') hosting a project-declared kind ('ticket') resolves
    parent<->kind and the container marker from the active spec."""
    svc = service.Service(project, spec=_spec_with_custom_kind())

    assert svc.subentity_parent["ticket"] == "gadget"
    assert svc.subentity_kind["gadget"] == "ticket"
    assert svc.subentity_container["ticket"] == "tickets"


async def test_bundled_maps_are_unaffected_by_another_services_custom_spec(project) -> None:
    """A service opened on the plain bundled spec never sees a kind declared only by another
    service's (project-)overridden spec — the maps are per-service, not a shared global."""
    svc = service.Service(project)

    assert "ticket" not in svc.subentity_parent
    assert "gadget" not in svc.subentity_kind
    assert svc.subentity_parent == {"story": "feature", "subtask": "task", "finding": "review"}


def _spec_with_shared_kind():
    """A second type ('ticket') declaring the SAME subentity_kind as the built-in `task`
    ('subtask') — the two-types-share-a-kind scenario."""
    base = bundled_spec()
    new_items = {
        **base.items,
        "ticket": ItemSpec(
            prefix="TICKET", folder="tickets", lifecycle="work", subentity_kind="subtask"
        ),
    }
    new_prefix_to_type = {**base.prefix_to_type, "TICKET": "ticket"}
    return base.model_copy(update={"items": new_items, "prefix_to_type": new_prefix_to_type})


def _write_ticket_template(squad_dir) -> None:
    """A `ticket` item needs its own template carrying the `subtasks` container marker —
    same requirement any project declaring a subtask-hosting type would face."""
    templates_dir = squad_dir / ".overrides" / "templates" / "items"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "ticket.md.j2").write_text(
        "<!-- sq:body -->\n_TODO_\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n",
        encoding="utf-8",
    )
    # the `project` fixture's init() already cached a bundled-only environment for this
    # squad dir before the override file existed; evict it so the new template is seen.
    invalidate_squad_dir(squad_dir)


async def test_two_types_sharing_a_kind_both_resolve_their_own_items(project) -> None:
    """add-subtask on a `task` item and on a `ticket` item both resolve correctly when the
    two types share subentity_kind="subtask" — neither is misrouted to the other."""
    _write_ticket_template(project.squad_dir)
    svc = service.Service(project, spec=_spec_with_shared_kind())

    task = (await svc.create("task", "t")).item
    ticket = (await svc.create("ticket", "tk")).item

    task_result = await svc.add_subtask(task.id, "task work")
    ticket_result = await svc.add_subtask(ticket.id, "ticket work")

    assert task_result.local_id == "ST1"
    assert ticket_result.local_id == "ST1"
    task_after = await svc.get(task.id)
    ticket_after = await svc.get(ticket.id)
    assert [s.title for s in task_after.subentities] == ["task work"]
    assert [s.title for s in ticket_after.subentities] == ["ticket work"]
