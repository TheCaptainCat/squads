"""The shared service core: state, backend access, and the primitives every concern builds on.

Each concern lives in its own ``_services/_*.py`` mixin subclassing ``ServiceCore``; the public
``Service`` (in ``_service.py``) multiply-inherits them. ``ServiceCore`` defines what's used across
concerns (create/get/list, the backend, the role/skill lookups + roster projection) so the mixins
only ever call core methods + their own.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from squads import _actor as actor
from squads import _aio
from squads import _clock as clock
from squads import _sections as sections
from squads._backends._base import AgentBackend, BackendContext, OperatorView, RoleView
from squads._backends._registry import get_backend
from squads._errors import ItemNotFoundError, SquadsError
from squads._index._resolver import item_file, require_item
from squads._index._store import IndexStore
from squads._interactions import (
    LANED_TYPES,
    allowed_create_types,
    in_lane_owner,
    is_lane_exempt,
)
from squads._itemfile import write_new
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import VALID_REF_KINDS, Item, split_ref
from squads._models._vocab import prefix_for
from squads._paths import SquadPaths, number_for_id
from squads._rendering._engine import render, set_active_squad_dir
from squads._roles._resolver import resolve_role
from squads._services._results import CreateResult, TreeNode
from squads._util import slugify
from squads._workflow import META_OPERATOR, META_ROLE, META_SKILL, bundled_spec
from squads._workflow._models import WorkflowSpec


# Body-local sub-entities: kind <-> parent item type, and the kind's container marker.
#
# These are derived from the ACTIVE spec's per-type `subentity_kind` (forward edge, invariant
# #4) rather than a hand-maintained literal dict, and rather than the bundled default — a
# project-declared type/kind must be visible here too. Free functions (not module constants)
# because the active spec is per-service, not global; ServiceCore exposes them as instance
# properties below so mixins read `self.subentity_parent`/`self.subentity_kind`/
# `self.subentity_container` and non-mixin callers (e.g. retype) pass a spec explicitly.
def subentity_parent_map(spec: WorkflowSpec) -> dict[str, str]:
    """Sub-entity kind -> ONE hosting item type, inverted from the spec's declared
    ``ItemSpec.subentity_kind``.

    The type<->kind relation is 1:many (two item types may declare the same kind, e.g.
    a project-declared type mirroring ``task``'s ``subentity_kind="subtask"``) — this
    inversion collapses that to a single representative type per kind, so it is only a
    naming HINT (e.g. for a help string) and must never back an ownership/validation
    decision. Use ``spec.item_subentity_kind(item.type) == kind`` (forward, 1:1) for that.
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
    #: Exact badge-field filters, keyed by field CODE (e.g. ``priority``, or a project's own
    #: custom axis) — generic over ``fields_for()``, not a hand-written priority-only param.
    badges: tuple[tuple[str, str], ...] = ()
    #: Threshold badge-field filters (ordered collections only): (field code, minimum code).
    #: Resolving "at least as high as" needs the field's declared collection, so this variant
    #: is only usable when ``spec`` is set.
    badge_min: tuple[tuple[str, str], ...] = ()
    #: The active spec — needed only to resolve ``badge_min`` rank; ``None`` disables it.
    spec: WorkflowSpec | None = None

    def matches(self, it: Item) -> bool:
        """Return True iff *it* satisfies every non-None dimension of this filter."""
        base = (
            (not self.item_type or it.type == self.item_type)
            and (not self.status or it.status == self.status)
            and (not self.parent or it.parent == self.parent)
            and (not self.label or self.label in it.labels)
            and (not self.assignee or it.assignee == self.assignee)
        )
        if not base:
            return False
        if any(it.badge_value(code) != want for code, want in self.badges):
            return False
        return all(self._meets_min(it, code, min_code) for code, min_code in self.badge_min)

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
                self.badges,
                self.badge_min,
            )
        )


def _compute_keep_set(
    match_set: set[str],
    id_map: dict[str, Item],
    seq_to_id: dict[int, str],
) -> set[str]:
    """Return match_set UNION all ancestors of each matched item.

    Walks parent links upward through the candidate set (width-tolerant via sequence
    numbers).  Items whose parent is not in the candidate set are treated as roots.
    """
    keep_set: set[str] = set(match_set)
    for mid in match_set:
        item = id_map.get(mid)
        while item is not None and item.parent is not None:
            p_seq = number_for_id(item.parent)
            canonical = seq_to_id.get(p_seq)
            if canonical is None or canonical not in id_map:
                break
            keep_set.add(canonical)
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
) -> TreeNode | None:
    """Recursive downward walk that prunes to *keep_set* and bounds to *depth*.

    Returns ``None`` when the node should be dropped (not in keep set, or is a
    path-only anchor with no surviving children).  ``depth`` is measured from the
    root (root = level 0); ``None`` means unbounded.
    """
    if it.id not in keep_set:
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
            )
            if child_node is not None:
                child_nodes.append(child_node)
    # Drop a path_only anchor with no surviving children (would be an empty branch)
    if path_only and not child_nodes:
        return None
    return TreeNode(item=it, path_only=path_only, children=child_nodes)


def _build_tree_children(
    listed: list[Item],
) -> dict[str | None, list[Item]]:
    """Group items by their canonical parent ID (width-tolerant).

    ``item.parent`` may store an old zero-pad width after ``sq migrate repad`` while
    ``item.id`` uses the current width.  Resolving via sequence number makes the tree
    correct across a repad boundary.

    Used by ``tree_view`` and shared by any future caller that needs the same
    parent-resolution logic; keeps parent resolution in one place.
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


def reject_markers(text: str, what: str = "body") -> None:
    """Raise ``SquadsError`` when *text* contains a well-formed sq marker tag.

    All prose inputs that land inside marker-delimited regions must pass through
    this guard before any file write.  The ``what`` label appears in the message
    (e.g. ``"body"``, ``"comment message"``, ``"title"``).

    For the legacy ``"body"`` label the message is kept verbatim so existing
    callers and tests stay unchanged.  All other labels get the extended message
    that points the author at a safe formulation.
    """
    if not sections.find_markers(text):
        return
    if what == "body":
        raise SquadsError("body must not contain sq marker comments (<!-- sq:… -->)")
    raise SquadsError(
        f"{what} must not contain sq marker comments (<!-- sq:… -->). "
        "Write the tag without its HTML-comment wrapper (e.g. sq:body rather than "
        "the comment form) — backtick-wrapping does not neutralize a well-formed tag."
    )


class ServiceCore:
    def __init__(self, paths: SquadPaths, spec: WorkflowSpec | None = None):
        self.paths = paths
        # Use the supplied spec, or fall back to the immutable bundled default.
        # open_service() always supplies the resolved (possibly overridden) spec;
        # sq init / sq adopt construct Service(sp) without an override spec, which
        # is fine because they operate on a fresh squad with no override file yet.
        self.spec: WorkflowSpec = spec if spec is not None else bundled_spec()
        self.store = IndexStore(paths.index_path, paths.lock_path, spec=self.spec)
        # Activate the squad-aware template search path so render() picks up any project
        # overrides under <squad_dir>/.overrides/templates/ for this service's squad.
        set_active_squad_dir(paths.squad_dir)

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
        """Return the Jinja2 template path for ``item_type``.

        Built-in types have a dedicated ``items/<type>.md.j2`` and are returned
        directly.  Custom types (no per-type template) fall back to the generic
        ``items/_default.md.j2`` so ``svc.create('incident', …)`` does not raise
        ``TemplateNotFound``.  The fallback is resolved via the Jinja2 environment's
        ``has_template`` check so user-supplied overrides in
        ``.overrides/templates/items/<type>.md.j2`` are still honoured.
        """
        if self.spec.item_is_meta(item_type):
            return f"agents/{item_type}.md.j2"
        per_type = f"items/{item_type}.md.j2"
        from squads._rendering._engine import has_template

        if has_template(per_type):
            return per_type
        return "items/_default.md.j2"

    # ------------------------------------------------------------------ backend
    @property
    def _ctx(self) -> BackendContext:
        return BackendContext(paths=self.paths, spec=self.spec)

    def _backends(self) -> list[AgentBackend]:
        """Return one backend instance for each active (deduped) backend name.

        Empty ``active_backends`` returns an empty list (sq-only squad).
        """
        return [get_backend(name) for name in self.paths.config.active_backends]

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
        priority: str | None = None,
        extra: dict[str, Any] | None = None,
        status: str | None = None,
        slug: str | None = None,
        body: str | None = None,
    ) -> CreateResult:
        item_type = str(item_type)  # coerce StrEnum members to plain str
        slug = slug or slugify(title)
        author = author or self.paths.config.default_role
        if refs:
            for ref_str in refs:
                _, kind = split_ref(ref_str)
                if kind not in VALID_REF_KINDS:
                    valid = ", ".join(sorted(VALID_REF_KINDS))
                    raise SquadsError(f"unknown ref kind {kind!r}. Valid kinds: {valid}")
        now = clock.now()
        async with self.store.transaction() as db:
            if parent:
                self._check_parent(db, item_type, parent)
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
                priority=priority,
                labels=labels or [],
                refs=refs or [],
                path=squad_rel,
                created_at=now,
                updated_at=now,
                created_session=sid,
                modified_session=sid,
                extra=extra or {},
            )
            rendered = render(
                self._template_for(item_type), item=item, description=description, extra=item.extra
            )
            if body is not None:
                reject_markers(body)
                rendered = sections.replace_section(rendered, markers.BODY, body)
            await write_new(self.paths.abspath(squad_rel), item, rendered)
            db.add(item)
            # Advisory lane check, keyed on the declared author slug. Exempt before lookup.
            # Service must NOT print — warning rides back in the result.
            # Only laned item types (those in LANED_TYPES) participate in the lane domain;
            # internal artifact types (role, skill, operator) are never lane-checked.
            lane_warning: str | None = None
            if (
                item_type in LANED_TYPES
                and not is_lane_exempt(author)
                and item_type not in allowed_create_types(author)
            ):
                owners = in_lane_owner(item_type)
                owner_str = (
                    ", ".join(f"'{s}'" for s in sorted(owners)) if owners else "no defined owner"
                )
                lane_warning = (
                    f"advisory: '{author}' is not the in-lane author for '{item_type}' items"
                    f" (expected: {owner_str})."
                    " Lane checks are best-effort and advisory — proceeding."
                )
            log_delta: dict[str, object] = {
                "title": item.title,
                "type": item_type,
                "status": item.status,
            }
            if lane_warning is not None:
                log_delta["lane_warning"] = {
                    "advisory": True,
                    "actor": author,
                    "expected": sorted(in_lane_owner(item_type)),
                    "type": item_type,
                }
            self.store._log(  # pyright: ignore[reportPrivateUsage]
                "create",
                item.id,
                log_delta,
            )
        return CreateResult(
            item=item, path=self.paths.abspath(squad_rel), lane_warning=lane_warning
        )

    async def get(self, item_id: str) -> Item:
        return require_item(await self.store.load(), item_id)

    async def list_items(
        self,
        *,
        item_type: str | None = None,
        status: str | None = None,
        parent: str | None = None,
        label: str | None = None,
        assignee: str | None = None,
        badges: dict[str, str] | None = None,
        badge_min: dict[str, str] | None = None,
    ) -> list[Item]:
        """List items matching every given filter dimension.

        ``badges``/``badge_min`` are keyed by badge field CODE (e.g. ``"priority"``, or a
        project's own custom axis) — generic over ``fields_for()``, not a dedicated param
        per axis. ``badge_min`` only matches ordered collections
        (see :meth:`ItemFilter._meets_min`).
        """
        f = ItemFilter(
            item_type=str(item_type) if item_type is not None else None,
            status=str(status) if status is not None else None,
            parent=parent,
            label=label,
            assignee=assignee,
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
        """Return the filtered, depth-bounded item hierarchy as a list of root ``TreeNode`` s.

        Algorithm:

        1. Load candidate set — all items; drop closed ones unless ``include_closed``.
        2. Build parent→children map and id→item map via ``_build_tree_children``.
        3. Determine roots: explicit ``root_id`` → that item; else the parentless forest.
        4. Compute match set = items that satisfy ``filter`` (all items when filter is
           None/empty).
        5. Compute keep set = match set UNION all ancestors of each matched item.
           Ancestors not themselves in the match set are flagged ``path_only=True``.
        6. Single downward walk: include a node iff it is in the keep set; stop recursing
           when the next level would exceed ``depth`` (depth measured from each root = 0).
           Depth wins — a match deeper than the cut is not shown.
        7. Drop empty/orphaned roots (roots with no kept descendants and not themselves a
           match).
        """
        db = await self.store.load()
        all_items_list = list(db.items.values())

        # Step 1: candidate set
        candidates: list[Item] = (
            all_items_list
            if include_closed
            else [i for i in all_items_list if self.spec.is_open(i.status)]
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
        else:
            root_items = sorted(children_map.get(None, []), key=lambda i: number_for_id(i.id))

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
            )
            if node is not None:
                result.append(node)
        return result

    def _check_parent(self, db: SquadsDB, child_type: str, parent_id: str) -> None:
        parent = db.get(parent_id)
        if parent is None:
            raise ItemNotFoundError(f"parent {parent_id!r} does not exist")
        if not self.spec.parent_allowed(child_type, parent.type):
            raise SquadsError(f"{self.spec.parent_hint(child_type)} (got {parent.type})")

    def _is_participant(self, db: SquadsDB, slug: str) -> bool:
        """A slug that can author/be-assigned work: a registered role agent or a human operator.

        Skills are meta-types but NOT participants — only role and operator are.
        ``item_is_meta(t) and t != META_SKILL`` expresses the same set.
        """
        return any(
            self.spec.item_is_meta(it.type)
            and it.type != META_SKILL
            and it.extra.get(X.SLUG) == slug
            for it in db.items.values()
        )

    def _check_author(self, db: SquadsDB, item_type: str, author: str, slug: str) -> None:
        # a meta-type (role/skill/operator) definition may self-author (bootstrap)
        if self.spec.item_is_meta(item_type) and author == slug:
            return
        if not self._is_participant(db, author):
            raise SquadsError(
                f"author {author!r} is not a registered agent or operator — register it first"
            )

    def _check_assignee(self, db: SquadsDB, assignee: str | None) -> None:
        # an assignee is optional, but when set it must name a participant (a role or an operator)
        if assignee and not self._is_participant(db, assignee):
            raise SquadsError(
                f"assignee {assignee!r} is not a registered agent or operator — register it first"
            )

    # ------------------------------------------------------------------ shared helpers
    async def _locked_section_edit(self, item_id: str, mutate: Callable[[str, Item], str]) -> Item:
        """Edit an item's prose under the index lock, atomically with the ``updated_at`` bump.

        ``mutate(text, item)`` returns the new file text (sync callable — may raise to abort
        before any write). The whole read → mutate → write happens within one ``transaction()``,
        so concurrent ``sq`` processes (e.g. parallel subagents commenting on the same item)
        can't lose each other's edits.
        """
        async with self.store.transaction() as db:
            it = require_item(db, item_id)
            path = item_file(self.paths, it)
            text = await _aio.read_text(path)
            new_text = mutate(text, it)
            it.updated_at = clock.now()
            it.modified_session, _ = actor.current_session()
            await _aio.write_text(
                path, sections.replace_frontmatter(new_text, it.to_frontmatter_dict())
            )
        return it

    # ------------------------------------------------------------------ role / skill lookups
    async def _role_item(self, slug: str) -> Item | None:
        for it in (await self.store.load()).items.values():
            if it.type == META_ROLE and it.extra.get(X.SLUG) == slug:
                return it
        return None

    async def role_body(self, slug: str) -> str | None:
        """Return the body-region content of the active role item for ``slug``, or None.

        Returns ``None`` when no tracked item exists for this slug (bundled-only role).
        The returned string is stripped of leading/trailing newlines.
        """
        item = await self._role_item(slug)
        if item is None:
            return None
        text = await _aio.read_text(item_file(self.paths, item))
        body = sections.get_section(text, markers.BODY)
        if body is None:
            return None
        return body.strip("\n")

    async def _skill_item(self, slug: str) -> Item | None:
        for it in (await self.store.load()).items.values():
            if it.type == META_SKILL and it.extra.get(X.SLUG, it.slug) == slug:
                return it
        return None

    async def _operator_item(self, slug: str) -> Item | None:
        for it in (await self.store.load()).items.values():
            if it.type == META_OPERATOR and it.extra.get(X.SLUG) == slug:
                return it
        return None

    async def author(self, slug: str) -> str:
        """Display (full) name for a participant slug; falls back to the slug if unknown."""
        if slug == "operator":
            return "Operator"
        participant = await self._role_item(slug) or await self._operator_item(slug)
        if participant is not None:
            return participant.extra.get(X.FULL_NAME, slug)
        try:
            return resolve_role(slug, self.paths.squad_dir).full_name
        except SquadsError:
            return slug

    async def roster(self) -> list[RoleView]:
        return [
            RoleView(
                slug=it.extra.get(X.SLUG, it.slug),
                full_name=it.extra.get(X.FULL_NAME, it.title),
                title=it.extra.get(X.TITLE, it.title),
                is_default=it.extra.get(X.IS_DEFAULT, False),
            )
            for it in await self.list_items(item_type=META_ROLE)
        ]

    async def operators(self) -> list[OperatorView]:
        return [
            OperatorView(
                slug=it.extra.get(X.SLUG, it.slug),
                full_name=it.extra.get(X.FULL_NAME, it.title),
            )
            for it in await self.list_items(item_type=META_OPERATOR)
        ]

    async def _skill_paths(self) -> dict[str, Path]:
        """Build a slug→absolute-body-path map for all SKILL items in the index.

        Backends receive this via BackendContext so they never need to load the
        index themselves (layering invariant: _backends must not import _index).
        """
        skill_items = await self.list_items(item_type=META_SKILL)
        return {
            it.extra[X.SLUG]: self.paths.abspath(it.path)
            for it in skill_items
            if X.SLUG in it.extra
        }

    async def refresh_managed(self) -> None:
        skill_map = await self._skill_paths()
        ctx = BackendContext(paths=self.paths, skill_paths=skill_map, spec=self.spec)
        roster = await self.roster()
        ops = await self.operators()
        for backend in self._backends():
            await backend.write_managed(ctx, roster, ops)
