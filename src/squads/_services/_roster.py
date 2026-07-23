"""Agent roster: activating bundled roles, on-demand stack developers, and skills."""

from squads._errors import SquadsError
from squads._interactions import skills_for_role
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._roles._resolver import resolve_dev_role, resolve_role
from squads._services._base import ServiceCore
from squads._services._results import WorkloadRow
from squads._util import operator_slug, slugify
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE, ROSTER_SKILL, STATUS_ACTIVE


class RosterMixin(ServiceCore):
    async def activate_role(self, slug: str, *, name: str | None = None) -> Item:
        """Activate a bundled (or project-override) role.

        ``name`` overrides the ``RoleDef.full_name`` that would otherwise be used.  When omitted
        the name comes from the resolved ``RoleDef`` (which already reads project TOML overrides,
        so a ``roles/<slug>.toml`` with ``full_name`` is also honoured).
        """
        role = resolve_role(slug, self.paths.squad_dir)
        existing = await self._role_item(slug)
        if existing is not None:
            return existing
        # Apply the explicit name override on top of whatever the resolver returned.
        if name is not None:
            from dataclasses import replace as dc_replace

            role = dc_replace(role, full_name=name)
        res = await self.create(
            ROSTER_ROLE,
            role.full_name,
            description=role.mission,
            status=STATUS_ACTIVE,
            slug=role.slug,
            author=role.slug,  # an activated role authors itself
            extra={
                **role.to_extra(),
                X.DESCRIPTION: role.description,
                X.SKILLS: skills_for_role(role.slug),
            },
        )
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
        if await self._role_item(role.slug) is not None:
            raise SquadsError(f"a developer with slug {role.slug!r} already exists")
        res = await self.create(
            ROSTER_ROLE,
            role.full_name,
            description=role.mission,
            status=STATUS_ACTIVE,
            slug=role.slug,
            author=role.slug,  # a dev role authors itself
            extra={
                **role.to_extra(),
                X.DESCRIPTION: role.description,
                X.IS_DEV: True,
                X.TECH: tech,
                X.SKILLS: skills_for_role(role.slug),
            },
        )
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
        if await self._skill_item(slug) is not None:
            raise SquadsError(f"a skill with slug {slug!r} already exists")
        res = await self.create(
            ROSTER_SKILL,
            name,
            description=description,
            parent=parent,
            status=STATUS_ACTIVE,
            slug=slug,
            author=slug,  # a skill authors itself
            extra={
                X.SLUG: slug,
                X.DESCRIPTION: description or name,
                X.WHEN_TO_USE: when_to_use,
                X.ALLOWED_TOOLS: allowed_tools,
            },
        )
        ctx = self._ctx
        for backend in self._backends():
            await backend.generate_skill_entry(ctx, res.item)
        return res.item

    async def add_operator(self, name: str, *, slug: str | None = None) -> Item:
        """Register a human operator (assignable + can author items/comments), e.g. `op-pierre`."""
        slug = slug or operator_slug(name)
        if await self._operator_item(slug) is not None:
            raise SquadsError(f"an operator with slug {slug!r} already exists")
        res = await self.create(
            ROSTER_OPERATOR,
            name,
            status=STATUS_ACTIVE,
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
        has no notion of a live item at all)."""
        return await self.list_items(item_type=ROSTER_ROLE)

    async def workload(self) -> list[WorkloadRow]:
        """Open/closed/total work-item counts per assignee (busiest first; unassigned last)."""
        counts: dict[str | None, list[int]] = {}
        for it in await self.list_items():
            if self.spec.item_is_roster(it.type):
                continue
            bucket = counts.setdefault(it.assignee, [0, 0])
            bucket[0 if self.spec.is_open(it.status) else 1] += 1
        rows = [
            WorkloadRow(assignee=a, open=o, closed=c, total=o + c) for a, (o, c) in counts.items()
        ]
        return sorted(rows, key=lambda r: (-r.open, -r.total, r.assignee or "~"))
