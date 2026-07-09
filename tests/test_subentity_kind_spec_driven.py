"""Service-level proof that sub-entity kind<->type<->container maps are active-spec-driven
(ADR-348 §5, TASK-351): a project-declared type hosting a project-declared kind resolves with
no code change, and the bundled maps stay untouched for a service on the default spec.
"""

import pytest

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
