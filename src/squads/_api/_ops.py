"""The operation table: one entry per operation, the single source of the routes, the request
and response types and how each runs.

Each resource group has its own section; a new operation is defined in its group's section and
listed in the same section of :data:`OPERATIONS`.
"""

from typing import Any

from squads._api._api import Operation
from squads._api._dto._items import (
    ItemList,
    ItemListRequest,
    ItemRow,
    ItemShow,
    ItemShowRequest,
    ItemStatusRequest,
)

# --- items --------------------------------------------------------------------------------------

ITEMS_LIST = Operation(
    "items.list", "GET", "/v1/items", ItemListRequest, ItemList, json_field="items"
)

# --- item reads ---------------------------------------------------------------------------------

ITEM_SHOW = Operation("items.show", "GET", "/v1/items/{id}", ItemShowRequest, ItemShow)

# --- item writes --------------------------------------------------------------------------------

ITEM_STATUS = Operation("items.status", "POST", "/v1/items/{id}/status", ItemStatusRequest, ItemRow)

# --- roster -------------------------------------------------------------------------------------

# --- squad state --------------------------------------------------------------------------------

# --- corpus-wide --------------------------------------------------------------------------------


OPERATIONS: tuple[Operation[Any, Any], ...] = (
    # --- items
    ITEMS_LIST,
    # --- item reads
    ITEM_SHOW,
    # --- item writes
    ITEM_STATUS,
    # --- roster
    # --- squad state
    # --- corpus-wide
)
