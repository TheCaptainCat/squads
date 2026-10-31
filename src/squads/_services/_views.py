"""The declared-view surface: resolve a ``[views]`` entry's source against one item, and optionally
render it. The mechanism lives in ``squads._views``; this mixin loads the index once and hands the
open ``db`` to it.
"""

from squads import _sections as sections
from squads import _view_tags as view_tags
from squads import _views as views
from squads._errors import SquadsError
from squads._index._resolver import item_file, require_item
from squads._models import _markers as markers
from squads._models._item import Item
from squads._paths import number_for_id
from squads._services._base import ServiceCore
from squads._transform import TransformLoader
from squads._workflow._models import ROSTER_ROLE, ROSTER_SKILL, ViewSpec


class ViewsMixin(ServiceCore):
    async def view_tag_state(self, item_id: str, name: str) -> bool | None:
        """Whether *item_id*'s ``sq:body`` carries *name*'s tag disabled, enabled only, absent,
        or conflicting (``None`` for the last two) — reads the raw region, never expanded, so
        an empty-body hint can tell "disabled" apart from "genuinely absent". Never a gate."""
        item = await self.get(item_id)
        text = await self._read_item_file(item, item_file(self.paths, item))
        region = sections.get_section(text, markers.BODY) or ""
        states = view_tags.view_tag_states(region, name)
        return next(iter(states)) if len(states) == 1 else None

    async def view_tag_present(self, item_id: str, name: str) -> bool:
        """Whether *item_id*'s ``sq:body`` carries *name*'s tag at all, in any state — unlike
        :meth:`view_tag_state`, which collapses "absent" and "conflicting" into one ``None``.
        The CLI reads this first, so it can say "placed" rather than "disabled" for a name
        with no prior tag."""
        item = await self.get(item_id)
        text = await self._read_item_file(item, item_file(self.paths, item))
        region = sections.get_section(text, markers.BODY) or ""
        return bool(view_tags.view_tag_states(region, name))

    async def add_view(self, item_id: str, name: str) -> bool:
        """Place the ``sq:view:<name>`` tag on *item_id*, enabled, or re-enable it if disabled
        — the ``view add`` verb, idempotent against an already-single-enabled tag. Refuses
        when *name* cannot resolve for this host's type. A roster host with no ``sq:body``
        region gets it reinstated first when that's safe; otherwise the same refusal as any
        other host with no region."""

        def mutate(text: str, item: Item) -> tuple[str, bool]:
            self._refuse_classified_roster_write(item_id, item, "A view edit", allow_view=name)
            reason = views.resolve_view_target(
                name, item.type, self.spec, self.playbook, from_squad=self.paths.squad_dir
            )
            if reason is not None:
                raise SquadsError(reason)
            if (stray := view_tags.out_of_region_view_error(item_id, name, text)) is not None:
                raise SquadsError(stray)
            reinstating = False
            if sections.get_section(text, markers.BODY) is None:
                reinstated = (
                    view_tags.reinstate_absent_body_region(text)
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
            # A reinstated region always counts as changed: the wrapper is new, and
            # `_section_edit_core` skips the write when `changed` is False, which would discard the
            # reinstatement.
            if not reinstating and view_tags.view_tag_settled(current, name, disabled=False):
                return text, False
            slug = item.slug
            addr: int | str = (
                slug if item.type in (ROSTER_ROLE, ROSTER_SKILL) else number_for_id(item_id)
            )
            new_inner = view_tags.place_view_tags(
                current,
                None,
                seeded=views.seeded_view_names(
                    item.type, slug, self.spec, from_squad=self.paths.squad_dir
                ),
                spec=self.spec,
                item_type=item.type,
                addr=addr,
                force=(name, False),
            )
            self.store.log("view", item.id, {"view": name, "state": "enabled"})
            return sections.replace_section(text, markers.BODY, new_inner), True

        _, inserted = await self._locked_section_edit(item_id, mutate)
        return inserted

    async def disable_view(self, item_id: str, name: str) -> bool:
        """Turn *item_id*'s ``sq:view:<name>`` tag disabled, or place it disabled if absent —
        the ``view disable`` verb, ungated (no name-resolution check), since it is the one
        recovery for a dangling or inapplicable tag; there is no ``view rm``. Same region
        reinstatement as :meth:`add_view` for a roster host with no ``sq:body`` region."""

        def mutate(text: str, item: Item) -> tuple[str, bool]:
            self._refuse_classified_roster_write(item_id, item, "A view edit")
            if (stray := view_tags.out_of_region_view_error(item_id, name, text)) is not None:
                raise SquadsError(stray)
            reinstating = False
            if sections.get_section(text, markers.BODY) is None:
                reinstated = (
                    view_tags.reinstate_absent_body_region(text)
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
            if not reinstating and view_tags.view_tag_settled(current, name, disabled=True):
                return text, False
            slug = item.slug
            addr: int | str = (
                slug if item.type in (ROSTER_ROLE, ROSTER_SKILL) else number_for_id(item_id)
            )
            new_inner = view_tags.place_view_tags(
                current,
                None,
                seeded=views.seeded_view_names(
                    item.type, slug, self.spec, from_squad=self.paths.squad_dir
                ),
                spec=self.spec,
                item_type=item.type,
                addr=addr,
                force=(name, True),
            )
            self.store.log("view", item.id, {"view": name, "state": "disabled"})
            return sections.replace_section(text, markers.BODY, new_inner), True

        _, disabled = await self._locked_section_edit(item_id, mutate)
        return disabled

    async def resolve_view_source(
        self, view_name: str, item_id: str
    ) -> tuple[ViewSpec, Item, views.SourceResult]:
        """*view_name*'s declared source resolved against *item_id* in its native shape (see
        :func:`~squads._views.resolve_source`), for callers that want the value rather than
        :meth:`render_view`'s presentation. Raises :class:`SquadsError` when *view_name* is
        undeclared or its source cannot apply to *item_id*'s type.
        """
        view = self.spec.views.get(view_name)
        if view is None:
            raise SquadsError(
                f"no declared view {view_name!r}; see `sq workflow views` for the declared set"
            )
        item_id = await self.resolve_any_id(item_id)
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
            self.catalog,
        )
        return view, item, result

    async def render_view(self, view_name: str, item_id: str) -> str:
        """*view_name* resolved against *item_id* and rendered through its declared presentation
        template: :meth:`resolve_view_source` then :func:`~squads._views.render_source_view`, in one
        index load.
        """
        view, item, result = await self.resolve_view_source(view_name, item_id)
        data = (
            TransformLoader(self.paths.squad_dir).run(
                view_name, view.transform, result, item=item, spec=self.spec
            )
            if view.transform is not None
            else None
        )
        return views.render_source_view(
            view_name,
            result,
            item,
            self.spec,
            self.paths.config.squad_dir,
            self.working_language,
            data,
            from_squad=self.paths.squad_dir,
        )
