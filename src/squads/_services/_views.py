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
from squads._index._resolver import require_item
from squads._models import _markers as markers
from squads._models._item import Item
from squads._services._base import ServiceCore
from squads._workflow._models import ViewSpec


class ViewsMixin(ServiceCore):
    async def insert_view(self, item_id: str, name: str) -> bool:
        """Insert the ``sq:view:<name>`` tag into *item_id*'s ``sq:body`` region — the
        placement verb's insert direction. Anchored at the region's end,
        insert-only, idempotent: a body already carrying the tag is left unchanged and this
        returns ``False`` (already present) rather than duplicating it.

        Refuses (:class:`SquadsError`) placing a tag that could not resolve when read back —
        *name* undeclared, its presentation template missing, or its declared source unable to
        apply to *item_id*'s own type — through the one predicate
        (:func:`~squads._views.resolve_view_target`) ``sq check``'s file-scan finding reports
        the same failure through, asked once inside the locked edit (where *item_id*'s real
        type is already in hand) rather than a second question of its own. The door is not the
        only way to reach that state — retype, or a later spec edit narrowing what a type
        hosts, both can too — so refusing here narrows what a *fresh* placement can create;
        it is not the corpus-wide guarantee. Also refuses an item whose file carries no
        ``sq:body`` region, rather than crashing or half-writing.
        """
        tag = markers.view_tag(name)

        def mutate(text: str, item: Item) -> tuple[str, bool]:
            reason = views.resolve_view_target(name, item.type, self.spec, self.playbook)
            if reason is not None:
                raise SquadsError(reason)
            try:
                return sections.insert_unpaired_marker(text, markers.BODY, tag)
            except KeyError as exc:
                raise SquadsError(
                    f"{item_id} has no sq:body region; a view tag cannot be placed on it"
                ) from exc

        _, inserted = await self._locked_section_edit(item_id, mutate)
        return inserted

    async def remove_view(self, item_id: str, name: str) -> bool:
        """Remove the ``sq:view:<name>`` tag from *item_id*'s ``sq:body`` region — the
        placement verb's remove direction. Removes only that tag; every other byte
        of the body — prose, any other view tag, any other marker — survives verbatim.

        Removing an absent tag is a safe no-op (returns ``False``), never an error. No
        name-resolution check runs here: taking a tag off a document must keep working even
        for a view the spec no longer declares — that is the repair path for exactly that
        case, not a place to refuse it.
        """
        tag = markers.view_tag(name)

        def mutate(text: str, item: Item) -> tuple[str, bool]:
            try:
                return sections.remove_unpaired_marker(text, markers.BODY, tag)
            except KeyError as exc:
                raise SquadsError(
                    f"{item_id} has no sq:body region; a view tag cannot be removed from it"
                ) from exc

        _, removed = await self._locked_section_edit(item_id, mutate)
        return removed

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
