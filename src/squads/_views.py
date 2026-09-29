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

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from squads._backends._base import RoleView
from squads._errors import SquadsError
from squads._interactions import item_type_for_skill_slug
from squads._interactions._models import ItemPlaybookSpec, PlaybookSpec
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import Item, effective_prefix, ref_id_matches, split_ref
from squads._models._subentity import SubEntity
from squads._paths import number_for_id
from squads._rendering._engine import creation_template_name, has_template, render, template_source
from squads._roles._catalog import RoleDef
from squads._roles._resolver import resolve_role_for_item
from squads._sections import get_section, iter_marker_spans
from squads._workflow._models import (
    ROSTER_ROLE,
    ROSTER_SKILL,
    ViewSpec,
    WorkflowSpec,
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


#: The three states an empty ``sq:body`` region naming a placement tag can be in, from the
#: operator's point of view — see :func:`empty_body_hint_state`.
type EmptyBodyHintState = Literal[
    "view_undeclared", "declared_drift_outstanding", "declared_no_drift"
]


def empty_body_hint_state(
    name: str, spec: WorkflowSpec, *, drift_outstanding: bool
) -> EmptyBodyHintState:
    """Which of three states explains an empty ``sq:body`` region whose seeded placement tag
    names view *name* — the single predicate ``sq role show`` and ``sq skill show`` each read
    in place of their own ad hoc, independently duplicated "is the view declared" boolean,
    so the two groups' empty-body hints cannot drift apart about what remedy is actually true.

    Two questions, not one. "Is *name* declared in *spec*'s ``[views]``" alone answers only
    whether the tag can ever resolve — it says nothing about whether ``sq sync`` specifically
    is what will populate it, because ``sq sync``'s only trigger for backfilling this exact
    region is an outstanding *version* drift
    (``MaintenanceMixin._backfill_roster_body_tags``, reached only when
    :func:`~squads._models._schema.version_drifted` is true). A declared view with no drift
    outstanding is a state ``sq sync`` provably cannot help: the guard that would seed the tag
    never runs, and ``_write_managed_skill``/the role-creation writer both leave an
    already-existing region byte-untouched by design. *drift_outstanding* is not recomputed
    here — the caller reads it once (the same comparison ``sync()`` itself gates the backfill
    on) and passes it in, so this stays a pure classification with no I/O of its own.

    Returns:
    - ``"view_undeclared"`` — *name* is not in *spec*'s ``[views]``; no remedy renders this
      empty body from that view at all.
    - ``"declared_drift_outstanding"`` — *name* is declared and a version drift is still
      outstanding; ``sq sync`` is genuinely the fix, because this is the one condition under
      which its backfill reaches this region.
    - ``"declared_no_drift"`` — *name* is declared but there is no drift left to trigger the
      backfill; ``sq sync`` is a no-op against this body. The real remedies are ``sq repair``
      (when the region might be carrying unrecognised marker-shaped content) or explicitly
      re-adding the tag (when the region is genuinely untagged), not the command this state
      exists to stop naming.
    """
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
    """Whether *text* carries at least one well-formed ``sq:view:<name>`` tag.

    Computed from the body text alone — no index, no spec, no item — the same span-and-name
    check :func:`expand_view_tags` itself does, exposed separately so the one shared body-read
    boundary (:meth:`~squads._services._items.ItemsMixin.read_body`) can decide whether an
    index load and an expansion call are needed at all *before* paying either cost. The
    overwhelming majority of bodies carry no tag, so this is the common case's fast path, not
    a redundant pre-check.
    """
    return any(markers.view_tag_name(raw) is not None for raw, _, _ in iter_marker_spans(text))


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
    Recognises a tag through :func:`~squads._models._markers.view_tag_name` over the same
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
        name
        for raw, _start, _end in iter_marker_spans(body)
        if (name := markers.view_tag_name(raw)) is not None
    )


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
    """*text* (an item's ``sq:body`` region content) with every well-formed
    ``sq:view:<name>`` tag replaced by that view's rendered output, in place — the
    mechanism behind the one shared body-read boundary
    (:meth:`squads._services._items.ItemsMixin.read_body`) every read surface (``sq show``,
    ``--raw``, ``--json``'s body field, the TUI, the operator pane, the skill read) inherits
    expansion from, with no per-surface reimplementation.

    *playbook*/*roster*/*squad_dir*/*squad_dir_display* only matter to a
    ``role``/``playbook``/``self``-sourced tag — a ``ref``/``subtree``/``subentity`` tag's
    expansion is untouched by any of the four (the byte-identical promise for the three
    relation kinds). The caller supplies all four regardless of which kind a given tag turns
    out to name, since a body can carry tags of more than one kind. *squad_dir* and
    *squad_dir_display* are two different values carried for two different jobs, not one value
    threaded twice: *squad_dir* is the resolved absolute :class:`Path`, handed to
    :func:`resolve_source` because :func:`_resolve_role_source` needs it to locate a project's
    ``.overrides/roles/`` on disk; *squad_dir_display* is the configured ``squad_dir`` string
    (:class:`~squads._models._config.SquadsConfig`'s own field), handed to
    :func:`_render_resolved_source_or_raise` because that is the value a template's
    ``{{ squad_dir }}`` means — see :func:`render_source_view`. Collapsing them back into one
    parameter is the regression this split exists to keep unreachable: a nested configured
    value (``docs/squad``) is not recoverable from the Path by taking its last segment.
    *playbook* and both *squad_dir* values are free to hand over; *roster* is not (a disk read
    per live role), which is why it is a :data:`RosterProvider` here — a tag naming anything
    but ``playbook`` never forces it, and a body carrying more than one ``playbook`` tag forces
    it once, not once per tag, only when the caller's own callable is itself memoized
    (:meth:`~squads._services._items.ItemsMixin.read_body` is).

    **Single pass, by construction — not by a depth counter.** Tag spans are found once
    against *text* exactly as given (:func:`~squads._sections.iter_marker_spans`) and the
    result is built from those original positions; the loop never re-matches inside a
    replacement it just inserted. Rendered view output is therefore never itself scanned for
    tags — a well-formed tag appearing inside a view's own presentation stays literal text.
    There is no second expansion site to recurse through, so there is nothing here for a
    depth limit or a visited set to guard.

    **The two failure modes stay distinct, deliberately.** A tag *spec* cannot resolve against
    *item*'s type — undeclared, template missing, or a declared source that cannot apply to
    this host (:func:`resolve_view_target`) — is left exactly as it appears in *text*: the read
    still succeeds, because reads must keep working on a broken corpus; ``sq check``'s
    file-scan finding is what reports it, through that same predicate this function gates on.
    A *resolvable* view whose template raises under Jinja's ``StrictUndefined`` is an engine or
    template defect, not corpus state: it propagates unchanged as :class:`SquadsError`, never
    swallowed and never degraded to an empty expansion.

    Read-only, and it must stay that way: nothing here writes anything, and the one caller
    that mutates the body region (``ItemsMixin.set_body``'s ``mutate`` closure) reads the
    region directly rather than through this function or :meth:`~squads._services._items
    .ItemsMixin.read_body` — expanded bytes must never reach disk.
    """
    pieces: list[str] = []
    last = 0
    changed = False
    for raw, start, end in iter_marker_spans(text):
        # `iter_marker_spans`/`find_markers` emit the tag with its "sq:" prefix still on (e.g.
        # "sq:view:milestone_rollup") — `view_tag_name` accepts that on-disk form directly, no
        # hand-strip needed at this call site.
        name = markers.view_tag_name(raw)
        if name is None:
            continue  # not a view tag — left literal
        reason = resolve_view_target(name, item.type, spec, playbook)
        if reason is not None:
            # undeclared, template missing, or source inapplicable — left literal; sq check
            # reports it
            continue
        view = spec.views[name]
        result = resolve_source(view, name, item, db, spec, playbook, roster, squad_dir)
        rendered = _render_resolved_source_or_raise(name, result, item, spec, squad_dir_display)
        pieces.append(text[last:start])
        pieces.append(rendered)
        last = end
        changed = True
    if not changed:
        return text
    pieces.append(text[last:])
    return "".join(pieces)


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
