"""The workflow cheatsheet's example anchor: the type and spec-derived values a "Common commands"
example block is built from.
"""

from typing import TypedDict

from squads import _badges as badges
from squads._workflow._models import Field, WorkflowSpec


def cheatsheet_anchor_type(spec: WorkflowSpec) -> str | None:
    """The one non-roster type that anchors a "Common commands" example (squads skill, AGENTS.md).

    It is chosen from *spec*, so a squad that drops or renames ``"task"`` still gets a runnable
    example. A type scores a point each for a sub-entity kind (``add-<kind>``), a required parent
    (``--parent``) and an ordered badge field (``--priority``); the highest score wins and ties
    break by ``ItemSpec.order`` then type name. On the bundled spec that is ``"task"``, the only
    type scoring on all three. ``None`` only when *spec* has no non-roster type.
    """
    types = sorted(spec.non_roster_types(), key=lambda t: (spec.items[t].order, t))
    if not types:
        return None

    def score(item_type: str) -> int:
        points = 0
        if spec.item_subentity_kind(item_type):
            points += 1
        if spec.item_parent_required(item_type):
            points += 1
        if any(spec.collection(f.collection).ordered for f in spec.fields_for(item_type)):
            points += 1
        return points

    best = max(score(t) for t in types)
    return next(t for t in types if score(t) == best)


class CheatsheetAnchorContext(TypedDict):
    """Return shape of :func:`cheatsheet_anchor_context` — see there for what each key means."""

    anchor: str | None
    anchor_prefix: str
    anchor_kind: str | None
    anchor_parent_prefix: str | None
    anchor_active: str | None
    anchor_settled: str | None
    priority_field: Field | None
    priority_values: list[str]


def cheatsheet_anchor_context(spec: WorkflowSpec) -> CheatsheetAnchorContext:
    """The spec-derived values a "Common commands" example needs to be runnable.

    The anchor type (:func:`cheatsheet_anchor_type`) plus its prefix, sub-entity kind,
    required-parent prefix and first active/settled status, and the ordered "priority"
    field/values any surviving type carries (:func:`squads._badges.first_ordered_field` scans
    every type, since one type cannot answer for all). The squads skill and AGENTS.md templates
    (a Jinja global) and the ``agents_md`` backend's ``also_creatable_types`` share it, so both
    render paths derive it from one place. Every value degrades to ``None``, or a placeholder
    like ``"TYPE"`` where a string is needed in-line, when *spec* has no non-roster type.
    """
    anchor = cheatsheet_anchor_type(spec)
    anchor_parent = spec.item_parent_required(anchor) if anchor else None
    priority_field = badges.first_ordered_field(spec)
    return {
        "anchor": anchor,
        "anchor_prefix": spec.items[anchor].prefix if anchor else "TYPE",
        "anchor_kind": spec.item_subentity_kind(anchor) if anchor else None,
        "anchor_parent_prefix": (spec.items[anchor_parent].prefix if anchor_parent else None),
        "anchor_active": spec.first_active_status(anchor) if anchor else None,
        "anchor_settled": spec.first_settled_status(anchor) if anchor else None,
        "priority_field": priority_field,
        "priority_values": (
            [b.code for b in spec.collection(priority_field.collection).badges]
            if priority_field
            else []
        ),
    }
