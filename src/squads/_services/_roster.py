"""Agent roster: activating bundled roles, on-demand stack developers, and skills."""

from squads import _actor as actor
from squads import _clock as clock
from squads._errors import SquadsError
from squads._index._resolver import item_file, require_item
from squads._itemfile import update_frontmatter
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._roles._resolver import (
    holds_default_designation,
    resolve_dev_role,
    resolve_role,
)
from squads._services._base import ServiceCore
from squads._services._results import DefaultRoleMoveResult, MineRow, WorkloadRow
from squads._util import operator_slug, slugify
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL


class RosterMixin(ServiceCore):
    async def activate_role(self, slug: str, *, name: str | None = None) -> Item:
        """Activate a bundled (or project-override) role.

        ``name`` overrides the ``RoleDef.full_name`` that would otherwise be used.  When omitted
        the name comes from the resolved ``RoleDef`` (which already reads project TOML overrides,
        so a ``roles/<slug>.toml`` with ``full_name`` is also honoured).

        **Postcondition: the returned role is live.**  An existing *live* entry is returned
        untouched (activating twice is a no-op, which `init`/`adopt` rely on).  An existing
        *retired* entry is refused, because this is a create verb, not a transition verb: every
        sibling (:meth:`add_dev`, :meth:`add_skill`, :meth:`add_operator`) raises on an existing
        slug, and reviving a retired entry is what ``sq role <slug> status <live-initial>`` is
        for.  Returning it untouched instead would report an activation that did not happen.
        """
        role = resolve_role(slug, self.paths.squad_dir)
        existing = await self.roster_item(ROSTER_ROLE, slug)
        if existing is not None:
            if existing.status in self.spec.live_statuses(ROSTER_ROLE):
                return existing
            raise SquadsError(
                f"role {slug!r} already exists and is {existing.status} ({existing.id}); "
                f"`activate` creates a role, it does not revive one — "
                f"run `sq role {slug} status {self.spec.live_initial(ROSTER_ROLE)}`"
            )
        # Apply the explicit name override on top of whatever the resolver returned.
        if name is not None:
            from dataclasses import replace as dc_replace

            role = dc_replace(role, full_name=name)
        res = await self.create(
            ROSTER_ROLE,
            role.full_name,
            description=role.mission,
            slug=role.slug,
            author=role.slug,  # an activated role authors itself
            extra=role.to_extra(),
        )
        # Materialise iff live: a project whose roster lifecycle's own
        # `initial` is non-live gets a parked-then-activated entry with no files yet —
        # nothing here branches on *how* the entry got created, only on the status it holds.
        if res.item.status in self.spec.live_statuses(ROSTER_ROLE):
            ctx = self._ctx
            for backend in self._backends():
                await backend.generate_role_entry(ctx, res.item, role)
        return res.item

    async def add_dev(
        self, tech: str, *, name: str | None = None, model: str | None = None
    ) -> Item:
        roles = await self.list_items(item_type=ROSTER_ROLE)
        seq = sum(1 for it in roles if it.extra.get(X.IS_DEV))
        role = resolve_dev_role(
            tech, name=name, seq=seq, model=model, squad_dir=self.paths.squad_dir
        )
        if await self.roster_item(ROSTER_ROLE, role.slug) is not None:
            raise SquadsError(f"a developer with slug {role.slug!r} already exists")
        res = await self.create(
            ROSTER_ROLE,
            role.full_name,
            description=role.mission,
            slug=role.slug,
            author=role.slug,  # a dev role authors itself
            extra={
                **role.to_extra(is_dev=True),
                X.IS_DEV: True,
                X.TECH: tech,
            },
        )
        # Materialise iff live — see the matching comment in activate_role.
        if res.item.status in self.spec.live_statuses(ROSTER_ROLE):
            ctx = self._ctx
            for backend in self._backends():
                await backend.generate_role_entry(ctx, res.item, role)
        await self.refresh_managed()
        return res.item

    async def add_skill(
        self,
        name: str,
        *,
        description: str = "",
        when_to_use: str = "",
        allowed_tools: str = "",
        parent: str | None = None,
    ) -> Item:
        slug = slugify(name)
        if await self.roster_item(ROSTER_SKILL, slug) is not None:
            raise SquadsError(f"a skill with slug {slug!r} already exists")
        res = await self.create(
            ROSTER_SKILL,
            name,
            description=description,
            parent=parent,
            slug=slug,
            author=slug,  # a skill authors itself
            extra={
                X.SLUG: slug,
                X.DESCRIPTION: description or name,
                X.WHEN_TO_USE: when_to_use,
                X.ALLOWED_TOOLS: allowed_tools,
            },
        )
        # Materialise iff live — see the matching comment in activate_role.
        if res.item.status in self.spec.live_statuses(ROSTER_SKILL):
            ctx = self._ctx
            for backend in self._backends():
                await backend.generate_skill_entry(ctx, res.item)
        return res.item

    async def add_operator(self, name: str, *, slug: str | None = None) -> Item:
        """Register a human operator (assignable + can author items/comments), e.g. `op-alice`."""
        slug = slug or operator_slug(name)
        if await self.roster_item(ROSTER_OPERATOR, slug) is not None:
            raise SquadsError(f"an operator with slug {slug!r} already exists")
        res = await self.create(
            ROSTER_OPERATOR,
            name,
            slug=slug,
            author=slug,  # an operator authors itself
            extra={X.SLUG: slug, X.FULL_NAME: name},
        )
        await self.refresh_managed()  # so the CLAUDE.md operator roster picks it up
        return res.item

    async def list_operators(self) -> list[Item]:
        return await self.list_items(item_type=ROSTER_OPERATOR)

    async def list_roles(self) -> list[Item]:
        """The active roster — activated ``ROLE`` items — distinct from ``sq role catalog``
        (the bundled-but-not-necessarily-active catalog, which reads from ``PREDEFINED`` and
        has no notion of an index item at all)."""
        return await self.list_items(item_type=ROSTER_ROLE)

    async def default_role_slug(self) -> str | None:
        """The slug of the live role this squad currently designates as its default, or
        ``None`` when no live role carries the designation.

        Reads :meth:`~ServiceCore.roster` — the same live-filtered, catalog-resolved
        projection the backend compiles the managed region's default-role line from, taking
        the first holder exactly as that line does — so a display surface asking "who is the
        default *here*" gets the same answer the generated agent files were written with,
        rather than the bundled catalog's shipped designation. ``None`` is a legitimate
        answer, not a gap: a squad that retired its designated role has no default until one
        is designated again, and the generated line omits itself in that state too.
        """
        return next((r.slug for r in await self.roster() if r.is_default), None)

    async def set_default_role(self, item_id: str) -> DefaultRoleMoveResult:
        """Move the ``is_default`` designation onto a live role — a move, not a set. The
        projection resolves the designation by first match over the roster and
        nothing validates a single holder at item level, so a plain set could silently leave
        two holders and an arbitrary winner; this clears **every** other holder found — not
        just the one it happens to know about — in the same transaction, so it also converges
        a squad that already carries two (the state the bulk importer's ``update`` event can
        reach, since it is the only path that writes this key today outside this method).

        **A holder is found by resolving, never by reading ``extra.is_default`` raw.** The
        stored key is an *override* on a designation the role catalog also answers
        (:func:`~squads._roles._resolver.role_base_from_item` falls back to the catalog's own
        ``is_default``), and a role item no longer stores the key unless something wrote it —
        so the catalog's designated role holds the designation with nothing in its ``extra`` at
        all. A raw read finds no holder there, clears nothing, and leaves the squad with two
        live defaults: the one this call just wrote and the one the catalog still names. That
        is the same failure as the sync revert, reached from the other end, and resolving is
        what closes both. Clearing writes an explicit ``False``, which is the only thing that
        can override a designation the catalog (or a project override document) declares.

        Refuses a non-live target: a designation the projection cannot read is not a
        designation, and the generated default-role line already omits itself when no live
        role carries it. Designating the role that already holds it — with nothing else to
        clear — is a reported no-op, not an error.

        The projection is refreshed after commit (:meth:`~ServiceCore.refresh_managed`) —
        the same path a roster status transition already uses — because ``is_default`` never
        appears in a role's own generated pointer, only in the compiled managed region (the
        default-role line and the orchestration prose that reads the same value), so there is
        nothing else to re-materialise. Skipped when nothing changed.
        """
        async with self.store.transaction() as db:
            item = require_item(db, item_id)
            if item.type != ROSTER_ROLE:
                raise SquadsError(
                    f"{item.id} is not a role — the default designation applies to roles only"
                )
            live = self.spec.live_statuses(ROSTER_ROLE)
            if item.status not in live:
                slug = item.extra.get(X.SLUG, item.slug)
                raise SquadsError(
                    f"{item.id} ({slug}) is not live — only a live role can be designated default"
                )

            # Resolved once for the whole pass (may clear several other roles below) rather
            # than once per role touched.
            default_kind = self.spec.default_ref_kind()
            cleared: list[str] = []
            for other in db.items.values():
                if (
                    other.type == ROSTER_ROLE
                    and other.id != item.id
                    and holds_default_designation(other, self.paths.squad_dir)
                ):
                    other_base = other.model_copy(deep=True)
                    other.extra[X.IS_DEFAULT] = False
                    other.updated_at = clock.now()
                    other.modified_session, _ = actor.current_session()
                    await update_frontmatter(
                        item_file(self.paths, other), other, other_base, default_kind=default_kind
                    )
                    cleared.append(other.id)

            was_default = holds_default_designation(item, self.paths.squad_dir)
            changed = bool(cleared) or not was_default
            if not was_default:
                base = item.model_copy(deep=True)
                item.extra[X.IS_DEFAULT] = True
                item.updated_at = clock.now()
                item.modified_session, _ = actor.current_session()
                await update_frontmatter(
                    item_file(self.paths, item), item, base, default_kind=default_kind
                )
            if changed:
                self.store.log("default_role", item.id, {"cleared": cleared})
        if changed:
            await self.refresh_managed()
        return DefaultRoleMoveResult(item=item, cleared=cleared, changed=changed)

    async def workload(self) -> list[WorkloadRow]:
        """Open/closed/total work-item counts per assignee (busiest first; unassigned last),
        plus each assignee's separate, additive sub-entity assignment counts.

        Sub-entity counts are resolved through the same spec predicate (`is_open`) applied to
        the sub-entity's own status — never folded into the item counts (see
        :class:`~squads._services._results.WorkloadRow`). Roster-category items (and their
        sub-entities, since a roster type declares none) stay excluded, as they are today.

        **Deliberately a different predicate from :meth:`mine`'s default filter.** This is a
        census — "how much active work does this slug carry" — so it reads the role's
        ``settled`` flag (`is_open`, unchanged since before the role-object model): a settled
        status is closed regardless of whether it stays visible elsewhere. `mine` answers a
        different question — "does this row belong in a default listing" — so it reads
        ``hidden`` instead (`hidden_by_default`, matching `sq list`/`sq tree`): an ``in_force``
        status (e.g. `Accepted`, `Published`) is settled yet stays visible there. The two flags
        coincide for every bundled lifecycle except `in_force`, which is why the split is easy
        to miss; see :meth:`mine`'s docstring for the same note from the other surface. Neither
        docstring is a substitute for stating this in the adopter-facing docs.

        **Sub-entity counts never fold in the parent item's status either** — a `Todo` subtask
        under a `Cancelled` or `Done` task still counts in `subentity_open`, purely on the
        sub-entity's own status. That is internally consistent with the item columns beside it
        (a closed item's own children get counted the same way regardless of the item's status),
        but it means `sq mine <slug>` and `sq workload` can disagree about whether the same
        slug has open work: `mine` has a deliberate per-reason rule where a settled sub-entity
        under an open parent still isn't the slug's queue (and vice versa); `workload` has no
        such rule because folding parent state in would change what these columns mean relative
        to the item columns next to them. Not a defect — a census answers "how much is on this
        status" per entity, not "is this actionable" — but worth knowing before comparing the
        two commands' numbers for the same slug.
        """
        counts: dict[str | None, list[int]] = {}
        sub_counts: dict[str | None, list[int]] = {}
        for it in await self.list_items():
            if self.spec.item_is_roster(it.type):
                continue
            bucket = counts.setdefault(it.assignee, [0, 0])
            bucket[0 if self.spec.is_open(it.status) else 1] += 1
            if self.spec.item_subentity_kind(it.type) is None:
                continue
            for sub in it.subentities:
                sbucket = sub_counts.setdefault(sub.assignee, [0, 0])
                sbucket[0 if self.spec.is_open(sub.status) else 1] += 1
        rows = [
            WorkloadRow(
                assignee=a,
                open=o,
                closed=c,
                total=o + c,
                subentity_open=sub_counts.get(a, [0, 0])[0],
                subentity_closed=sub_counts.get(a, [0, 0])[1],
                subentity_total=sum(sub_counts.get(a, [0, 0])),
            )
            for a, (o, c) in counts.items()
        ]
        # An assignee owning only sub-entities (never an item) has no `counts` entry at all —
        # give them a zero-item row so their sub-entity counts are visible too.
        rows += [
            WorkloadRow(
                assignee=a,
                open=0,
                closed=0,
                total=0,
                subentity_open=o,
                subentity_closed=c,
                subentity_total=o + c,
            )
            for a, (o, c) in sub_counts.items()
            if a not in counts
        ]
        return sorted(rows, key=lambda r: (-r.open, -r.total, r.assignee or "~"))

    async def mine(self, slug: str, *, include_closed: bool = False) -> list[MineRow]:
        """Items assigned to ``slug`` directly, or via one of their sub-entities.

        Default (``include_closed=False``) visibility is evaluated per matched reason: an
        item-level match is judged on the item's own status, a sub-entity match on that
        sub-entity's own status (`spec.hidden_by_default` applied at sub-entity granularity —
        the same role-derived predicate items use, not a parallel visibility concept). The row
        shows if at least one matching reason is open. ``include_closed=True`` bypasses the
        predicate entirely, exactly as it does for item-level matches today.

        **Deliberately reads `hidden_by_default`, not `is_open`.** This filter answers "does
        this row belong in a default listing", the same question `sq list`/`sq tree` ask — so
        it reads the role's ``hidden`` flag, under which a settled-but-``in_force`` status
        (`Accepted`, `Published`) stays visible without ``--all``, exactly as it does in those
        two commands. :meth:`workload`'s open/closed columns ask a different question — a
        census of active work — and read ``settled`` (`is_open`) instead, so an `in_force`
        status counts closed there while showing here. Both are correct for what they answer;
        keep this predicate in sync with `sq list`'s, not with `workload`'s, if you touch it.

        Roster-category items are excluded, matching :meth:`workload`'s own guard — no CLI verb
        sets ``assignee`` on a role/skill/operator today, so this is a consistency fix rather
        than a reachable behaviour change, but the two functions sit adjacent and answer the
        same question, so they should agree on it rather than one stating the exclusion and the
        other omitting it.
        """
        rows: list[MineRow] = []
        for it in await self.list_items():
            if self.spec.item_is_roster(it.type):
                continue
            kind = self.spec.item_subentity_kind(it.type)
            matched_subs = [s for s in it.subentities if s.assignee == slug] if kind else []
            item_match = it.assignee == slug
            if not item_match and not matched_subs:
                continue
            if not include_closed:
                item_open = item_match and not self.spec.hidden_by_default(it.type, it.status)
                sub_open = kind is not None and any(
                    not self.spec.hidden_by_default(kind, s.status) for s in matched_subs
                )
                if not (item_open or sub_open):
                    continue
            rows.append(MineRow(item=it, matched_subentities=matched_subs))
        return rows
