"""The items operations of the table."""

from squads._api._api import Operation
from squads._api._dto import (
    Blocked,
    BlockedRequest,
    Comments,
    CommentsRequest,
    GraphNode,
    GraphRequest,
    Inbox,
    InboxRequest,
    ItemList,
    ItemListRequest,
    ItemShow,
    ItemShowRequest,
    ItemStatusRequest,
    ItemWritten,
    Mine,
    MineRequest,
    Refs,
    RefsRequest,
    SearchRequest,
    SearchResults,
    SubentitiesRequest,
    SubentityList,
    SubentityRequest,
    SubentityShow,
    TreeRequest,
    TreeView,
    Workload,
    WorkloadRequest,
)

ITEMS_LIST = Operation(
    "items.list", "GET", "/v1/items", ItemListRequest, ItemList, json_field="items"
)
ITEM_SHOW = Operation("items.show", "GET", "/v1/items/{id}", ItemShowRequest, ItemShow)
TREE = Operation("tree", "GET", "/v1/tree", TreeRequest, TreeView, json_field="items")
GRAPH = Operation("graph", "GET", "/v1/graph", GraphRequest, GraphNode)
SEARCH = Operation("search", "GET", "/v1/search", SearchRequest, SearchResults, json_field="items")
INBOX = Operation("inbox", "GET", "/v1/inbox/{slug}", InboxRequest, Inbox, json_field="items")
MINE = Operation("mine", "GET", "/v1/mine/{slug}", MineRequest, Mine, json_field="items")
BLOCKED = Operation("blocked", "GET", "/v1/blocked", BlockedRequest, Blocked, json_field="items")
WORKLOAD = Operation(
    "workload", "GET", "/v1/workload", WorkloadRequest, Workload, json_field="items"
)
ITEM_REFS = Operation("items.refs", "GET", "/v1/items/{id}/refs", RefsRequest, Refs)
ITEM_COMMENTS = Operation(
    "items.comments",
    "GET",
    "/v1/items/{id}/comments",
    CommentsRequest,
    Comments,
    json_field="items",
)
ITEM_SUBENTITIES = Operation(
    "items.subentities.list",
    "GET",
    "/v1/items/{id}/subentities",
    SubentitiesRequest,
    SubentityList,
    json_field="items",
)
ITEM_SUBENTITY = Operation(
    "items.subentities.show",
    "GET",
    "/v1/items/{id}/subentities/{local}",
    SubentityRequest,
    SubentityShow,
)
ITEM_STATUS = Operation(
    "items.status", "POST", "/v1/items/{id}/status", ItemStatusRequest, ItemWritten
)
