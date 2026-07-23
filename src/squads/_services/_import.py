"""Bulk event import engine (``sq import``): validate-first pre-pass + single-
transaction apply. The CLI command itself is a separate concern (a later task) — this module
exposes the whole engine as one service entry point, :meth:`ImportMixin.import_events`.

**Two passes, one op set.** Every op's real mutation lives in exactly one place — the
``_X_model``/``_X_core`` pure/IO split each interactive mutation method already exposes
(:mod:`squads._services._base`, :mod:`_items`, :mod:`_collab`, :mod:`_refs`,
:mod:`_subentities`). The pre-pass (:meth:`ImportMixin._plan_import`) calls the PURE
``_X_model`` half against a throwaway, never-persisted deep copy of the index — including the
id allocation, so a create's simulated id comes from the exact same ``db.allocate_id`` the real
apply uses, just against a copy invariant #2 never lets reach a real transaction. The apply
pass (:meth:`ImportMixin._apply_import`) calls the full ``_X_core`` (model + file I/O + reflog)
against the real ``db``, inside ONE open transaction, rebinding the ambient clock/actor per
event via the ``RequestContext`` seam so every event's own ``at``/``as`` drives its
``created_at``/``updated_at``/authorship exactly as an interactive ``--at``/``--as`` call would.
"""

from dataclasses import dataclass, field
from datetime import datetime

from pydantic import ValidationError

from squads import _actor as actor
from squads import _aio
from squads import _clock as clock
from squads._context import bind_context, get_context
from squads._errors import SquadsError
from squads._index._resolver import item_file, require_item
from squads._models._extras import ExtraKey as X
from squads._models._index import SquadsDB
from squads._models._item import VALID_REF_KINDS, make_ref, split_ref
from squads._services._base import reject_markers
from squads._services._collab import CollabMixin
from squads._services._import_model import (
    AddFindingEvent,
    AddStoryEvent,
    AddSubEvent,
    AddSubtaskEvent,
    AssignEvent,
    BodyEvent,
    CommentEvent,
    CreateEvent,
    RefEvent,
    ResolvedEvent,
    StatusEvent,
    SubBodyEvent,
    SubStatusEvent,
    UpdateEvent,
    generic_add_sub,
    parse_events,
    utc_now_floor,
)
from squads._services._items import ItemsMixin
from squads._services._refs import RefsMixin
from squads._services._results import (
    ImportApplyResult,
    ImportIssue,
    ImportOpCount,
    ImportPlan,
    ImportResult,
)
from squads._services._subentities import SubentitiesMixin
from squads._services._validators import ValidatorEngine
from squads._workflow import ROSTER_OPERATOR, ROSTER_SKILL
from squads._workflow._models import Field, WorkflowSpec

#: Exception types the per-event dispatch treats as a collectible validation problem rather
#: than a bug: every check a ``_X_model``/pre-pass helper raises is a ``SquadsError`` (or one
#: of its subclasses); a pydantic ``ValidationError`` surfaces from constructing an ``Item``/
#: ``SubEntity`` with a bad value (e.g. an empty title) the event models don't already reject.
_COLLECTIBLE: tuple[type[Exception], ...] = (SquadsError, ValidationError)


@dataclass
class HandleMap:
    """Client-handle resolution: ``handle -> allocated item id`` and, for sub-entities,
    ``handle -> (parent item id, local id)`` — built up as creating events are (simulated or
    really) applied, in file order. A later event's ``target``/``to``/``parent``/``story``
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
        """The real local id for *token*: a registered sub-entity handle resolves to its local
        id (raising if it's known to belong to a DIFFERENT parent than *parent_id*); anything
        else passes through unchanged (assumed to already be a literal local id, e.g. a
        story's own displayed number).
        ``parent_id=None`` skips the cross-check (the caller has no confirmed parent yet — the
        model-level check downstream reports the real problem)."""
        entry = self.subentities.get(token)
        if entry is None:
            return token
        sub_parent, local_id = entry
        if parent_id is not None and sub_parent != parent_id:
            raise SquadsError(
                f"handle {token!r} names a sub-entity of {sub_parent}, not {parent_id}"
            )
        return local_id


def _resolve_refs(handles: HandleMap, refs: list[str]) -> list[str]:
    """Resolve every ``"ID-or-handle"`` / ``"ID-or-handle:kind"`` token in *refs*, validating
    the kind against :data:`VALID_REF_KINDS` — the same hard check ``create()``/``add_ref()``
    run before ever touching the transaction."""
    out: list[str] = []
    for ref_str in refs:
        rid, kind = split_ref(ref_str)
        if kind not in VALID_REF_KINDS:
            valid = ", ".join(sorted(VALID_REF_KINDS))
            raise SquadsError(f"unknown ref kind {kind!r}. Valid kinds: {valid}")
        out.append(make_ref(handles.resolve_item(rid), kind))
    return out


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
    the same way :meth:`~squads._services._items.ItemsMixin._apply_extra` does for
    ``update``'s ``--set``."""
    out: dict[str, str] = {}
    for code, raw in fields.items():
        declared = _field_for(spec, type_or_kind, code)
        if declared is None:
            raise SquadsError(f"{code!r} is not a declared field for {type_or_kind}")
        out[declared.code] = _parse_badge_code(spec, declared, raw)
    return out


class ImportMixin(ItemsMixin, CollabMixin, SubentitiesMixin, RefsMixin):
    """The bulk-import engine: :meth:`import_events` is the whole entry point the CLI task
    wraps. Both passes share one op-name dispatch table shape; see the module docstring.

    Inherits every mutation mixin it drives (rather than just ``ServiceCore``, like every
    other single-concern mixin does) because it is the one place that reuses ANOTHER mixin's
    ``_X_model``/``_X_core`` pair — an intentional, sole exception to the one-concern-per-file
    convention, not a precedent for the rest of ``_services/``. ``Service`` already composes
    all of these directly; this repeats them so the type checker (and this file in isolation)
    sees the exact same method set ``self`` really has at runtime.
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
        """Parse, validate, and (unless *dry_run* or the pre-pass found any issue) apply a
        JSONL event stream.

        ``default_at``/``default_as`` are the file-level fallbacks an event without its own
        ``at``/``as`` inherits when there is no PRIOR event to inherit from either — the CLI
        task's ``--at``/``--as``. Left ``None``, they default to "now" and this squad's
        configured default role, mirroring the interactive commands' own defaults.
        """
        effective_default_at = default_at if default_at is not None else utc_now_floor()
        effective_default_as = default_as or self.paths.config.default_role

        events, parse_issues = parse_events(
            text, default_at=effective_default_at, default_as=effective_default_as
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
        """Resolve every handle, simulate id allocation, and check every event against the
        active spec — writing nothing, collecting EVERY error (never stopping at the first).

        ``shadow`` is a throwaway, never-persisted deep copy of the loaded index: mutating it
        (including bumping its counter) is exactly invariant #2's "simulate only" — the real
        counter lives in ``self.store`` and is untouched until (and unless) :meth:`_apply_import`
        opens its own transaction.
        """
        shadow = (await self.store.load()).model_copy(deep=True)
        handles = HandleMap()
        counts = ImportOpCount()
        issues: list[ImportIssue] = []
        for ev in events:
            counts.bump(ev.event.op)
            try:
                self._simulate_one(shadow, handles, ev)
            except _COLLECTIBLE as exc:
                issues.append(ImportIssue(line=ev.line, message=str(exc)))
        return ImportPlan(
            op_counts=counts,
            handle_to_id=dict(handles.items),
            handle_to_sub=dict(handles.subentities),
            issues=issues,
        )

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
            self._sim_comment(shadow, handles, event)
        elif isinstance(event, RefEvent):
            from_id = handles.resolve_item(event.target)
            to_id = handles.resolve_item(event.to)
            self._add_ref_model(shadow, from_id, to_id, kind=event.kind, now=ev.at)
        elif isinstance(event, AddSubEvent | AddStoryEvent | AddSubtaskEvent | AddFindingEvent):
            self._sim_add_sub(shadow, handles, ev, generic_add_sub(event))
        elif isinstance(event, SubStatusEvent):
            target = handles.resolve_item(event.target)
            local_id = handles.resolve_local(target, event.local)
            self._set_block_status_model(
                shadow, target, event.kind, local_id, event.status, force=event.force, now=ev.at
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
        resolved_refs = _resolve_refs(handles, event.refs)
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
        if event.handle:
            handles.items[event.handle] = item.id

    def _sim_body(self, shadow: SquadsDB, handles: HandleMap, event: BodyEvent) -> None:
        target = handles.resolve_item(event.target)
        item = require_item(shadow, target)
        if item.type == ROSTER_SKILL:
            slug = item.extra.get(X.SLUG, item.slug)
            from squads._interactions import is_system_skill

            if is_system_skill(slug, self.spec):
                raise SquadsError(
                    f"{target} is a system skill; its body is regenerated by `sq sync`"
                )
        elif self.spec.item_is_roster(item.type) and item.type != ROSTER_OPERATOR:
            raise SquadsError(f"{target} is a {item.type}; its body is generated from its fields")
        reject_markers(event.body)

    def _sim_comment(self, shadow: SquadsDB, handles: HandleMap, event: CommentEvent) -> None:
        target = handles.resolve_item(event.target)
        item = require_item(shadow, target)
        messages = event.all_messages()
        if not messages:
            raise SquadsError("a comment needs at least one message")
        for msg in messages:
            reject_markers(msg, "comment message")
        story = handles.resolve_local(target, event.story) if event.story else None
        subtask = handles.resolve_local(target, event.subtask) if event.subtask else None
        finding = handles.resolve_local(target, event.finding) if event.finding else None
        sub: tuple[str, str] | None = None
        if event.sub is not None:
            sub_kind, local_or_handle = event.sub
            sub = (sub_kind, handles.resolve_local(target, local_or_handle))
        self._discussion_tag(story, subtask, finding, sub)  # raises on a multi-selector conflict
        if sub is not None:
            self._find(item, sub[0], sub[1])
        elif story is not None:
            self._find(item, "story", story)
        elif subtask is not None:
            self._find(item, "subtask", subtask)
        elif finding is not None:
            self._find(item, "finding", finding)

    def _sim_add_sub(
        self, shadow: SquadsDB, handles: HandleMap, ev: ResolvedEvent, event: AddSubEvent
    ) -> None:
        target = handles.resolve_item(event.target)
        parent_item = shadow.get(target)
        story = (
            handles.resolve_local(parent_item.parent if parent_item else None, event.story)
            if event.story
            else None
        )
        resolved_fields = _resolve_fields(self.spec, event.kind, event.fields)
        item, sub = self._add_block_model(
            shadow,
            target,
            event.kind,
            event.title,
            story=story,
            fields=resolved_fields,
            assignee=event.assignee,
            status=event.status,
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

    def _sim_update(
        self, shadow: SquadsDB, handles: HandleMap, ev: ResolvedEvent, event: UpdateEvent
    ) -> None:
        target = handles.resolve_item(event.target)
        parent = handles.resolve_item(event.parent) if event.parent else None
        self._update_model(
            shadow,
            target,
            title=event.title,
            description=event.description,
            assignee=event.assignee,
            add_labels=list(event.add_labels) or None,
            rm_labels=list(event.rm_labels) or None,
            status=event.status,
            force=event.force,
            parent=parent,
            clear_parent=event.clear_parent,
            set_extra=dict(event.fields) or None,
            unset_extra=list(event.unset_fields) or None,
            now=ev.at,
        )

    # ------------------------------------------------------------------ apply
    async def _apply_import(self, events: list[ResolvedEvent]) -> ImportApplyResult:
        """Apply every event inside ONE open transaction: real ids from the real counter, a
        real file write per event, and a per-event reflog entry under that event's own
        actor/clock (rebound via the ``RequestContext`` seam, restored right after).

        Only called once :meth:`_plan_import` reports a fully clean pre-pass — an apply-time
        failure here can therefore only be I/O: the store's own ``transaction()``
        preserves the files-then-index safe-failure order, so a mid-flush crash simply leaves
        the index uncommitted for ``sq repair`` to reconcile.
        """
        handles = HandleMap()
        counts = ImportOpCount()
        warnings: list[str] = []
        touched_ids: set[str] = set()
        async with self.store.transaction() as db:
            for ev in events:
                counts.bump(ev.event.op)
                prior = get_context()
                try:
                    clock.set_now(ev.at)
                    actor.set_actor(ev.actor)
                    touched_ids |= await self._apply_one(db, handles, ev, warnings)
                finally:
                    bind_context(prior)
        warnings.extend(await self._board_debt_warnings(touched_ids))
        return ImportApplyResult(
            op_counts=counts,
            handle_to_id=dict(handles.items),
            handle_to_sub=dict(handles.subentities),
            created_ids=sorted(touched_ids & set(handles.items.values())),
            warnings=warnings,
        )

    async def _board_debt_warnings(self, touched_ids: set[str]) -> list[str]:
        """The same catalog ``sq check`` reports (unwritten sub-entity bodies, over-long
        titles, …), scoped to just the items THIS import touched — read post-commit, since
        the files now exist on disk. Squad-global validators (index/backend reconciliation)
        are irrelevant to one import run, so they're excluded from this engine entirely."""
        if not touched_ids:
            return []
        final_db = await self.store.load()
        bodies: dict[int, str] = {}
        for item_id in touched_ids:
            item = final_db.get(item_id)
            if item is None:
                continue
            bodies[item.sequence_id] = await _aio.read_text(item_file(self.paths, item))
        engine = ValidatorEngine(spec=self.spec, squad_global={})
        issues = engine.report(final_db, {}, bodies=bodies)
        return [f"{i.item}: {i.message}" for i in issues if i.item in touched_ids]

    async def _apply_one(  # noqa: PLR0911 — one per-op dispatch, mirrors _simulate_one's shape
        self, db: SquadsDB, handles: HandleMap, ev: ResolvedEvent, warnings: list[str]
    ) -> set[str]:
        event = ev.event
        if isinstance(event, CreateEvent):
            parent = handles.resolve_item(event.parent) if event.parent else None
            resolved_refs = _resolve_refs(handles, event.refs)
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
            item = await self._set_status_core(db, target, event.status, force=event.force)
            return {item.id}
        if isinstance(event, BodyEvent):
            target = handles.resolve_item(event.target)
            mutate = self._body_mutate(target, event.body, append=event.append)
            item = await self._section_edit_core(db, target, mutate)
            return {item.id}
        if isinstance(event, CommentEvent):
            return {await self._apply_comment(db, handles, event, ev.actor)}
        if isinstance(event, RefEvent):
            from_id = handles.resolve_item(event.target)
            to_id = handles.resolve_item(event.to)
            item = await self._add_ref_core(db, from_id, to_id, kind=event.kind)
            return {item.id}
        if isinstance(event, AddSubEvent | AddStoryEvent | AddSubtaskEvent | AddFindingEvent):
            return await self._apply_add_sub(db, handles, generic_add_sub(event), warnings)
        if isinstance(event, SubStatusEvent):
            target = handles.resolve_item(event.target)
            local_id = handles.resolve_local(target, event.local)
            await self._set_block_status_core(
                db, target, event.kind, local_id, event.status, force=event.force
            )
            return {target}
        if isinstance(event, SubBodyEvent):
            target = handles.resolve_item(event.target)
            local_id = handles.resolve_local(target, event.local)
            mutate = self._block_body_mutate(event.kind, local_id, event.body, append=event.append)
            item = await self._section_edit_core(db, target, mutate)
            return {item.id}
        if isinstance(event, AssignEvent):
            return {await self._apply_assign(db, handles, event)}
        # UpdateEvent — the last member of the exhaustive ImportEvent union
        return {await self._apply_update(db, handles, event)}

    async def _apply_comment(
        self, db: SquadsDB, handles: HandleMap, event: CommentEvent, actor_slug: str
    ) -> str:
        target = handles.resolve_item(event.target)
        story = handles.resolve_local(target, event.story) if event.story else None
        subtask = handles.resolve_local(target, event.subtask) if event.subtask else None
        finding = handles.resolve_local(target, event.finding) if event.finding else None
        sub: tuple[str, str] | None = None
        if event.sub is not None:
            sub_kind, local_or_handle = event.sub
            sub = (sub_kind, handles.resolve_local(target, local_or_handle))
        item = await self._comment_core(
            db,
            target,
            event.all_messages(),
            as_slug=actor_slug,
            story=story,
            subtask=subtask,
            finding=finding,
            sub=sub,
        )
        return item.id

    async def _apply_add_sub(
        self, db: SquadsDB, handles: HandleMap, event: AddSubEvent, warnings: list[str]
    ) -> set[str]:
        target = handles.resolve_item(event.target)
        parent_item = db.get(target)
        story = (
            handles.resolve_local(parent_item.parent if parent_item else None, event.story)
            if event.story
            else None
        )
        resolved_fields = _resolve_fields(self.spec, event.kind, event.fields)
        result = await self._add_block_core(
            db,
            target,
            event.kind,
            event.title,
            story=story,
            fields=resolved_fields,
            assignee=event.assignee,
            status=event.status,
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
        item = await self._update_core(
            db,
            target,
            title=event.title,
            description=event.description,
            assignee=event.assignee,
            add_labels=list(event.add_labels) or None,
            rm_labels=list(event.rm_labels) or None,
            status=event.status,
            force=event.force,
            parent=parent,
            clear_parent=event.clear_parent,
            set_extra=dict(event.fields) or None,
            unset_extra=list(event.unset_fields) or None,
        )
        return item.id
