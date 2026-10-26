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
    """Whether *item* (a ``role`` or ``skill``) should have a materialised backend artifact: the one
    predicate behind ``project_item``, ``sq check``'s ``backend_reconciled`` and ``sync``'s
    report. The status must carry the type's ``live`` flag and, for a ``SKILL``, the slug must still
    name a type the active spec declares, so a dropped type's skill is withdrawn. ``False`` for any
    other type. Pure: reads only *item* and *spec*.
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
        """Display (full) name for a participant slug against an already-loaded *db*, the pure core
        of :meth:`author`; a fresh load would miss a role or operator created earlier in the same
        bulk import. A role's name is ``item.title`` rather than a catalog resolution, since an
        operator can rename a role's display without changing which entry authored a past comment.
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
        """The roles this squad currently offers (status in ``spec.live_statuses("role")``): what
        ``write_managed`` compiles config from and :meth:`role_skills_map` iterates. Use
        :meth:`roster_all` for every entry regardless of status. It loads its own index; a caller
        holding a ``db`` should use :meth:`roster_from_db`.
        """
        return self.roster_from_db(await self.store.load())

    def roster_from_db(self, db: SquadsDB) -> list[RoleView]:
        """:meth:`roster` computed against an already-loaded *db* instead of loading one: the one
        implementation, for a caller mid-transaction or that already paid for a load.
        """
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
        """Slug to absolute body path for live SKILL items, passed to backends through
        BackendContext so they never load the index. Live-only because it only locates files for
        ``write_managed``; ``candidate_orphans`` needs the full slug vocabulary and builds it
        itself.
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
        """Pure core of the resolver: *db* and *role* are already loaded. It starts from
        ``role_guidance.skills_for_role(slug)`` and adds every custom skill with a forward edge to
        this role in the declared ``preload`` kind (found by inverting refs). The result is deduped,
        system skills first then scoped ones in lexical order.
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
        """A live role's full preload-skill set, one index load (see :meth:`resolve_role_skills`);
        bulk callers use :meth:`role_skills_map`. A retired role resolves as if absent, with only
        the system-membership fallback.
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
        """Slug to resolved preload-skill list for every live role (``BackendContext.role_skills``),
        from one index load rather than one per role; a retired role's list is never consumed.
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
        """WARN-only candidate-orphan pointer and skill files across every active backend: present
        on disk but managed by none, never deleted. Backends get the full roster
        (:meth:`roster_all`) and every SKILL slug regardless of status, since a withdrawn entry's
        leftover file is this squad's own debt. The known-slug floor is :func:`active_skill_slugs`,
        not the allocation-order union, which would exempt a dropped type's stale skill.
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
        """Recompute and rewrite one role's backend pointer, the incremental path for ``sq skill
        link-role``/``unlink-role``; other pointers are untouched and a full ``sq sync`` stays
        authoritative. The resolved-skills list is computed on demand and only the pointer carries
        it, since a non-human host reads a file. Only a live role is regenerated, so scoping a skill
        to a retired role does not resurrect it.
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
        """Materialise or withdraw *item*'s per-entry backend artifact: materialised iff
        :func:`is_live_roster_entry`, withdrawn otherwise (a withdrawn skill re-materialises when
        its type returns). The one place the predicate and backend calls live, shared by
        :meth:`project_transition` and ``MaintenanceMixin.sync``; an operator is a no-op, and *ctx*
        must carry the preload map (:meth:`role_skills_map`) for a role. It returns the WARN-only
        notices from the writes (``Artifact.warning``), which never gate.
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
        """Materialise or withdraw *item*'s backend projection after a roster status transition
        commits, outside the transaction since a generated file is regenerable. It resolves the
        preload map in one read (:meth:`role_skills_map`) so a role's ``scopes``-derived skills
        survive a retire/reactivate round trip, and always recompiles the managed regions
        (:meth:`refresh_managed`), as withdrawal changes prose beyond the roster table.
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
