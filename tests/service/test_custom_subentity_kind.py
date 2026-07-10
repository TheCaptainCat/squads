"""Sub-entity kind<->parent-type<->container resolution is active-spec-driven (P1, generic
once): a project-declared type hosting a project-declared kind resolves with zero code change,
the maps are per-``Service`` (never a shared global another squad's override could leak into),
and two distinct types are free to share the same kind without either misrouting to the other.
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
    return base.model_copy(
        update={
            "items": new_items,
            "subentity_kinds": new_kinds,
            "prefix_to_type": {**base.prefix_to_type, "GDG": "gadget"},
        }
    )


async def test_a_project_declared_type_hosting_a_project_declared_kind_resolves_with_no_code_change(
    project,
) -> None:
    svc = service.Service(project, spec=_spec_with_custom_kind())
    assert svc.subentity_parent["ticket"] == "gadget"
    assert svc.subentity_kind["gadget"] == "ticket"
    assert svc.subentity_container["ticket"] == "tickets"


async def test_the_bundled_maps_are_per_service_never_a_shared_global(project) -> None:
    svc = service.Service(project)  # a different service, bundled spec only
    assert "ticket" not in svc.subentity_parent
    assert "gadget" not in svc.subentity_kind
    assert svc.subentity_parent == {"story": "feature", "subtask": "task", "finding": "review"}


async def test_two_types_sharing_one_kind_each_resolve_their_own_items_independently(
    project,
) -> None:
    base = bundled_spec()
    ticket_type = ItemSpec(
        prefix="TICKET", folder="tickets", lifecycle="work", subentity_kind="subtask"
    )
    spec = base.model_copy(
        update={
            "items": {**base.items, "ticket": ticket_type},
            "prefix_to_type": {**base.prefix_to_type, "TICKET": "ticket"},
        }
    )
    templates_dir = project.squad_dir / ".overrides" / "templates" / "items"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "ticket.md.j2").write_text(
        "<!-- sq:body -->\n_TODO_\n<!-- sq:body:end -->\n\n"
        "<!-- sq:summary -->\n<!-- sq:summary:end -->\n\n"
        "<!-- sq:subtasks -->\n<!-- sq:subtasks:end -->\n\n"
        "<!-- sq:discussion -->\n<!-- sq:discussion:end -->\n",
        encoding="utf-8",
    )
    invalidate_squad_dir(project.squad_dir)  # evict the pre-existing-template env cache
    svc = service.Service(project, spec=spec)

    task = (await svc.create("task", "t")).item
    ticket = (await svc.create("ticket", "tk")).item
    task_sub = await svc.add_subtask(task.id, "task work")
    ticket_sub = await svc.add_subtask(ticket.id, "ticket work")

    assert task_sub.local_id == "ST1" and ticket_sub.local_id == "ST1"
    assert [s.title for s in (await svc.get(task.id)).subentities] == ["task work"]
    assert [s.title for s in (await svc.get(ticket.id)).subentities] == ["ticket work"]
