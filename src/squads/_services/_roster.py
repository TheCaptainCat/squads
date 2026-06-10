"""Agent roster: activating bundled roles, on-demand stack developers, and skills."""

from squads._errors import SquadsError
from squads._interactions import skills_for_role
from squads._models._enums import ItemType, Status
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._roles._catalog import dev_role, role_by_slug
from squads._services._base import ServiceCore
from squads._services._results import WorkloadRow
from squads._util import slugify
from squads._workflow import is_open

_AGENT_TYPES = {ItemType.ROLE, ItemType.SKILL}


class RosterMixin(ServiceCore):
    def activate_role(self, slug: str) -> Item:
        role = role_by_slug(slug)
        existing = self._role_item(slug)
        if existing is not None:
            return existing
        res = self.create(
            ItemType.ROLE,
            role.full_name,
            description=role.mission,
            status=Status.ACTIVE,
            slug=role.slug,
            author=role.slug,  # an activated role authors itself
            extra={
                **role.to_extra(),
                X.DESCRIPTION: role.description,
                X.SKILLS: skills_for_role(role.slug),
            },
        )
        self._backend().generate_role_pointer(self._ctx, res.item, role)
        return res.item

    def add_dev(self, tech: str, *, name: str | None = None, model: str | None = None) -> Item:
        seq = sum(1 for it in self.list_items(item_type=ItemType.ROLE) if it.extra.get(X.IS_DEV))
        role = dev_role(tech, name=name, seq=seq, model=model)
        if self._role_item(role.slug) is not None:
            raise SquadsError(f"a developer with slug {role.slug!r} already exists")
        res = self.create(
            ItemType.ROLE,
            role.full_name,
            description=role.mission,
            status=Status.ACTIVE,
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
        self._backend().generate_role_pointer(self._ctx, res.item, role)
        self.refresh_managed()
        return res.item

    def add_skill(
        self,
        name: str,
        *,
        description: str = "",
        when_to_use: str = "",
        allowed_tools: str = "",
        parent: str | None = None,
    ) -> Item:
        slug = slugify(name)
        if self._skill_item(slug) is not None:
            raise SquadsError(f"a skill with slug {slug!r} already exists")
        res = self.create(
            ItemType.SKILL,
            name,
            description=description,
            parent=parent,
            status=Status.ACTIVE,
            slug=slug,
            author=slug,  # a skill authors itself
            extra={
                X.SLUG: slug,
                X.DESCRIPTION: description or name,
                X.WHEN_TO_USE: when_to_use,
                X.ALLOWED_TOOLS: allowed_tools,
            },
        )
        self._backend().generate_skill_pointer(self._ctx, res.item)
        return res.item

    def workload(self) -> list[WorkloadRow]:
        """Open/closed/total work-item counts per assignee (busiest first; unassigned last)."""
        counts: dict[str | None, list[int]] = {}
        for it in self.list_items():
            if it.type in _AGENT_TYPES:
                continue
            bucket = counts.setdefault(it.assignee, [0, 0])
            bucket[0 if is_open(it.status) else 1] += 1
        rows = [
            WorkloadRow(assignee=a, open=o, closed=c, total=o + c) for a, (o, c) in counts.items()
        ]
        return sorted(rows, key=lambda r: (-r.open, -r.total, r.assignee or "~"))
