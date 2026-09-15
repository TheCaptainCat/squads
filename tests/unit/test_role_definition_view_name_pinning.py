"""``ROLE_DEFINITION_VIEW_NAME`` — the three writers that must agree on a role's placement-tag
view name, and the declaration all three are checked against.

Mirrors the pinning ``SYSTEM_SKILL_VIEW_NAMES``/``ITEM_SKILL_VIEW_NAME`` already get: the
creation scaffold's seeded tag, ``ServiceCore._create_core``'s belt-and-suspenders reseed, and
``MaintenanceMixin._repair_body_tag``'s classification each name a role's view independently,
and none of the four reads from any of the others — only a shared constant, checked against
``[views.role_definition]`` in ``_specs/workflow.toml``, can keep them from disagreeing. A rename
that missed one of the four would seed or classify a dangling tag with no test catching it.
"""

from pathlib import Path

import pytest

from squads import _clock as clock
from squads._index._resolver import item_file
from squads._interactions import ROLE_DEFINITION_VIEW_NAME
from squads._models import _markers as markers
from squads._models._item import Item
from squads._rendering import _engine
from squads._sections import get_section
from squads._services._maintenance import MaintenanceMixin
from squads._workflow import ROSTER_ROLE, bundled_spec

pytestmark = pytest.mark.anyio


def test_the_constant_is_declared_in_the_bundled_spec() -> None:
    assert ROLE_DEFINITION_VIEW_NAME in bundled_spec().views


def test_the_creation_scaffold_seeds_the_same_tag() -> None:
    """``agents/role.md.j2`` cannot read a Python constant (a static scaffold file) — pinned
    here instead, so a rename to the constant without updating the template's own literal
    reddens this rather than silently seeding a dangling tag into every newly-activated role."""
    template = Path(_engine.__file__).parent / "templates" / "agents" / "role.md.j2"
    text = template.read_text(encoding="utf-8")
    assert markers.open_marker(markers.view_tag(ROLE_DEFINITION_VIEW_NAME)) in text


async def test_the_create_core_reseed_writes_the_same_tag(svc) -> None:
    """``ServiceCore._create_core``'s belt-and-suspenders reseed — driven through
    ``activate_role``, a real creation path, not the template's static bytes."""
    item = await svc.activate_role("architect")
    path = item_file(svc.paths, item)
    region = (get_section(path.read_text(encoding="utf-8"), markers.BODY) or "").strip()
    assert region == markers.open_marker(markers.view_tag(ROLE_DEFINITION_VIEW_NAME))


async def test_the_repair_classifier_names_the_same_tag(svc) -> None:
    """``MaintenanceMixin._repair_body_tag`` — the third writer, driven directly rather than
    through the whole ``sq repair`` sweep (which is exercised end to end elsewhere). A
    never-persisted role ``Item`` is enough: the classification is a pure function of
    ``item.type`` and the active spec, not of anything a real seed would add."""
    now = clock.now()
    role = Item(
        sequence_id=0,
        type=ROSTER_ROLE,
        title="Manager",
        slug="manager",
        status=svc.spec.live_initial(ROSTER_ROLE),
        path="agents/roles/manager.md",
        created_at=now,
        updated_at=now,
    )
    assert isinstance(svc, MaintenanceMixin)
    assert svc._repair_body_tag(role) == ROLE_DEFINITION_VIEW_NAME
