"""Derived views: resolve a declared ``[views]`` entry's source and render it.

A view's declaration is a source and nothing else (:func:`resolve_source`): refs of a declared
kind pointing at the item, a sub-entity collection, a subtree, the item's merged role
definition, a type's playbook lane, or the item itself. Presentation is a Jinja2 template,
``templates/views/<name>.md.j2``, rendered by :func:`render_source_view` and handed the
resolved value in its native shape. Every view is computed on request; nothing here writes
into an item body.

Six source kinds, in two families. ``ref``/``subtree``/``subentity`` are relations, returned
as a flat ``list[Item]``/``list[SubEntity]`` that a template groups and sorts itself (Jinja's
``groupby``/``sort``/``selectattr`` under ``StrictUndefined``). ``role``/``playbook``/``self``
are not relations: each resolves to its own shape (a ``RoleDef``, a :class:`PlaybookSource`,
the host item).

``sq workflow view --json`` serializes each resolved value in the shape its kind already has a
serializer for (``squads._cli._workflow_cmd._view_json_payload``). Cost is one loaded index
plus an inversion or walk over it; nothing is cached or stored on an item.

:func:`~squads._view_tags.expand_view_tags` is the read-time counterpart of the placement verb
(``ViewsMixin.add_view``/``disable_view``): a ``sq:view:<name>`` tag in a body names a view and
nothing else, and is turned into the rendered output on every read, never stored back.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from squads._errors import SquadsError
from squads._interactions._loader import PLAYBOOK_OVERRIDE_FILENAME
from squads._interactions._models import ItemPlaybookSpec, PlaybookSpec
from squads._interactions._role_guidance import developer_roles
from squads._interactions._skills import (
    GREETING_SKILL,
    MEMORY_SKILL,
    SQUADS_SKILL,
    item_type_for_skill_slug,
)
from squads._language import WorkingLanguage
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import (
    Item,
    effective_prefix,
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
from squads._roles._models import CatalogSource
from squads._roles._projection import RoleView
from squads._roles._resolver import resolve_role_for_item
from squads._sections import get_section, iter_marker_spans
from squads._transform import TransformData, TransformLoader
from squads._workflow._models import (
    ROSTER_ROLE,
    ROSTER_SKILL,
    ViewSpec,
    WorkflowSpec,
)
from squads._workflow._validity import subentity_source_reason

#: A deferred roster: only the ``playbook`` source kind calls it, so every other kind costs
#: nothing. A caller invoked more than once per roster (a body with several ``playbook`` tags)
#: memoizes its own callable; see ``ItemsMixin.read_body``.
type RosterProvider = Callable[[], list[RoleView]]


# --------------------------------------------------------------------------- source resolution


@dataclass(frozen=True)
class PlaybookSource:
    """The resolved value of a ``playbook`` source: a type's playbook lane and the live roster.

    ``lane`` (overview, lifecycle line, commands, role guides) is ``None`` for a declared type
    with no playbook entry, a well-formed empty result rather than a failure (see
    :func:`_playbook_source_applies`). The raw ingredients let ``templates/views/item_skill.md.j2``
    derive its rendered values through the ``item_skill_role_sections``/
    ``custom_item_skill_commands``/``label_for``/``linearize_lifecycle`` filters; the active spec
    reaches the template separately as ``spec=``.

    ``playbook`` is the whole merged document *lane* came from: ``squads_skill.md.j2``'s embedded
    cheatsheet loops every declared type's authoring lane (``authoring_owners``), which one type's
    ``lane`` cannot answer. It is carried here because it is already in hand in
    :func:`_resolve_playbook_source`.
    """

    item_type: str
    lane: ItemPlaybookSpec | None
    roster: list[RoleView]
    playbook: PlaybookSpec
    developer_slugs: tuple[str, ...] = ()
    """The slugs of the live roles holding a capability the resolved catalog's ``dev`` template
    declares — what a generated example prefers as an assignee."""


#: Every shape :func:`resolve_source` can return — a relation's flat ``Item``/``SubEntity``
#: list for ``ref``/``subtree``/``subentity``, or one of the three other kinds' own native
#: value. No middle-layer record type sits between a source and the objects it actually holds.
type SourceResult = list[Item] | list[SubEntity] | RoleDef | PlaybookSource | Item


def _resolve_subentity_source(view: ViewSpec, item: Item) -> list[SubEntity]:
    """*item*'s sub-entity collection of *view*'s declared kind, as real ``SubEntity`` objects.

    The kind is fixed by the view's declaration (``source.name``) and known to whoever writes
    ``templates/views/<name>.md.j2``, which hard-codes it: :func:`render_source_view` hands a
    template only ``source``, ``item`` and ``spec``, never the :class:`ViewSpec`.

    It carries no applicability check and raises nothing. Whether the kind applies to *item*'s
    type is a precondition decided by :func:`resolve_view_target` (quiet consumers) or
    :func:`resolve_source` (the loud ``sq workflow view``) before this runs; if a caller skipped
    that gate, ``item.subentities`` is empty and the result is ``[]``, the right answer to "no
    records" (see the emptiness clause on :func:`resolve_view_target`).
    """
    del view  # kept for dispatch symmetry with the other two relation resolvers; unread here
    return list(item.subentities)


def _resolve_role_source(item: Item, squad_dir: Path | None, catalog: CatalogSource) -> RoleDef:
    """*item*'s merged role definition: catalog default, project ``.overrides/roles/<slug>.toml``,
    then the operator-settable fields *item* carries.

    It goes through :func:`~squads._roles._resolver.resolve_role_for_item`, the seam every
    consumer of a live role's ``RoleDef`` uses, so it inherits that seam's graceful degrade. There
    is no applicability check, as in :func:`_resolve_subentity_source`: the item being the role
    type is a precondition. Unlike that resolver this one can fail to resolve for an item's own
    slug, which its type alone cannot decide; ``resolve_role_for_item`` degrades that case to
    ``RoleDef.from_item`` instead of raising, so an orphaned role item stays readable.
    """
    return resolve_role_for_item(item, squad_dir, catalog=catalog)


def _playbook_subject(item: Item, spec: WorkflowSpec) -> str:
    """The type *item* speaks for when a ``playbook`` source's ``name`` is unset.

    That is its own type, except for the declared roster skill type (:data:`ROSTER_SKILL`), whose
    per-type skill speaks for the type its slug documents (``sq-<type>`` to ``<type>``, via
    :func:`item_type_for_skill_slug`, the same inversion :data:`active_skill_slugs` is built
    from). A slug that documents no declared type falls back to the host's own type (``"skill"``):
    the three permanent system skills, an author skill that happens to start with ``sq-``, and a
    dropped or renamed type's stale slug all land there, and none has a playbook lane
    (``[views.squads_skill]`` relies on this).

    The gate is load-bearing: ``Item.slug`` is the filename slug of every item, so an ungated
    inversion would resolve another type's lane for a work item whose title slugifies to
    ``sq-<declared type>``.
    """
    if item.type != ROSTER_SKILL:
        return item.type
    slug = item.slug
    return item_type_for_skill_slug(slug, spec) or item.type


def _resolve_playbook_source(
    view: ViewSpec,
    item: Item,
    playbook: PlaybookSpec,
    roster: RosterProvider,
    spec: WorkflowSpec,
    catalog: CatalogSource,
) -> PlaybookSource:
    """The playbook lane of *view*'s named type, or of the type *item* speaks for.

    The type comes from :func:`_playbook_subject` when *view* names none, and the lane from
    *playbook*, the caller's active merged document, so a project override is what answers. Never
    raises: a resolved type with no entry is ``lane=None``, the empty case
    :func:`_playbook_source_applies` lets through. *roster* is called here, the one place in the
    dispatch that forces it (see :data:`RosterProvider`).
    """
    target_type = view.source.name or _playbook_subject(item, spec)
    live = roster()
    return PlaybookSource(
        item_type=target_type,
        lane=playbook.types.get(target_type),
        roster=live,
        playbook=playbook,
        developer_slugs=tuple(r.slug for r in developer_roles(live, catalog())),
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
    """Canonical parent to children, width-tolerant, as ``_build_tree_children`` resolves.

    It is reimplemented, not imported, because ``_services`` sits above this module. Public because
    the ``ref``/``subtree`` ``--json`` arm of ``squads._cli._workflow_cmd._view_json_payload``
    reuses this walk to fill each record's descendant subtree.
    """
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


#: One applicability predicate per source ``kind``, taking ``(view, view_name, item_type, spec,
#: playbook)`` and returning ``None`` when *item_type* can host *view*'s source, else the
#: reason (never a bare boolean, so placement, read-time skip and the file scan name one cause).
#: Every kind declares one. A predicate decides from the spec and the host's type alone, so the
#: file scan can ask it before ``read_frontmatter`` (see ``CheckMixin._scan_for_check``).
type _SourceApplicability = Callable[[ViewSpec, str, str, WorkflowSpec, PlaybookSpec], str | None]


def _ref_source_applies(
    view: ViewSpec, view_name: str, item_type: str, spec: WorkflowSpec, playbook: PlaybookSpec
) -> str | None:
    """A ``ref`` source imposes no constraint on its host (inverting forward edges ignores type).

    The unused parameters are deliberate: every entry in :data:`_SOURCE_APPLICABILITY` shares one
    call shape, and *item_type* stays structurally checkable as ``str`` on every kind.
    """
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
    Asks through :func:`~squads._workflow._validity.subentity_source_reason`, the one place this
    comparison is worded."""
    del playbook
    return subentity_source_reason(view_name, item_type, view.source.name, spec.items)


def _role_source_applies(
    view: ViewSpec, view_name: str, item_type: str, spec: WorkflowSpec, playbook: PlaybookSpec
) -> str | None:
    """A ``role`` source's one host constraint: *item_type* must be the declared role type
    (:data:`~squads._workflow._models.ROSTER_ROLE`).

    Whether this role item's slug resolves against the catalog or a project override depends on
    the item and the override tree, not its type, so it is not decided here;
    :func:`_resolve_role_source` degrades that case instead of raising.
    """
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


def resolve_source(  # noqa: PLR0913 — the squad context a non-relation kind reads
    view: ViewSpec,
    view_name: str,
    item: Item,
    db: SquadsDB,
    spec: WorkflowSpec,
    playbook: PlaybookSpec,
    roster: RosterProvider,
    squad_dir: Path | None,
    catalog: CatalogSource,
) -> SourceResult:
    """Every value *view* resolves to when read against *item*, dispatched on ``source.kind``.

    A relation kind (``ref``/``subtree``/``subentity``) returns a flat ``list[Item]``/
    ``list[SubEntity]``; ``role``/``playbook``/``self`` return their own shape (see the module
    docstring). Only the three non-relation kinds need *playbook*/*roster*/*squad_dir*/*catalog*,
    but every caller supplies them all, since the service layer holds them and omitting them per
    kind would have to change with the view's declared kind. *roster* alone is a
    :data:`RosterProvider` because it costs a disk read per live role; it is called at most once,
    in :func:`_resolve_playbook_source`.

    This is the loud consumer of source applicability: it raises :class:`SquadsError` when the
    source cannot apply to *item*'s type, through :data:`_SOURCE_APPLICABILITY`, the predicate
    :func:`resolve_view_target` composes for the quiet consumers. A direct ``sq workflow view
    <name> <id>`` names a pair, and an inapplicable one is a bad argument. :func:`expand_view_tags`
    gates through :func:`resolve_view_target` first, so for it this check never fires.
    """
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
        return _resolve_role_source(item, squad_dir, catalog)
    if kind == "playbook":
        return _resolve_playbook_source(view, item, playbook, roster, spec, catalog)
    return _resolve_self_source(item)  # "self"


def view_template_name(name: str) -> str:
    """The presentation template path a view named *name* resolves to, bundled or
    adopter-overridden — ``templates/views/<name>.md.j2``. The one place that path is
    composed, so :func:`resolve_view_target` and :func:`render_source_view` can never spell it
    differently."""
    return f"views/{name}.md.j2"


def resolve_view_target(
    name: str,
    item_type: str,
    spec: WorkflowSpec,
    playbook: PlaybookSpec,
    *,
    from_squad: Path | None,
) -> str | None:
    """Can a ``sq:view:<name>`` tag on a host of *item_type* resolve? ``None`` if so, else why not.

    Three questions, asked once: is *name* declared in *spec*'s ``[views]``; does its template
    resolve (bundled or an override shadow, via ``has_template``); and does its source apply to
    *item_type* (:data:`_SOURCE_APPLICABILITY`).

    Every quiet consumer uses this one predicate: the placement verb refuses an unresolvable tag,
    read-time expansion leaves it literal, and ``sq check``'s file scan reports it. The loud
    consumer, ``sq workflow view``, asks the third question through :func:`resolve_source` and
    raises.

    It reads only *item_type*, *spec* and *playbook*, never an item's content, so the file scan
    can ask before ``read_frontmatter`` runs and it stays out of the per-item validator catalog.
    Spec and playbook come from the caller, never a module global, so an overridden project spec
    is honoured; only the ``playbook`` kind reads *playbook*.

    Emptiness is never a failure. This covers only conditions where a resolver cannot produce a
    well-formed result at all; a host with no members, or a ``subtree`` over a type it never
    parents, yields an empty result and that is the correct answer.
    """
    if name not in spec.views or not has_template(view_template_name(name), from_squad=from_squad):
        return (
            f"no declared view {name!r} with a resolvable presentation template; "
            "see `sq workflow views` for the declared set"
        )
    return _source_incompatibility(spec.views[name], name, item_type, spec, playbook)


#: The three states an empty-or-disabled ``sq:body`` region naming a placement tag can be in,
#: from the operator's point of view — see :func:`empty_body_hint_state`.
type EmptyBodyHintState = Literal["view_undeclared", "declared", "disabled"]


def empty_body_hint_state(
    name: str, spec: WorkflowSpec, *, disabled: bool = False
) -> EmptyBodyHintState:
    """Which of three states explains an empty ``sq:body`` region tagged for view *name*.

    ``sq role show`` and ``sq skill show`` share this so their hints agree. *name* is checked for
    declaration first (an undeclared view's tag cannot be re-enabled), then *disabled*. Returns
    ``"disabled"`` (``view add`` re-enables it), ``"view_undeclared"`` (no remedy renders it), or
    ``"declared"`` (``sq sync`` populates it, else declare the definition or ``view add``).
    """
    if name not in spec.views:
        return "view_undeclared"
    if disabled:
        return "disabled"
    return "declared"


class ViewTemplateMissingError(SquadsError):
    """The pre-check refusal of :func:`render_source_view`: the named view has no template.

    It is a :class:`SquadsError` subtype so :func:`render_resolved_source_or_raise` can tell it
    apart from an engine-translated render failure and let it through unwrapped.
    """


def render_source_view(
    view_name: str,
    result: SourceResult,
    item: Item,
    spec: WorkflowSpec,
    squad_dir_display: str | None,
    working_language: WorkingLanguage,
    data: TransformData | None = None,
    *,
    from_squad: Path | None,
) -> str:
    """Render *view_name*'s resolved *result* through ``templates/views/<view_name>.md.j2``.

    The one render entry point for all six source kinds, through the one Jinja2 engine; an
    adopter's ``.overrides/templates/views/<view_name>.md.j2`` shadows the bundled template. The
    template receives *result* as ``source`` in its native shape, plus ``item``, ``spec`` and
    ``squad_dir``, so grouping, ordering and badges for a relation are the template's job.

    A coherent spec (:func:`~squads._workflow._validity.check_views`) can still name a view whose
    template was never written, which no load-time check can see. It is checked here, the funnel
    every presentation render goes through, so the failure is a :class:`ViewTemplateMissingError`
    naming the bundled path and the override shadow, not a ``jinja2.TemplateNotFound`` traceback.

    *squad_dir_display* is the configured folder name (``SquadsConfig.squad_dir``, as the backend
    templates render it), handed verbatim as ``{{ squad_dir }}``. It is not derived from the
    resolved :class:`Path`, whose last segment equals the configured value only for a
    single-segment name. *data* is the view's transform output; the template gets it as ``data``
    only when given, so a transform-less view that reads ``data`` fails under ``StrictUndefined``.
    *working_language* reaches the template as ``working_language``.
    """
    template_name = view_template_name(view_name)
    if not has_template(template_name, from_squad=from_squad):
        raise ViewTemplateMissingError(
            f"view {view_name!r} has no presentation template — create one at "
            f"templates/{template_name} (or shadow it with an adopter override at "
            f".overrides/templates/{template_name}) before it can be rendered; until then, "
            "resolve it with `--json`, which does not render at all"
        )
    context: dict[str, object] = {
        "source": result,
        "item": item,
        "spec": spec,
        "squad_dir": squad_dir_display,
        "working_language": working_language,
    }
    if data is not None:
        context["data"] = data
    return render(template_name, from_squad=from_squad, **context)


def has_view_tag(text: str) -> bool:
    """Whether *text* carries at least one well-formed ``sq:view:<name>`` tag, enabled or disabled.

    It uses the span-and-name check :func:`expand_view_tags` does, on the text alone, so
    :meth:`~squads._services._items.ItemsMixin.read_body` can skip the index load and expansion
    for the common tagless body. A disabled-only body answers ``True``: the read boundary must
    still strip it rather than let the raw tag reach ``sq show``.
    """
    return any(markers.view_tag_parts(raw) is not None for raw, _, _ in iter_marker_spans(text))


def template_seeded_view_names(
    item_type: str, spec: WorkflowSpec, *, from_squad: Path | None
) -> frozenset[str]:
    """The ``sq:view:<name>`` tags *item_type*'s creation template places in its ``sq:body`` region.

    Read from the template source, not a render (there is no item to render against). The
    template is resolved as the create path does (``creation_template_name``, with the
    ``items/_default.md.j2`` fallback) through the override-aware ``template_source``, so an
    overridden creation template gives the overridden answer. The retroactive migration and the
    ``sq check`` advisory for a missing seeded tag both read it, so they agree on what "the
    template seeds this tag" means. Tags are recognised through ``view_tag_parts`` over
    ``iter_marker_spans``, with no re-spelled ``sq:view:`` literal.

    Empty, never an error, when *item_type* is undeclared, its template is missing, it has no
    ``sq:body`` region, or the region carries no view tag.
    """
    if item_type not in spec.items:
        return frozenset()
    template_name = creation_template_name(item_type, spec, from_squad=from_squad)
    if not has_template(template_name, from_squad=from_squad):
        return frozenset()
    body = get_section(template_source(template_name, from_squad=from_squad), markers.BODY)
    if body is None:
        return frozenset()
    return frozenset(
        parts.name
        for raw, _start, _end in iter_marker_spans(body)
        if (parts := markers.view_tag_parts(raw)) is not None
    )


#: Slug to the view rendering each always-on skill's definition, seeded at creation
#: (``_write_managed_skill``) and backfilled by ``sq repair``; per-type skills use
#: :data:`ITEM_SKILL_VIEW_NAME`.
SYSTEM_SKILL_VIEW_NAMES: dict[str, str] = {
    SQUADS_SKILL: "squads_skill",
    GREETING_SKILL: "greeting_skill",
    MEMORY_SKILL: "memory_skill",
}


#: The one view every per-type ``sq-<type>`` skill's tag names. A view named per type would
#: put the type name in corpus bytes and dangle on a rename or drop; the ``playbook`` source
#: resolves the type from the host's slug at read time (``_playbook_subject``).
ITEM_SKILL_VIEW_NAME = "item_skill"


#: The view a role's placement tag names, seeded at activation (``templates/agents/role.md.j2``,
#: reasserted by ``ServiceCore._create_core``) and backfilled by ``sq repair``. Declared as
#: ``[views.role_definition]`` in ``_specs/workflow.toml``, which all three writers agree with.
ROLE_DEFINITION_VIEW_NAME = "role_definition"


def roster_body_view_name(item_type: str, slug: str, spec: WorkflowSpec) -> str | None:
    """The view name a role's or skill's own ``sq:body`` region is classified as carrying, from
    *item_type* and *slug* alone — ``None`` for every other item type, and ``None`` when the
    classified view is dropped from ``[selected]`` or the slug matches no known role/system
    skill/declared type. The one derivation the write path and the file checks both read."""
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


def seeded_view_names(
    item_type: str, slug: str, spec: WorkflowSpec, *, from_squad: Path | None
) -> frozenset[str]:
    """The view name(s) a document of *item_type* named *slug* is seeded with, gated on the
    view still being declared — :func:`roster_body_view_name` for a role or skill,
    :func:`template_seeded_view_names` for every other type. Type and slug only, never the
    host's content, so the file checks can call this before frontmatter ever parses."""
    if item_type in (ROSTER_ROLE, ROSTER_SKILL):
        return frozenset(
            n for n in (roster_body_view_name(item_type, slug, spec),) if n is not None
        )
    return frozenset(
        n
        for n in template_seeded_view_names(item_type, spec, from_squad=from_squad)
        if n in spec.views
    )


def view_data(
    text: str,
    item: Item,
    db: SquadsDB,
    spec: WorkflowSpec,
    playbook: PlaybookSpec,
    roster: RosterProvider,
    squad_dir: Path | None,
    catalog: CatalogSource,
) -> dict[str, TransformData]:
    """Each enabled, resolvable ``sq:view:<name>`` tag of *text* whose view declares a
    transform, mapped to that transform's output. Gated by :func:`resolve_view_target` exactly
    as :func:`expand_view_tags` is, so text and data agree on which tags are live; a disabled,
    unresolvable or transform-less tag contributes nothing."""
    loader = TransformLoader(squad_dir)
    data: dict[str, TransformData] = {}
    for raw, _start, _end in iter_marker_spans(text):
        parts = markers.view_tag_parts(raw)
        if parts is None or parts.disabled or parts.name in data:
            continue
        if (
            resolve_view_target(parts.name, item.type, spec, playbook, from_squad=squad_dir)
            is not None
        ):
            continue
        view = spec.views[parts.name]
        if view.transform is None:
            continue
        result = resolve_source(
            view, parts.name, item, db, spec, playbook, roster, squad_dir, catalog
        )
        data[parts.name] = loader.run(parts.name, view.transform, result, item=item, spec=spec)
    return data


def render_resolved_source_or_raise(
    view_name: str,
    result: SourceResult,
    item: Item,
    spec: WorkflowSpec,
    squad_dir_display: str | None,
    working_language: WorkingLanguage,
    data: TransformData | None = None,
    *,
    from_squad: Path | None,
) -> str:
    """:func:`render_source_view`, with a ``StrictUndefined`` template failure naming *item*.

    The engine's ``render`` turns a ``jinja2.TemplateError`` into a bare :class:`SquadsError`; this
    re-raises it naming the item the tag was read from (the engine-defect half of the read-time
    failure modes in :func:`expand_view_tags`). An unresolvable tag never reaches here because the
    caller gates on :func:`resolve_view_target`; :class:`ViewTemplateMissingError` is re-raised
    unchanged should the template vanish between the two checks.
    """
    try:
        return render_source_view(
            view_name,
            result,
            item,
            spec,
            squad_dir_display,
            working_language,
            data,
            from_squad=from_squad,
        )
    except ViewTemplateMissingError:
        raise
    except SquadsError as exc:
        raise SquadsError(f"view {view_name!r} failed to render on {item.id}: {exc}") from exc
