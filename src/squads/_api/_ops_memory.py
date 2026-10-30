"""The memory operations of the table."""

from squads._api._api import Operation
from squads._api._dto._memory import (
    Memory,
    MemoryAdded,
    MemoryAddRequest,
    MemoryForgetRequest,
    MemoryForgotten,
    MemoryList,
    MemoryListRequest,
    MemorySearch,
    MemorySearchRequest,
    MemoryShowRequest,
)

MEMORY_LIST = Operation(
    "memory.list", "GET", "/v1/memory/{role}", MemoryListRequest, MemoryList, json_field="items"
)
MEMORY_SEARCH = Operation(
    "memory.search",
    "GET",
    "/v1/search/memory/{role}",
    MemorySearchRequest,
    MemorySearch,
    json_field="items",
)
MEMORY_SHOW = Operation("memory.show", "GET", "/v1/memory/{role}/{slug}", MemoryShowRequest, Memory)
MEMORY_ADD = Operation("memory.add", "POST", "/v1/memory/{role}", MemoryAddRequest, MemoryAdded)
MEMORY_FORGET = Operation(
    "memory.forget", "DELETE", "/v1/memory/{role}/{slug}", MemoryForgetRequest, MemoryForgotten
)
