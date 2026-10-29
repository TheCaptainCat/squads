"""The shared service core: state, backend access, and the primitives every concern builds on.

Each concern lives in its own ``_services/_*.py`` mixin subclassing ``ServiceCore``; the public
``Service`` (in ``_service.py``) multiply-inherits them. ``ServiceCore`` defines what's used across
concerns (create/get/list, the backend, the role/skill lookups and the ``roster_projection``
collaborator) so the mixins only ever call core methods + their own.
"""

import contextlib
import unicodedata
from collections.abc import AsyncGenerator, Callable, Collection, Iterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from squads import _actor as actor
from squads import _aio
from squads import _clock as clock
from squads import _discussion as discussion
from squads import _sections as sections
from squads import _view_tags as view_tags
from squads import _views as views
from squads._backends._base import AgentBackend, BackendContext
from squads._errors import ItemNotFoundError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._index._store import IndexStore
from squads._interactions._models import PlaybookSpec
from squads._interactions._role_guidance import (
    RoleLike,
    allowed_create_types,
    catalog_default_slug,
    in_lane_owner,
    is_lane_exempt,
    laned_types,
    slug_only_role,
)
from squads._interactions._skills import item_origin
from squads._itemfile import (
    ensure_no_skew,
    new_item_text,
    read_item_text,
    write_new,
    write_text,
)
from squads._language import WorkingLanguage, resolve_working_language
from squads._models import _markers as markers
from squads._models._attributes import AttributeKey
from squads._models._index import SquadsDB
from squads._models._item import (
    DISPLAY_ID_PADDING,
    Item,
    effective_prefix,
    format_item_id,
    make_ref,
    parse_item_token,
    split_ref,
)
from squads._models._participants import (
    ANONYMOUS_SLUG,
    OPERATOR_SLUG_PREFIX,
    group_verb_problem,
    operator_slug_problem,
    operator_slug_suggestion,
    require_valid_slug,
    reserved_role_slug_reason,
)
from squads._models._vocab import prefix_for
from squads._paths import SquadPaths, number_for_id
from squads._rendering._engine import render, scaffold_body
from squads._roles._catalog import RoleDef
from squads._roles._loader import ROLES_OVERRIDE_FILENAME
from squads._roles._models import CatalogSource
from squads._roles._projection import OperatorView, RoleView
from squads._roles._resolver import (
    holds_default_designation,
    resolve_role_tolerantly,
)
from squads._services._duplicate_ids import (
    DUPLICATE_ID_REMEDY,
    SHARED_NUMBER_REMEDY,
    CarrierLog,
    groups_among,
    name_number,
    normalized_id,
    read_id,
)
from squads._services._results import CreateResult, SelfRemedied, TreeNode
from squads._services._roster_projection import RosterProjection
from squads._services._skill_files import (
    SkillFolder,
    SkillScan,
    managed_skill_slugs,
    remedy_text,
    stamped_skill_slug,
)
from squads._services._validators import ValidatorEngine
from squads._specload import OverrideFiles
from squads._util import operator_slug, slugify
from squads._view_remedies import view_placement_invocation
from squads._workflow import (
    ROSTER_OPERATOR,
    ROSTER_ROLE,
    ROSTER_SKILL,
    dropped_via_selected,
)
from squads._workflow._models import Field, ItemSpec, WorkflowSpec


# Body-local sub-entities: kind <-> parent type and the container marker, derived from the active
# spec's `subentity_kind` (forward edge, invariant #4) so project-declared types are visible. Free
# functions because the spec is per-service; ServiceCore exposes them as properties.
def subentity_parent_map(spec: WorkflowSpec) -> dict[str, str]:
    """Sub-entity kind to one hosting item type, inverted from the spec's
    ``ItemSpec.subentity_kind``. Two types may declare the same kind, so the result is a naming hint
    only and must never back an ownership or validation decision; use
    ``spec.item_subentity_kind(item.type) == kind`` for that.
    """
    return {ts.subentity_kind: t for t, ts in spec.items.items() if ts.subentity_kind}


def subentity_kind_map(spec: WorkflowSpec) -> dict[str, str]:
    """Item type -> sub-entity kind, read directly off the spec (genuinely 1:1 per type;
    NOT built by inverting :func:`subentity_parent_map`, which would drop every type that
    map's inversion collapsed away)."""
    return {t: ts.subentity_kind for t, ts in spec.items.items() if ts.subentity_kind}


def subentity_container_map(spec: WorkflowSpec) -> dict[str, str]:
    """Sub-entity kind -> container marker tag — simply the kind's declared ``plural``."""
    return {kind: ks.plural for kind, ks in spec.subentity_kinds.items()}


def ensure_subentity_container_text(spec: WorkflowSpec, item_type: str, text: str) -> str:
    """Append an empty sub-entity container block to *text* when *item_type* hosts a sub-entity kind
    and the block is absent (idempotent, see :func:`squads._discussion.ensure_container`). It is the
    one primitive behind item creation (``_create_core``) and retype (``_services._retype``); tag
    and heading come from the active spec, never a template literal.
    """
    kind = subentity_kind_map(spec).get(item_type)
    if kind is None:
        return text
    container_tag = spec.subentity_plural(kind)
    heading = spec.subentity_container_heading(kind)
    return discussion.ensure_container(text, heading, container_tag)


@dataclass(frozen=True)
class ItemFilter:
    """The shared list/tree filter spec.  One match predicate, used by both ``list_items``
    and ``tree_view`` so the two commands can never drift.

    All fields default to ``None`` (no constraint on that dimension).  ``matches()``
    applies every non-``None`` field as an AND condition.  ``is_empty()`` is True when no
    field is set — an empty filter matches every item.
    """

    item_type: str | None = None
    status: str | None = None
    parent: str | None = None
    label: str | None = None
    assignee: str | None = None
    #: Category filter (``roster``/``work``/``records``): matches when the item's type
    #: declares it, and never matches without ``spec``, like ``badge_min``. The value is
    #: validated at the CLI edge against ``squads._workflow.CATEGORIES``.
    category: str | None = None
    #: Exact badge-field filters, keyed by field CODE — generic over ``fields_for()``.
    badges: tuple[tuple[str, str], ...] = ()
    #: Threshold badge-field filters (ordered collections only): (field code, minimum code).
    #: Resolving "at least as high as" needs the field's declared collection, so this variant
    #: is only usable when ``spec`` is set.
    badge_min: tuple[tuple[str, str], ...] = ()
    #: The active spec — needed only to resolve ``badge_min`` rank and ``category``;
    #: ``None`` disables both.
    spec: WorkflowSpec | None = None

    def matches(self, it: Item) -> bool:
        """Return True iff *it* satisfies every non-None dimension of this filter."""
        base = (
            (not self.item_type or it.type == self.item_type)
            and (not self.status or it.status == self.status)
            and (not self.parent or it.parent == self.parent)
            and (not self.label or self.label in it.labels)
            and (not self.assignee or it.assignee == self.assignee)
            and (not self.category or self._category_of(it) == self.category)
        )
        if not base:
            return False
        if any(it.badge_value(code) != want for code, want in self.badges):
            return False
        return all(self._meets_min(it, code, min_code) for code, min_code in self.badge_min)

    def _category_of(self, it: Item) -> str | None:
        """The declared category of *it*'s type, or ``None`` when unresolvable (no active
        spec, or the type is not declared in it) — a graceful non-match, never a crash."""
        if self.spec is None:
            return None
        ts = self.spec.items.get(it.type)
        return ts.category if ts else None

    def _meets_min(self, it: Item, code: str, min_code: str) -> bool:
        """True when *it*'s badge for *code* ranks at least as high as *min_code* (lower
        index = higher-ranked). Unresolvable (no spec, no field, no ordered collection, or
        an unrecognised code) is a graceful non-match, never a crash."""
        if self.spec is None:
            return False
        field = next((f for f in self.spec.fields_for(it.type) if f.code == code), None)
        coll = self.spec.collections.get(field.collection) if field else None
        if coll is None:
            return False
        order = [b.code for b in coll.badges]
        value = it.badge_value(code)
        return value in order and min_code in order and order.index(value) <= order.index(min_code)

    def is_empty(self) -> bool:
        """Return True when no filter dimension is set (matches all items)."""
        return not any(
            (
                self.item_type,
                self.status,
                self.parent,
                self.label,
                self.assignee,
                self.category,
                self.badges,
                self.badge_min,
            )
        )


def _compute_keep_set(
    match_set: set[str],
    id_map: dict[str, Item],
    seq_to_id: dict[int, str],
) -> set[str]:
    """Return match_set UNION all ancestors of each matched item, walking parent links upward
    through the candidate set by sequence number so a stored parent's zero-pad width does not
    matter. Items whose parent is outside the set are roots. Each walk has its own visited set so a
    parent cycle terminates, and the revisited ancestor is still kept so a cyclic pair renders
    whole.
    """
    keep_set: set[str] = set(match_set)
    for mid in match_set:
        item = id_map.get(mid)
        seen: set[int] = set() if item is None else {item.sequence_id}
        while item is not None and item.parent is not None:
            p_seq = number_for_id(item.parent)
            canonical = seq_to_id.get(p_seq)
            if canonical is None or canonical not in id_map:
                break
            keep_set.add(canonical)
            if p_seq in seen:
                break
            seen.add(p_seq)
            item = id_map.get(canonical)
    return keep_set


def _walk_tree(
    it: Item,
    current_depth: int,
    *,
    keep_set: set[str],
    match_set: set[str],
    children_map: dict[str | None, list[Item]],
    depth: int | None,
    ancestors: frozenset[int] = frozenset(),
    anchor: bool = False,
) -> TreeNode | None:
    """Recursive downward walk pruning to *keep_set* and bounding to *depth* (root = 0, ``None``
    unbounded); ``None`` drops the node (not kept, already on the path, or a path-only anchor with
    no survivors). *ancestors* (sequence numbers, width-tolerant) is the cycle guard; *anchor* marks
    a root invented for a parent cycle (:func:`_cycle_anchor_ids`) and is carried onto that node
    only.
    """
    if it.id not in keep_set or it.sequence_id in ancestors:
        return None
    path_only = it.id not in match_set
    child_nodes: list[TreeNode] = []
    if depth is None or current_depth < depth:
        for child in sorted(children_map.get(it.id, []), key=lambda i: number_for_id(i.id)):
            child_node = _walk_tree(
                child,
                current_depth + 1,
                keep_set=keep_set,
                match_set=match_set,
                children_map=children_map,
                depth=depth,
                ancestors=ancestors | {it.sequence_id},
            )
            if child_node is not None:
                child_nodes.append(child_node)
    # Drop a path_only anchor with no surviving children (would be an empty branch)
    if path_only and not child_nodes:
        return None
    return TreeNode(item=it, path_only=path_only, children=child_nodes, anchor=anchor)


def _cycle_anchor_ids(listed: list[Item]) -> set[str]:
    """Return one anchor id per parent cycle in *listed*: its lowest sequence number, so a bare tree
    does not lose a cycle whose members all have parents. The anchor comes from the cycle's own
    items, not "the lowest item not rendered", which would render an item below the cycle twice. One
    per cycle suffices since cycles are disjoint, and it is computed on the candidate set the roots
    come from, not the whole index.
    """
    seq_to_id: dict[int, str] = {number_for_id(i.id): i.id for i in listed}
    parent_of: dict[int, int] = {}
    for it in listed:
        if not it.parent:
            continue
        parent_seq = number_for_id(it.parent)
        if parent_seq in seq_to_id:
            parent_of[number_for_id(it.id)] = parent_seq

    anchors: set[str] = set()
    settled: set[int] = set()  # every sequence whose upward walk has already been resolved
    for start in seq_to_id:
        if start in settled:
            continue
        position: dict[int, int] = {}  # sequence -> where it sits on the current walk
        walk: list[int] = []
        node: int | None = start
        while node is not None and node not in settled:
            if node in position:  # the walk closed on itself: everything from here is the cycle
                anchors.add(seq_to_id[min(walk[position[node] :])])
                break
            position[node] = len(walk)
            walk.append(node)
            node = parent_of.get(node)
        settled.update(walk)
    return anchors


def _build_tree_children(
    listed: list[Item],
) -> dict[str | None, list[Item]]:
    """Group items by their canonical parent id. ``item.parent`` may keep an old zero-pad width
    after ``sq migrate repad``, so resolving by sequence number keeps the tree correct;
    ``tree_view`` and any caller needing it share this one parent resolution.
    """
    all_ids = {i.id for i in listed}
    seq_to_id: dict[int, str] = {number_for_id(i.id): i.id for i in listed}
    children: dict[str | None, list[Item]] = {}
    for it in listed:
        parent_canonical: str | None = None
        if it.parent:
            canonical = seq_to_id.get(number_for_id(it.parent))
            if canonical is not None and canonical in all_ids:
                parent_canonical = canonical
        children.setdefault(parent_canonical, []).append(it)
    return children


def is_blank(text: str) -> bool:
    """Whether *text* shows nothing: empty, or only whitespace and Unicode format characters
    (category Cf, such as the zero-width space and the byte-order mark)."""
    return all(ch.isspace() or unicodedata.category(ch) == "Cf" for ch in text)


def require_title(title: str, what: str = "title") -> None:
    """Raise ``SquadsError`` when *title* is blank (see :func:`is_blank`).

    The guard behind every write that sets an item's title: a blank title is not storable (the
    index model requires one), so it is refused before anything is written. A title that slugs
    to nothing, such as ``"!!!"``, is valid; its filename slug is ``untitled``.
    """
    if is_blank(title):
        raise SquadsError(f"{what} must not be empty")


def reject_markers(text: str, what: str = "body") -> None:
    """Raise ``SquadsError`` when *text* contains a well-formed sq marker tag. Every prose input
    landing inside a marker region passes through it before a write; *what* names the input in the
    message (``"body"``, ``"comment message"``, ``"title"``). Every label gets the remediation
    guidance, since an author writing about the marker system reaches for backticks first, which do
    not help, and so must be told what to write instead.
    """
    if not sections.find_markers(text):
        return
    raise SquadsError(
        f"{what} must not contain sq marker comments (<!-- sq:… -->). "
        "Write the tag without its HTML-comment wrapper (e.g. sq:body rather than "
        "the comment form) — backtick-wrapping does not neutralize a well-formed tag."
    )


def reject_non_view_markers(text: str, what: str = "body") -> None:
    """:func:`reject_markers` over *text* with its ``sq:view:<name>`` tags set aside, for the body
    writers that compare those tags with the ones already placed instead of refusing them."""
    reject_markers(view_tags.strip_view_tags(text), what)


#: How many leading lines of the body about to be discarded the refusal quotes back.  Enough to
#: recognise the content, short enough that the message stays readable in a terminal.
BODY_OVERWRITE_PREVIEW_LINES = 3

#: Per roster type, the metadata fields an update may change on a generated entry: identity the
#: operator sets, never generated content. Keyed by the field names ``_update_model`` reports.
ROSTER_UPDATE_EXEMPT: Mapping[str, frozenset[str]] = MappingProxyType(
    {ROSTER_ROLE: frozenset({"title", "model"}), ROSTER_SKILL: frozenset()}
)


def reject_body_overwrite(target: str, current: str) -> None:
    """Raise ``SquadsError`` rather than let a plain ``body`` write discard authored prose. It
    refuses instead of prompting because agents cannot answer a prompt and a skip flag would be
    passed reflexively; a first write over the template scaffold is unaffected, and the message
    gives the line count and opening lines at stake. *target* names the thing written and *current*
    is the body that would be discarded.
    """
    lines = current.splitlines()
    head = "\n".join(f"    {line}" for line in lines[:BODY_OVERWRITE_PREVIEW_LINES])
    rest = len(lines) - BODY_OVERWRITE_PREVIEW_LINES
    if rest > 0:
        head += f"\n    … ({rest} more line{'s' if rest != 1 else ''})"
    raise SquadsError(
        f"{target} already has a body ({len(lines)} line{'s' if len(lines) != 1 else ''}); "
        f"setting one would discard it:\n\n{head}\n\n"
        "Nothing was written. Add to it with `--append`, or pass `--force` to replace it."
    )


def _check_roster_slug(item_type: str, is_roster: bool, slug: str) -> None:
    """Raise when a roster entry would be created with a slug outside its grammar: an operator's
    is ``op-`` plus the slug grammar, a role's is the slug grammar minus the reserved names."""
    if not is_roster:
        return
    for candidate in (slug,):
        if item_type == ROSTER_OPERATOR:
            if operator_slug_problem(candidate) is not None:
                example = operator_slug_suggestion(candidate)
                hint = f" (e.g. {example!r})" if example else ""
                rule = (
                    f"must be {OPERATOR_SLUG_PREFIX!r} followed by lowercase letters, digits "
                    "and hyphens"
                    if candidate.startswith(OPERATOR_SLUG_PREFIX)
                    else f"must start with {OPERATOR_SLUG_PREFIX!r} and be lowercase letters, "
                    "digits and hyphens"
                )
                raise SquadsError(f"operator slug {candidate!r} {rule}{hint}")
            continue
        require_valid_slug(candidate, action=f"create this {item_type}")
        if item_type == ROSTER_ROLE and (reason := reserved_role_slug_reason(candidate)):
            raise SquadsError(f"{reason}; a role needs another slug")
        if item_type in (ROSTER_ROLE, ROSTER_SKILL) and (
            verb := group_verb_problem(item_type, candidate)
        ):
            raise SquadsError(f"{item_type} slug {candidate!r} {verb}; pick another slug")


def _stamp_origin(item: Item, spec: WorkflowSpec) -> None:
    """Give a new role or skill its origin unless the caller supplied one."""
    if item.type in (ROSTER_ROLE, ROSTER_SKILL):
        item.attributes.setdefault(AttributeKey.ORIGIN, item_origin(item, spec))


class ServiceCore:
    def __init__(
        self,
        paths: SquadPaths,
        spec: WorkflowSpec,
        playbook: PlaybookSpec,
        store: IndexStore,
        backends: Callable[[], list[AgentBackend]],
        catalog: CatalogSource,
        files: OverrideFiles,
        refusal: SquadsError | None = None,
    ):
        self.paths = paths
        self.spec = spec
        self.playbook = playbook
        self.store = store
        self._backends = backends
        self.catalog = catalog
        self.files = files
        self.roster_projection = RosterProjection(paths, spec, playbook, store, backends, catalog)
        self._refusal = refusal

    @property
    def refusal(self) -> SquadsError | None:
        """Why the composition this service was asked for fell back to the documents it holds;
        ``None`` when it holds what was asked for."""
        return self._refusal

    @property
    def working_language(self) -> WorkingLanguage:
        """The squad's working language, English when the configured value is unusable."""
        return resolve_working_language(self.paths.config.working_language)[0]

    # ------------------------------------------------------------------ sub-entity vocabulary
    # Resolved from THIS service's active spec (self.spec), not the bundled default — a
    # project-declared type/kind is visible here with no code change.
    @property
    def subentity_parent(self) -> dict[str, str]:
        """Sub-entity kind -> hosting item type."""
        return subentity_parent_map(self.spec)

    @property
    def subentity_kind(self) -> dict[str, str]:
        """Item type -> sub-entity kind (inverse of ``subentity_parent``)."""
        return subentity_kind_map(self.spec)

    @property
    def subentity_container(self) -> dict[str, str]:
        """Sub-entity kind -> container marker tag."""
        return subentity_container_map(self.spec)

    def _template_for(self, item_type: str) -> str:
        """Return the Jinja2 template path for ``item_type`` — a thin wrapper over
        :func:`~squads._rendering._engine.creation_template_name`, which does the actual
        resolution. Shared rather than reimplemented here so the create path and the
        template-seeded-view derivation (:func:`~squads._views.template_seeded_view_names`,
        the migration/``sq check`` seam) can never resolve a type to two different templates.
        """
        from squads._rendering._engine import creation_template_name

        return creation_template_name(item_type, self.spec, from_squad=self.paths.squad_dir)

    def pristine_body(self, item: Item) -> str | None:
        """The ``:body`` region a freshly-created *item* of this type would carry, or ``None``
        when the scaffold cannot be reproduced (see :func:`~squads._rendering._engine.
        scaffold_body`). It is derived rather than pattern-matched because the scaffold differs
        per type, interpolates item fields and can be replaced by a project template."""
        return scaffold_body(item, self.spec, from_squad=self.paths.squad_dir)

    # ------------------------------------------------------------------ backend
    @property
    def _ctx(self) -> BackendContext:
        return BackendContext(
            paths=self.paths, spec=self.spec, playbook=self.playbook, catalog=self.catalog
        )

    async def scaffold_backend(self) -> None:
        """Public entry for init(): create backend scaffolding for every active backend."""
        ctx = self._ctx
        for backend in self._backends():
            await backend.ensure_scaffold(ctx)

    # ------------------------------------------------------------------ create / read
    async def create(  # noqa: PLR0913 — a creation entrypoint with clear keyword-only fields
        self,
        item_type: str,
        title: str,
        *,
        description: str = "",
        parent: str | None = None,
        author: str | None = None,
        labels: list[str] | None = None,
        refs: list[str] | None = None,
        assignee: str | None = None,
        attributes: dict[str, Any] | None = None,
        status: str | None = None,
        slug: str | None = None,
        body: str | None = None,
        fields: dict[str, str] | None = None,
    ) -> CreateResult:
        """Create an item — opens its own transaction, then delegates to :meth:`_create_core`.

        The bulk-importer calls :meth:`_create_core` directly (its own single transaction is
        already open), so this wrapper stays a thin two-liner and the mutation logic lives in
        exactly one place.
        """
        async with self.store.transaction() as db:
            return await self._create_core(
                db,
                item_type,
                title,
                description=description,
                parent=parent,
                author=author,
                labels=labels,
                refs=refs,
                assignee=assignee,
                attributes=attributes,
                status=status,
                slug=slug,
                body=body,
                fields=fields,
            )

    def _live_role_likes(self, db: SquadsDB) -> list[RoleDef]:
        """The resolved definition of every live role in *db*, in index order."""
        live = self.spec.live_statuses(ROSTER_ROLE)
        return [
            resolve_role_tolerantly(it, self.paths.squad_dir, catalog=self.catalog)
            for it in db.items.values()
            if it.type == ROSTER_ROLE and it.status in live
        ]

    def _role_like(self, db: SquadsDB, slug: str) -> RoleLike:
        """The live role *slug* resolves to, or a bare role holding no capability when *slug*
        is not a live role (an operator, or an author the roster does not carry)."""
        live = self.spec.live_statuses(ROSTER_ROLE)
        item = next(
            (
                it
                for it in db.items.values()
                if it.type == ROSTER_ROLE and it.slug == slug and it.status in live
            ),
            None,
        )
        if item is None:
            return slug_only_role(slug)
        return resolve_role_tolerantly(item, self.paths.squad_dir, catalog=self.catalog)

    def _default_role_slug(self, db: SquadsDB) -> str | None:
        """This squad's own ``is_default`` role slug from the live roster in *db*, which the lane
        exemption follows, or ``None`` when no live role holds it (the caller then uses
        :func:`~squads._interactions._role_guidance.catalog_default_slug`). It uses
        :func:`~squads._roles._resolver.holds_default_designation`, not the stored attribute, which
        only overrides the catalog's answer.
        """
        live = self.spec.live_statuses(ROSTER_ROLE)
        for it in db.items.values():
            if (
                it.type == ROSTER_ROLE
                and it.status in live
                and holds_default_designation(it, self.paths.squad_dir, catalog=self.catalog)
            ):
                return it.slug
        return None

    @staticmethod
    def _check_operator_slug_free(db: SquadsDB, item_type: str, slug: str) -> None:
        """Raise when creating an operator whose *slug* another operator already answers to."""
        if item_type == ROSTER_OPERATOR and any(
            it.type == ROSTER_OPERATOR and it.slug == slug for it in db.items.values()
        ):
            raise SquadsError(f"an operator with slug {slug!r} already exists")

    def _classified_view(self, item: Item) -> str | None:
        """The view a role's or skill's body renders through, or ``None`` when its body is
        authored. The one place the classification is asked for a write or a re-render."""
        if item.type not in (ROSTER_ROLE, ROSTER_SKILL):
            return None
        return views.roster_body_view_name(item.type, item.slug, self.spec)

    def _refuse_classified_roster_write(
        self,
        item_id: str,
        item: Item,
        verb: str,
        *,
        fields: Collection[str] | None = None,
        allow_view: str | None = None,
    ) -> None:
        """Raise when *item* is a role or skill whose body renders through a declared view, so its
        one validated authoring surface is not duplicated by *verb*. Metadata updates, view verbs
        and skill body writes ask this, and ``--force`` does not lift it; dropping the view from
        ``[selected]`` does.
        *allow_view* is the one view the verb may place; *fields* passes when all are in the type's
        :data:`ROSTER_UPDATE_EXEMPT` set.
        """
        if fields is not None and set(fields) <= ROSTER_UPDATE_EXEMPT.get(item.type, frozenset()):
            return
        roster_view = self._classified_view(item)
        if roster_view is None or roster_view == allow_view:
            return
        authoring_surface = (
            f"`{ROLES_OVERRIDE_FILENAME}` (or `.overrides/roles/<slug>.toml`), or `sq role "
            f"{item.slug} update` for a role that defines itself"
            if item.type == ROSTER_ROLE
            else views.skill_authoring_surface(roster_view, item.slug, self.spec, self.playbook)
        )
        tag = f"{markers.PREFIX}{markers.view_tag(roster_view)}"
        head = (
            f"{item_id}'s body renders through its declared {tag} tag, and "
            f"its content already has one validated authoring surface: {authoring_surface}. "
            f"{verb} is refused — `--force` does not lift this."
        )
        disable = view_placement_invocation(item.type, item.slug, "disable", roster_view)
        if item.type == ROSTER_ROLE:
            raise SquadsError(
                f"{head} To add prose beside the definition, use `sq role {item.slug} body`. "
                "To replace the generated definition itself, drop the view from `[selected]`, "
                f"then clear its leftover tag with `{disable}`."
            )
        raise SquadsError(
            f"{head} Drop the view from `[selected]` to author this directly instead, then "
            f"clear its leftover tag with `{disable}`."
        )

    def _create_model(  # noqa: PLR0913 — mirrors `create`'s own keyword surface
        self,
        db: SquadsDB,
        item_type: str,
        title: str,
        *,
        description: str = "",
        parent: str | None = None,
        author: str | None = None,
        labels: list[str] | None = None,
        refs: list[str] | None = None,
        assignee: str | None = None,
        attributes: dict[str, Any] | None = None,
        status: str | None = None,
        slug: str | None = None,
        body: str | None = None,
        fields: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> tuple[Item, str | None]:
        """The pure half of create: every check, the id allocation and the ``Item``, with no file
        I/O, returning ``(item, lane_warning)``. Shared by :meth:`_create_core` and the bulk
        importer's pre-pass, which runs it on a throwaway ``db`` copy so the allocation stays within
        invariant #2, passing the event's ``at`` as *now*. ``fields`` is a badge-code map.
        ``author`` is required in practice and keyword-with-default only to keep test call sites
        type-correct.
        """
        item_type = str(item_type)  # coerce StrEnum members to plain str
        # Membership gate: later lookups index `self.spec.items[item_type]` unguarded, so a type
        # absent from the active spec is refused here with the read path's "unknown item type"
        # message, not a raw KeyError.
        if item_type not in self.spec.items:
            # `dropped_via_selected` is the shared "bundled type the active spec no longer
            # declares" check (`_workflow/__init__.py`), also used by the loader and
            # `resolve_item_id_typed`.
            if dropped_via_selected(item_type, self.spec):
                raise SquadsError(
                    f"unknown item type {item_type!r}: {item_type!r} was dropped from a "
                    "[selected] list (selected.items) in .overrides/workflow.toml, not left "
                    "undeclared — add it back to selected.items to restore it"
                )
            raise SquadsError(
                f"unknown item type {item_type!r}: no spec supplied, or the spec does not "
                "declare this type. Declare it in .overrides/workflow.toml or check for a typo."
            )
        require_title(title)
        slug = slug or (operator_slug(title) if item_type == ROSTER_OPERATOR else slugify(title))
        is_roster = self.spec.item_is_roster(item_type)
        _check_roster_slug(item_type, is_roster, slug)
        self._check_operator_slug_free(db, item_type, slug)
        if refs:
            # Validate every declared kind, then rewrite to the canonical wire form, as `add_ref`
            # does: an edge of the default kind is written bare. Done at the one pure seam every
            # create path shares.
            default_kind = self.spec.default_ref_kind()
            normalised_refs: list[str] = []
            for ref_str in refs:
                rid, kind = split_ref(ref_str)
                # A bare/unspelled kind ("") is always valid — it names whichever declared
                # entry carries role="default", which is guaranteed to exist and be accepted.
                if kind and kind not in self.spec.ref_kinds:
                    valid = ", ".join(sorted(self.spec.ref_kinds))
                    raise SquadsError(f"unknown ref kind {kind!r}. Valid kinds: {valid}")
                normalised_refs.append(make_ref(rid, "" if kind == default_kind else kind))
            refs = normalised_refs
        if body is not None:
            reject_markers(body)
        effective_now = now if now is not None else clock.now()
        if parent:
            self._check_parent(db, item_type, parent)
        if not author:
            raise SquadsError("author is required: the actor's slug")
        self._check_author(db, item_type, author, slug)
        self._check_assignee(db, assignee)
        # Resolve the prefix from the spec before allocation so both the filename and
        # Item.id agree on the correct prefix.
        resolved_prefix = prefix_for(item_type, self.spec)
        # item_id is the padded filename stem (SquadsDB.allocate_id formats at db.padding);
        # deliberately NOT the same width as the displayed Item.id.
        item_id = db.allocate_id(item_type, prefix=resolved_prefix)
        filename = f"{item_id}-{slug}.md"
        squad_rel = self.paths.squad_relative(item_type, filename, spec=self.spec)
        sid, _psid = actor.current_session()
        item = Item(
            sequence_id=db.counter,
            type=str(item_type),
            prefix=resolved_prefix,
            title=title,
            slug=slug,
            status=str(status) if status is not None else self.spec.initial_status(item_type),
            description=description,
            parent=parent,
            author=author,
            assignee=assignee,
            labels=labels or [],
            refs=refs or [],
            path=squad_rel,
            created_at=effective_now,
            updated_at=effective_now,
            created_session=sid,
            modified_session=sid,
            slug_in_file=is_roster,
            attributes=attributes or {},
        )
        _stamp_origin(item, self.spec)
        self._set_declared_fields(item, fields or {})
        db.add(item)
        # Fail-closed on the new item's first error-level catalog violation (parent
        # type-eligibility, item status validity, …) — the same engine `sq check` reports.
        ValidatorEngine(spec=self.spec, playbook=self.playbook).gate(item, db)
        # Advisory lane check on the declared author slug, exempting the default role first; the
        # service never prints, the warning rides back in the result. Only types some playbook guide
        # declares an author for are lane-checked, resolved through the active spec and playbook.
        lane_warning: str | None = None
        if (
            item_type in laned_types(self.playbook)
            and not is_lane_exempt(
                author,
                self._default_role_slug(db) or catalog_default_slug(self.catalog()),
            )
            and item_type
            not in allowed_create_types(self._role_like(db, author), self.spec, self.playbook)
        ):
            owners = in_lane_owner(item_type, self.playbook, self._live_role_likes(db))
            owner_str = (
                ", ".join(f"'{s}'" for s in sorted(owners)) if owners else "no defined owner"
            )
            lane_warning = (
                f"advisory: '{author}' is not the in-lane author for '{item_type}' items"
                f" (expected: {owner_str})."
                " Lane checks are best-effort and advisory — proceeding."
            )
        return item, lane_warning

    def _set_declared_fields(self, item: Item, given: dict[str, str]) -> None:
        """Store each *given* field value on a new *item*, then the declared default of every
        field still unset. A code the type does not declare is refused."""
        for code, value in given.items():
            field = self._badge_field(item.type, code)
            if field is None:
                raise SquadsError(f"{code!r} is not a declared field for {item.type}")
            item.set_badge_value(field.code, self._parse_badge_code(field, value))
        for field in self.spec.fields_for(item.type):
            if item.badge_value(field.code) is None and (
                default := self.field_default(item.type, field.code)
            ):
                item.set_badge_value(field.code, default)

    async def _create_core(  # noqa: PLR0913 — mirrors `create`'s own keyword surface
        self,
        db: SquadsDB,
        item_type: str,
        title: str,
        *,
        description: str = "",
        parent: str | None = None,
        author: str | None = None,
        labels: list[str] | None = None,
        refs: list[str] | None = None,
        assignee: str | None = None,
        attributes: dict[str, Any] | None = None,
        status: str | None = None,
        slug: str | None = None,
        body: str | None = None,
        fields: dict[str, str] | None = None,
    ) -> CreateResult:
        """The create mutation core: takes an already-open transaction's ``db``, runs
        :meth:`_create_model`, then renders + writes the file and logs the reflog op.

        Shared by the interactive :meth:`create` (which opens its own transaction) and the
        bulk importer (which calls this directly inside its one open transaction — the
        store's file lock is not reentrant, so the importer cannot call :meth:`create` itself).
        """
        item, lane_warning = self._create_model(
            db,
            item_type,
            title,
            description=description,
            parent=parent,
            author=author,
            labels=labels,
            refs=refs,
            assignee=assignee,
            attributes=attributes,
            status=status,
            slug=slug,
            body=body,
            fields=fields,
        )
        item_type = item.type
        # ``agents/role.md.j2`` is only the file scaffold: a `sq:body` seeding the
        # ``sq:view:role_definition`` tag. The definition renders at read time
        # (`squads._view_tags.expand_view_tags`), not from anything computed here.
        rendered = render(
            self._template_for(item_type),
            item=item,
            description=item.description,
            spec=self.spec,
            from_squad=self.paths.squad_dir,
        )
        # Guarantee a working sub-entity container whatever template rendered: a custom type falls
        # back to `_default.md.j2` (none) and a renamed kind's bundled template hardcodes its old
        # tag. A no-op when the template already emitted it.
        rendered = ensure_subentity_container_text(self.spec, item_type, rendered)
        # The re-placement routine runs on creation too, so a seeded view lands at its declared
        # position. Template-hardcoded view tags are stripped first as stale scaffolding, so
        # `seeded` alone decides what lands.
        host_slug = item.slug
        addr: int | str = (
            host_slug if item_type in (ROSTER_ROLE, ROSTER_SKILL) else number_for_id(item.id)
        )
        template_region = view_tags.strip_view_tags(
            sections.get_section(rendered, markers.BODY) or ""
        )
        new_inner = view_tags.place_view_tags(
            template_region,
            body,
            seeded=views.seeded_view_names(
                item_type, host_slug, self.spec, from_squad=self.paths.squad_dir
            ),
            spec=self.spec,
            item_type=item_type,
            addr=addr,
        )
        if sections.get_section(rendered, markers.BODY) is None:
            raise SquadsError(
                f"the {item_type} creation template renders no body region; "
                "check its project override under .overrides/templates/"
            )
        rendered = sections.replace_section(rendered, markers.BODY, new_inner)
        squad_rel = item.path
        await self._write_new_item_file(self.paths.abspath(squad_rel), item, rendered)
        log_delta: dict[str, object] = {
            "title": item.title,
            "type": item_type,
            "status": item.status,
        }
        if lane_warning is not None:
            log_delta["lane_warning"] = {
                "advisory": True,
                "actor": item.author,
                "expected": sorted(
                    in_lane_owner(item_type, self.playbook, self._live_role_likes(db))
                ),
                "type": item_type,
            }
        self.store.log(
            "create",
            item.id,
            log_delta,
        )
        return CreateResult(
            item=item, path=self.paths.abspath(squad_rel), lane_warning=lane_warning
        )

    @staticmethod
    def check_role_slug(slug: str) -> None:
        """Raise when *slug* may not name a role: outside the slug grammar, or reserved. The one
        check every role creation verb runs before it writes."""
        _check_roster_slug(ROSTER_ROLE, True, slug)

    async def get(self, item_id: str) -> Item:
        """Return *item_id* as a deep copy, so no two callers share an object: one snapshot may
        serve many callers in an invocation (``squads._index._store.read_scope``), and an in-place
        mutation must not contaminate a later read.
        """
        item = require_item(await self.store.load(), item_id)
        return item.model_copy(deep=True)

    def _type_folders(self) -> Iterator[tuple[str, ItemSpec, Path]]:
        """``(type, its spec, its folder)`` for every declared type whose folder exists, in each
        type's ``order`` (name breaking a tie) -- the one order every corpus walk follows."""
        for item_type, ts in sorted(self.spec.items.items(), key=lambda kv: (kv[1].order, kv[0])):
            folder = self.paths.squad_dir / ts.folder
            if folder.is_dir():
                yield item_type, ts, folder

    def _all_item_files(self) -> list[Path]:
        """Every markdown file in every type folder, whatever it is named."""
        return [
            md
            for _item_type, _ts, folder in self._type_folders()
            for md in sorted(folder.glob("*.md"))
        ]

    async def duplicate_files(self, item: Item) -> list[Path]:
        """The other files carrying *item*'s id, by the detector's rule (frontmatter id).

        Only files whose name could carry the item's number, or carries no number at all, are
        read; a file named for a different number that still carries this id is `check`'s and
        `repair`'s to find. Empty when *item*'s own file is missing, so the caller's
        missing-file error is the one reported."""
        own = item_file(self.paths, item)
        key = normalized_id(item.id)
        if key is None or not own.is_file():
            return []
        candidates = [
            md
            for md in self._all_item_files()
            if md != own and name_number(md.name) in (item.sequence_id, None)
        ]
        return [md for md in candidates if await read_id(md) == key]

    async def duplicate_id_error(self, item: Item) -> str | None:
        """The refusal text when another file carries *item*'s id, else ``None``."""
        others = await self.duplicate_files(item)
        if not others:
            return None
        named = ", ".join(
            p.relative_to(self.paths.squad_dir).as_posix()
            for p in sorted([item_file(self.paths, item), *others])
        )
        return f"{item.id}: {len(others) + 1} files carry this id ({named})"

    async def _refuse_duplicated_ids(self, *items: Item) -> None:
        """Refuse, before any file is touched, a write whose subject or referrer is an id more
        than one file carries: it would land on whichever copy the scan reached."""
        for item in items:
            message = await self.duplicate_id_error(item)
            if message is not None:
                raise SquadsError(f"{message}; refusing to write -- {DUPLICATE_ID_REMEDY}")

    async def _refuse_any_duplicated_id(self) -> None:
        """Refuse a write that may rewrite any file (an id rename touches every mention) while
        some id is carried by more than one file."""
        groups = await groups_among(self._all_item_files())
        for key, files in groups.items():
            named = ", ".join(p.relative_to(self.paths.squad_dir).as_posix() for p in files)
            raise SquadsError(
                f"{key}: {len(files)} files carry this id ({named}); refusing a write that "
                f"could touch them -- {DUPLICATE_ID_REMEDY}"
            )

    async def _read_item_file(self, item: Item, path: Path) -> str:
        """Read *item*'s file at *path*, turning a missing file into an actionable error: the read
        seam for show/body/discussion/comment and for write seams needing the text. An interrupted
        title-changing update or retype can leave *path* stale. It uses
        :func:`~squads._itemfile.read_item_text`, whose message names the item and points at ``sq
        repair``; callers reading the file as a signal keep using ``_aio.read_text``.
        """
        held = self.store.held_item_files()
        if held is None:
            return await read_item_text(path, item.id)
        if path in held.texts:
            return held.texts[path]
        return await read_item_text(held.disk_path(path), item.id)

    async def _write_item_file(self, path: Path, text: str) -> None:
        """Write *text* to the existing item file at *path*, or hold it for the flush of
        :meth:`_deferred_item_writes` when a hold is open."""
        held = self.store.held_item_files()
        if held is None:
            await write_text(path, text)
        else:
            held.texts[path] = text

    async def _write_new_item_file(self, path: Path, item: Item, rendered_body: str) -> None:
        """Create the item file at *path*, or hold its text for the flush of
        :meth:`_deferred_item_writes` when a hold is open."""
        held = self.store.held_item_files()
        if held is None:
            await write_new(path, item, rendered_body)
        else:
            held.texts[path] = new_item_text(item, rendered_body)

    async def _update_item_frontmatter(
        self, item: Item, base: Item, *, rescaffold: bool = False
    ) -> None:
        """Rewrite *item*'s frontmatter in its file, refusing a file that has skewed from
        *base*: the read-check-write of :func:`~squads._itemfile.update_frontmatter`, over the
        text :meth:`_read_item_file` sees."""
        path = item_file(self.paths, item)
        text = await self._read_item_file(item, path)
        ensure_no_skew(text, base, default_kind=self.spec.default_ref_kind())
        new_text = sections.replace_frontmatter(text, item.to_frontmatter_dict(), source=str(path))
        if rescaffold:
            new_text = self._rescaffolded_body(new_text, item, base)
        await self._write_item_file(path, new_text)

    def _rescaffolded_body(self, text: str, item: Item, base: Item) -> str:
        """An item's *text* with its ``sq:body`` region re-rendered for *item*'s new type,
        title, description and fields when the region is still *base*'s unwritten scaffold, so
        an edit never makes the scaffold read as written. View tags keep their places;
        a written body is untouched."""
        if self._classified_view(item) is not None:
            return text  # the body comes from a view
        region = sections.get_section(text, markers.BODY)
        old, new = self.pristine_body(base), self.pristine_body(item)
        if region is None or new is None or new == old:
            return text  # nothing in the scaffold changed
        if not view_tags.strip_view_tags(region).strip():
            return text  # a tag alone is the seeded shape, not the template
        if not view_tags.body_is_unwritten(region, old):
            return text
        slug = item.slug
        inner = view_tags.place_view_tags(
            region.strip("\n"),
            view_tags.strip_view_tags(new).strip(),
            seeded=views.seeded_view_names(
                item.type, slug, self.spec, from_squad=self.paths.squad_dir
            ),
            spec=self.spec,
            item_type=item.type,
            addr=slug,
        )
        return sections.replace_section(text, markers.BODY, inner)

    async def _item_file_exists(self, path: Path) -> bool:
        """Whether an item file exists at *path*, on disk or held."""
        held = self.store.held_item_files()
        if held is None:
            return await _aio.path_exists(path)
        if path in held.texts or path in held.moves.values():
            return True
        return path not in held.moves and await _aio.path_exists(path)

    async def _move_item_file(self, old: Path, new: Path) -> None:
        """Move an item file from *old* to *new*, or hold the move for the flush of
        :meth:`_deferred_item_writes` when a hold is open; a text held for *old* moves with it."""
        held = self.store.held_item_files()
        if held is None:
            if await _aio.path_exists(old):
                await _aio.path_rename(old, new)
            return
        origin = held.disk_path(old)
        if origin != old or await _aio.path_exists(old):
            held.moves[origin] = new
        text = held.texts.pop(old, None)
        if text is not None:
            held.texts[new] = text

    @asynccontextmanager
    async def _deferred_item_writes(self) -> AsyncGenerator[None]:
        """Hold every item-file write made inside the block in memory, then write each touched
        file once, in first-touch order, when the block ends normally; a raise discards them.

        A file moved inside the block is renamed at the flush, just before its write. Must be
        opened inside a transaction, so the flush precedes the index commit; opening one
        inside another is refused.
        """
        held = self.store.open_held_item_files()
        try:
            yield
            moves = {final: origin for origin, final in held.moves.items()}
            for path, text in held.texts.items():
                await _aio.mkdir(path.parent, parents=True, exist_ok=True)
                if path in moves:
                    await _aio.path_rename(moves.pop(path), path)
                await write_text(path, text)
            for final, origin in moves.items():
                await _aio.mkdir(final.parent, parents=True, exist_ok=True)
                await _aio.path_rename(origin, final)
        finally:
            self.store.close_held_item_files()

    async def list_items(
        self,
        *,
        item_type: str | None = None,
        status: str | None = None,
        parent: str | None = None,
        label: str | None = None,
        assignee: str | None = None,
        category: str | None = None,
        badges: dict[str, str] | None = None,
        badge_min: dict[str, str] | None = None,
    ) -> list[Item]:
        """List items matching every given filter dimension. ``category`` narrows to one of
        ``roster``/``work``/``records`` (validated at the CLI edge). ``badges``/``badge_min`` are
        keyed by badge field code, generic over ``fields_for()``; ``badge_min`` only matches ordered
        collections (:meth:`ItemFilter._meets_min`).
        """
        f = ItemFilter(
            item_type=str(item_type) if item_type is not None else None,
            status=str(status) if status is not None else None,
            parent=parent,
            label=label,
            assignee=assignee,
            category=category,
            badges=tuple((badges or {}).items()),
            badge_min=tuple((badge_min or {}).items()),
            spec=self.spec,
        )
        out: list[Item] = []
        for it in (await self.store.load()).items.values():
            if not f.matches(it):
                continue
            out.append(it)
        return sorted(out, key=lambda i: number_for_id(i.id))

    async def tree_view(
        self,
        root_id: str | None = None,
        *,
        filter: ItemFilter | None = None,
        depth: int | None = None,
        include_closed: bool = False,
    ) -> list[TreeNode]:
        """Return the filtered, depth-bounded item hierarchy as root ``TreeNode`` s. Closed items
        are dropped unless ``include_closed``; roots are ``root_id``, else parentless items in view
        plus one anchor per cycle (``_cycle_anchor_ids``). The keep set is the matches plus their
        ancestors (``path_only=True``), walked down to ``depth``, and roots with no kept descendants
        and no match are dropped.
        """
        db = await self.store.load()
        all_items_list = list(db.items.values())

        # Step 1: candidate set — default visibility keyed on the status's role (settled +
        # hidden work/roster items drop out; an in-force record like Accepted/Published stays
        # visible; see WorkflowSpec.hidden_by_default).
        candidates: list[Item] = (
            all_items_list
            if include_closed
            else [i for i in all_items_list if not self.spec.hidden_by_default(i.type, i.status)]
        )

        # Step 2: build maps
        id_map: dict[str, Item] = {i.id: i for i in candidates}
        children_map: dict[str | None, list[Item]] = _build_tree_children(candidates)
        seq_to_id: dict[int, str] = {number_for_id(i.id): i.id for i in candidates}

        # Step 3: determine root(s)
        if root_id is not None:
            if root_id not in id_map:
                what = "item" if include_closed else "open item"
                raise SquadsError(
                    f"no {what} {root_id!r} to root the tree"
                    " (add --all to include closed items, or check it exists)"
                )
            root_items: list[Item] = [id_map[root_id]]
            # An explicitly rooted tree roots where the caller asked: nothing is fabricated
            # here, so nothing is marked. Rooting inside a cycle already rendered the component
            # correctly before this change and still does.
            anchor_ids: set[str] = set()
        else:
            # Widens "no resolvable parent in view" to "no resolvable acyclic path to a root",
            # on the same candidate graph the grouping resolved parents against.
            anchor_ids = _cycle_anchor_ids(candidates)
            forest = [*children_map.get(None, []), *(id_map[a] for a in anchor_ids)]
            root_items = sorted(forest, key=lambda i: number_for_id(i.id))

        # Step 4: compute match set (all candidates when filter is empty)
        effective_filter = filter if filter is not None else ItemFilter()
        match_set: set[str] = (
            {i.id for i in candidates}
            if effective_filter.is_empty()
            else {i.id for i in candidates if effective_filter.matches(i)}
        )

        # Step 5 + 6 + 7: compute keep set, walk down, prune and apply depth
        keep_set = _compute_keep_set(match_set, id_map, seq_to_id)
        result: list[TreeNode] = []
        for r in root_items:
            node = _walk_tree(
                r,
                0,
                keep_set=keep_set,
                match_set=match_set,
                children_map=children_map,
                depth=depth,
                anchor=r.id in anchor_ids,
            )
            if node is not None:
                result.append(node)
        return result

    def _check_parent(self, db: SquadsDB, child_type: str, parent_id: str) -> None:
        """Existence-only pre-check: a genuinely missing parent id is caught here, before the
        item enters the transaction, so it stays ``ItemNotFoundError`` (a distinct type/message
        from the engine's ``dangling parent`` report text). Parent-*type* eligibility is the
        catalog's ``parent_in``/``no_parent`` — enforced by the ``ValidatorEngine.gate()`` call
        every create/update/link site makes right after, not duplicated here.
        """
        del child_type
        if db.get(parent_id) is None:
            raise ItemNotFoundError(f"parent {parent_id!r} does not exist")

    def _is_participant(self, db: SquadsDB, slug: str) -> bool:
        """A slug that can author/be-assigned work: a registered role agent or a human operator.

        Skills are roster types but NOT participants — only role and operator are. The catalog's
        ``agent_registered`` validator is warn-level (report-only) but reads the same set.
        """
        return any(
            self.spec.item_is_roster(it.type) and it.type != ROSTER_SKILL and it.slug == slug
            for it in db.items.values()
        )

    def _check_author(self, db: SquadsDB, item_type: str, author: str, slug: str) -> None:
        # a roster type (role/skill/operator) definition may self-author (bootstrap)
        if self.spec.item_is_roster(item_type) and author == slug:
            return
        if not self._is_participant(db, author):
            raise SquadsError(
                f"author {author!r} is not a registered role or operator — register it first"
            )

    def _check_assignee(self, db: SquadsDB, assignee: str | None) -> None:
        # an assignee is optional, but when set it must name a participant (a role or an operator)
        if assignee and not self._is_participant(db, assignee):
            raise SquadsError(
                f"assignee {assignee!r} is not a registered role or operator — register it first"
            )

    def _badge_field(self, item_type: str, key: str) -> Field | None:
        """The declared field for *key* on *item_type*, generic over every axis (``--set
        <field>=<code>``): every declared axis alike — not a
        hand-maintained allowlist of attribute-backed codes."""
        return next((f for f in self.spec.fields_for(item_type) if f.code == key), None)

    def field_default(self, type_or_kind: str, code: str) -> str | None:
        """The badge code an omitted field falls back to: the field's own ``default``,
        else its collection's ``default``, else ``None`` (generic — no field/collection
        special-cased by name). Public: create and the CLI's generic add-<kind> builder
        both resolve an omitted field through it."""
        field = next((f for f in self.spec.fields_for(type_or_kind) if f.code == code), None)
        if field is None:
            return None
        if field.default:
            return field.default
        coll = self.spec.collections.get(field.collection)
        return coll.default if coll else None

    def _parse_badge_code(self, field: Field, raw: str) -> str:
        """Validate/normalize a ``--set <field>=<code>`` value against its bound collection."""
        coll = self.spec.collection(field.collection)
        code = raw.strip().lower()
        if code not in coll.badge_codes:
            choices = ", ".join(b.code for b in coll.badges)
            raise SquadsError(f"invalid {field.code} {raw!r} (one of: {choices})")
        return code

    # ------------------------------------------------------------------ shared helpers
    async def _locked_section_edit(
        self, item_id: str, mutate: Callable[[str, Item], tuple[str, bool]]
    ) -> tuple[Item, bool]:
        """Edit an item's prose under the index lock, atomically with the ``updated_at`` bump.

        Opens its own transaction, then delegates to :meth:`_section_edit_core` — the
        bulk importer calls that core directly (its own transaction is already open).
        """
        async with self.store.transaction() as db:
            return await self._section_edit_core(db, item_id, mutate)

    async def _section_edit_core(
        self, db: SquadsDB, item_id: str, mutate: Callable[[str, Item], tuple[str, bool]]
    ) -> tuple[Item, bool]:
        """The section-edit core: takes an already-open transaction's ``db`` and adds any region the
        file lacks before ``mutate(text, item)`` runs. ``mutate`` (a sync callable that may raise to
        abort before any write) returns ``(new_text, changed)``; when ``changed`` is ``False`` the
        file is not rewritten and ``updated_at`` does not bump. ``base`` is captured before
        ``mutate``, this being the second write seam, after
        :func:`~squads._itemfile.update_frontmatter`, that rewrites frontmatter from an index-
        derived ``Item``.
        """
        it = require_item(db, item_id)
        await self._refuse_duplicated_ids(it)
        base = it.model_copy(deep=True)
        path = item_file(self.paths, it)
        text = await self._read_item_file(it, path)
        ensure_no_skew(text, base, default_kind=self.spec.default_ref_kind())
        text = discussion.restore_regions(
            text,
            it,
            self.spec.item_subentity_kind(it.type),
            self.spec,
            from_squad=self.paths.squad_dir,
        )
        new_text, changed = mutate(text, it)
        if not changed:
            return it, False
        it.updated_at = clock.now()
        it.modified_session, _ = actor.current_session()
        await self._write_item_file(
            path, sections.replace_frontmatter(new_text, it.to_frontmatter_dict())
        )
        return it, True

    # ------------------------------------------------------------------ role / skill lookups
    # One-line delegates over the roster projection, for the callers outside the mixins.
    async def roster_item(self, item_type: str, slug: str) -> Item | None:
        """The roster item of *item_type* whose slug matches, or ``None``."""
        return await self.roster_projection.roster_item(item_type, slug)

    async def author(self, slug: str) -> str:
        """Display (full) name for a participant slug; falls back to the slug if unknown."""
        return await self.roster_projection.author(slug)

    async def roster(self) -> list[RoleView]:
        """The roles this squad currently offers."""
        return await self.roster_projection.roster()

    def roster_from_db(self, db: SquadsDB) -> list[RoleView]:
        """:meth:`roster`, computed against an already-loaded *db*."""
        return self.roster_projection.roster_from_db(db)

    async def roster_all(self) -> list[RoleView]:
        """Every role entry regardless of status."""
        return await self.roster_projection.roster_all()

    async def operators(self) -> list[OperatorView]:
        """The operators this squad currently offers."""
        return await self.roster_projection.operators()

    async def operators_all(self) -> list[OperatorView]:
        """Every operator entry regardless of status."""
        return await self.roster_projection.operators_all()

    async def resolve_participant(self, slug: str, *, live_only: bool = True) -> str:
        """Validate *slug* against the roster (agents and operators) and return it normalised.

        Raises :class:`SquadsError` naming the valid slugs when it is unknown; the legacy anonymous
        sentinel is not validated. With *live_only* a retired entry is refused, naming the entry and
        the command that reactivates it; a read or a filter by a participant passes ``False`` so a
        retired role's items and mentions stay reachable.
        """
        normalised = slug.lstrip("@").lower()
        if normalised == ANONYMOUS_SLUG:
            return normalised
        if live_only:
            agent_slugs = [r.slug for r in await self.roster()]
            operator_slugs = [o.slug for o in await self.operators()]
            if normalised in agent_slugs or normalised in operator_slugs:
                return normalised
            retired = await self._retired_participant_hint(normalised)
            if retired is not None:
                raise SquadsError(retired)
        else:
            agent_slugs = [r.slug for r in await self.roster_all()]
            operator_slugs = [o.slug for o in await self.operators_all()]
            if normalised in agent_slugs or normalised in operator_slugs:
                return normalised
        valid = sorted(agent_slugs + operator_slugs)
        hint = (
            ", ".join(valid) if valid else "(none registered — run `sq init` or `sq operator add`)"
        )
        raise SquadsError(f"unknown slug {slug!r}; valid slugs: {hint}")

    async def _retired_participant_hint(self, slug: str) -> str | None:
        """The retired-entry refusal for *slug*, or ``None`` when no roster entry has it."""
        role = await self.roster_item(ROSTER_ROLE, slug)
        if role is not None:
            target = self.spec.live_initial(ROSTER_ROLE)
            return (
                f"{slug!r} ({role.id}) is retired; reactivate it with `sq role {slug} status "
                f"{target}`"
            )
        op = await self.roster_item(ROSTER_OPERATOR, slug)
        if op is not None:
            target = self.spec.live_initial(ROSTER_OPERATOR)
            return (
                f"{slug!r} ({op.id}) is retired; reactivate it with `sq operator {slug} status "
                f"{target}`"
            )
        return None

    async def adopt_declared_actor(self) -> None:
        """Validate the actor the request declares against the live roster and record it
        normalised; without one the actor stays the system's."""
        declared = actor.declared_actor()
        if declared is not None:
            actor.set_actor(await self.resolve_participant(declared))

    async def resolve_any_id(self, token: str) -> str:
        """The id of whatever item owns *token*'s number; a full id's prefix must be its owner's."""
        seq, given_prefix = parse_item_token(token)
        item = (await self.store.load()).get(str(seq))
        if item is None:
            hint = format_item_id("TYPE", seq, DISPLAY_ID_PADDING)
            raise ItemNotFoundError(
                f"no item with number {seq} (use a full ID like {hint} or bare {seq})"
            )
        if given_prefix is not None and given_prefix != effective_prefix(item.prefix):
            raise SquadsError(f"{token} is {item.id} ({item.type})")
        return item.id

    async def resolved_skills_for_role(self, slug: str) -> list[str]:
        """A live role's full preload-skill set."""
        return await self.roster_projection.resolved_skills_for_role(slug)

    async def refresh_managed(self) -> list[str]:
        """(Re)write every active backend's roster/version-dependent files; returns the warnings."""
        return await self.roster_projection.refresh_managed()

    async def candidate_orphans(self) -> list[str]:
        """WARN-only candidate-orphan pointer/skill files across every active backend."""
        return await self.roster_projection.candidate_orphans()

    # ------------------------------------------------------------------ corpus reading
    async def _skill_folder_state(self, scan: SkillScan) -> SkillFolder:
        """The skill folder's files and who carries which id and slug; built once per scan and
        given the index's skill items only if some file could be restamped."""
        if scan.state is None:
            texts = {md.name: text for md, text in (await self._read_skill_texts(scan)).items()}
            state = SkillFolder.build(texts, self.spec)
            if state.needs_index:
                state = state.with_index(await self._indexed_skills(scan))
            scan.state = state
        return scan.state

    async def _read_skill_texts(self, scan: SkillScan) -> dict[Path, str]:
        """The stamped skill files' text: what this scan already read, else read now."""
        if scan.texts is not None:
            return scan.texts
        folder = self.paths.squad_dir / self.spec.items[ROSTER_SKILL].folder
        texts: dict[Path, str] = {}
        if folder.is_dir():
            for md in sorted(folder.glob(f"{prefix_for(ROSTER_SKILL, self.spec)}-*.md")):
                with contextlib.suppress(OSError):
                    texts[md] = await _aio.read_text(md)
        return texts

    @staticmethod
    async def _scan_text(md: Path, scan: SkillScan) -> str:
        """A file's text for the ``check`` scan: the up-front skill read if it has one."""
        cached = scan.texts.get(md) if scan.texts else None
        return cached if cached is not None else await _aio.read_text(md)

    async def _indexed_skills(self, scan: SkillScan | None = None) -> list[Item]:
        """The skill items the index holds, or none when there is no readable index -- the
        restamp treats the index as a hint and never needs it."""
        if scan is not None and scan.items is not None:
            return scan.items
        if not self.store.exists():
            return []
        with contextlib.suppress(SquadsError):
            return await self.list_items(item_type=ROSTER_SKILL)
        return []

    async def _skill_remedy(self, md: Path, item_type: str, scan: SkillScan) -> str | None:
        """The remedy a report line gives for a stamped managed-skill file, else ``None``."""
        if item_type != ROSTER_SKILL or stamped_skill_slug(md, self.spec) is None:
            return None
        if stamped_skill_slug(md, self.spec) not in managed_skill_slugs(self.spec):
            state = await self._skill_folder_state(scan)
            if not state.known:
                state = state.with_index(await self._indexed_skills(scan))
            return state.stray_remedy(md.name, self.spec)
        return remedy_text((await self._skill_folder_state(scan)).verdict(md.name, self.spec))

    async def _id_carriers(self, log: CarrierLog | None = None) -> list[tuple[object, Path]]:
        """``(frontmatter id, file)`` for every item file whose frontmatter parses and has an
        ``id`` -- the one input the duplicate-id detector groups. Files a scan already read
        (*log*) are not read again."""
        carriers: list[tuple[object, Path]] = list(log.pairs) if log else []
        seen = log.seen if log else set[Path]()
        # Every markdown file in a type folder, not only the ones named for its prefix: a copy
        # of another type's file dropped here carries the id all the same.
        for md in self._all_item_files():
            if md in seen:
                continue
            with contextlib.suppress(OSError, SquadsError):
                fid = sections.split_frontmatter(await _aio.read_text(md))[0].get("id")
                if fid:
                    carriers.append((fid, md))
        return carriers

    def _duplicate_id_message(self, files: list[Path]) -> SelfRemedied:
        """The report line for an id carried by several files, naming every one."""
        named = ", ".join(f.relative_to(self.paths.squad_dir).as_posix() for f in files)
        return SelfRemedied(f"{len(files)} files carry this id ({named}); {DUPLICATE_ID_REMEDY}")

    def _shared_number_message(
        self, number: int, files: list[Path], remedy: str = SHARED_NUMBER_REMEDY
    ) -> str:
        """The report line for a number carried under different ids, naming every file and the
        *remedy* to run."""
        named = ", ".join(f.relative_to(self.paths.squad_dir).as_posix() for f in files)
        return f"{len(files)} files carry number {number} under different ids ({named}); {remedy}"

    async def _missing_id_message(self, md: Path, item_type: str, scan: SkillScan) -> str:
        """The "no ``id``" report line; a stamped managed-skill file also names the remedy that
        works for its state."""
        remedy = await self._skill_remedy(md, item_type, scan)
        msg = "file has no `id` in frontmatter"
        return SelfRemedied(f"{msg}; {remedy}") if remedy else msg

    # ------------------------------------------------------------------ scan helpers
    def _iter_item_files(self) -> Iterator[tuple[str, Path]]:
        """Yield (item_type, markdown path) for every item file, for every type the active spec
        declares in ``ItemSpec.order`` then type name, which fixes the scan order collision
        resolution relies on. Skill files match the ``PREFIX-*.md`` glob and legacy slug-named files
        are yielded too, for the repair/check callers to skip when they lack an ``id``.
        """
        for item_type, ts, folder in self._type_folders():
            prefix = ts.prefix
            if item_type == ROSTER_SKILL:
                # Convention files follow SKILL-*.md (post-migration / fresh init).
                # Also include legacy <slug>.md files so pre-migration squads can still be
                # repaired/checked (they will be silently skipped by callers that require an id).
                convention = sorted(folder.glob(f"{prefix}-*.md"))
                legacy = sorted(md for md in folder.glob("*.md") if not md.name.startswith(prefix))
                yield from ((item_type, md) for md in convention + legacy)
            else:
                yield from ((item_type, md) for md in sorted(folder.glob(f"{prefix}-*.md")))
