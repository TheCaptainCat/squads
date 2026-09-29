"""The declared-view surface: resolve a ``[views]`` entry's source against one item, and
optionally render it.

The mechanism itself (source resolution, presentation) lives in ``squads._views`` — a
top-level module with no service dependency, the same layering ``squads._discussion`` already
has. This mixin is the one seam that loads the index and hands the already-open ``db`` to it,
so a resolve-and-render call costs one index load, matching ``sq tree``/``sq blocked``.
"""

from squads import _sections as sections
from squads import _views as views
from squads._errors import SquadsError
from squads._index._resolver import item_file, require_item
from squads._models import _markers as markers
from squads._models._item import Item
from squads._paths import number_for_id
from squads._services._base import ServiceCore
from squads._workflow._models import ROSTER_ROLE, ROSTER_SKILL, ViewSpec


class ViewsMixin(ServiceCore):
    async def view_tag_state(self, item_id: str, name: str) -> bool | None:
        """Whether *item_id*'s ``sq:body`` carries *name*'s tag disabled, enabled only, absent,
        or conflicting (``None`` for the last two) — reads the raw region, never expanded, so
        an empty-body hint can tell "disabled" apart from "genuinely absent". Never a gate."""
        item = await self.get(item_id)
        text = await self._read_item_file(item, item_file(self.paths, item))
        region = sections.get_section(text, markers.BODY) or ""
        states = views.view_tag_states(region, name)
        return next(iter(states)) if len(states) == 1 else None

    async def view_tag_present(self, item_id: str, name: str) -> bool:
        """Whether *item_id*'s ``sq:body`` carries *name*'s tag at all, in any state — unlike
        :meth:`view_tag_state`, which collapses "absent" and "conflicting" into one ``None``.
        The CLI reads this first, so it can say "placed" rather than "disabled" for a name
        with no prior tag."""
        item = await self.get(item_id)
        text = await self._read_item_file(item, item_file(self.paths, item))
        region = sections.get_section(text, markers.BODY) or ""
        return bool(views.view_tag_states(region, name))

    async def add_view(self, item_id: str, name: str) -> bool:
        """Place the ``sq:view:<name>`` tag on *item_id*, enabled, or re-enable it if disabled
        — the ``view add`` verb, idempotent against an already-single-enabled tag. Refuses
        when *name* cannot resolve for this host's type. A roster host with no ``sq:body``
        region gets it reinstated first when that's safe; otherwise the same refusal as any
        other host with no region."""

        def mutate(text: str, item: Item) -> tuple[str, bool]:
            reason = views.resolve_view_target(name, item.type, self.spec, self.playbook)
            if reason is not None:
                raise SquadsError(reason)
            reinstating = False
            if sections.get_section(text, markers.BODY) is None:
                reinstated = (
                    views.reinstate_absent_body_region(text)
                    if item.type in (ROSTER_ROLE, ROSTER_SKILL)
                    else None
                )
                if reinstated is None:
                    raise SquadsError(
                        f"{item_id} has no sq:body region; a view tag cannot be placed on it"
                    )
                text = reinstated
                reinstating = True
            current = sections.get_section(text, markers.BODY) or ""
            # A reinstated region always counts as changed, even when the tag it turns out to
            # already carry is exactly the one this call would have placed — the wrapper itself
            # is new, and the caller (`_section_edit_core`) never rewrites the file at all when
            # `changed` is False, which would silently discard the reinstatement.
            if not reinstating and views.view_tag_settled(current, name, disabled=False):
                return text, False
            slug = views.roster_slug(item.type, item.slug, item.extra)
            addr: int | str = (
                slug if item.type in (ROSTER_ROLE, ROSTER_SKILL) else number_for_id(item_id)
            )
            new_inner = views.place_view_tags(
                current,
                None,
                seeded=views.seeded_view_names(item.type, slug, self.spec),
                spec=self.spec,
                item_type=item.type,
                addr=addr,
                force=(name, False),
            )
            return sections.replace_section(text, markers.BODY, new_inner), True

        _, inserted = await self._locked_section_edit(item_id, mutate)
        return inserted

    async def disable_view(self, item_id: str, name: str) -> bool:
        """Turn *item_id*'s ``sq:view:<name>`` tag disabled, or place it disabled if absent —
        the ``view disable`` verb, ungated (no name-resolution check), since it is the one
        recovery for a dangling or inapplicable tag; there is no ``view rm``. Same region
        reinstatement as :meth:`add_view` for a roster host with no ``sq:body`` region."""

        def mutate(text: str, item: Item) -> tuple[str, bool]:
            reinstating = False
            if sections.get_section(text, markers.BODY) is None:
                reinstated = (
                    views.reinstate_absent_body_region(text)
                    if item.type in (ROSTER_ROLE, ROSTER_SKILL)
                    else None
                )
                if reinstated is None:
                    raise SquadsError(
                        f"{item_id} has no sq:body region; a view tag cannot be disabled on it"
                    )
                text = reinstated
                reinstating = True
            current = sections.get_section(text, markers.BODY) or ""
            # See `add_view`'s matching comment: a reinstated region always counts as changed.
            if not reinstating and views.view_tag_settled(current, name, disabled=True):
                return text, False
            slug = views.roster_slug(item.type, item.slug, item.extra)
            addr: int | str = (
                slug if item.type in (ROSTER_ROLE, ROSTER_SKILL) else number_for_id(item_id)
            )
            new_inner = views.place_view_tags(
                current,
                None,
                seeded=views.seeded_view_names(item.type, slug, self.spec),
                spec=self.spec,
                item_type=item.type,
                addr=addr,
                force=(name, True),
            )
            return sections.replace_section(text, markers.BODY, new_inner), True

        _, disabled = await self._locked_section_edit(item_id, mutate)
        return disabled

    async def resolve_view_source(
        self, view_name: str, item_id: str
    ) -> tuple[ViewSpec, Item, views.SourceResult]:
        """*view_name*'s declared source resolved against *item_id*, in its own native shape —
        the declared view, the host item, and whatever :func:`~squads._views.resolve_source`
        returns for it (a flat ``list[Item]``/``list[SubEntity]`` for a relation kind, or the
        ``RoleDef`` / :class:`~squads._views.PlaybookSource` / host ``Item`` a
        ``role``/``playbook``/``self`` source resolves to). Raises :class:`SquadsError` when
        *view_name* isn't declared, or when its source cannot apply to *item_id*'s type — the
        same loud refusal :func:`~squads._views.resolve_source` always raises, never a quiet
        one.

        Works for all six source kinds — the resolution entry point for a caller that wants
        the resolved value itself rather than :meth:`render_view`'s presentation: ``sq workflow
        view <name> <id> --json`` (``squads._cli._workflow_cmd.workflow_view``) is that caller,
        and it serializes each kind's result in that kind's own existing shape — a decision
        this method has no part in, since which shape a resolved value serializes as is a
        presentation choice and every such choice in this codebase lives in ``_cli``, never in
        this service layer."""
        view = self.spec.views.get(view_name)
        if view is None:
            raise SquadsError(
                f"no declared view {view_name!r}; see `sq workflow views` for the declared set"
            )
        db = await self.store.load()
        item = require_item(db, item_id)
        result = views.resolve_source(
            view,
            view_name,
            item,
            db,
            self.spec,
            self.playbook,
            lambda: self.roster_from_db(db),
            self.paths.squad_dir,
        )
        return view, item, result

    async def render_view(self, view_name: str, item_id: str) -> str:
        """*view_name* resolved against *item_id* and rendered through its declared
        presentation template — one index load, then the same Jinja2 engine every other
        rendering path uses. A thin wrapper over :meth:`resolve_view_source` (the one
        resolution entry point) followed by :func:`~squads._views.render_source_view` (the one
        render entry point, shared with read-time tag expansion): this method has no
        resolution logic of its own to keep in step with it."""
        view, item, result = await self.resolve_view_source(view_name, item_id)
        del view  # the resolved source is what render_source_view needs, not the declaration
        return views.render_source_view(
            view_name, result, item, self.spec, self.paths.config.squad_dir
        )
