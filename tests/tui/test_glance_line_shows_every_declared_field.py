"""The reader's glance header renders one badge per declared field, not a hardcoded
``priority``.

An adopter that declares its own axis on a type could filter and sort ``sq ui`` by it (both
of those enumerate declared codes) and never see it in the header, with ``sq check`` and
``sq workflow lint`` clean and the value storing and reading back — the axis existed
everywhere except where you look at it.
"""

import pytest

pytest.importorskip("textual")

from squads._tui._reader import _glance_line
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import Badge, Collection, Field, WorkflowSpec

pytestmark = pytest.mark.anyio


def _spec_with(bug_fields: list[Field]) -> WorkflowSpec:
    base = load_workflow_spec()
    items = dict(base.items)
    items["bug"] = base.items["bug"].model_copy(update={"fields": bug_fields})
    collections = dict(base.collections)
    collections["impact"] = Collection(
        label="Impact",
        ordered=True,
        badges=[
            Badge(code="blocker", label="Blocker", emoji="🔴"),
            Badge(code="cosmetic", label="Cosmetic", emoji="🟢"),
        ],
    )
    return WorkflowSpec.model_validate(
        {
            "items": items,
            "statuses": base.statuses,
            "lifecycles": base.lifecycles,
            "prefix_to_type": base.prefix_to_type,
            "alias_to_type": base.alias_to_type,
            "collections": collections,
            "subentity_kinds": base.subentity_kinds,
            "roles": base.roles,
        }
    )


async def test_a_declared_non_priority_field_appears_in_the_glance_line(svc) -> None:
    bug = (await svc.create("bug", "Crash on save", author="manager")).item
    bug.set_badge_value("impact", "blocker")
    spec = _spec_with([Field(code="impact", label="Impact", collection="impact")])

    assert "Blocker" in str(_glance_line(bug, spec))


async def test_every_declared_field_with_a_value_appears_in_order(svc) -> None:
    """The bundled `bug` declares both priority and severity — both render, in declaration
    order, rather than only the first one a literal happened to name."""
    bug = (await svc.create("bug", "Crash on save", author="manager", priority="high")).item
    bug.set_badge_value("severity", "critical")

    line = str(_glance_line(bug, svc.spec))
    assert line.index("High") < line.index("Critical")


async def test_a_field_with_no_stored_value_is_skipped(svc) -> None:
    bug = (await svc.create("bug", "Crash on save", author="manager")).item
    line = str(_glance_line(bug, svc.spec))
    assert "unassigned" in line
    assert "High" not in line


async def test_a_type_declaring_no_fields_still_renders_status_and_assignee(svc) -> None:
    bug = (await svc.create("bug", "Crash on save", author="manager", priority="high")).item
    spec = _spec_with([])

    line = str(_glance_line(bug, spec))
    assert "Open" in line
    assert "High" not in line
