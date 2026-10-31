"""Bulk event import engine (``sq import``): a validate-first pre-pass and a single-transaction
apply (:meth:`ImportMixin.import_events`). The pre-pass runs each op's pure ``_X_model`` half, id
allocation included, on a throwaway deep copy of the index and pre-flights the skew guard
from each targeted ``.md``, since an apply-time refusal would leave the batch partly applied; the
apply runs ``_X_core`` on the real ``db`` in one transaction, rebinding clock and actor per event.
"""

from dataclasses import dataclass, field
from datetime import datetime

from pydantic import ValidationError

from squads import _actor as actor
from squads import _aio
from squads import _clock as clock
from squads import _sections as sections
from squads._context import bind_context, get_context
from squads._errors import SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import frontmatter_skew, skew_message
from squads._models import _markers as markers
from squads._models._index import SquadsDB
from squads._models._item import make_ref, split_ref
from squads._models._participants import refuse_system_actor, require_valid_slug
from squads._services._base import reject_markers, reject_non_view_markers
from squads._services._collab import CollabMixin
from squads._services._import_model import (
    AddSubEvent,
    AssignEvent,
    BodyEvent,
    CommentEvent,
    CreateEvent,
    ImportEvent,
    RefEvent,
    ResolvedEvent,
    StatusEvent,
    SubBodyEvent,
    SubStatusEvent,
    UpdateEvent,
    parse_events,
    utc_now_floor,
)
from squads._services._items import ItemsMixin
from squads._services._refs import RefsMixin
from squads._services._results import (
    CheckIssue,
    ImportApplyResult,
    ImportIssue,
    ImportOpCount,
    ImportPlan,
    ImportResult,
    check_issue_sort_key,
)
from squads._services._subentities import SubentitiesMixin
from squads._services._validators import ValidatorEngine
from squads._workflow._models import ROSTER_ROLE, Field, WorkflowSpec

#: Exception types the per-event dispatch collects as validation problems rather than bugs:
#: ``SquadsError`` subclasses, and the pydantic ``ValidationError`` from building an
#: ``Item``/``SubEntity`` with a bad value.
_COLLECTIBLE: tuple[type[Exception], ...] = (SquadsError, ValidationError)


@dataclass
class HandleMap:
    """Client-handle resolution: ``handle -> allocated item id`` and, for sub-entities,
    ``handle -> (parent item id, local id)`` — built up as creating events are (simulated or
    really) applied, in file order. A later event's ``target``/``to``/``parent``/``maps_to``
    resolves against this first, falling back to the literal token when it names no handle."""

    items: dict[str, str] = field(default_factory=lambda: dict[str, str]())
    subentities: dict[str, tuple[str, str]] = field(
        default_factory=lambda: dict[str, tuple[str, str]]()
    )

    def resolve_item(self, token: str) -> str:
        """The real item id for *token*: a registered handle resolves to its allocated id;
        anything else passes through unchanged (assumed to already be a literal id)."""
        return self.items.get(token, token)

    def resolve_local(self, parent_id: str | None, token: str) -> str:
        """The real local id for *token*: a registered sub-entity handle resolves to its local id
        (raising if it belongs to a different parent than *parent_id*); anything else passes through
        as a literal local id. ``parent_id=None`` skips the cross-check.
        """
        entry = self.subentities.get(token)
        if entry is None:
            return token
        sub_parent, local_id = entry
        if parent_id is not None and sub_parent != parent_id:
            raise SquadsError(
                f"handle {token!r} names a sub-entity of {sub_parent}, not {parent_id}"
            )
        return local_id


def _resolve_refs(handles: HandleMap, refs: list[str], spec: WorkflowSpec) -> list[str]:
    """Resolve every ``"ID-or-handle"`` / ``"ID-or-handle:kind"`` token in *refs*, validating
    the kind against *spec*'s declared ``ref_kinds`` — the same hard check ``create()``/
    ``add_ref()`` run before ever touching the transaction. A spelled kind that names the
    declared default is written back out bare, so an imported ``:related``-style token
    normalises to the wire form ``add_ref`` itself would have written.
    """
    default_kind = spec.default_ref_kind()
    out: list[str] = []
    for ref_str in refs:
        rid, kind = split_ref(ref_str)
        if kind and kind not in spec.ref_kinds:
            valid = ", ".join(sorted(spec.ref_kinds))
            raise SquadsError(f"unknown ref kind {kind!r}. Valid kinds: {valid}")
        wire_kind = "" if kind == default_kind else kind
        out.append(make_ref(handles.resolve_item(rid), wire_kind))
    return out


def _event_target_token(event: ImportEvent) -> str | None:
    """The raw ``target``/handle token an event names, or ``None`` for a create (which
    names no existing item — there is nothing for the batch skew pre-flight to check).
    Every other event carries a ``target`` field, sub-entity events included: the host
    item is what the frontmatter rewrite touches, whatever local id inside it changed."""
    return None if isinstance(event, CreateEvent) else event.target


def _comment_selector(
    handles: HandleMap, target: str, event: CommentEvent
) -> tuple[str, str] | None:
    """The one ``(kind, local_id)`` a comment event addresses, or ``None`` for the item itself;
    a handle resolves to its local id."""
    if event.sub is None:
        return None
    kind, local_or_handle = event.sub
    return kind, handles.resolve_local(target, local_or_handle)


def _field_for(spec: WorkflowSpec, type_or_kind: str, code: str) -> Field | None:
    return next((f for f in spec.fields_for(type_or_kind) if f.code == code), None)


def _parse_badge_code(spec: WorkflowSpec, declared: Field, raw: str) -> str:
    coll = spec.collection(declared.collection)
    code = raw.strip().lower()
    if code not in coll.badge_codes:
        choices = ", ".join(b.code for b in coll.badges)
        raise SquadsError(f"invalid {declared.code} {raw!r} (one of: {choices})")
    return code


def _resolve_fields(
    spec: WorkflowSpec, type_or_kind: str, fields: dict[str, str]
) -> dict[str, str]:
    """Validate a ``create``/``add-sub`` event's badge-code map against *type_or_kind*'s
    declared fields — the vocabulary check ``_create_model``/``_add_block_model`` don't run
    themselves (they take an already-resolved code), so the importer resolves it up front,
    the same way :meth:`~squads._services._items.ItemsMixin._apply_attributes` does for
    ``update``'s ``--set``."""
    out: dict[str, str] = {}
    for code, raw in fields.items():
        declared = _field_for(spec, type_or_kind, code)
        if declared is None:
            raise SquadsError(f"{code!r} is not a declared field for {type_or_kind}")
        out[declared.code] = _parse_badge_code(spec, declared, raw)
    return out


class ImportMixin(ItemsMixin, CollabMixin, SubentitiesMixin, RefsMixin):
    """The bulk-import engine; :meth:`import_events` is its entry point. It inherits every mutation
    mixin whose ``_X_model``/``_X_core`` pair it reuses, the one exception to one-concern-per-file,
    so the type checker sees the method set ``self`` has at runtime.
    """

    # ------------------------------------------------------------------ entry point
    async def import_events(
        self,
        text: str,
        *,
        default_at: datetime | None = None,
        default_as: str | None = None,
        dry_run: bool = False,
    ) -> ImportResult:
        """Parse, validate, and (unless *dry_run* or the pre-pass found an issue) apply a JSONL
        event stream. ``default_at``/``default_as`` are the file-level fallbacks for an event with
        no ``at``/``as`` of its own and no prior event to inherit from; ``default_at`` falls back to
        now, while ``default_as`` has none, so an event with no actor becomes an issue naming the
        missing actor.
        """
        effective_default_at = default_at if default_at is not None else utc_now_floor()

        events, parse_issues = parse_events(
            text, spec=self.spec, default_at=effective_default_at, default_as=default_as
        )
        plan = await self._plan_import(events)
        # Parse-time issues (bad JSON, an unrecognised op, …) merge into the pre-pass's own
        # issue list, line-ordered — the caller sees ONE ordered error list either way.
        all_issues = sorted([*parse_issues, *plan.issues], key=lambda i: i.line)
        plan = ImportPlan(
            op_counts=plan.op_counts,
            handle_to_id=plan.handle_to_id,
            handle_to_sub=plan.handle_to_sub,
            issues=all_issues,
        )
        if not plan.ok or dry_run:
            return ImportResult(plan=plan)
        applied = await self._apply_import(events)
        return ImportResult(plan=plan, applied=applied)

    # ------------------------------------------------------------------ validate-first pre-pass
    async def _plan_import(self, events: list[ResolvedEvent]) -> ImportPlan:
        """Resolve every handle, simulate id allocation, and check every event against the active
        spec, writing nothing and collecting every error. ``shadow`` is a throwaway deep copy of the
        index, so bumping its counter leaves the real one in ``self.store`` untouched. It also pre-
        flights the skew guard once per targeted pre-existing item.
        """
        shadow = (await self.store.load()).model_copy(deep=True)
        pre_existing_seqs = set(shadow.items)
        handles = HandleMap()
        counts = ImportOpCount()
        issues: list[ImportIssue] = []
        skew_checked: set[int] = set()
        # Resolved once, outside the per-event try/except: a spec declaring the wrong number of
        # default ref kinds must fail the call once, not be re-reported as a per-event ImportIssue.
        default_kind = self.spec.default_ref_kind()
        for ev in events:
            counts.bump(ev.op_name)
            try:
                await self._check_target_skew(
                    shadow,
                    handles,
                    ev,
                    pre_existing_seqs,
                    skew_checked,
                    issues,
                    default_kind=default_kind,
                )
                if isinstance(ev.event, BodyEvent):
                    await self._check_body_view_tags(shadow, handles, ev.event)
                self._simulate_one(shadow, handles, ev)
            except _COLLECTIBLE as exc:
                issues.append(ImportIssue(line=ev.line, message=str(exc)))
        return ImportPlan(
            op_counts=counts,
            handle_to_id=dict(handles.items),
            handle_to_sub=dict(handles.subentities),
            issues=issues,
        )

    async def _check_body_view_tags(
        self, shadow: SquadsDB, handles: HandleMap, event: BodyEvent
    ) -> None:
        """Run the apply pass's placed-view-tag comparison against the target's current
        ``sq:body`` region: its file for an item that exists, its creation scaffold for one this
        import creates. A missing file or region is left to the apply pass to report."""
        item = shadow.get(handles.resolve_item(event.target))
        if item is None:
            return
        try:
            text = await _aio.read_text(item_file(self.paths, item))
        except FileNotFoundError:
            region = self.pristine_body(item)
        else:
            region = sections.get_section(text, markers.BODY)
        if region is not None:
            self._refuse_unplaced_view_tags(item, region.strip("\n"), event.body)

    async def _check_target_skew(
        self,
        shadow: SquadsDB,
        handles: HandleMap,
        ev: ResolvedEvent,
        pre_existing_seqs: set[int],
        checked: set[int],
        issues: list[ImportIssue],
        *,
        default_kind: str,
    ) -> None:
        """Skew-check each *pre-existing* item once, on the first event that targets it (never for a
        handle created in this import). Later divergence from disk is the import's own pending
        delta, so a second check would false-refuse. It runs before :meth:`_simulate_one`, so
        ``shadow.get(target)`` is still the unmutated base, and only ever adds a skew issue.
        """
        token = _event_target_token(ev.event)
        if token is None:
            return
        target_id = handles.resolve_item(token)
        item = shadow.get(target_id)
        if item is None or item.sequence_id not in pre_existing_seqs:
            return
        if item.sequence_id in checked:
            return
        checked.add(item.sequence_id)
        base = item.model_copy(deep=True)
        try:
            text = await _aio.read_text(item_file(self.paths, item))
        except FileNotFoundError:
            return  # on-disk reconciliation is `sq check`'s claim to make, not this guard's
        diverging = frontmatter_skew(text, base, default_kind=default_kind)
        if diverging:
            issues.append(ImportIssue(line=ev.line, message=skew_message(base, diverging)))

    def _simulate_one(self, shadow: SquadsDB, handles: HandleMap, ev: ResolvedEvent) -> None:
        """One per-op dispatch — mirrors :meth:`_apply_one`'s shape (validate side)."""
        event = ev.event
        if isinstance(event, CreateEvent):
            self._sim_create(shadow, handles, ev, event)
        elif isinstance(event, StatusEvent):
            target = handles.resolve_item(event.target)
            self._set_status_model(shadow, target, event.status, force=event.force, now=ev.at)
        elif isinstance(event, BodyEvent):
            self._sim_body(shadow, handles, event)
        elif isinstance(event, CommentEvent):
            self._sim_comment(shadow, handles, event, ev.actor)
        elif isinstance(event, RefEvent):
            from_id = handles.resolve_item(event.target)
            to_id = handles.resolve_item(event.to)
            self._add_ref_model(shadow, from_id, to_id, kind=event.kind, now=ev.at)
        elif isinstance(event, AddSubEvent):
            self._sim_add_sub(shadow, handles, ev, event)
        elif isinstance(event, SubStatusEvent):
            target = handles.resolve_item(event.target)
            local_id = handles.resolve_local(target, event.local)
            self._set_block_status_model(
                shadow,
                target,
                event.kind,
                local_id,
                event.status,
                force=event.force,
                deferred_to=handles.resolve_item(event.deferred_to) if event.deferred_to else None,
                now=ev.at,
            )
        elif isinstance(event, SubBodyEvent):
            self._sim_sub_body(shadow, handles, event)
        elif isinstance(event, AssignEvent):
            self._sim_assign(shadow, handles, ev, event)
        else:  # UpdateEvent — the last member of the exhaustive ImportEvent union
            self._sim_update(shadow, handles, ev, event)

    def _sim_create(
        self, shadow: SquadsDB, handles: HandleMap, ev: ResolvedEvent, event: CreateEvent
    ) -> None:
        if event.type not in self.spec.items:
            raise SquadsError(f"unknown item type {event.type!r}")
        parent = handles.resolve_item(event.parent) if event.parent else None
        resolved_refs = _resolve_refs(handles, event.refs, self.spec)
        resolved_fields = _resolve_fields(self.spec, event.type, event.fields)
        item, _lane_warning = self._create_model(
            shadow,
            event.type,
            event.title,
            description=event.description,
            parent=parent,
            author=ev.actor,
            labels=list(event.labels),
            refs=resolved_refs,
            assignee=event.assignee,
            status=event.status,
            slug=event.slug,
            body=event.body,
            fields=resolved_fields,
            now=ev.at,
        )
        if item.type == ROSTER_ROLE:
            raise SquadsError(
                f"an import does not create the role {item.slug!r}: a role needs a base. Create "
                "it with `sq role add <slug> …`, `sq role activate <slug>` or "
                "`sq role activate --from <template>`"
            )
        if event.handle:
            handles.items[event.handle] = item.id

    def _sim_body(self, shadow: SquadsDB, handles: HandleMap, event: BodyEvent) -> None:
        target = handles.resolve_item(event.target)
        item = require_item(shadow, target)
        # Delegates to the exact predicate the real apply pass's `_body_mutate` closure asks —
        # see `ItemsMixin._reject_unwritable_body`'s own docstring for why a second, hand-rolled
        # membership test here would be exactly the drift a single derivation exists to prevent.
        self._reject_unwritable_body(target, item, append=event.append)
        reject_non_view_markers(event.body)

    def _sim_comment(
        self, shadow: SquadsDB, handles: HandleMap, event: CommentEvent, actor_slug: str
    ) -> None:
        require_valid_slug(actor_slug, action="write a comment")
        refuse_system_actor(actor_slug)
        target = handles.resolve_item(event.target)
        item = require_item(shadow, target)
        messages = event.all_messages()
        if not messages:
            raise SquadsError("a comment needs at least one message")
        for msg in messages:
            reject_markers(msg, "comment message")
        sub = _comment_selector(handles, target, event)
        if sub is not None:
            self._find(item, sub[0], sub[1])

    def _sim_add_sub(
        self, shadow: SquadsDB, handles: HandleMap, ev: ResolvedEvent, event: AddSubEvent
    ) -> None:
        target = handles.resolve_item(event.target)
        parent_item = shadow.get(target)
        story = (
            handles.resolve_local(parent_item.parent if parent_item else None, event.maps_to)
            if event.maps_to
            else None
        )
        resolved_fields = _resolve_fields(self.spec, event.kind, event.fields)
        item, sub, _base = self._add_block_model(
            shadow,
            target,
            event.kind,
            event.title,
            maps_to=story,
            fields=resolved_fields,
            assignee=event.assignee,
            status=event.status,
            deferred_to=handles.resolve_item(event.deferred_to) if event.deferred_to else None,
            body=event.body,
            now=ev.at,
        )
        if event.handle:
            handles.subentities[event.handle] = (item.id, sub.local_id)

    def _sim_sub_body(self, shadow: SquadsDB, handles: HandleMap, event: SubBodyEvent) -> None:
        target = handles.resolve_item(event.target)
        item = self._require_parent(shadow, target, event.kind)
        local_id = handles.resolve_local(target, event.local)
        self._find(item, event.kind, local_id)
        reject_markers(event.body)

    def _sim_assign(
        self, shadow: SquadsDB, handles: HandleMap, ev: ResolvedEvent, event: AssignEvent
    ) -> None:
        target = handles.resolve_item(event.target)
        if event.kind and event.local:
            local_id = handles.resolve_local(target, event.local)
            self._set_block_assignee_model(
                shadow, target, event.kind, local_id, event.assignee, now=ev.at
            )
        else:
            self._update_model(shadow, target, assignee=event.assignee or "", now=ev.at)

    @staticmethod
    def _clears_nothing(db: SquadsDB, target: str, event: UpdateEvent) -> bool:
        """Whether *event* only removes an assignee the target does not have: no write."""
        return event.only_clears_assignee() and require_item(db, target).assignee is None

    def _sim_update(
        self, shadow: SquadsDB, handles: HandleMap, ev: ResolvedEvent, event: UpdateEvent
    ) -> None:
        target = handles.resolve_item(event.target)
        parent = handles.resolve_item(event.parent) if event.parent else None
        if self._clears_nothing(shadow, target, event):
            return
        self._update_model(
            shadow,
            target,
            title=event.title,
            description=event.description,
            assignee=event.assignee,
            clear_assignee=event.clear_assignee,
            add_labels=list(event.add_labels) or None,
            rm_labels=list(event.rm_labels) or None,
            status=event.status,
            force=event.force,
            parent=parent,
            clear_parent=event.clear_parent,
            set_attributes=dict(event.fields) or None,
            unset_attributes=list(event.unset_fields) or None,
            now=ev.at,
        )

    # ------------------------------------------------------------------ apply
    async def _apply_import(self, events: list[ResolvedEvent]) -> ImportApplyResult:
        """Apply every event in one open transaction: real ids from the real counter, each touched
        file written once when the deferred block closes, and a reflog entry per event under that
        event's actor and clock. Only called after a clean pre-pass, so a failure here is I/O, and
        the store's files-then-index order leaves the index uncommitted for ``sq repair``.
        """
        handles = HandleMap()
        counts = ImportOpCount()
        warnings: list[str] = []
        touched_ids: set[str] = set()
        async with self.store.transaction() as db, self._deferred_item_writes():
            for ev in events:
                counts.bump(ev.op_name)
                prior = get_context()
                try:
                    clock.set_now(ev.at)
                    actor.set_actor(ev.actor)
                    touched_ids |= await self._apply_one(db, handles, ev, warnings)
                finally:
                    bind_context(prior)
        findings = await self._board_debt_findings(touched_ids)
        warnings.extend(f"{f.item}: {f.message}" for f in findings if f.level != "error")
        return ImportApplyResult(
            op_counts=counts,
            handle_to_id=dict(handles.items),
            handle_to_sub=dict(handles.subentities),
            created_ids=sorted(touched_ids & set(handles.items.values())),
            warnings=warnings,
            findings=findings,
        )

    async def _board_debt_findings(self, touched_ids: set[str]) -> list[CheckIssue]:
        """The ``sq check`` catalog (unwritten bodies, over-long titles, ...) scoped to the items
        this import touched, read post-commit and in ``sq check`` print order. Squad-global
        validators are excluded. The ``CheckIssue`` objects are returned whole and unfiltered, so an
        error-level finding stays distinguishable from an advisory one.
        """
        if not touched_ids:
            return []
        final_db = await self.store.load()
        bodies: dict[int, str] = {}
        for item_id in touched_ids:
            item = final_db.get(item_id)
            if item is None:
                continue
            bodies[item.sequence_id] = await self._read_item_file(item, item_file(self.paths, item))
        engine = ValidatorEngine(
            spec=self.spec, playbook=self.playbook, squad_global={}, paths=self.paths
        )
        issues = engine.report(final_db, {}, bodies=bodies, only=frozenset(touched_ids))
        return sorted((i for i in issues if i.item in touched_ids), key=check_issue_sort_key)

    async def _apply_one(  # noqa: PLR0911 — one per-op dispatch, mirrors _simulate_one's shape
        self, db: SquadsDB, handles: HandleMap, ev: ResolvedEvent, warnings: list[str]
    ) -> set[str]:
        event = ev.event
        if isinstance(event, CreateEvent):
            parent = handles.resolve_item(event.parent) if event.parent else None
            resolved_refs = _resolve_refs(handles, event.refs, self.spec)
            resolved_fields = _resolve_fields(self.spec, event.type, event.fields)
            result = await self._create_core(
                db,
                event.type,
                event.title,
                description=event.description,
                parent=parent,
                author=ev.actor,
                labels=list(event.labels),
                refs=resolved_refs,
                assignee=event.assignee,
                status=event.status,
                slug=event.slug,
                body=event.body,
                fields=resolved_fields,
            )
            if event.handle:
                handles.items[event.handle] = result.item.id
            if result.lane_warning:
                warnings.append(result.lane_warning)
            return {result.item.id}
        if isinstance(event, StatusEvent):
            target = handles.resolve_item(event.target)
            item, _severed, _warnings = await self._set_status_core(
                db, target, event.status, force=event.force
            )
            return {item.id}
        if isinstance(event, BodyEvent):
            target = handles.resolve_item(event.target)
            mutate = self._body_mutate(target, event.body, append=event.append, force=event.force)
            item, _changed = await self._section_edit_core(db, target, mutate)
            return {item.id}
        if isinstance(event, CommentEvent):
            return {await self._apply_comment(db, handles, event, ev.actor)}
        if isinstance(event, RefEvent):
            from_id = handles.resolve_item(event.target)
            to_id = handles.resolve_item(event.to)
            item = await self._add_ref_core(db, from_id, to_id, kind=event.kind)
            return {item.id}
        if isinstance(event, AddSubEvent):
            return await self._apply_add_sub(db, handles, event, warnings)
        if isinstance(event, SubStatusEvent):
            target = handles.resolve_item(event.target)
            local_id = handles.resolve_local(target, event.local)
            await self._set_block_status_core(
                db,
                target,
                event.kind,
                local_id,
                event.status,
                force=event.force,
                deferred_to=handles.resolve_item(event.deferred_to) if event.deferred_to else None,
            )
            return {require_item(db, target).id}
        if isinstance(event, SubBodyEvent):
            target = handles.resolve_item(event.target)
            local_id = handles.resolve_local(target, event.local)
            mutate = self._block_body_mutate(
                event.kind, local_id, event.body, append=event.append, force=event.force
            )
            item, _changed = await self._section_edit_core(db, target, mutate)
            return {item.id}
        if isinstance(event, AssignEvent):
            return {await self._apply_assign(db, handles, event)}
        # UpdateEvent — the last member of the exhaustive ImportEvent union
        return {await self._apply_update(db, handles, event)}

    async def _apply_comment(
        self, db: SquadsDB, handles: HandleMap, event: CommentEvent, actor_slug: str
    ) -> str:
        target = handles.resolve_item(event.target)
        sub = _comment_selector(handles, target, event)
        item, _written = await self._comment_core(
            db,
            target,
            event.all_messages(),
            as_slug=actor_slug,
            sub=sub,
        )
        return item.id

    async def _apply_add_sub(
        self, db: SquadsDB, handles: HandleMap, event: AddSubEvent, warnings: list[str]
    ) -> set[str]:
        target = handles.resolve_item(event.target)
        parent_item = db.get(target)
        story = (
            handles.resolve_local(parent_item.parent if parent_item else None, event.maps_to)
            if event.maps_to
            else None
        )
        resolved_fields = _resolve_fields(self.spec, event.kind, event.fields)
        result = await self._add_block_core(
            db,
            target,
            event.kind,
            event.title,
            maps_to=story,
            fields=resolved_fields,
            assignee=event.assignee,
            status=event.status,
            deferred_to=handles.resolve_item(event.deferred_to) if event.deferred_to else None,
            body=event.body,
        )
        if event.handle:
            handles.subentities[event.handle] = (target, result.local_id)
        if result.title_advisory:
            warnings.append(result.title_advisory)
        return {target}

    async def _apply_assign(self, db: SquadsDB, handles: HandleMap, event: AssignEvent) -> str:
        target = handles.resolve_item(event.target)
        if event.kind and event.local:
            local_id = handles.resolve_local(target, event.local)
            await self._set_block_assignee_core(db, target, event.kind, local_id, event.assignee)
            return target
        item = await self._update_core(db, target, assignee=event.assignee or "")
        return item.id

    async def _apply_update(self, db: SquadsDB, handles: HandleMap, event: UpdateEvent) -> str:
        target = handles.resolve_item(event.target)
        parent = handles.resolve_item(event.parent) if event.parent else None
        if self._clears_nothing(db, target, event):
            return target
        item = await self._update_core(
            db,
            target,
            title=event.title,
            description=event.description,
            assignee=event.assignee,
            clear_assignee=event.clear_assignee,
            add_labels=list(event.add_labels) or None,
            rm_labels=list(event.rm_labels) or None,
            status=event.status,
            force=event.force,
            parent=parent,
            clear_parent=event.clear_parent,
            set_attributes=dict(event.fields) or None,
            unset_attributes=list(event.unset_fields) or None,
        )
        return item.id
