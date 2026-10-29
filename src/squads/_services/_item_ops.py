"""The item operations: an item's show, a listing of items and a status move, each answering
with its DTO."""

from squads import _spans as spans
from squads._api._dto._item_writes import ItemWritten
from squads._api._dto._items import (
    ItemAddress,
    ItemList,
    ItemListRequest,
    ItemShow,
    ItemShowRequest,
    ItemStatusRequest,
)
from squads._api._response import Response
from squads._badges import resolve_badges
from squads._errors import ItemNotFoundError, SquadsError
from squads._models._index import SquadsDB
from squads._models._item import DISPLAY_ID_PADDING, Item, format_item_id, parse_item_token
from squads._models._vocab import prefix_for
from squads._services._collab import CollabMixin
from squads._services._item_dto import (
    comment_dtos,
    item_row,
    list_columns,
    participant_names,
    show_display,
    sort_by_badge,
    subentity_dto,
)
from squads._services._items import ItemsMixin
from squads._services._subentities import SubentitiesMixin

#: The note the duplicate-id warning carries on a read.
_DUPLICATE_READ_NOTE = "showing the indexed file; run `sq check`"


def badge_pairs(pairs: list[str]) -> dict[str, str]:
    """``CODE=VALUE`` pairs as a mapping."""
    split = (pair.partition("=") for pair in pairs)
    return {code: value for code, _, value in split}


class ItemOpsMixin(ItemsMixin, CollabMixin, SubentitiesMixin):
    async def shown_pronouns(self) -> dict[str, str | None]:
        """Each role's and operator's pronouns by slug, or none when the squad hides them."""
        if not self.paths.config.display.pronouns:
            return {}
        roles = {r.slug: r.pronouns for r in await self.roster_all()}
        return roles | {o.slug: o.pronouns for o in await self.operators_all()}

    async def display_names(self, db: SquadsDB | None = None) -> dict[str, str]:
        """Each role's and operator's display name by slug, with pronouns when the squad shows
        them; *db* is the index when the caller already loaded it."""
        loaded = db if db is not None else await self.store.load()
        return participant_names(loaded, await self.shown_pronouns())

    async def addressed_item(self, address: ItemAddress) -> Item:
        """The item *address* names, refused when no item has its number or when the item is
        not of the type the address expects, when it names one."""
        if address.type is None:
            item_id = await self.resolve_any_id(address.address or address.id)
            return await self.get(item_id)
        seq, given_prefix = parse_item_token(address.id)
        prefix = prefix_for(address.type, self.spec)
        item = (await self.store.load()).get(str(seq))
        if item is None:
            hint = format_item_id(prefix, seq, DISPLAY_ID_PADDING)
            raise ItemNotFoundError(f"no item with number {seq} (use {hint} or bare {seq})")
        typed = address.address if address.address is not None else address.id
        if given_prefix != prefix:
            shown = typed
        elif item.type != address.type:
            shown = typed.strip()
        else:
            return item.model_copy(deep=True)
        raise SquadsError(f"{shown} is {item.id} ({item.type}), not of type {address.type}")

    async def _duplicate_warnings(self, item: Item) -> list[str]:
        """The duplicate-id warning a read of *item* carries, when another file has its id."""
        duplicate = await self.duplicate_id_error(item)
        return [] if duplicate is None else [f"{duplicate} -- {_DUPLICATE_READ_NOTE}"]

    async def show_item(
        self, req: ItemShowRequest, *, keep_view: str | None = None
    ) -> Response[ItemShow]:
        """The item in full, with a warning when more than one file carries its id or a view in
        its body fails to render; the tag of the view *keep_view* names stays unexpanded in the
        displayed body."""
        item = await self.addressed_item(req)
        warnings = await self._duplicate_warnings(item)
        names = await self.display_names()
        kind = self.spec.item_subentity_kind(item.type)
        row = item.to_row()
        expanded = await self.read_body(item.id, keep_view=keep_view)
        if kind is not None:
            row["subentities"] = [
                subentity_dto(
                    kind, await self.get_block(item.id, kind, sub.local_id), self.spec, names
                )
                for sub in item.subentities
            ]
        stored_body = await self.read_stored_body(item.id)
        views = await self.view_data(item.id)
        discussion = comment_dtos(await self.comments(item.id))
        with spans.span("dto"):
            shown = ItemShow.model_validate(
                {
                    **row,
                    "body": stored_body,
                    "views": views,
                    "discussion": discussion,
                    "badges": resolve_badges(self.spec, item.type, item.badge_value),
                    "display": show_display(item, kind, expanded.text, self.spec, names),
                }
            )
        return Response(data=shown, warnings=[*warnings, *expanded.warnings])

    async def list_item_rows(self, req: ItemListRequest) -> Response[ItemList]:
        """The items matching every filter, closed ones hidden unless asked for or filtered on
        by status, sorted by a badge field's rank when one is named."""
        assignee = (
            await self.resolve_participant(req.assignee, live_only=False) if req.assignee else None
        )
        parent = await self.resolve_any_id(req.parent) if req.parent else None
        items = await self.list_items(
            item_type=req.type,
            status=req.status,
            parent=parent,
            label=req.label,
            assignee=assignee,
            category=req.category,
            badges=badge_pairs(req.badge) or None,
            badge_min=badge_pairs(req.min_badge) or None,
        )
        hidden = 0
        if not (req.all or req.status):
            visible = [i for i in items if not self.spec.hidden_by_default(i.type, i.status)]
            hidden = len(items) - len(visible)
            items = visible
        names = await self.display_names()
        with spans.span("dto"):
            rows = [
                item_row(i, self.spec, names) for i in sort_by_badge(items, req.sort, self.spec)
            ]
        return Response(data=ItemList(items=rows, columns=list_columns(self.spec), hidden=hidden))

    async def move_item_status(self, req: ItemStatusRequest) -> Response[ItemWritten]:
        """Move the item to the requested status, as the declared actor; answers its new row."""
        item = await self.addressed_item(req)
        await self.adopt_declared_actor()
        moved = await self.set_status(item.id, req.status, force=req.force)
        names = await self.display_names()
        return Response(data=ItemWritten(entry=item_row(moved, self.spec, names)))
