"""Derived views: resolve a declared ``[views]`` entry's source and render it.

A view's *declaration* is a source and nothing else — what to resolve (refs of a declared
kind pointing at the item, a sub-entity collection, a subtree, the item's own merged role
definition, a type's playbook lane, or the item itself, resolved by :func:`resolve_source`).
*Resolving* it has one further step, presentation: a Jinja2 template resolved by
:func:`render_source_view` at ``templates/views/<name>.md.j2`` — the view's own declared name,
never a separate stored field. Whatever :func:`resolve_source` returns is handed to the
template directly, in its own native shape, unflattened. Every view is computed on request;
nothing here ever writes into an item body.

Six source kinds, in two families. ``ref``/``subtree``/``subentity`` are **relations** — a
join over other items/sub-entities, returned as a flat ``list[Item]``/``list[SubEntity]`` a
template iterates directly (with Jinja's own ``groupby``/``sort``/``selectattr`` under
``StrictUndefined`` doing whatever grouping/ordering the presentation wants).
``role``/``playbook``/``self`` are **not** relations — each resolves to its own native shape
(a ``RoleDef``, a :class:`PlaybookSource`, the host item itself) that a template reads
directly.

``sq workflow view --json`` dispatches per source kind
(``squads._cli._workflow_cmd._view_json_payload``), serializing each resolved value in the
shape its own kind already has a serializer for — never a shared envelope.

Cost is one already-loaded index plus an inversion/walk over it — the same shape ``sq tree``
and ``sq blocked`` have always had; nothing here caches a resolved value or stores one on an
item.

:func:`expand_view_tags` is the read-time counterpart of the placement verb
(``ServiceMixin.insert_view``/``remove_view`` in ``squads._services._views``): a
``sq:view:<name>`` tag placed in a body is content-free — it names a view and nothing else —
and this is where that name turns into the view's rendered output, on every read, computed
fresh, never stored back.
"""

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal

from squads._backends._base import RoleView
from squads._errors import SquadsError
from squads._interactions import (
    ITEM_SKILL_VIEW_NAME,
    ROLE_DEFINITION_VIEW_NAME,
    SYSTEM_SKILL_VIEW_NAMES,
    item_type_for_skill_slug,
)
from squads._interactions._loader import PLAYBOOK_OVERRIDE_FILENAME
from squads._interactions._models import ItemPlaybookSpec, PlaybookSpec
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import (
    DISPLAY_ID_PADDING,
    Item,
    effective_prefix,
    format_item_id,
    ref_id_matches,
    split_ref,
)
from squads._models._subentity import SubEntity
from squads._paths import number_for_id
from squads._rendering._engine import (
    TEMPLATES_OVERRIDE_DIR,
    creation_template_name,
    has_template,
    render,
    template_source,
)
from squads._roles._catalog import RoleDef
from squads._roles._resolver import resolve_role_for_item
from squads._sections import get_section, iter_marker_spans, split_frontmatter, strip_marker_lines
from squads._workflow._models import (
    ROSTER_ROLE,
    ROSTER_SKILL,
    ViewSpec,
    WorkflowSpec,
    parse_view_position,
    subentity_source_reason,
)

#: A zero-argument roster provider — deferred, so a caller that already has the roster in hand
#: (or a cheap way to get it) pays nothing for a body/view whose source never looks at it.
#: ``playbook`` is the one source kind that ever calls this; the other five never do (see
#: :func:`resolve_source`, :func:`expand_view_tags`), so threading a callable rather than a
#: materialised ``list[RoleView]`` is what keeps their cost at zero rather than "however much
#: the caller happened to precompute". A caller invoked more than once per roster (a body
#: carrying more than one ``playbook`` tag) is expected to memoize its own callable rather than
#: relying on this type to do it — see ``ItemsMixin.read_body``.
type RosterProvider = Callable[[], list[RoleView]]


# --------------------------------------------------------------------------- source resolution


@dataclass(frozen=True)
class PlaybookSource:
    """The resolved value of a ``playbook`` source: *item_type*'s own playbook lane —
    overview, lifecycle line, commands, role guides — and the squad's live roster. ``lane`` is
    ``None`` for a type that is declared but carries no playbook entry at all (a project's own
    custom type nobody wrote guidance for): a well-formed, empty result, not a failure — see
    :func:`_playbook_source_applies`. Carries the raw ingredients
    ``templates/views/item_skill.md.j2`` derives its eight rendered values from (lane + roster
    + the active spec, the last of which reaches the template separately, as ``spec=``), so a
    template derives what it needs — through the registered ``item_skill_role_sections``/
    ``custom_item_skill_commands``/``label_for``/``linearize_lifecycle`` filters — rather than
    being handed pre-computed strings.

    ``playbook`` is the *whole* active/merged document *lane* was looked up in — not one
    consumer's ingredient, a second one: a per-type skill (``lane`` alone) never reads it, but
    ``squads_skill.md.j2``'s embedded workflow cheatsheet loops every declared type's own
    authoring lane (``authoring_owner``, via the shared ``workflow.md.j2`` partial), which
    ``lane`` — one type's own entry — cannot answer. Carried here rather than added as a
    parallel ``render_source_view`` context key because it is already in hand at the one place
    a ``playbook`` source resolves (:func:`_resolve_playbook_source`), the same reasoning that
    keeps ``squad_dir`` off a per-kind special case."""

    item_type: str
    lane: ItemPlaybookSpec | None
    roster: list[RoleView]
    playbook: PlaybookSpec


#: Every shape :func:`resolve_source` can return — a relation's flat ``Item``/``SubEntity``
#: list for ``ref``/``subtree``/``subentity``, or one of the three other kinds' own native
#: value. No middle-layer record type sits between a source and the objects it actually holds.
type SourceResult = list[Item] | list[SubEntity] | RoleDef | PlaybookSource | Item


def _resolve_subentity_source(view: ViewSpec, item: Item) -> list[SubEntity]:
    """*item*'s own sub-entity collection of *view*'s declared kind — the real
    :class:`~squads._models._subentity.SubEntity` objects, never a normalised record. Every
    record shares the one kind a ``subentity`` source ever resolves, and that kind is fixed by
    the view's own declaration (``source.name``) — known to whoever writes the view's own
    ``templates/views/<name>.md.j2``, so a template needing it hard-codes it rather than
    reading it off anything passed at render time. :func:`render_source_view` hands a template
    only the resolved ``source``, the host ``item`` and the active ``spec`` — never the
    :class:`ViewSpec` declaration itself — so no template can read the kind off *view*.

    Carries no applicability check and raises nothing: whether this kind applies to *item*'s
    type is a precondition, decided once by :func:`resolve_view_target` (the quiet consumers —
    placement, read-time expansion, the file scan) or by :func:`resolve_source` (the loud,
    direct-question consumer — ``sq workflow view``) *before* either ever calls this function.
    A resolver may not raise for a condition its kind's predicate could already have decided —
    reached with an incompatible *item* only if a caller skipped that gate, in which case
    ``item.subentities`` is simply empty and this returns ``[]``,
    which is the correct answer to "no records", not a failure (see the emptiness clause on
    :func:`resolve_view_target`)."""
    del view  # kept for dispatch symmetry with the other two relation resolvers; unread here
    return list(item.subentities)


def _resolve_role_source(item: Item, squad_dir: Path | None) -> RoleDef:
    """*item*'s own merged role definition — catalog default, layered with any project
    ``.overrides/roles/<slug>.toml``, layered with the operator-settable fields *item* itself
    carries. Calls the documented seam every other consumer of a live role item's full
    ``RoleDef`` goes through (:func:`~squads._roles._resolver.resolve_role_for_item`) rather
    than re-deriving its two-call resolution here, so this inherits that seam's graceful
    degrade along with its happy path.

    Carries no applicability check, for the same reason :func:`_resolve_subentity_source`
    doesn't: whether *item*'s type is the declared role type is a precondition, decided before
    this is ever called. Unlike that resolver, this one *can* still fail to resolve against the
    catalog or a project override for this specific item's own slug — a condition not decidable
    from *item*'s type alone — but :func:`resolve_role_for_item` degrades that case to
    :meth:`~squads._roles._catalog.RoleDef.from_extra_or_item` rather than raising, the same
    tolerance the rest of the codebase already extends to an orphaned role item (see that
    seam's own docstring), so a read through this source stays readable rather than joining
    the genuine per-item defects :func:`resolve_source` still raises for."""
    return resolve_role_for_item(item, squad_dir)


def _playbook_subject(item: Item, spec: WorkflowSpec) -> str:
    """The type *item* speaks for when a ``playbook`` source's ``name`` is unset — its own
    type for every host except the declared roster skill type (:data:`ROSTER_SKILL`), whose
    per-item-type skill instead speaks for the item type its own slug *documents*
    (``sq-<type>`` -> ``<type>``, via :func:`~squads._interactions.item_type_for_skill_slug`,
    the same declared-type inversion :data:`~squads._interactions.active_skill_slugs` is built
    from — never a second, hand-rolled one here).

    A slug that documents no declared type falls back to the host's own type (``"skill"``) —
    the emptiness case, never a predicate refusal: one of
    the three permanently-system skills (``squads``/``greeting``/``sq-memory``), an
    author-created skill sharing the ``sq-`` convention by coincidence, and a dropped or
    renamed type's now-stale slug all land here, none of them carrying a playbook lane —
    ``[views.squads_skill]`` relies on exactly this fallback for its own host.

    **The gate is load-bearing, not tidiness.** ``Item.slug`` is the filename slug segment for
    *every* item, not only a skill — an ungated inversion would resolve a different type's
    lane for an ordinary work item whose title happened to slugify to ``sq-<some declared
    type>``. Restricting the slug-inversion attempt to a roster-skill host is what keeps that
    from ever being reached for anything but a skill item, whose slug is the only one this
    naming convention was ever meant to describe."""
    if item.type != ROSTER_SKILL:
        return item.type
    slug = item.extra.get(X.SLUG, item.slug)
    return item_type_for_skill_slug(slug, spec) or item.type


def _resolve_playbook_source(
    view: ViewSpec, item: Item, playbook: PlaybookSpec, roster: RosterProvider, spec: WorkflowSpec
) -> PlaybookSource:
    """The playbook lane of *view*'s named type, or the type *item* speaks for
    (:func:`_playbook_subject`) when *view* names none — resolved against *playbook* (the
    caller's active, merged spec — never the bundled singleton, so a project's own playbook
    override is what this answers against). Never raises: a resolved type with no entry is
    :class:`PlaybookSource`'s ``lane=None``, the well-formed empty case
    :func:`_playbook_source_applies` already lets through.

    *roster* is called here — the one call, anywhere in the dispatch, that ever forces it (see
    :data:`RosterProvider`)."""
    target_type = view.source.name or _playbook_subject(item, spec)
    return PlaybookSource(
        item_type=target_type,
        lane=playbook.types.get(target_type),
        roster=roster(),
        playbook=playbook,
    )


def _resolve_self_source(item: Item) -> Item:
    """A ``self`` source resolves to the host item itself — no join, no lookup, nothing this
    function computes that its caller didn't already have. Kept as a real function (rather
    than inlined at the call site) purely so every source kind has one resolver function
    dispatch can name uniformly."""
    return item


def _resolve_ref_source(view: ViewSpec, item: Item, db: SquadsDB, spec: WorkflowSpec) -> list[Item]:
    """Items carrying a ref of the declared kind pointing at *item*, recovered by inverting
    stored forward edges — the same shape ``squads._services._refs.RefsMixin.refs_in``
    computes, inlined here so it shares the one index load the caller already made rather than
    loading a second time. Real ``Item`` objects, ascending by sequence number — never a
    normalised record."""
    target_kind = view.source.name
    assert target_kind is not None, "a 'ref' source's name is validated non-None at spec load"
    default_kind = spec.default_ref_kind()
    target_prefix = effective_prefix(item.prefix)
    target_seq = item.sequence_id
    matched: list[Item] = []
    for it in sorted(db.items.values(), key=lambda i: number_for_id(i.id)):
        for r in it.refs:
            rid, kind = split_ref(r)
            if (kind or default_kind) == target_kind and ref_id_matches(
                rid, target_prefix, target_seq
            ):
                matched.append(it)
                break
    return matched


def children_by_parent(db: SquadsDB) -> dict[str, list[Item]]:
    """Canonical-parent → children, width-tolerant (mirrors
    ``squads._services._base._build_tree_children``'s resolution, reimplemented rather than
    imported: ``_services`` sits above this module in the layering, so the edge runs one way
    only — a service may call into ``squads._views``, never the reverse). Public (no leading
    underscore) because ``squads._cli._workflow_cmd._view_json_payload``'s ``ref``/``subtree``
    ``--json`` arm reuses this exact walk to populate each matched record's real descendant
    subtree — the same "who are this item's children" resolution, never a second
    implementation of it."""
    all_ids = {i.id for i in db.items.values()}
    seq_to_id = {number_for_id(i.id): i.id for i in db.items.values()}
    children: dict[str, list[Item]] = {}
    for it in db.items.values():
        if not it.parent:
            continue
        canonical = seq_to_id.get(number_for_id(it.parent))
        if canonical is not None and canonical in all_ids:
            children.setdefault(canonical, []).append(it)
    return children


def _resolve_subtree_source(view: ViewSpec, item: Item, db: SquadsDB) -> list[Item]:
    """*item*'s descendants whose type is *view*'s declared ``source.name`` — real ``Item``
    objects, ascending by sequence number."""
    target_type = view.source.name
    assert target_type is not None, "a 'subtree' source's name is validated non-None at spec load"
    children = children_by_parent(db)
    seen = {item.id}
    stack = [item.id]
    matched: list[Item] = []
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            if child.id in seen:
                continue
            seen.add(child.id)
            stack.append(child.id)
            if child.type == target_type:
                matched.append(child)
    matched.sort(key=lambda i: number_for_id(i.id))
    return matched


# --------------------------------------------------------------------------- source applicability


#: One applicability predicate per declared source ``kind`` — the classification test every
#: source kind is judged by: is this condition decidable from the declared spec plus the host
#: item's *type* alone, before any record is read and before any template is rendered. Each
#: entry takes ``(view, view_name, item_type, spec, playbook)`` and returns ``None`` when
#: *item_type* can host *view*'s source, else the reason it cannot — never a bare boolean, so
#: the placement refusal, the read-time quiet skip and the file-scan finding all name the same
#: cause. **Every kind declares an entry, including the ones that impose nothing on the host**
#: — explicit, rather than a kind silently satisfying every predicate by absence from this
#: mapping. A predicate reads only *item_type*, *spec* and *playbook* — never *item* itself:
#: that is what keeps this answerable by the file-level scan, which binds a host's type from
#: its folder and filename before ``read_frontmatter`` ever runs (see
#: ``MaintenanceMixin._scan_for_check``), and it is checked structurally in
#: ``tests/unit/test_view_source_applicability_predicate.py`` rather than trusted by
#: inspection. *playbook* is threaded rather than read off a bundled singleton so the one
#: kind that needs it (``playbook``) answers against the *active*, possibly-overridden
#: playbook — the same one ``templates/views/item_skill.md.j2`` decides its own rich/thin
#: branch against (a ``lane is None`` test) — and every other entry ignores the parameter, the
#: same way each already ignores
#: whichever of *view*/*view_name*/*item_type*/*spec* it has no use for.
type _SourceApplicability = Callable[[ViewSpec, str, str, WorkflowSpec, PlaybookSpec], str | None]


def _ref_source_applies(
    view: ViewSpec, view_name: str, item_type: str, spec: WorkflowSpec, playbook: PlaybookSpec
) -> str | None:
    """A ``ref`` source imposes no constraint on its host: inverting stored forward edges reads
    the same regardless of the host's own type. Declared explicitly true.

    Every parameter goes unused — the point being made, not an oversight: this predicate's
    answer does not depend on *view*, *view_name*, *item_type*, *spec* or *playbook*. The full
    signature is kept (rather than a narrower one) so every entry in
    :data:`_SOURCE_APPLICABILITY` shares one call shape, and *item_type* stays checkable
    structurally as ``str`` on every registered kind, this one included."""
    del view, view_name, item_type, spec, playbook
    return None


def _subtree_source_applies(
    view: ViewSpec, view_name: str, item_type: str, spec: WorkflowSpec, playbook: PlaybookSpec
) -> str | None:
    """A ``subtree`` source imposes no constraint on its host either: a descendant walk over a
    type this host will never in practice parent simply yields zero rows, which is the correct
    answer to "no records" — never a failure (the emptiness clause; see
    :func:`resolve_view_target`). Declared explicitly true; see :func:`_ref_source_applies` for
    why every parameter here is unused rather than dropped."""
    del view, view_name, item_type, spec, playbook
    return None


def _subentity_source_applies(
    view: ViewSpec, view_name: str, item_type: str, spec: WorkflowSpec, playbook: PlaybookSpec
) -> str | None:
    """A ``subentity`` source's one host constraint: *item_type* must itself host the projected
    kind — decidable from the type alone, never from a resolved item's actual sub-entities.
    Asks through :func:`~squads._workflow._models.subentity_source_reason`, the one place this
    comparison is worded."""
    del playbook
    return subentity_source_reason(view_name, item_type, view.source.name, spec.items)


def _role_source_applies(
    view: ViewSpec, view_name: str, item_type: str, spec: WorkflowSpec, playbook: PlaybookSpec
) -> str | None:
    """A ``role`` source's one host constraint: *item_type* must itself be the declared role
    type (:data:`~squads._workflow._models.ROSTER_ROLE`) — decidable from the type alone.

    What is *not* decided here, deliberately: whether *this specific* role item's identity
    actually resolves against the catalog or a project override. That depends on the item's
    own slug and the override tree on disk, not on its type, so it fails the classification
    test's "type alone" clause — not a precondition this predicate could ever decide.
    :func:`_resolve_role_source` degrades that case rather than raising it (see
    :func:`~squads._roles._resolver.resolve_role_for_item`'s own docstring)."""
    del view, spec, playbook
    if item_type == ROSTER_ROLE:
        return None
    return (
        f"view {view_name!r} is a role source, but {item_type!r} is not the role "
        f"type ({ROSTER_ROLE!r})"
    )


def _playbook_source_applies(
    view: ViewSpec, view_name: str, item_type: str, spec: WorkflowSpec, playbook: PlaybookSpec
) -> str | None:
    """A ``playbook`` source imposes no constraint on its host: a resolved type that carries no
    playbook entry at all yields :class:`PlaybookSource`'s ``lane=None``, the well-formed empty
    result — never a failure (the emptiness clause; see :func:`resolve_view_target`). Declared
    explicitly true; see :func:`_ref_source_applies` for why every parameter here is unused
    rather than dropped."""
    del view, view_name, item_type, spec, playbook
    return None


def _self_source_applies(
    view: ViewSpec, view_name: str, item_type: str, spec: WorkflowSpec, playbook: PlaybookSpec
) -> str | None:
    """A ``self`` source imposes no constraint on its host at all — it resolves to the host
    itself, which every item trivially has. Declared explicitly true; see
    :func:`_ref_source_applies` for why every parameter here is unused rather than dropped."""
    del view, view_name, item_type, spec, playbook
    return None


_SOURCE_APPLICABILITY: dict[str, _SourceApplicability] = {
    "ref": _ref_source_applies,
    "subtree": _subtree_source_applies,
    "subentity": _subentity_source_applies,
    "role": _role_source_applies,
    "playbook": _playbook_source_applies,
    "self": _self_source_applies,
}


def _source_incompatibility(
    view: ViewSpec, view_name: str, item_type: str, spec: WorkflowSpec, playbook: PlaybookSpec
) -> str | None:
    """``None`` when *view*'s declared source can resolve against a host of *item_type*, else
    the reason it cannot — the one place :data:`_SOURCE_APPLICABILITY` is dispatched, so no
    consumer re-implements the ``source.kind`` switch."""
    return _SOURCE_APPLICABILITY[view.source.kind](view, view_name, item_type, spec, playbook)


def resolve_source(
    view: ViewSpec,
    view_name: str,
    item: Item,
    db: SquadsDB,
    spec: WorkflowSpec,
    playbook: PlaybookSpec,
    roster: RosterProvider,
    squad_dir: Path | None,
) -> SourceResult:
    """Every value *view* resolves to when read against *item* — dispatches on the declared
    ``source.kind``; never named as a bare string here (it comes straight off the
    already-validated spec). A relation kind (``ref``/``subtree``/``subentity``) returns a flat
    ``list[Item]``/``list[SubEntity]``, unflattened; ``role``/``playbook``/``self`` each return
    their own native shape — see the module docstring.

    *playbook*/*roster*/*squad_dir* are needed only by the three non-relation kinds (a
    relation resolver ignores them entirely), but every caller supplies all three regardless:
    each already has *playbook* and *squad_dir* in hand at the one call site that matters (the
    service layer, which already holds both), so a caller-side branch to omit them for "a view
    I know is a relation" would buy nothing and would have to be undone the moment that view's
    declared kind changes. *roster* is the one of the three actually expensive to produce (a
    disk read per live role), which is why it alone is a :data:`RosterProvider` rather than an
    already-materialised list: this dispatch calls it at most once, inside
    :func:`_resolve_playbook_source`, and every other kind never forces it at all.

    This is the **loud** consumer of source applicability: it raises :class:`SquadsError`
    when *view*'s source cannot apply to *item*'s type, through the same
    :data:`_SOURCE_APPLICABILITY` predicate :func:`resolve_view_target` composes for the quiet
    consumers. That is deliberate and not a duplicate gate — a direct call here (``sq workflow
    view <name> <id>``, via :meth:`~squads._services._views.ViewsMixin.resolve_view_source`/
    :meth:`~squads._services._views.ViewsMixin.render_view`) is a direct question about a named
    pair, and an inapplicable pair is a bad argument, not a broken read to be left quiet.
    :func:`expand_view_tags` already gates through :func:`resolve_view_target` before ever
    reaching here, so for that caller this check never fires — it exists for the caller that
    has not already asked."""
    reason = _source_incompatibility(view, view_name, item.type, spec, playbook)
    if reason is not None:
        raise SquadsError(reason)
    kind = view.source.kind
    if kind == "subentity":
        return _resolve_subentity_source(view, item)
    if kind == "ref":
        return _resolve_ref_source(view, item, db, spec)
    if kind == "subtree":
        return _resolve_subtree_source(view, item, db)
    if kind == "role":
        return _resolve_role_source(item, squad_dir)
    if kind == "playbook":
        return _resolve_playbook_source(view, item, playbook, roster, spec)
    return _resolve_self_source(item)  # "self"


def view_template_name(name: str) -> str:
    """The presentation template path a view named *name* resolves to, bundled or
    adopter-overridden — ``templates/views/<name>.md.j2``. The one place that path is
    composed, so :func:`resolve_view_target` and :func:`render_source_view` can never spell it
    differently."""
    return f"views/{name}.md.j2"


def resolve_view_target(
    name: str, item_type: str, spec: WorkflowSpec, playbook: PlaybookSpec
) -> str | None:
    """Can a ``sq:view:<name>`` tag on a host of *item_type* resolve? ``None`` if it can, else
    the reason it cannot — three questions, asked once: is *name* declared in *spec*'s
    ``[views]``; does its presentation template resolve (bundled, or shadowed by an adopter
    override — :func:`~squads._rendering._engine.has_template` already resolves through both);
    and does its declared source apply to *item_type* (:data:`_SOURCE_APPLICABILITY`, never a
    second implementation of that question at this call site).

    The one predicate a ``sq:view:<name>`` tag's every **quiet** consumer needs answered — the
    placement verb refuses inserting an unresolvable tag through this exact function, read-time
    expansion leaves an unresolvable tag literal through it, and ``sq check``'s file-scan
    finding reports the same failure through the same one, never a re-implementation of the
    question at any of the three. (The **loud** consumer, ``sq workflow view`` /
    :meth:`~squads._services._views.ViewsMixin.resolve_view_source`/``render_view``, asks the
    third question through :func:`resolve_source` instead, and raises rather than reporting a
    reason — see that function.)

    Reads only *item_type*, *spec* and *playbook* — never a resolved item's content, not its
    refs, its sub-entities, or its status — which is what lets the file-level scan ask this
    before ``read_frontmatter`` ever runs, and what keeps this out of the per-item validator
    catalog. Threaded off the caller's own *spec*/*playbook* (never a module global), so it
    answers correctly for an overridden project spec or playbook, not just the bundled ones —
    *playbook* only matters to the one kind that reads it (``playbook``); every other kind's
    predicate ignores it.

    **Emptiness is never a failure.** This only covers conditions under which a resolver
    cannot produce a well-formed result at all — never conditions under which it produces an
    empty one. A host with no members renders an empty result list; a ``subtree`` source over a
    type this host will never in practice parent yields zero rows, and that is the correct
    answer, not a reason to refuse."""
    if name not in spec.views or not has_template(view_template_name(name)):
        return (
            f"no declared view {name!r} with a resolvable presentation template; "
            "see `sq workflow views` for the declared set"
        )
    return _source_incompatibility(spec.views[name], name, item_type, spec, playbook)


#: The four states an empty-or-disabled ``sq:body`` region naming a placement tag can be in,
#: from the operator's point of view — see :func:`empty_body_hint_state`.
type EmptyBodyHintState = Literal[
    "view_undeclared", "declared_drift_outstanding", "declared_no_drift", "disabled"
]


def empty_body_hint_state(
    name: str, spec: WorkflowSpec, *, drift_outstanding: bool, disabled: bool = False
) -> EmptyBodyHintState:
    """Which of four states explains an empty-rendering ``sq:body`` region tagged for view
    *name* — the one predicate ``sq role show``/``sq skill show`` both read, so their empty-body
    hints can't disagree. Checks *disabled* first (its own unconditional remedy), then whether
    *name* is declared, then whether *drift_outstanding* is what ``sq sync`` would actually fix.

    Returns: ``"disabled"`` (``view add`` re-enables it); ``"view_undeclared"`` (no remedy
    renders this); ``"declared_drift_outstanding"`` (``sq sync`` is the fix);
    ``"declared_no_drift"`` (``sq sync`` is a no-op — ``view add`` is the real remedy)."""
    if disabled:
        return "disabled"
    if name not in spec.views:
        return "view_undeclared"
    return "declared_drift_outstanding" if drift_outstanding else "declared_no_drift"


class ViewTemplateMissingError(SquadsError):
    """:func:`render_source_view`'s own pre-check refusal — the named view has no presentation
    template — distinct from a :class:`SquadsError` the Jinja2 engine translates out of an
    actual render. Still a :class:`SquadsError`, so every existing catcher of that base class
    keeps working unchanged; the subtype exists solely so
    :func:`_render_resolved_source_or_raise` can tell its own pre-check refusal apart from an
    engine-translated failure and let the former through unrewrapped."""


def render_source_view(
    view_name: str,
    result: SourceResult,
    item: Item,
    spec: WorkflowSpec,
    squad_dir_display: str | None,
) -> str:
    """Render *view_name*'s already-resolved *result* through its presentation template —
    ``templates/views/<view_name>.md.j2``, resolved by the one Jinja2 engine every rendering
    path already uses. An adopter's ``.overrides/templates/views/<view_name>.md.j2`` shadows it
    exactly the way every other bundled template already does. The **one** render entry point,
    for all six source kinds: a relation kind's *result* is the flat ``list[Item]``/
    ``list[SubEntity]`` :func:`resolve_source` produced, unflattened; a
    ``role``/``playbook``/``self`` kind's is its own native shape (a ``RoleDef``, a
    :class:`PlaybookSource`, the host item). Whichever it is, the template receives it under
    the fixed name ``source`` — never a normalised record — plus ``item``/``spec``/
    ``squad_dir`` always, so grouping/ordering/badge-resolution for a relation kind is
    entirely the template's own job (Jinja's ``groupby``/``sort``/``selectattr`` plus the
    registered ``badge`` filter), not a step this function performs first.

    A coherent spec (:func:`~squads._workflow._models._check_views`) can still name a view
    whose template simply was never written — that's a filesystem fact, not a spec fact, so no
    load-time check can catch it. Checked here, the one funnel every presentation-render
    caller already goes through, so the failure is a clean :class:`ViewTemplateMissingError`
    naming the exact path to create — both the bundled location and the override shadow —
    rather than an unhandled ``jinja2.TemplateNotFound`` traceback.

    *squad_dir_display* is the **configured folder name** — :class:`~squads._models._config
    .SquadsConfig`'s own ``squad_dir`` string, the same value every backend template
    (``claude/claude_section.md.j2``, ``agents_md/agents_section.md.j2``) already renders under
    this key — handed to a template verbatim under ``{{ squad_dir }}``, never derived from the
    resolved absolute :class:`Path`. That Path is a different value with a different job: it is
    what :func:`_resolve_role_source` needs upstream in :func:`resolve_source` to actually open
    a project override on disk, and deriving a display string from it (e.g. its last path
    segment) is only correct when the configured value happens to be a single path segment —
    nothing about ``squad_dir`` requires that, so this function is handed the configured string
    directly and never touches the Path at all."""
    template_name = view_template_name(view_name)
    if not has_template(template_name):
        raise ViewTemplateMissingError(
            f"view {view_name!r} has no presentation template — create one at "
            f"templates/{template_name} (or shadow it with an adopter override at "
            f".overrides/templates/{template_name}) before it can be rendered; until then, "
            "resolve it with `--json`, which does not render at all"
        )
    return render(template_name, source=result, item=item, spec=spec, squad_dir=squad_dir_display)


def has_view_tag(text: str) -> bool:
    """Whether *text* carries at least one well-formed ``sq:view:<name>`` tag, enabled or
    disabled.

    Computed from the body text alone — no index, no spec, no item — the same span-and-name
    check :func:`expand_view_tags` itself does, exposed separately so the one shared body-read
    boundary (:meth:`~squads._services._items.ItemsMixin.read_body`) can decide whether an
    index load and an expansion call are needed at all *before* paying either cost. The
    overwhelming majority of bodies carry no tag, so this is the common case's fast path, not
    a redundant pre-check. A disabled-only body still answers ``True``: the read boundary must
    still strip it (to nothing) rather than let the raw tag reach ``sq show``.
    """
    return any(markers.view_tag_parts(raw) is not None for raw, _, _ in iter_marker_spans(text))


def template_seeded_view_names(item_type: str, spec: WorkflowSpec) -> frozenset[str]:
    """The ``sq:view:<name>`` tag names *item_type*'s creation template places inside its
    ``sq:body`` region, as that template stands today — read from the template's own SOURCE,
    never a render (there is no item to render against, and a render would need a context this
    question does not have).

    Resolves the template through the identical resolution the create path uses
    (:func:`~squads._rendering._engine.creation_template_name`, including the
    ``items/_default.md.j2`` fallback) and the same override-aware loader
    (:func:`~squads._rendering._engine.template_source`), so a project that overrode a type's
    creation template to add or drop a tag gets the overridden answer, never the bundled one.

    The one derivation the retroactive migration (which view names to place, and on which
    types) and the ``sq check`` advisory for a template-seeded tag missing from a body both
    read, so the two can never disagree about what "the template seeds this tag" means.
    Recognises a tag through :func:`~squads._models._markers.view_tag_parts` over the same
    positional marker scan every other consumer of the family uses
    (:func:`~squads._sections.iter_marker_spans`) — never a re-spelled ``sq:view:`` literal at
    this call site.

    Empty — never an error — when *item_type* isn't declared, its resolved template doesn't
    exist, its file carries no ``sq:body`` region, or that region carries no view tag: a type
    asked about that seeds nothing is an ordinary, unremarkable answer.
    """
    if item_type not in spec.items:
        return frozenset()
    template_name = creation_template_name(item_type, spec)
    if not has_template(template_name):
        return frozenset()
    body = get_section(template_source(template_name), markers.BODY)
    if body is None:
        return frozenset()
    return frozenset(
        parts.name
        for raw, _start, _end in iter_marker_spans(body)
        if (parts := markers.view_tag_parts(raw)) is not None
    )


def roster_slug(item_type: str, slug: str, extra: dict[str, Any]) -> str:
    """The identity a roster host (role or skill) classifies by — a skill's own ``extra.slug``
    when set, else *slug* unchanged. The one derivation every caller (write-path refusal,
    ``view rm``, :func:`roster_body_view_name`, the check tier) shares, so a hand-renamed skill
    file is classified identically everywhere."""
    return extra.get(X.SLUG, slug) if item_type == ROSTER_SKILL else slug


def roster_body_view_name(item_type: str, slug: str, spec: WorkflowSpec) -> str | None:
    """The view name a role's or skill's own ``sq:body`` region is classified as carrying, from
    *item_type* and *slug* alone — ``None`` for every other item type, and ``None`` when the
    classified view is dropped from ``[selected]`` or the slug matches no known role/system
    skill/declared type. The one derivation the write path and the check tier both read."""
    if item_type == ROSTER_ROLE:
        return ROLE_DEFINITION_VIEW_NAME if ROLE_DEFINITION_VIEW_NAME in spec.views else None
    if item_type == ROSTER_SKILL:
        view_name = SYSTEM_SKILL_VIEW_NAMES.get(slug)
        if view_name is not None:
            return view_name if view_name in spec.views else None
        if item_type_for_skill_slug(slug, spec) is not None:
            return ITEM_SKILL_VIEW_NAME if ITEM_SKILL_VIEW_NAME in spec.views else None
        return None
    return None


def skill_authoring_surface(
    view_name: str, slug: str, spec: WorkflowSpec, playbook: PlaybookSpec
) -> str:
    """The real surface a roster skill's *view_name* tag is authored through — resolved off
    the view's own declared source, never off *slug* as a literal, so it stays correct under a
    project override. A ``self`` source names its own template override; a ``playbook`` source
    names the resolved type's playbook lane, or the bare playbook file when there is none."""
    view = spec.views[view_name]
    if view.source.kind != "playbook":
        template = view_template_name(view_name)
        return (
            f"its `{TEMPLATES_OVERRIDE_DIR}/{template}` view template override "
            f"(`sq override scaffold {template}` creates it)"
        )
    target_type = view.source.name or item_type_for_skill_slug(slug, spec) or ROSTER_SKILL
    if playbook.types.get(target_type) is not None:
        return f"the `[types.{target_type}]` lane in `{PLAYBOOK_OVERRIDE_FILENAME}`"
    return f"`{PLAYBOOK_OVERRIDE_FILENAME}`"


def seeded_view_names(item_type: str, slug: str, spec: WorkflowSpec) -> frozenset[str]:
    """The view name(s) a document of *item_type* named *slug* is seeded with, gated on the
    view still being declared — :func:`roster_body_view_name` for a role or skill,
    :func:`template_seeded_view_names` for every other type. Type and slug only, never the
    host's content, so the check tier can call this before frontmatter ever parses."""
    if item_type in (ROSTER_ROLE, ROSTER_SKILL):
        return frozenset(
            n for n in (roster_body_view_name(item_type, slug, spec),) if n is not None
        )
    return frozenset(n for n in template_seeded_view_names(item_type, spec) if n in spec.views)


def view_placement_invocation(
    item_type: str, addr: int | str, verb: Literal["add", "disable"], name: str
) -> str:
    """The real ``sq … view add|disable <name>`` invocation for a document of *item_type*
    addressed by *addr* (slug for a role/skill, item number otherwise) — there is no bare
    ``sq view add``/``sq view disable``. The one place a message composes this, so it can
    never spell out a command form that does not exist."""
    if item_type == ROSTER_ROLE:
        return f"sq role {addr} view {verb} {name}"
    if item_type == ROSTER_SKILL:
        return f"sq skill {addr} view {verb} {name}"
    return f"sq {item_type} {addr} view {verb} {name}"


def clear_roster_body_cmd(item_type: str, slug: str, n: int | None, spec: WorkflowSpec) -> str:
    """The real, filled-in command that clears a roster host's body text, once its view is
    dropped from ``[selected]`` (what lifts the roster write refusal). A skill uses its own
    ``body`` verb; a role has none, so it's a single-event ``sq import -`` instead. The one
    derivation both check remedies that need this compose through, so they never disagree."""
    if item_type == ROSTER_SKILL:
        return f'sq skill {slug} body -m "" --force'
    if n is None:
        return (
            f'echo \'{{"op":"body","target":"<see sq role {slug} show for its id>",'
            '"body":"","force":true}}\' | sq import -'
        )
    item_id = format_item_id(spec.items[item_type].prefix, n, DISPLAY_ID_PADDING)
    event = json.dumps({"op": "body", "target": item_id, "body": "", "force": True, "as": slug})
    return f"echo '{event}' | sq import -"


# --------------------------------------------------------------------------- placement


def view_tag_states(region: str, name: str) -> set[bool]:
    """Every state *name*'s view tag currently carries in *region* — empty, one state, or two
    for a conflicting pair. Answers "what state does it render as", not "how many copies"; use
    :func:`view_tag_settled` to check whether placing a tag would be a no-op."""
    _prose, parts = _region_view_tags(region)
    return {p.disabled for p in parts if p.name == name}


def view_tag_settled(region: str, name: str, *, disabled: bool) -> bool:
    """Whether *region* already carries exactly one copy of *name*'s tag in *disabled*'s
    state — the "nothing to do" condition ``view add``/``view disable`` gate their no-op
    return on. Stricter than :func:`view_tag_states`: a same-state duplicate must fall through
    to placement, never read as already settled."""
    _prose, parts = _region_view_tags(region)
    matches = [p for p in parts if p.name == name]
    return len(matches) == 1 and matches[0].disabled == disabled


def strip_view_tags(text: str) -> str:
    """*text* with every view tag stripped, each together with its own line — so a tag's state
    or location never by itself makes a body count as authored when the authored-content guard
    compares through this."""
    stripped, _tags = _region_view_tags(text)
    return stripped


def _region_view_tags(region: str) -> tuple[str, list[markers.ViewTagParts]]:
    """*region* with every view tag — enabled or disabled, named or not — stripped together
    with its own line, and the parsed tags taken out, in file order (duplicates included). The
    read half of :func:`place_view_tags`, built on
    :func:`~squads._sections.strip_marker_lines`."""
    stripped, raw = strip_marker_lines(region, lambda tag: markers.view_tag_parts(tag) is None)
    parts = [p for tag in raw if (p := markers.view_tag_parts(tag)) is not None]
    return stripped, parts


def reinstate_absent_body_region(text: str) -> str | None:
    """*text* with a fresh ``sq:body``/``sq:body:end`` pair inserted right after the
    frontmatter, when *text* carries neither marker at all. Reclaims only the leading run of
    view tags, plus — if present — exactly one heading line immediately followed by the real
    ``sq:discussion`` marker; anything else (real prose, or a heading not immediately bounding
    that marker) refuses by returning ``None`` rather than guessing, the same as when there is
    no frontmatter to anchor the search from. A caller getting ``None`` back must leave the
    file untouched and never raise."""
    if get_section(text, markers.BODY) is not None:
        return None
    _fm, rest = split_frontmatter(text)
    if rest == text:  # no frontmatter at all — nothing to anchor the search from
        return None
    fm_len = len(text) - len(rest)
    pos = 0
    next_marker_start = len(rest)
    stop_raw: str | None = None
    for raw, start, end in iter_marker_spans(rest):
        if rest[pos:start].strip("\n \t") or markers.view_tag_parts(raw) is None:
            next_marker_start = start
            stop_raw = raw
            break
        line_end = rest.find("\n", end)
        pos = line_end + 1 if line_end != -1 else len(rest)
    else:
        next_marker_start = len(rest)
    after = rest[pos:next_marker_start].strip("\n \t")
    if after:
        # A heading is only ever the discussion region's own — never accepted on the strength
        # of its text or its mere presence — when *after* reduces to exactly **one** non-blank
        # line, that line is a heading, and the very next marker reached is that region's own
        # open tag. An author's own body can itself start with a heading and run on for several
        # more lines before a real "## Discussion" of its own — the single-line requirement is
        # what tells "just the discussion heading, nothing else in between" apart from that
        # shape, which the first-character check alone cannot: it would otherwise pass on the
        # strength of the trailing "## Discussion" a role's own multi-line prose still ends in.
        after_lines = [line for line in after.splitlines() if line.strip()]
        is_discussion_heading = (
            len(after_lines) == 1
            and after_lines[0].lstrip().startswith("#")
            and stop_raw == f"{markers.PREFIX}{markers.DISCUSSION}"
        )
        if not is_discussion_heading:
            return None
    boundary = fm_len + pos
    inner = text[fm_len:boundary].strip("\n")
    return (
        text[:fm_len]
        + markers.open_marker(markers.BODY)
        + "\n"
        + (f"{inner}\n" if inner else "")
        + markers.close_marker(markers.BODY)
        + "\n"
        + text[boundary:]
    )


class ConflictingViewStateError(SquadsError):
    """:func:`place_view_tags`'s own refusal when one view's tags disagree on state (an
    enabled copy and a disabled copy both present) — a distinct type so a caller that must
    catch it apart from every other :class:`SquadsError` can."""


def place_view_tags(
    region: str,
    edit: str | None,
    *,
    append: bool = False,
    seeded: frozenset[str],
    spec: WorkflowSpec,
    item_type: str,
    addr: int | str,
    force: tuple[str, bool] | None = None,
) -> str:
    """The one re-placement routine every ``sq:body`` writer drives: strips every view tag out
    of *region*, applies the prose edit, and re-inserts one tag per view at its declared
    position and prior state, plus any *seeded* view that was missing — so no caller inserts,
    removes or moves a tag on its own. A tag mirrors whatever separator already sat at its
    landing spot (never manufacturing a blank line), which is what makes stripping it back out
    the exact inverse; conflicting states raise :class:`ConflictingViewStateError`, and *force*
    is how ``view add``/``view disable`` settle that without tripping it."""
    prose, existing = _region_view_tags(region)
    prose = prose.strip("\n")
    if edit is not None:
        prose = (f"{prose}\n\n{edit}" if prose else edit) if append else edit

    final, first_seen = _resolve_final_states(existing, seeded, force, item_type, addr)
    decl_order = {name: i for i, name in enumerate(spec.views)}
    declared = [n for n in final if n in decl_order]
    undeclared = sorted(
        (n for n in final if n not in decl_order),
        key=lambda n: first_seen.get(n, len(existing)),
    )

    name_cut_points = _resolve_cut_points(prose, declared, decl_order, spec)
    tag_cut_points = {
        off: [markers.open_marker(markers.view_tag(n, disabled=final[n])) for n in names]
        for off, names in name_cut_points.items()
    }
    atoms = _build_segments(prose, tag_cut_points)
    atoms.extend(
        (markers.open_marker(markers.view_tag(n, disabled=final[n])), len(prose), len(prose))
        for n in undeclared
    )
    seps = _boundary_separators(prose, atoms)
    out = atoms[0][0] if atoms else ""
    for (text, _left, _right), sep in zip(atoms[1:], seps, strict=True):
        out += sep + text
    return out


def _resolve_final_states(
    existing: list[markers.ViewTagParts],
    seeded: frozenset[str],
    force: tuple[str, bool] | None,
    item_type: str,
    addr: int | str,
) -> tuple[dict[str, bool], dict[str, int]]:
    """The final ``name -> disabled`` state map :func:`place_view_tags` re-inserts, plus each
    name's first-seen index in *existing* (used only to order the undeclared tags among
    themselves) — split out purely to keep that function under the complexity ceiling.

    Collapses same-state duplicates, raises :class:`ConflictingViewStateError` for a name
    carrying both states (unless *force* names it), inserts every *seeded* name absent so far
    as enabled, then applies *force* last so it always wins."""
    states: dict[str, set[bool]] = {}
    first_seen: dict[str, int] = {}
    for i, part in enumerate(existing):
        states.setdefault(part.name, set()).add(part.disabled)
        first_seen.setdefault(part.name, i)

    final: dict[str, bool] = {}
    for name, seen in states.items():
        if force is not None and force[0] == name:
            continue
        if len(seen) > 1:
            add_cmd = view_placement_invocation(item_type, addr, "add", name)
            disable_cmd = view_placement_invocation(item_type, addr, "disable", name)
            raise ConflictingViewStateError(
                f"{item_type} {addr}: {markers.PREFIX}{markers.view_tag(name)} carries both an "
                f"enabled and a disabled tag; settle its state with `{add_cmd}` or "
                f"`{disable_cmd}`"
            )
        final[name] = next(iter(seen))
    for name in seeded:
        final.setdefault(name, False)
    if force is not None:
        final[force[0]] = force[1]
    return final, first_seen


def _resolve_cut_points(
    prose: str,
    declared: list[str],
    decl_order: dict[str, int],
    spec: WorkflowSpec,
) -> dict[int, list[str]]:
    """Every declared view's resolved insertion offset into *prose*, grouped by offset and
    ordered by declaration order within each group. ``"top"`` is offset 0, ``"bottom"`` (or a
    non-matching ``"after(<regex>)"``) is ``len(prose)``, and a matching ``"after(<regex>)"``
    resolves right after the line holding the match's last character."""
    entries: list[tuple[int, int, str]] = []
    for name in declared:
        pos = parse_view_position(spec.views[name].position)
        if pos.kind == "top":
            offset = 0
        elif pos.kind == "bottom" or pos.pattern is None:
            offset = len(prose)
        else:
            m = pos.pattern.search(prose)
            if m is None:
                offset = len(prose)
            else:
                anchor = m.end() - 1 if m.end() > m.start() else m.end()
                nl = prose.find("\n", anchor)
                offset = nl + 1 if nl != -1 else len(prose)
        entries.append((offset, decl_order[name], name))
    entries.sort(key=lambda e: (e[0], e[1]))

    cut_points: dict[int, list[str]] = {}
    for offset, _idx, name in entries:
        cut_points.setdefault(offset, []).append(name)
    return cut_points


#: A leading/trailing run of newline-delimited blank lines, whitespace-only lines included —
#: the same shape :func:`_local_separator` reads by character count, spelled as a regex here
#: because :func:`_build_segments` strips a whole run at once rather than counting it.
_LEADING_BLANK_RUN_RE = re.compile(r"^(?:[ \t]*\n)+")
_TRAILING_BLANK_RUN_RE = re.compile(r"(?:\n[ \t]*)+$")


def _build_segments(prose: str, cut_points: dict[int, list[str]]) -> list[tuple[str, int, int]]:
    """*prose* sliced at every offset in *cut_points* and interleaved with the tag lines
    declared there, as an ordered list of ``(text, left_offset, right_offset)`` atoms. Each
    prose slice is trimmed of its own leading/trailing separator (a run of newlines,
    whitespace-only lines included) — never interior content — and an empty slice contributes
    no atom at all."""
    atoms: list[tuple[str, int, int]] = []
    prev = 0
    for off in sorted(set(cut_points) | {0, len(prose)}):
        if off > prev:
            slice_ = _LEADING_BLANK_RUN_RE.sub("", prose[prev:off])
            slice_ = _TRAILING_BLANK_RUN_RE.sub("", slice_)
            if slice_:
                atoms.append((slice_, prev, off))
        prev = off
        if off in cut_points:
            atoms.extend((tag, off, off) for tag in cut_points[off])
    return atoms


def _blank_run_length(text: str, offset: int, *, forward: bool, limit: int = 2) -> int:
    """How many newlines bound *offset* on one side, up to *limit* — a line holding only
    spaces/tabs between two newlines counts as blank too, the same as an empty line, since
    that is how Markdown (and an author's own eye) reads it."""
    count = 0
    pos = offset if forward else offset - 1
    step = 1 if forward else -1
    n = len(text)
    while count < limit:
        scan = pos
        while 0 <= scan < n and text[scan] in " \t":
            scan += step
        if not (0 <= scan < n and text[scan] == "\n"):
            break
        count += 1
        pos = scan + step
    return count


def _local_separator(prose: str, offset: int) -> str:
    """The separator a tag placed at *offset* shares with the prose beside it, mirroring
    whatever newline run already sat there — a run of 2 or more newlines (a blank line, or
    several, whitespace-only lines included) collapses to exactly one blank line; a single
    newline (no blank line at all) stays a single newline."""
    lead = _blank_run_length(prose, offset, forward=False)
    trail = _blank_run_length(prose, offset, forward=True)
    return "\n\n" if lead + trail >= 2 else "\n"


def _boundary_separators(prose: str, atoms: list[tuple[str, int, int]]) -> list[str]:
    """One separator per gap between consecutive *atoms*: always one blank line between two
    tags, :func:`_local_separator` between a tag and prose at an interior cut point, and one
    blank line at the region's own edges (nothing there to mirror either way)."""
    seps: list[str] = []
    for (_lt, _ll, left_right), (_rt, right_left, _rr) in pairwise(atoms):
        boundary = left_right  # == right_left, by construction
        left_is_tag = _ll == left_right
        right_is_tag = right_left == _rr
        if left_is_tag and right_is_tag:
            seps.append("\n\n")
        elif 0 < boundary < len(prose):
            seps.append(_local_separator(prose, boundary))
        else:
            seps.append("\n\n")
    return seps


def _keep_unless_disabled_view_tag(raw: str) -> bool:
    """False only for a disabled view tag — what ``strip_marker_lines`` should remove."""
    parts = markers.view_tag_parts(raw)
    return parts is None or not parts.disabled


def expand_view_tags(
    text: str,
    item: Item,
    db: SquadsDB,
    spec: WorkflowSpec,
    playbook: PlaybookSpec,
    roster: RosterProvider,
    squad_dir: Path | None,
    squad_dir_display: str | None,
) -> str:
    """*text* with every well-formed ``sq:view:<name>`` tag replaced by that view's rendered
    output, in place. A disabled tag is removed the way ``strip_marker_lines`` removes a
    marker, never left as a blank line; an unresolvable enabled tag stays literal. Read-only,
    and pads a rendered view with a blank line against neighbouring prose."""
    text, _ = strip_marker_lines(text, _keep_unless_disabled_view_tag)
    segments: list[tuple[str, str]] = []
    pending = ""
    last = 0
    changed = False
    for raw, start, end in iter_marker_spans(text):
        # `iter_marker_spans`/`find_markers` emit the tag with its "sq:" prefix still on (e.g.
        # "sq:view:milestone_rollup") — `view_tag_parts` accepts that on-disk form directly, no
        # hand-strip needed at this call site.
        parts = markers.view_tag_parts(raw)
        if parts is None:
            continue  # not a view tag — left literal
        name = parts.name
        reason = resolve_view_target(name, item.type, spec, playbook)
        if reason is not None:
            continue  # undeclared, template missing, or source inapplicable — left literal
        view = spec.views[name]
        result = resolve_source(view, name, item, db, spec, playbook, roster, squad_dir)
        rendered = _render_resolved_source_or_raise(name, result, item, spec, squad_dir_display)
        pending += text[last:start]
        segments.append(("literal", pending))
        # Stripped of its own leading/trailing newlines so the padding this function adds is
        # the only source of blank lines at its edges — a template ending in its own trailing
        # newline must not stack with that padding into a double blank line.
        segments.append(("rendered", rendered.strip("\n")))
        pending = ""
        last = end
        changed = True
    if not changed:
        return text
    pending += text[last:]
    segments.append(("literal", pending))
    return _assemble_padded_expansion(segments)


def _pad_between(chunk: str, *, pad_before: bool, pad_after: bool) -> str:
    """Normalise *chunk* to a full blank line on each side that borders a rendered view, never
    at a body edge and never stacking beyond one blank line."""
    if pad_before:
        chunk = chunk.lstrip("\n")
    if pad_after:
        chunk = chunk.rstrip("\n")
    if not chunk:
        return "\n\n" if (pad_before and pad_after) else ""
    if pad_before:
        chunk = "\n\n" + chunk
    if pad_after:
        chunk = chunk + "\n\n"
    return chunk


def _assemble_padded_expansion(segments: list[tuple[str, str]]) -> str:
    """Join alternating literal/rendered segments, padding each literal one against any
    rendered neighbour so a view never merges into surrounding prose."""
    out: list[str] = []
    for i, (kind, content) in enumerate(segments):
        if kind == "rendered":
            out.append(content)
            continue
        pad_before = i > 0 and segments[i - 1][0] == "rendered"
        pad_after = i < len(segments) - 1 and segments[i + 1][0] == "rendered"
        out.append(_pad_between(content, pad_before=pad_before, pad_after=pad_after))
    return "".join(out)


def _render_resolved_source_or_raise(
    view_name: str,
    result: SourceResult,
    item: Item,
    spec: WorkflowSpec,
    squad_dir_display: str | None,
) -> str:
    """:func:`render_source_view`, with a template failure under ``StrictUndefined``
    translated into a :class:`SquadsError` naming *item* — the engine-defect half of
    read-time expansion's two failure modes (see :func:`expand_view_tags`), for any of the
    six source kinds. :func:`render_source_view` already reaches
    :func:`~squads._rendering._engine.render`, which is what turns the underlying
    ``jinja2.TemplateError`` into a bare :class:`SquadsError`; this catches that specific,
    engine-translated failure and re-raises with *item* named, so read-time expansion's error
    names the item the tag was read from, not just the template. An unresolvable tag never
    reaches here: the caller gates on :func:`resolve_view_target` first, so
    :class:`ViewTemplateMissingError` is not expected in ordinary operation, and — because it
    is caught and re-raised unchanged rather than falling into the broader
    :class:`SquadsError` clause below — is let through unchanged on the rare race where the
    template disappears between the two checks."""
    try:
        return render_source_view(view_name, result, item, spec, squad_dir_display)
    except ViewTemplateMissingError:
        raise
    except SquadsError as exc:
        raise SquadsError(f"view {view_name!r} failed to render on {item.id}: {exc}") from exc
