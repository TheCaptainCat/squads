"""The workflow cheatsheet's example anchor: the type and spec-derived values a "Common commands"
example block is built from.
"""

from collections.abc import Iterable, Mapping
from typing import Any, TypedDict

from squads import _badges as badges
from squads._interactions._models import PlaybookSpec
from squads._interactions._playbook import authoring_owners
from squads._interactions._role_guidance import role_like
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


def cheatsheet_alias_example(spec: WorkflowSpec) -> str:
    """A runnable ``sq <alias> 26 <kind> 4 show`` line built from the first non-roster type that
    declares an alias, with the sub-entity kind it hosts when it hosts one. Without an aliased
    type it names the anchor type, or ``<type>``, so the line never names a vocabulary the
    squad lacks.
    """
    for item_type in sorted(spec.non_roster_types(), key=lambda t: (spec.items[t].order, t)):
        aliases = spec.items[item_type].aliases
        if aliases:
            kind = spec.item_subentity_kind(item_type)
            return f"sq {aliases[-1]} 26 {kind} 4 show" if kind else f"sq {aliases[-1]} 26 show"
    return f"sq {cheatsheet_anchor_type(spec) or '<type>'} 26 show"


class ReviewGate(TypedDict):
    """Return shape of :func:`cheatsheet_review_gate`."""

    type: str | None
    kind: str | None


def cheatsheet_review_gate(
    spec: WorkflowSpec,
    roster: Iterable[Mapping[str, Any]] | None,
    playbook: PlaybookSpec,
) -> ReviewGate:
    """The type a live role holding the ``review`` capability authors, and the sub-entity kind that
    type hosts, so generated guidance can name what gates a piece of work. Both are ``None`` when
    the spec, playbook and roster declare no such type or kind.
    """
    live = [role_like(r) for r in roster or ()]
    titles = {r.slug: r.title for r in live}
    reviewers = {r.slug for r in live if "review" in r.capabilities}
    for item_type in sorted(spec.non_roster_types(), key=lambda t: (spec.items[t].order, t)):
        owners = authoring_owners(item_type, live, playbook, titles)
        if any(slug in reviewers for slug, _title in owners):
            return {"type": item_type, "kind": spec.item_subentity_kind(item_type)}
    return {"type": None, "kind": None}


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
