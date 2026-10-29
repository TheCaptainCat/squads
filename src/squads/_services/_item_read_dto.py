"""The item read results projected onto their DTOs: tree and graph nodes, search hits, queue
rows, refs and sub-entity listings, with the display content the spec and the roster decide."""

from collections.abc import Mapping

from squads import _badges as badges
from squads import _discussion as discussion
from squads._api._dto._display import Column
from squads._api._dto._graph import GraphNode, GraphNodeDisplay
from squads._api._dto._items import SubentitySummary
from squads._api._dto._queues import (
    BlockedEntry,
    Blocker,
    InboxEntry,
    MatchedSubentity,
    MineDisplay,
    MineRow,
    QueueDisplay,
    WorkloadDisplay,
    WorkloadEntry,
)
from squads._api._dto._refs import RefDisplay, RefEntry
from squads._api._dto._search import SearchHit, SearchMatch
from squads._api._dto._subentities import KindDisplay, SubentityEntry
from squads._api._dto._tree import TreeNode, TreeNodeDisplay
from squads._models._item import Item
from squads._models._subentity import SubEntity
from squads._models._vocab import label_for
from squads._services import _results as results
from squads._services._item_dto import (
    badge_displays,
    item_display,
    list_columns,
    status_display,
    subentity_display,
)
from squads._workflow import ROSTER_OPERATOR, ROSTER_ROLE
from squads._workflow._models import WorkflowSpec


def mine_columns(spec: WorkflowSpec) -> list[Column]:
    """The columns of the ``mine`` table: the listing's, then the sub-entities that match."""
    return [*list_columns(spec), Column(key="display.matched", header="Matched")]


#: The columns of the ``workload`` table.
WORKLOAD_COLUMNS: tuple[Column, ...] = (
    Column(key="display.assignee", header="Assignee"),
    Column(key="open", header="Open"),
    Column(key="closed", header="Closed"),
    Column(key="total", header="Total"),
    Column(key="subentity_open", header="Sub Open"),
    Column(key="subentity_closed", header="Sub Closed"),
    Column(key="subentity_total", header="Sub Total"),
)

#: What a workload row shows for the work nobody is assigned.
_UNASSIGNED = "(unassigned)"


def tree_node(
    node: results.TreeNode,
    spec: WorkflowSpec,
    names: Mapping[str, str],
    *,
    blocked_ids: set[str],
    pronouns: Mapping[str, str | None],
    sort: str | None,
) -> TreeNode:
    """*node* and the nodes below it, each level ranked by the badge field *sort* names."""
    it = node.item
    notebook = it.slug if it.slug and it.type in (ROSTER_ROLE, ROSTER_OPERATOR) else None
    display = TreeNodeDisplay(
        **dict(item_display(it, spec, names)),
        dimmed=node.path_only,
        anchor=results.TREE_ANCHOR_MARKER if node.anchor else None,
        pronouns=pronouns.get(notebook) if notebook else None,
    )
    return TreeNode(
        id=it.id,
        type=it.type,
        title=it.title,
        status=it.status,
        priority=it.badge_value("priority"),
        assignee=it.assignee,
        blocked=it.id in blocked_ids,
        badges=badges.resolve_badges(spec, it.type, it.badge_value),
        anchor=node.anchor,
        children=[
            tree_node(c, spec, names, blocked_ids=blocked_ids, pronouns=pronouns, sort=sort)
            for c in sort_tree_level(node.children, sort, spec)
        ],
        display=display,
        notebook=notebook,
        closed=spec.hidden_by_default(it.type, it.status),
        updated_at=it.model_dump(mode="json", include={"updated_at"})["updated_at"],
    )


def sort_tree_level(
    nodes: list[results.TreeNode], sort: str | None, spec: WorkflowSpec
) -> list[results.TreeNode]:
    """*nodes* stable-sorted by a badge field's rank when *sort* names one."""
    if sort is None:
        return nodes
    return sorted(
        nodes, key=lambda n: badges.badge_rank(n.item.type, sort, n.item.badge_value(sort), spec)
    )


def edge_text(edge_kind: str, edge_semantic: str | None, direction: str) -> str:
    """How a graph edge reads: a dependency as ``depends on`` or ``required by`` by direction,
    any other kind as its key."""
    if edge_semantic == "dependency":
        return "depends on" if direction == "out" else "required by"
    return edge_kind


def graph_node(node: results.GraphNode, spec: WorkflowSpec, names: Mapping[str, str]) -> GraphNode:
    """*node* and the nodes its refs reach."""
    edge = None
    edge_label = None
    if node.edge_kind is not None and node.direction is not None:
        edge = edge_text(node.edge_kind, node.edge_semantic, node.direction)
        declared = spec.ref_kinds.get(node.edge_kind)
        edge_label = declared.label if declared is not None else None
    display = GraphNodeDisplay(
        type=label_for(node.type, "singular", spec) if node.type else "",
        status=status_display(node.status, spec),
        badges=badge_displays(spec, node.type, node.badges.get),
        assignee=names.get(node.assignee) if node.assignee else None,
        edge=edge,
        edge_label=edge_label,
    )
    return GraphNode(
        id=node.id,
        type=node.type,
        status=node.status,
        priority=node.priority,
        badges=node.badges,
        assignee=node.assignee,
        edge_kind=node.edge_kind,
        edge_semantic=node.edge_semantic,
        direction=node.direction,
        seen=node.seen,
        children=[graph_node(c, spec, names) for c in node.children],
        display=display,
    )


def search_hit(
    result: results.SearchResult, spec: WorkflowSpec, names: Mapping[str, str]
) -> SearchHit:
    """An item that matched, with its matching lines."""
    it = result.item
    return SearchHit(
        id=it.id,
        title=it.title,
        type=it.type,
        status=it.status,
        hits=[
            SearchMatch(region=h.region, location=h.location, snippet=h.snippet, hash=h.hash)
            for h in result.hits
        ],
        display=item_display(it, spec, names),
    )


def queue_display(item: Item, spec: WorkflowSpec, names: Mapping[str, str]) -> QueueDisplay:
    """How *item* is shown in a queue."""
    return QueueDisplay(**dict(item_display(item, spec, names)), status_code=item.status)


def inbox_entry(hit: results.InboxHit, spec: WorkflowSpec, names: Mapping[str, str]) -> InboxEntry:
    """An item that mentions the slug, with its mentioning lines."""
    return InboxEntry(
        id=hit.item.id,
        title=hit.item.title,
        lines=[ln.text for ln in hit.lines],
        regions=[ln.region for ln in hit.lines],
        hashes=[ln.hash for ln in hit.lines],
        display=queue_display(hit.item, spec, names),
    )


def mine_row(row: results.MineRow, spec: WorkflowSpec, names: Mapping[str, str]) -> MineRow:
    """An assigned item as a row, with the sub-entities that make it the slug's."""
    kind = spec.item_subentity_kind(row.item.type)
    subs = row.matched_subentities
    display = MineDisplay(
        **dict(item_display(row.item, spec, names)),
        matched=", ".join(f"{s.local_id} ({s.status})" for s in subs),
    )
    return MineRow.model_validate(
        {
            **row.item.to_row(),
            "matched_subentities": [
                MatchedSubentity(local_id=s.local_id, kind=kind, title=s.title, status=s.status)
                for s in subs
            ],
            "display": display,
        }
    )


def blocked_entry(
    target: Item, blockers: list[Item], spec: WorkflowSpec, names: Mapping[str, str]
) -> BlockedEntry:
    """A waiting item and what it waits on."""
    return BlockedEntry(
        id=target.id,
        title=target.title,
        blockers=[Blocker(id=b.id, title=b.title, status=b.status) for b in blockers],
        display=queue_display(target, spec, names),
    )


def workload_entry(row: results.WorkloadRow) -> WorkloadEntry:
    """One assignee's counts."""
    return WorkloadEntry(
        assignee=row.assignee,
        open=row.open,
        closed=row.closed,
        total=row.total,
        subentity_open=row.subentity_open,
        subentity_closed=row.subentity_closed,
        subentity_total=row.subentity_total,
        display=WorkloadDisplay(assignee=row.assignee or _UNASSIGNED),
    )


def ref_entry(item_id: str, kind: str, spec: WorkflowSpec) -> RefEntry:
    """One ref, labelled by its kind's declaration (its key when it has none)."""
    declared = spec.ref_kinds.get(kind)
    label = declared.label if declared is not None else kind
    return RefEntry(id=item_id, kind=kind, display=RefDisplay(kind=label))


def kind_display(kind: str, spec: WorkflowSpec) -> KindDisplay:
    """How sub-entity *kind* is named."""
    return KindDisplay(
        name=kind,
        label=kind.title(),
        plural=spec.subentity_plural(kind),
        heading=spec.subentity_container_heading(kind),
    )


def subentity_summary(kind: str, subs: list[SubEntity], spec: WorkflowSpec) -> SubentitySummary:
    """The summary table of *subs*."""
    return SubentitySummary(
        kind=kind,
        columns=discussion.summary_columns(kind, spec),
        rows=[discussion.summary_row(kind, sub, spec) for sub in subs],
    )


def subentity_entry(
    kind: str,
    sub: SubEntity,
    carrier_title: str | None,
    spec: WorkflowSpec,
    names: Mapping[str, str],
) -> SubentityEntry:
    """A sub-entity as a listing row."""
    return SubentityEntry(
        local_id=sub.local_id,
        title=sub.title,
        status=sub.status,
        assignee=sub.assignee,
        severity=sub.badge_value("severity"),
        story=sub.maps_to,
        deferred_to=sub.deferred_to,
        display=subentity_display(kind, sub, carrier_title, spec, names),
    )
