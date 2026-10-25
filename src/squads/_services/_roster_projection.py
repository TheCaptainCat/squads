"""The roster projection: roles, operators and skills read off the index for the backends.

``ServiceCore`` holds it as ``roster_projection`` and keeps one-line delegates for the entry points
the CLI, the TUI and tests call.
"""

from collections.abc import Callable
from pathlib import Path

from squads._backends._base import AgentBackend, BackendContext
from squads._errors import SquadsError
from squads._index._store import IndexStore
from squads._interactions._models import PlaybookSpec
from squads._interactions._role_guidance import skills_for_role, slug_only_role
from squads._interactions._skills import (
    active_skill_slugs,
    orphaned_skill_item_type,
    resolve_operator_invocable,
)
from squads._models._index import SquadsDB
from squads._models._item import Item, effective_prefix, ref_id_matches, split_ref
from squads._models._participants import ANONYMOUS_NAME, ANONYMOUS_SLUG
from squads._paths import SquadPaths, number_for_id
from squads._pronouns import pronouns
from squads._roles._models import CatalogSource
from squads._roles._projection import OperatorView, RoleView
from squads._roles._resolver import resolve_role, resolve_role_for_item, resolve_role_tolerantly
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL
from squads._workflow._models import WorkflowSpec


def is_live_roster_entry(item: Item, spec: WorkflowSpec) -> bool:
    """Whether *item* (a ``role`` or ``skill`` roster item) currently should have a
    materialised per-entry backend artifact — the same two-clause predicate
    ``ServiceCore._project_roster_item`` (:mod:`squads._services._base`) already applies
    while materialising/withdrawing, extracted here so that caller and every other reader of
    "is this roster entry live" — ``sq check``'s ``backend_reconciled`` rule and ``sync``'s
    own before/after regeneration report (both in :mod:`squads._services`) — derive it from
    this one function instead of growing a second, separately-maintained notion of the same
    fact. ``False`` for any other item type (an operator, or an ordinary work item, has no
    per-entry backend artifact at all).

    Two clauses, both required for a ``SKILL`` item, only the first for a ``ROLE`` item:

    - the item's own status carries the type's ``live`` flag
      (:meth:`WorkflowSpec.live_statuses`); and
    - for a ``SKILL`` item only, its slug still names a type the active spec declares
      (:func:`orphaned_skill_item_type` returns ``None``) — a dropped or renamed built-in's
      stale ``sq-<type>`` skill is withdrawn right alongside a manually-retired one, with no
      separate mechanism. Miss this clause and a squad whose workflow override dropped a type
      reports a permanent false positive no ``sq sync`` can clear.

    Pure: reads only *item* and *spec*, no index, no filesystem — safe for a backend-context
    caller that must not load the index itself.
    """
    if item.type not in (ROSTER_ROLE, ROSTER_SKILL):
        return False
    live = item.status in spec.live_statuses(item.type)
    if item.type == ROSTER_SKILL and live:
        live = orphaned_skill_item_type(item.slug, spec) is None
    return live


class RosterProjection:
    """Resolve the squad's roles, operators and skills and project them onto the active backends."""

    def __init__(
        self,
        paths: SquadPaths,
        spec: WorkflowSpec,
        playbook: PlaybookSpec,
        store: IndexStore,
        backends: Callable[[], list[AgentBackend]],
        catalog: CatalogSource,
    ):
        self.paths = paths
        self.spec = spec
        self.playbook = playbook
        self.store = store
        self._backends = backends
        self.catalog = catalog

    async def _items_of(self, item_type: str) -> list[Item]:
        """Every indexed item of *item_type*, in ascending sequence number."""
        items = (await self.store.load()).items.values()
        return sorted(
            (it for it in items if it.type == item_type), key=lambda i: number_for_id(i.id)
        )

    async def roster_item(self, item_type: str, slug: str) -> Item | None:
        """Return the roster item of *item_type* (``ROSTER_ROLE``/``ROSTER_SKILL``/
        ``ROSTER_OPERATOR``) whose slug matches, or ``None``.

        An entry's slug is its file name's when its file stores none.
        """
        for it in (await self.store.load()).items.values():
            if it.type == item_type and it.slug == slug:
                return it
        return None

    def author_of(self, db: SquadsDB, slug: str) -> str:
        """Display (full) name for a participant slug, resolved against an already-loaded
        *db* — the pure core :meth:`author` wraps with its own fresh load.

        Reading from a caller-supplied ``db`` (rather than re-loading from disk) matters
        inside the bulk importer's one open transaction: an earlier event in the same run may
        have just created the role/operator this slug names, and that item is only visible in
        the in-memory ``db``, not yet on disk.

        A role participant's name comes from ``item.title`` — the uniform record's own copy of
        the resolved full name — never a catalog resolution: this
        is a display name on a comment attribution, and resolving through the catalog here
        would be both wrong (an operator can rename a role's *display*, via ``sq role activate
        --name``, without that changing which catalog entry authored a past comment) and
        needlessly expensive for a lookup this cheap. An operator participant's name is its
        ``title``.
        """
        if slug == ANONYMOUS_SLUG:
            return ANONYMOUS_NAME
        participant = next(
            (
                it
                for it in db.items.values()
                if it.type in (ROSTER_ROLE, ROSTER_OPERATOR) and it.slug == slug
            ),
            None,
        )
        if participant is not None:
            if participant.type == ROSTER_ROLE:
                return participant.title
            return participant.title
        try:
            return resolve_role(slug, self.paths.squad_dir, catalog=self.catalog).full_name
        except SquadsError:
            return slug

    async def author(self, slug: str) -> str:
        """Display (full) name for a participant slug; falls back to the slug if unknown."""
        return self.author_of(await self.store.load(), slug)

    def role_view(self, it: Item) -> RoleView:
        """Resolve *it* (a ROLE item) to the ``RoleView`` a backend compiles into the managed
        region — through the catalog (:func:`resolve_role_for_item`), never off the
        item's own fields directly."""
        role = resolve_role_for_item(it, self.paths.squad_dir, catalog=self.catalog)
        return RoleView(
            slug=role.slug,
            full_name=role.full_name,
            title=role.title,
            is_default=role.is_default,
            mission=role.mission,
            responsibilities=role.responsibilities,
            capabilities=role.capabilities,
            pronouns=role.pronouns,
        )

    async def roster(self) -> list[RoleView]:
        """The roles this squad currently **offers** — ``item.status in
        spec.live_statuses("role")``. This is what ``write_managed`` compiles the host's
        config from and what skill-preload resolution (:meth:`role_skills_map`) iterates;
        a retired role has no business in either. Use :meth:`roster_all` for a caller that
        needs every entry regardless of status (orphan detection, authorship display,
        registration checks, the roster's own views).

        Loads its own index; a caller that already has one open (a service method mid-
        transaction, or the view-rendering path that must not pay a second load for what
        :meth:`~squads._services._items.ItemsMixin.read_body`'s own docstring already prices
        as "under the CLI a second index load is free... but ``sq ui`` opts out of that
        scope") should call :meth:`roster_from_db` against the ``db`` it already holds
        instead."""
        return self.roster_from_db(await self.store.load())

    def roster_from_db(self, db: SquadsDB) -> list[RoleView]:
        """:meth:`roster`, computed against an already-loaded *db* rather than loading one —
        the seam a caller mid-transaction, or one that has already paid for a load for an
        unrelated reason (:meth:`~squads._services._views.ViewsMixin.render_view` resolving a
        ``playbook`` source, which needs both the index and the roster), reuses instead of
        loading a second time. Filters and sorts exactly as :meth:`roster` does (live status,
        ascending sequence number) — this is the one implementation, not a parallel one that
        could drift from it."""
        live = self.spec.live_statuses(ROSTER_ROLE)
        matching = [it for it in db.items.values() if it.type == ROSTER_ROLE and it.status in live]
        return [self.role_view(it) for it in sorted(matching, key=lambda i: number_for_id(i.id))]

    async def roster_all(self) -> list[RoleView]:
        """Every role entry regardless of status — the full-vocabulary counterpart to
        :meth:`roster`. See that method's docstring for which callers want which."""
        return [self.role_view(it) for it in await self._items_of(ROSTER_ROLE)]

    async def operators(self) -> list[OperatorView]:
        """The operators this squad currently **offers** — see :meth:`roster`'s docstring;
        same live/full split, mirrored for the operator type. Use :meth:`operators_all`
        for a full-vocabulary caller."""
        live = self.spec.live_statuses(ROSTER_OPERATOR)
        return [
            OperatorView(
                slug=it.slug,
                full_name=it.title,
                pronouns=pronouns(it),
            )
            for it in await self._items_of(ROSTER_OPERATOR)
            if it.status in live
        ]

    async def operators_all(self) -> list[OperatorView]:
        """Every operator entry regardless of status — the full-vocabulary counterpart to
        :meth:`operators`."""
        return [
            OperatorView(
                slug=it.slug,
                full_name=it.title,
                pronouns=pronouns(it),
            )
            for it in await self._items_of(ROSTER_OPERATOR)
        ]

    async def skill_paths(self) -> dict[str, Path]:
        """Build a slug→absolute-body-path map for **live** SKILL items in the index.

        Backends receive this via BackendContext so they never need to load the
        index themselves (layering invariant: _backends must not import _index). Live-only
        because this only ever locates a managed skill's own file for ``write_managed`` (which
        gives a missing one its frontmatter-safe empty ``sq:body`` region and leaves an existing
        one alone) — a withdrawn skill has no generated entry to locate a file for.
        ``candidate_orphans`` needs the full skill-slug vocabulary instead and builds it
        directly rather than reusing this map (see that method).
        """
        skill_items = await self._items_of(ROSTER_SKILL)
        live = self.spec.live_statuses(ROSTER_SKILL)
        return {it.slug: self.paths.abspath(it.path) for it in skill_items if it.status in live}

    async def skill_invocable(self) -> dict[str, bool]:
        """Slug -> resolved ``operator_invocable`` for every live SKILL item, handed to the
        backends so none re-derives the value."""
        live = self.spec.live_statuses(ROSTER_SKILL)
        return {
            it.slug: resolve_operator_invocable(it.slug, it, self.spec)[0]
            for it in await self._items_of(ROSTER_SKILL)
            if it.status in live
        }

    def resolve_role_skills(self, slug: str, role: Item | None, db: SquadsDB) -> list[str]:
        """Pure (no I/O) core of the resolver: *db* and *role* are already loaded by the caller.

        Starts from ``role_guidance.skills_for_role(slug)`` (index-blind, always-on skills +
        the role's item-type skills), then unions in every custom skill carrying a forward
        edge to this role in the declared ``preload`` semantic (:meth:`WorkflowSpec
        .preload_ref_kind`) — found by inverting refs (``SquadsDB.backrefs``, kind-agnostic,
        so filtered here to that one declared kind) and mapping to slugs. Deduped, system-first
        then scoped skills in lexical order, so the result is stable and — with no preload
        edges anywhere — byte-identical to the pure function's own output.
        """
        resolved = (
            slug_only_role(slug)
            if role is None
            else resolve_role_tolerantly(role, self.paths.squad_dir, catalog=self.catalog)
        )
        system = skills_for_role(resolved, self.spec, self.playbook)
        if role is None:
            return system
        role_prefix = effective_prefix(role.prefix)
        seen = set(system)
        scoped: set[str] = set()
        preload_kind = self.spec.preload_ref_kind()
        for candidate_id in db.backrefs(role.id):
            skill = db.get(candidate_id)
            if skill is None or skill.type != ROSTER_SKILL:
                continue
            for r in skill.refs:
                rid, kind = split_ref(r)
                if kind == preload_kind and ref_id_matches(rid, role_prefix, role.sequence_id):
                    scoped.add(skill.slug)
                    break
        return [*system, *sorted(s for s in scoped if s not in seen)]

    async def resolved_skills_for_role(self, slug: str) -> list[str]:
        """A **live** role's full preload-skill set — standalone entry point (e.g. the
        link/unlink partial-sync hook), one index load. See :meth:`resolve_role_skills` for
        the algorithm; bulk callers over every role should use :meth:`role_skills_map`
        instead, which loads the index once for the whole roster rather than once per role.

        Live-only: a role that isn't on offer has no generated entry to preload skills
        into, so a slug naming a retired role resolves as if the role were absent — the pure
        system-membership fallback, never its scoped skills.
        """
        db = await self.store.load()
        live = self.spec.live_statuses(ROSTER_ROLE)
        role = next(
            (
                it
                for it in db.items.values()
                if it.type == ROSTER_ROLE and it.slug == slug and it.status in live
            ),
            None,
        )
        return self.resolve_role_skills(slug, role, db)

    async def role_skills_map(self) -> dict[str, list[str]]:
        """Slug → resolved preload-skill list for every **live** role — the
        ``BackendContext.role_skills`` field.  Companion to :meth:`skill_paths`: loads the
        index ONCE and resolves every live role's list from that single snapshot (mirrors
        ``skill_paths``'s single-load shape), rather than re-parsing the index per role via
        :meth:`resolved_skills_for_role`. Live-only for the same reason as that method: a
        retired role's entry is never written, so its preload list is never consumed.
        """
        db = await self.store.load()
        live = self.spec.live_statuses(ROSTER_ROLE)
        return {
            it.slug: self.resolve_role_skills(it.slug, it, db)
            for it in db.items.values()
            if it.type == ROSTER_ROLE and it.status in live
        }

    async def refresh_managed(self) -> list[str]:
        """(Re)write every active backend's roster/version-dependent files.

        Returns any WARN-only notices the writes surfaced (e.g. a pre-existing hand-written
        CLAUDE.md/AGENTS.md contradiction warning) — never gates the run, just bubbles up for
        the caller (``init``/``adopt``) to report.
        """
        skill_map = await self.skill_paths()
        role_skills = await self.role_skills_map()
        ctx = BackendContext(
            paths=self.paths,
            skill_paths=skill_map,
            skill_invocable=await self.skill_invocable(),
            role_skills=role_skills,
            spec=self.spec,
            playbook=self.playbook,
            catalog=self.catalog,
        )
        roster = await self.roster()
        ops = await self.operators()
        warnings: list[str] = []
        for backend in self._backends():
            artifacts = await backend.write_managed(ctx, roster, ops)
            warnings += [a.warning for a in artifacts if a.warning]
        return warnings

    async def candidate_orphans(self) -> list[str]:
        """WARN-only candidate-orphan pointer/skill files across every active backend —
        present on disk but managed by none of them. Never deletes anything; the caller
        only reports these for the adopter to reconcile by hand.

        Feeds backends the **full** roster vocabulary (:meth:`roster_all`) and the full
        known skill-slug set (every SKILL item regardless of status, not just
        :meth:`skill_paths`'s live-only map) — an orphan means "a file this squad never
        managed", and a withdrawn entry's leftover file is this squad's own convergence
        debt, never a foreign file. Feeding the live-only projection here would relabel
        that debt as a stranger's file, loudest on exactly the squads that have retired
        an entry.

        The known-slug floor is :func:`active_skill_slugs` (the active spec's *current*
        vocabulary), not the allocation-order union
        (``bundled_skill_slugs() | custom_skill_slugs(spec)``) those two seeding helpers use —
        that union always covers every historically-bundled ``sq-<type>`` slug, so it would
        keep exempting a dropped/renamed type's stale skill from ever being flagged since a
        workflow override can shadow a built-in type instead of only adding to it.
        """
        all_skills = await self._items_of(ROSTER_SKILL)
        skill_slugs = {it.slug for it in all_skills} | active_skill_slugs(self.spec)
        roster = await self.roster_all()
        ctx = BackendContext(
            paths=self.paths, spec=self.spec, playbook=self.playbook, catalog=self.catalog
        )
        orphans: list[str] = []
        for backend in self._backends():
            orphans += await backend.candidate_orphans(ctx, roster, skill_slugs)
        return [
            f"candidate orphan (not managed by this squad, never auto-deleted): {p}"
            for p in orphans
        ]

    async def resync_role_skills(self, slug: str) -> None:
        """Partial-sync hook: recompute and rewrite ONE role's backend pointer.

        The supported incremental path for the ``sq skill link-role``/``unlink-role`` verbs —
        mirrors the per-role pointer step a full :meth:`sync` runs, scoped to a single role;
        every other role's pointer is left byte-untouched. A full ``sq sync`` remains the
        authoritative recomputation for the whole roster — this is an optimization on top of
        it, never the only path.

        The resolved-skills list itself is never persisted anywhere: it is a computed
        projection, recovered on demand from the index the caller already loaded
        (:meth:`resolved_skills_for_role`), not a cache this hook refreshes. What this
        recomputes and writes is the *backend pointer* — the one materialised artifact that
        still carries the list, because a non-human agent host reads it as a file rather than
        running a command.

        The backend pointer is only regenerated when the role is **live** — scoping a
        skill to a retired role must not resurrect its withdrawn projection.
        """
        role = await self.roster_item(ROSTER_ROLE, slug)
        if role is None:
            return  # nothing to resync — caller already validated the role exists
        resolved = await self.resolved_skills_for_role(slug)
        if role.status in self.spec.live_statuses(ROSTER_ROLE):
            role_ctx = BackendContext(
                paths=self.paths,
                spec=self.spec,
                playbook=self.playbook,
                role_skills={slug: resolved},
                catalog=self.catalog,
            )
            role_def = resolve_role_for_item(role, self.paths.squad_dir, catalog=self.catalog)
            for backend in self._backends():
                await backend.generate_role_entry(role_ctx, role, role_def)

    async def project_item(self, item: Item, ctx: BackendContext) -> list[str]:
        """Materialise or withdraw *item*'s own per-entry backend artifact: an entry is
        materialised iff its status carries the ``live`` flag; every other status is
        withdrawn. The single place the materialise-or-withdraw predicate and the backend
        calls it drives are expressed — shared by the single-item transition path
        (:meth:`project_transition`) and ``sync``'s roster sweep
        (`MaintenanceMixin.sync`), so the two cannot disagree on either the
        predicate or the context they hand the backend.

        The materialise-or-withdraw predicate itself is
        :func:`is_live_roster_entry` — shared verbatim with ``sq
        check``'s ``backend_reconciled`` rule and ``sync``'s own regeneration report
        (both in :mod:`squads._services`), so none of the three can drift onto a different
        notion of "live" than the others. For a ``SKILL`` item its second clause requires the
        slug to still name a type the active spec declares: a dropped or renamed built-in's
        stale ``sq-<type>`` skill is withdrawn right alongside a manually-retired one, with no
        separate mechanism — and re-materialises on its own the moment the type comes back,
        since this is a pure per-call derivation, never a stored flag. This is what keeps a
        drop's generated-skill residue from outliving the type it described.

        A no-op for an operator item (no per-entry file — only a row in a compiled region);
        the caller's own managed-region recompile is what represents it. *ctx* must already
        carry the resolved preload map (:meth:`role_skills_map`) for a role item — this
        method never resolves it itself, so a caller processing many items resolves the map
        once and reuses this same *ctx* for all of them rather than once per item.

        Fans out over every active backend (:meth:`_backends`, already empty-safe: with
        ``active_backends = []`` there is nothing to project). Materialise calls
        ``generate_role_entry``/``generate_skill_entry``; withdraw calls the existing
        ``remove_artifacts`` (missing-tolerant and idempotent by its own contract, so
        withdrawing against a never-scaffolded backend is a clean no-op).

        Returns the WARN-only notices the per-entry writes surfaced (``Artifact.warning`` —
        e.g. a declared model the host's own frontmatter cannot express, dropped from the
        rendered pointer), for the caller to report alongside its own. Empty in the normal
        case. Never gates anything: this is the same "the write went through, but you should
        know what it did" channel :meth:`refresh_managed` already bubbles up for the compiled
        regions, extended to the per-entry files — without it, the only record of the drop is
        the absence of a line in a generated file.
        """
        if item.type not in (ROSTER_ROLE, ROSTER_SKILL):
            return []
        live = is_live_roster_entry(item, self.spec)
        role_def = (
            resolve_role_for_item(item, self.paths.squad_dir, catalog=self.catalog)
            if live and item.type == ROSTER_ROLE
            else None
        )
        warnings: list[str] = []
        for backend in self._backends():
            if live:
                if item.type == ROSTER_ROLE:
                    assert role_def is not None  # resolved above, live ROSTER_ROLE guaranteed it
                    artifact = await backend.generate_role_entry(ctx, item, role_def)
                else:
                    artifact = await backend.generate_skill_entry(ctx, item)
                if artifact.warning:
                    warnings.append(artifact.warning)
            else:
                await backend.remove_artifacts(ctx, item)
        return warnings

    async def project_transition(self, item: Item) -> list[str]:
        """Materialise or withdraw *item*'s backend projection after a single roster item's
        status transition commits — the projection write happens outside the transaction,
        same ordering the roster create verbs already use, since a generated file is
        regenerable cache rather than a markdown item.

        Resolves the whole roster's preload map in one index read
        (:meth:`role_skills_map`) — even though only one entry is transitioning, the map
        is a single-load computation over every live role, never a per-role read — and hands
        it to :meth:`project_item` so a role's ``scopes``-derived skills survive a
        retire/reactivate round trip exactly as a first creation would.

        Every transition, in either direction, ends by recompiling the managed regions
        (:meth:`refresh_managed`): withdrawal changes generated *prose* beyond the roster
        table (the default-role line, the developer-gated per-item-type skill text), so the
        compiled regions must be rewritten every time, not only the entry's own file. This
        also covers an operator transition, which has no per-entry file at all and so skips
        straight to this region refresh.

        Returns the WARN-only notices both halves surfaced — the entry's own
        (:meth:`project_item`) followed by the region recompile's
        (:meth:`refresh_managed`) — so a caller that has somewhere to print them can, and one
        that has not is unchanged. The full ``sq sync`` sweep is the surface that always
        reports; a single transition is the incremental path onto the same files.
        """
        role_skills = await self.role_skills_map()
        ctx = BackendContext(
            paths=self.paths,
            spec=self.spec,
            playbook=self.playbook,
            role_skills=role_skills,
            catalog=self.catalog,
        )
        warnings = await self.project_item(item, ctx)
        return warnings + await self.refresh_managed()
