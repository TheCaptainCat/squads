"""The item read operations: the tree, the ref graph, search, the work queues, an item's refs
and discussion, and its sub-entities, each answering with its DTO."""

from squads import _spans as spans
from squads._api._dto._comments import Comments, CommentsRequest
from squads._api._dto._graph import GraphNode, GraphRequest
from squads._api._dto._queues import (
    Blocked,
    BlockedRequest,
    Inbox,
    InboxRequest,
    Mine,
    MineRequest,
    Workload,
    WorkloadRequest,
)
from squads._api._dto._refs import Refs, RefsRequest
from squads._api._dto._search import SearchRequest, SearchResults
from squads._api._dto._subentities import (
    SubentitiesRequest,
    SubentityEntry,
    SubentityList,
    SubentityRequest,
    SubentityShow,
    SubentityShowDisplay,
)
from squads._api._dto._tree import TreeRequest, TreeView
from squads._api._response import Response
from squads._errors import SquadsError
from squads._models._item import Item
from squads._services._base import ItemFilter
from squads._services._item_dto import comment_dtos, participant_names, subentity_dto
from squads._services._item_ops import ItemOpsMixin, badge_pairs
from squads._services._item_read_dto import (
    WORKLOAD_COLUMNS,
    blocked_entry,
    graph_node,
    inbox_entry,
    kind_display,
    mine_columns,
    mine_row,
    ref_entry,
    search_hit,
    sort_tree_level,
    subentity_entry,
    subentity_summary,
    tree_node,
    workload_entry,
)
from squads._services._refs import RefsMixin
from squads._services._roster import RosterMixin


class ItemReadOpsMixin(ItemOpsMixin, RefsMixin, RosterMixin):
    async def tree_items(self, req: TreeRequest) -> Response[TreeView]:
        """The hierarchy under the root, or the whole squad's, kept to the items matching every
        filter and their ancestors; closed items hidden unless asked for or filtered on by
        status, with their count."""
        root = await self.resolve_any_id(req.root) if req.root else None
        # A filter, not authorship: a retired role's assigned items stay reachable.
        assignee = (
            await self.resolve_participant(req.assignee, live_only=False) if req.assignee else None
        )
        item_filter = ItemFilter(
            item_type=req.type,
            status=req.status,
            assignee=assignee,
            category=req.category,
            label=req.label,
            badges=tuple(badge_pairs(req.badge).items()),
            badge_min=tuple(badge_pairs(req.min_badge).items()),
            spec=self.spec,
        )
        include_closed = req.all or bool(req.status)
        hidden = 0 if include_closed else await self._hidden_count(item_filter)
        nodes = await self.tree_view(
            root, filter=item_filter, depth=req.depth, include_closed=include_closed
        )
        blocked_ids = {target.id for target, _ in await self.blocked()}
        pronouns = await self.shown_pronouns()
        names = participant_names(await self.store.load(), pronouns)
        with spans.span("dto"):
            roots = [
                tree_node(
                    n, self.spec, names, blocked_ids=blocked_ids, pronouns=pronouns, sort=req.sort
                )
                for n in sort_tree_level(nodes, req.sort, self.spec)
            ]
        return Response(data=TreeView(items=roots, hidden=hidden))

    async def _hidden_count(self, item_filter: ItemFilter) -> int:
        """How many items the filter's other dimensions match that the default visibility
        hides: the count ``sq list`` reports for the same filter."""
        matching = await self.list_items(
            item_type=item_filter.item_type,
            status=item_filter.status,
            assignee=item_filter.assignee,
            label=item_filter.label,
            category=item_filter.category,
            badges=dict(item_filter.badges) or None,
            badge_min=dict(item_filter.badge_min) or None,
        )
        return sum(1 for i in matching if self.spec.hidden_by_default(i.type, i.status))

    async def graph_items(self, req: GraphRequest) -> Response[GraphNode]:
        """The items linked to the root by refs, a few hops out."""
        root = await self.resolve_any_id(req.root)
        node = await self.graph(
            root,
            depth=req.depth,
            kinds=set(req.kind) if req.kind else None,
            direction=req.direction,
            include_closed=req.all,
        )
        names = await self.display_names()
        return Response(data=graph_node(node, self.spec, names))

    async def search_items(self, req: SearchRequest) -> Response[SearchResults]:
        """The items that match the query; an unreadable item file is named in ``omitted``."""
        found, unreadable = await self.search(req.q, item_type=req.type, status=req.status)
        names = await self.display_names()
        hits = [search_hit(r, self.spec, names) for r in found]
        return Response(data=SearchResults(items=hits), omitted=unreadable)

    async def inbox_items(self, req: InboxRequest) -> Response[Inbox]:
        """The open items whose discussion mentions the slug; an unreadable item file is named
        in ``omitted``."""
        # A read: a retired role's past mentions stay reachable.
        slug = await self.resolve_participant(req.slug, live_only=False)
        hits, unreadable = await self.inbox(slug)
        names = await self.display_names()
        entries = [inbox_entry(h, self.spec, names) for h in hits]
        return Response(data=Inbox(slug=slug, items=entries), omitted=unreadable)

    async def mine_items(self, req: MineRequest) -> Response[Mine]:
        """The items assigned to the slug, directly or through a sub-entity."""
        # A read: a retired role's open items stay reachable.
        slug = await self.resolve_participant(req.slug, live_only=False)
        rows = await self.mine(slug, include_closed=req.all)
        names = await self.display_names()
        mine = [mine_row(r, self.spec, names) for r in rows]
        return Response(data=Mine(slug=slug, items=mine, columns=mine_columns(self.spec)))

    async def blocked_items(self, req: BlockedRequest) -> Response[Blocked]:
        """The open items that wait on another open item."""
        names = await self.display_names()
        rows = [blocked_entry(t, bs, self.spec, names) for t, bs in await self.blocked()]
        return Response(data=Blocked(items=rows))

    async def workload_items(self, req: WorkloadRequest) -> Response[Workload]:
        """Each assignee's open and closed work, busiest first."""
        rows = [workload_entry(r) for r in await self.workload()]
        return Response(data=Workload(items=rows, columns=list(WORKLOAD_COLUMNS)))

    async def item_refs(self, req: RefsRequest) -> Response[Refs]:
        """The refs the item carries, the refs other items carry to it, or both."""
        item = await self.addressed_item(req)
        out = incoming = None
        if req.out:
            out = [ref_entry(i, k, self.spec) for i, k in await self.refs_out(item.id)]
        if req.incoming:
            incoming = [ref_entry(i, k, self.spec) for i, k in await self.refs_in(item.id)]
        return Response(data=Refs.model_validate({"out": out, "in": incoming}))

    async def item_comments(self, req: CommentsRequest) -> Response[Comments]:
        """The item's top-level discussion."""
        item = await self.addressed_item(req)
        return Response(data=Comments(items=comment_dtos(await self.comments(item.id))))

    def _hosted_kind(self, item: Item, kind: str | None) -> str:
        """The sub-entity kind a request names, or the one the item's type hosts."""
        hosted = kind or self.spec.item_subentity_kind(item.type)
        if hosted is None:
            raise SquadsError(f"{item.id} ({item.type}) hosts no sub-entities")
        return hosted

    async def list_subentities(self, req: SubentitiesRequest) -> Response[SubentityList]:
        """The item's sub-entities, with their summary table."""
        item = await self.addressed_item(req)
        kind = self._hosted_kind(item, req.kind)
        subs = await self.list_blocks(item.id, kind)
        db = await self.store.load()
        names = await self.display_names(db)
        entries: list[SubentityEntry] = []
        for sub in subs:
            carrier = db.get(sub.deferred_to) if sub.deferred_to else None
            title = carrier.title if carrier is not None else None
            entries.append(subentity_entry(kind, sub, title, self.spec, names))
        listing = SubentityList(
            items=entries,
            summary=subentity_summary(kind, subs, self.spec),
            kind=kind_display(kind, self.spec),
        )
        return Response(data=listing)

    async def show_subentity(self, req: SubentityRequest) -> Response[SubentityShow]:
        """One sub-entity in full."""
        item = await self.addressed_item(req)
        kind = self._hosted_kind(item, req.kind)
        detail = await self.get_block(item.id, kind, req.local)
        names = await self.display_names()
        full = subentity_dto(kind, detail, self.spec, names)
        unparsed = detail.discussion if detail.discussion and not detail.comments else None
        display = SubentityShowDisplay(
            **dict(full.display),
            kind=kind_display(kind, self.spec),
            maps_to_kind=self.spec.mapping_target_kind(kind),
            discussion=unparsed,
        )
        return Response(data=SubentityShow.model_validate({**dict(full), "display": display}))
