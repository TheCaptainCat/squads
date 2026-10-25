"""The workflow cheatsheet's example anchor: the type and spec-derived values a "Common commands"
example block is built from.
"""

from typing import TypedDict

from squads import _badges as badges
from squads._workflow._models import Field, WorkflowSpec


def cheatsheet_anchor_type(spec: WorkflowSpec) -> str | None:
    """The single non-roster type used to build a "Common commands" example block (the
    squads skill, AGENTS.md) — chosen generically from *spec* so a squad that drops or
    renames ``"task"`` still gets a fully runnable,
    representative example instead of one built from a type that no longer exists.

    Scored by how much of the example surface a type can actually demonstrate: a
    sub-entity kind (for ``add-<kind>``), a required parent (for ``--parent``), and an
    ordered badge field (for ``--priority``-shaped metadata) each add a point. The
    highest-scoring type wins; ties break by declared registration order
    (``ItemSpec.order``, then type name) for determinism — on the bundled spec this
    reproduces ``"task"`` exactly, since it's the only type that scores on all three axes.

    ``None`` only when *spec* has no non-roster type at all (every work/records type
    dropped) — there is nothing left to anchor an example on.
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
    """Bundle of spec-derived values a "Common commands" example block needs to build a
    fully runnable, representative example: the anchor type
    (:func:`cheatsheet_anchor_type`) plus everything about it an example command might
    show — its prefix, sub-entity kind, required-parent prefix, first active/settled
    status — and the ordered "priority" field/values any surviving type carries (never
    just the anchor's own, since :func:`squads._badges.first_ordered_field` scans every
    type — see its docstring for why one type can't be trusted to answer for all of them).

    Shared by the squads skill and AGENTS.md templates (registered as a Jinja global) and
    by the ``agents_md`` backend's Python-side ``also_creatable_types`` computation, so
    the two render paths derive this from one place rather than independently.

    Every value degrades to ``None`` (or, where a string is unavoidable in-line, a
    generic placeholder like ``"TYPE"``) when *spec* has no non-roster type left to
    anchor on at all.
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
