"""Derived views: resolve a declared ``[views]`` entry's source and render it.

A view has three parts and no fourth: **source** (what to resolve — refs of a declared kind
pointing at the item, a sub-entity collection, a subtree, the item's own merged role
definition, a type's playbook lane, or the item itself, resolved by :func:`resolve_source`),
**projection** (for the three *relation* kinds only — which fields, how grouped, how ordered —
produced by :func:`project`, never a presentation decision; the three non-relation kinds have
no projection step at all, see below), and **presentation** (a Jinja2 template resolved by
:func:`render_view`/:func:`render_source_view` at ``templates/views/<name>.md.j2`` — the
view's own declared name, never a separate stored field). Every view is computed on request;
nothing here ever writes into an item body.

Six source kinds split into two families, and the split runs through every function below:
``ref``/``subtree``/``subentity`` are **relations** — a join over other items, normalised to
:class:`_RawRecord` and projected through :func:`project` into a :class:`Projection` a
template iterates as rows. ``role``/``playbook``/``self`` are **not** relations — each
resolves to its own native shape (a ``RoleDef``, a :class:`PlaybookSource`, the host item
itself) that a template reads directly; forcing one through :func:`project` would be the exact
flattening the source-widening decision retired the middle layer to stop doing, so none of
them ever reaches it.
``sq workflow view --json`` dispatches per source kind
(``squads._cli._workflow_cmd._view_json_payload``), serializing each resolved value in its own
existing shape rather than through a shared envelope; :func:`projection_json` is one remaining
caller's contract, not that dispatch point — the type-attached ``items.<type>.views`` surface
(``build_item_json``'s ``views`` key) still resolves a relation kind through it, since that
surface has no serializer for anything else and never attaches a non-relation kind (see
:data:`~squads._workflow._models.VIEW_BASE_FIELDS_BY_SOURCE`, checked at spec load).

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
from squads._badges import badge_parts, resolve_collection
from squads._errors import InvalidIdError, SquadsError
from squads._interactions import item_type_for_skill_slug
from squads._interactions._models import ItemPlaybookSpec, PlaybookSpec
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import Item, effective_prefix, prefix_from_id, ref_id_matches, split_ref
from squads._models._subentity import SubEntity
from squads._paths import number_for_id
from squads._rendering._engine import has_template, render
from squads._roles._catalog import RoleDef
from squads._roles._resolver import resolve_role_for_item
from squads._sections import iter_marker_spans
from squads._workflow._models import (
    ROSTER_ROLE,
    ROSTER_SKILL,
    VIEW_BASE_FIELDS_BY_SOURCE,
    ViewSpec,
    WorkflowSpec,
    subentity_source_reason,
)

JsonValue = str | bool | dict[str, str] | None

#: A zero-argument roster provider — deferred, so a caller that already has the roster in hand
#: (or a cheap way to get it) pays nothing for a body/view whose source never looks at it.
#: ``playbook`` is the one source kind that ever calls this; the other five never do (see
#: :func:`resolve_source`, :func:`expand_view_tags`), so threading a callable rather than a
#: materialised ``list[RoleView]`` is what keeps their cost at zero rather than "however much
#: the caller happened to precompute". A caller invoked more than once per roster (a body
#: carrying more than one ``playbook`` tag) is expected to memoize its own callable rather than
#: relying on this type to do it — see ``ItemsMixin.read_body``.
type RosterProvider = Callable[[], list[RoleView]]

#: The three relation source kinds — the ones :data:`VIEW_BASE_FIELDS_BY_SOURCE` declares a
#: field grammar for, and the only ones :func:`project` ever runs over. Membership in that
#: dict *is* the family test everywhere below (never a hand-duplicated tuple literal), so
#: adding a future relation kind only ever means adding one entry there.
RELATION_KINDS = frozenset(VIEW_BASE_FIELDS_BY_SOURCE)


@dataclass(frozen=True)
class Cell:
    """One resolved field value on one record: a presentation-ready ``text`` (what every
    template needs, regardless of the field's type — a badge already carries its emoji), and a
    structured ``json_value`` for the ``--json`` contract (a plain scalar for a text field, a
    ``{code, label, emoji}`` object for a badge field, ``None`` for an absent value)."""

    text: str
    json_value: JsonValue


@dataclass(frozen=True)
class ViewFieldMeta:
    """One projected column's metadata — travels with the payload so a client can render an
    unfamiliar view without special-casing it."""

    code: str
    label: str
    type: str  # "text" | "badge"


@dataclass(frozen=True)
class ViewRecord:
    values: dict[str, Cell]


@dataclass(frozen=True)
class ViewGroup:
    """One group of records. ``key`` is ``None`` for an ungrouped view's single implicit
    group — the top-level shape stays ``groups`` either way, so a client never special-cases
    "this view happens to be ungrouped"."""

    key: JsonValue
    records: list[ViewRecord]

    @property
    def count(self) -> int:
        """The one place ``len(records)`` is computed — both documented consumers of a
        projection (a template's ``group.count`` and ``--json``'s ``"count"``) read this
        property, so they can never drift apart the way they did before it existed."""
        return len(self.records)


@dataclass(frozen=True)
class Projection:
    fields: list[ViewFieldMeta]
    group_by: str | None
    groups: list[ViewGroup]

    def records(self) -> list[ViewRecord]:
        return [r for g in self.groups for r in g.records]


@dataclass(frozen=True)
class _RawRecord:
    """A source record normalised to one shape before field projection — an ``Item`` or a
    ``SubEntity``, whichever the source produced. ``kind`` is the record's own item type (a
    ref/subtree source) or the declared sub-entity kind it was resolved under (a subentity
    source) — the namespace :func:`squads._badges.resolve_collection` looks a badge field up
    in. ``story``/``type`` sit outside every base-attribute set their source kind doesn't
    allow (:data:`~squads._workflow._models.VIEW_BASE_FIELDS_BY_SOURCE`), so a field
    resolution never reads them there."""

    identity: str
    kind: str
    status: str
    assignee: str | None
    title: str
    story: str | None
    badge_value: Callable[[str], str | None]


def _record_from_item(it: Item) -> _RawRecord:
    return _RawRecord(
        identity=it.id,
        kind=it.type,
        status=it.status,
        assignee=it.assignee,
        title=it.title,
        story=None,
        badge_value=it.badge_value,
    )


def _record_from_subentity(sub: SubEntity, kind: str) -> _RawRecord:
    return _RawRecord(
        identity=sub.local_id,
        kind=kind,
        status=sub.status,
        assignee=sub.assignee,
        title=sub.title,
        story=sub.story,
        badge_value=sub.badge_value,
    )


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


#: Every shape :func:`resolve_source` can return — a relation's flat record list for
#: ``ref``/``subtree``/``subentity``, or one of the three new kinds' own native value.
type SourceResult = list[_RawRecord] | RoleDef | PlaybookSource | Item


def _resolve_subentity_source(view: ViewSpec, item: Item) -> list[_RawRecord]:
    """*item*'s own sub-entity collection of the kind *view* projects.

    Carries no applicability check and raises nothing: whether this kind applies to *item*'s
    type is a precondition, decided once by :func:`resolve_view_target` (the quiet consumers —
    placement, read-time expansion, the file scan) or by :func:`resolve_source` (the loud,
    direct-question consumer — ``sq workflow view``) *before* either ever calls this function.
    A resolver may not raise for a condition its kind's predicate could already have decided —
    reached with an incompatible *item* only if a caller skipped that gate, in which case
    ``item.subentities`` is simply empty and this returns ``[]``,
    which is the correct answer to "no records", not a failure (see the emptiness clause on
    :func:`resolve_view_target`)."""
    kind = view.source.name
    assert kind is not None, "a 'subentity' source's name is validated non-None at spec load"
    return [_record_from_subentity(s, kind) for s in item.subentities]


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


def _resolve_ref_source(
    view: ViewSpec, item: Item, db: SquadsDB, spec: WorkflowSpec
) -> list[_RawRecord]:
    """Refs of the declared kind pointing at *item*, recovered by inverting stored forward
    edges — the same shape ``squads._services._refs.RefsMixin.refs_in`` computes, inlined here
    so it shares the one index load the caller already made rather than loading a second
    time."""
    target_kind = view.source.name
    assert target_kind is not None, "a 'ref' source's name is validated non-None at spec load"
    default_kind = spec.default_ref_kind()
    target_prefix = effective_prefix(item.prefix)
    target_seq = item.sequence_id
    records: list[_RawRecord] = []
    for it in sorted(db.items.values(), key=lambda i: number_for_id(i.id)):
        for r in it.refs:
            rid, kind = split_ref(r)
            if (kind or default_kind) == target_kind and ref_id_matches(
                rid, target_prefix, target_seq
            ):
                records.append(_record_from_item(it))
                break
    return records


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


def _resolve_subtree_source(view: ViewSpec, item: Item, db: SquadsDB) -> list[_RawRecord]:
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
    return [_record_from_item(i) for i in matched]


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
    Asks through :func:`~squads._workflow._models.subentity_source_reason`, the same function
    ``_check_item_views`` (the load-time attached-view check) composes its own reason from, so
    the two can never quietly word this comparison differently."""
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
        f"view {view_name!r} projects a role definition, but {item_type!r} is not the role "
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
    already-validated spec). A relation kind (``ref``/``subtree``/``subentity``) returns a
    flat ``list[_RawRecord]``, ready for :func:`project`; ``role``/``playbook``/``self`` each
    return their own native shape and never reach :func:`project` at all — see the module
    docstring.

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
    view <name> <id>``, via :meth:`~squads._services._views.ViewsMixin.resolve_view`/
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


# --------------------------------------------------------------------------- field resolution


def _delivery_target(kind: str, spec: WorkflowSpec) -> str | None:
    """The status *kind*'s own declared lifecycle treats as reaching its goal — the
    happy-path settled terminal (:meth:`WorkflowSpec.first_settled_status`, which resolves
    an item type or a sub-entity kind against its own declared ``lifecycle``). Never a
    literal status name: a custom lifecycle gets the same answer its own declared spine
    gives, exactly as :func:`squads._badges.status_badge` and friends already resolve
    per-spec rather than per-literal. ``None`` when *kind* names neither namespace, or its
    lifecycle reaches no settled status at all — no record legitimately hits either case."""
    return spec.first_settled_status(kind)


def _is_delivered(rec: _RawRecord, spec: WorkflowSpec) -> bool:
    """Whether *rec* reached its own kind's delivery target — settled and on the happy-path
    spine, not merely settled. This is what tells a genuinely finished record (``Done``,
    ``Accepted``, ``Verified`` — whatever a lifecycle's own spine terminal is named) from one
    that is settled some *other* way (``Cancelled``, ``Superseded`` — off the spine): both
    are ``settled``, only one is ``delivered``. Used by the bundled roll-up (and any adopter
    view) instead of a bare ``group.key == "done"`` check, which silently treats every
    settled-but-not-delivered record as still outstanding.

    Kept as its own comparison against :func:`_delivery_target` rather than delegating to
    :meth:`WorkflowSpec.is_delivered` (the bare-``(kind, status)`` generalisation, for a
    template that has no ``_RawRecord`` to hand it): this function's own caller
    (:data:`_BASE_RESOLVERS`'s ``"delivered"`` entry, still backing the untouched
    ``ref``/``subtree``/``subentity`` projection path) is real, ongoing use of
    :func:`_delivery_target`, and a private module function pyright's strict mode would flag as
    dead the moment nothing calls it — delegating here would have deleted its only caller. The
    two are pinned to always agree by ``tests/unit/test_settled_versus_delivered_status.py``
    instead."""
    return rec.status == _delivery_target(rec.kind, spec)


#: Base record attributes resolved directly off :class:`_RawRecord` / the active spec, never
#: off a declared badge field — the counterpart, at the resolving end, of
#: ``VIEW_BASE_FIELDS_BY_SOURCE`` at the declaring end. A code outside this set is resolved as
#: a badge field instead (already refused at load if it names neither). ``"settled"``/
#: ``"delivered"`` are the two booleans; every other entry is a plain string-or-``None``.
_BASE_RESOLVERS: dict[str, Callable[[_RawRecord, WorkflowSpec], str | bool | None]] = {
    "id": lambda r, _spec: r.identity,
    "type": lambda r, _spec: r.kind,
    "status": lambda r, _spec: r.status,
    "status_role": lambda r, spec: spec.status_role(r.status),
    "assignee": lambda r, _spec: r.assignee,
    "title": lambda r, _spec: r.title,
    "story": lambda r, _spec: r.story,
    "settled": lambda r, spec: spec.role_for(r.status).settled,
    "delivered": _is_delivered,
}


def _badge_cell(kind: str, code: str, raw: str, spec: WorkflowSpec) -> Cell:
    coll_code = resolve_collection(kind, code, spec)
    emoji, badge_code, label = badge_parts(coll_code, raw, spec)
    json_value = {"code": badge_code, "label": label, "emoji": emoji}
    return Cell(text=f"{emoji} {label}", json_value=json_value)


def _cell(rec: _RawRecord, code: str, spec: WorkflowSpec) -> Cell:
    base = _BASE_RESOLVERS.get(code)
    if base is not None:
        value = base(rec, spec)
        if isinstance(value, bool):
            # `value or ""` would collapse a real `False` into the same empty text an
            # absent value renders, and a client reading `.text` should see the boolean
            # spelled out rather than silently losing it.
            return Cell(text="true" if value else "false", json_value=value)
        return Cell(text=value or "", json_value=value)
    raw = rec.badge_value(code)
    if raw is None:
        return Cell(text="", json_value=None)
    return _badge_cell(rec.kind, code, raw, spec)


def _sort_key(
    rec_kind: str, code: str, cell: Cell, spec: WorkflowSpec
) -> tuple[int, int, int, str]:
    """Sort key for one cell of a declared ``order_by`` field, resolved against the field's
    declared vocabulary rather than its presentation string.

    - ``id`` orders by sequence number (:func:`~squads._paths.number_for_id`), not the
      formatted string — a ``ref``/``subtree`` source's own resolvers already produce that
      order, which sorting on the formatted string would discard. A record whose id carries
      no parseable number
      (a sub-entity's local id — a letter prefix immediately followed by a digit, no
      separating dash) falls back to its text rather than raising. **Mixed-type
      tie-break:** two records of different declared types can carry the very same
      sequence number, so the prefix breaks the tie — deliberate, so ``order_by = ["id"]``
      alone is still fully deterministic without also naming ``"type"`` first, the way the
      bundled roll-up does.
    - A badge field on a collection declaring ``ordered = true`` orders by the collection's
      declared position (mirrors ``ItemFilter._meets_min``'s own ranking). A badge field on
      an unordered collection, or a code the resolved collection doesn't recognise, falls
      back to ordering by its own code — today's behaviour, kept as the graceful degrade.
    - Everything else orders by its text, as before.

    Always a 4-tuple so one ``order_by`` pass never compares an ``int`` rank against a
    ``str`` fallback: a ``ref`` source's records can span types, and the same field code can
    resolve to an ordered collection for one type and an unordered one for another.
    ``major`` separates an absent cell from a present one; ``unranked`` is ``0`` when this
    function produced a real numeric rank and ``1`` when it can only fall back to text;
    exactly one of ``rank``/``fallback`` is meaningful per cell, the other left at its zero
    value, so the tuple shape — and the types at each position — never varies within one
    field."""
    v = cell.json_value
    if v is None:
        return (0, 0, 0, "")
    if code == "id":
        try:
            num = number_for_id(cell.text)
        except InvalidIdError:
            return (1, 1, 0, cell.text)
        return (1, 0, num, prefix_from_id(cell.text))
    if isinstance(v, dict):
        coll_code = resolve_collection(rec_kind, code, spec)
        coll = spec.collections.get(coll_code)
        badge_code = str(v.get("code", ""))
        if coll is not None and coll.ordered:
            order = [b.code for b in coll.badges]
            if badge_code in order:
                return (1, 0, order.index(badge_code), "")
        return (1, 1, 0, badge_code)
    return (1, 1, 0, str(v))


# --------------------------------------------------------------------------- projection


def project(view: ViewSpec, records: list[_RawRecord], spec: WorkflowSpec) -> Projection:
    """Records with typed fields, optionally grouped — identically shaped whichever source
    produced *records*. Makes no presentation decision: no template is touched
    here."""
    base_allowed = VIEW_BASE_FIELDS_BY_SOURCE[view.source.kind]
    field_meta = [
        ViewFieldMeta(
            code=f.code, label=f.label, type="text" if f.code in base_allowed else "badge"
        )
        for f in view.fields
    ]

    # `_sort_key` needs each record's own kind (badge-collection resolution is per
    # type/kind) — kept paired with its `ViewRecord` only for the sort below, then dropped.
    built_pairs: list[tuple[str, ViewRecord]] = [
        (rec.kind, ViewRecord(values={f.code: _cell(rec, f.code, spec) for f in view.fields}))
        for rec in records
    ]

    if view.order_by:
        for code in reversed(view.order_by):
            built_pairs.sort(key=lambda p, c=code: _sort_key(p[0], c, p[1].values[c], spec))

    built = [vr for _, vr in built_pairs]

    if view.group_by is None:
        groups = [ViewGroup(key=None, records=built)]
    else:
        buckets: dict[str, list[ViewRecord]] = {}
        bucket_key_repr: dict[str, JsonValue] = {}
        for rec in built:
            cell = rec.values[view.group_by]
            key_repr = "\0none" if cell.json_value is None else repr(cell.json_value)
            buckets.setdefault(key_repr, []).append(rec)
            bucket_key_repr[key_repr] = cell.json_value
        groups = [ViewGroup(key=bucket_key_repr[k], records=recs) for k, recs in buckets.items()]

    return Projection(fields=field_meta, group_by=view.group_by, groups=groups)


# --------------------------------------------------------------------------- output


def projection_json(projection: Projection) -> dict[str, object]:
    """A :class:`Projection`'s own JSON shape — field metadata + grouping + records, no
    presentation output. The type-attached ``items.<type>.views`` surface's contract
    (``build_item_json``'s ``views`` key, the one caller this serves) — not ``sq workflow view
    --json``'s, for any source kind; see the module docstring for that dispatch."""
    return {
        "fields": [{"code": f.code, "label": f.label, "type": f.type} for f in projection.fields],
        "group_by": projection.group_by,
        "groups": [
            {
                "key": g.key,
                "count": g.count,
                "records": [
                    {code: cell.json_value for code, cell in rec.values.items()}
                    for rec in g.records
                ],
            }
            for g in projection.groups
        ],
    }


def view_template_name(name: str) -> str:
    """The presentation template path a view named *name* resolves to, bundled or
    adopter-overridden — ``templates/views/<name>.md.j2``. The one place that path is
    composed, so :func:`resolve_view_target` and :func:`render_view` can never spell it
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
    :meth:`~squads._services._views.ViewsMixin.resolve_view`/``render_view``, asks the third
    question through :func:`resolve_source` instead, and raises rather than reporting a
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
    empty one. A host with no members renders an empty projection; a ``subtree`` source over a
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
    """:func:`render_view`'s/:func:`render_source_view`'s own pre-check refusal — the named
    view has no presentation template — distinct from a :class:`SquadsError` the Jinja2 engine
    translates out of an actual render. Still a :class:`SquadsError`, so every existing
    catcher of that base class keeps working unchanged; the subtype exists solely so
    :func:`_render_resolved_source_or_raise` can tell its own pre-check refusal apart from an
    engine-translated failure and let the former
    through unrewrapped."""


def render_view(view_name: str, projection: Projection) -> str:
    """Render *projection* through the presentation template declared at the view's own name —
    ``templates/views/<view_name>.md.j2``, resolved by the one Jinja2 engine every rendering
    path already uses. An adopter's ``.overrides/templates/views/<view_name>.md.j2`` shadows
    it exactly the way every other bundled template already does; no view-specific override
    code exists to do that.

    A coherent spec (every axis :func:`~squads._workflow._models._check_item_views` and
    :func:`~squads._workflow._models._check_views` can check) can still name a view whose
    template simply was never written — that's a filesystem fact, not a spec fact, so no
    load-time check can catch it. Checked here, the one funnel every presentation-render
    caller already goes through, so the failure is a clean :class:`ViewTemplateMissingError`
    naming the exact path to create — both the bundled location and the override shadow —
    rather than an unhandled ``jinja2.TemplateNotFound`` traceback."""
    template_name = view_template_name(view_name)
    if not has_template(template_name):
        raise ViewTemplateMissingError(
            f"view {view_name!r} has no presentation template — create one at "
            f"templates/{template_name} (or shadow it with an adopter override at "
            f".overrides/templates/{template_name}) before it can be rendered; until then, "
            "resolve it with `--json`, which does not render at all"
        )
    return render(
        template_name,
        fields=projection.fields,
        group_by=projection.group_by,
        groups=projection.groups,
    )


def render_source_view(
    view_name: str,
    result: SourceResult,
    item: Item,
    spec: WorkflowSpec,
    squad_dir_display: str | None,
) -> str:
    """Render a ``role``/``playbook``/``self`` source's own resolved *result* through its
    presentation template — the non-relation counterpart to :func:`render_view`, which stays
    the ``ref``/``subtree``/``subentity`` path over a :class:`Projection` unchanged.

    The template receives *result* itself (a ``RoleDef``, a :class:`PlaybookSource`, or the
    host item — never a :class:`Cell`/:class:`ViewRecord`) under the fixed name ``source``,
    plus ``item``/``spec``/``squad_dir`` always — every one of the three non-relation kinds,
    not ``self`` alone. The single call site (:func:`render_resolved_source`) already has
    *squad_dir_display* in hand regardless of which kind resolved, so carrying it
    unconditionally removes a per-kind special case rather than adding one, and costs a
    template that never reads it nothing: an unread context key is free under Jinja. This is
    what lets a ``playbook``-sourced template (``squads_skill.md.j2``) reach ``{{ squad_dir }}``
    the same way a ``self``-sourced one always could.

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


def render_resolved_source(
    view_name: str,
    view: ViewSpec,
    result: SourceResult,
    item: Item,
    spec: WorkflowSpec,
    squad_dir_display: str | None,
) -> str:
    """*result* (already resolved by :func:`resolve_source` against *view*) rendered through
    its presentation template — the one place that branches between the two families
    :func:`resolve_source` can return: a relation kind's flat record list goes through
    :func:`project` into a :class:`Projection` and :func:`render_view`; a non-relation kind's
    own native shape goes straight to :func:`render_source_view`. Shared by
    :func:`expand_view_tags` (wrapped, so a template
    failure names the item it was read from) and
    :meth:`~squads._services._views.ViewsMixin.render_view` (unwrapped, since its caller
    already has the item id in hand), so the branch lives in exactly one place rather than
    once per caller.

    *squad_dir_display* is the configured ``squad_dir`` string (never the resolved absolute
    Path) — see :func:`render_source_view` for why the two must not collapse into one value."""
    if view.source.kind in RELATION_KINDS:
        assert isinstance(result, list), (
            f"resolve_source returned {type(result).__name__} for a {view.source.kind!r} "
            "source — a relation kind must resolve to a list[_RawRecord]"
        )
        return render_view(view_name, project(view, result, spec))
    return render_source_view(view_name, result, item, spec, squad_dir_display)


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
        rendered = _render_resolved_source_or_raise(
            name, view, result, item, spec, squad_dir_display
        )
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
    view: ViewSpec,
    result: SourceResult,
    item: Item,
    spec: WorkflowSpec,
    squad_dir_display: str | None,
) -> str:
    """:func:`render_resolved_source`, with a template failure under ``StrictUndefined``
    translated into a :class:`SquadsError` naming *item* — the engine-defect half of
    read-time expansion's two failure modes (see :func:`expand_view_tags`), for any of the
    six source kinds. :func:`render_resolved_source` already reaches
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
        return render_resolved_source(view_name, view, result, item, spec, squad_dir_display)
    except ViewTemplateMissingError:
        raise
    except SquadsError as exc:
        raise SquadsError(f"view {view_name!r} failed to render on {item.id}: {exc}") from exc
