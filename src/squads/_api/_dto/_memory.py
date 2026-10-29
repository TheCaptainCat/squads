"""The memory DTOs: a role's notebook listed and searched, one memory shown, added and
forgotten. ``role`` in a request is the slug as given; a response names it as resolved."""

from squads._api._dto._base import DTO


class MemoryListRequest(DTO):
    """List *role*'s memories."""

    role: str


class MemoryRow(DTO):
    """A memory in a listing: its slug, file name, summary and creation time."""

    slug: str
    filename: str
    description: str
    created_at: str


class MemoryList(DTO):
    """A role's memories, by slug."""

    role: str
    items: list[MemoryRow]


class MemorySearchRequest(DTO):
    """Find *role*'s memories whose summary or body contains *query*, ignoring case."""

    role: str
    query: str


class MemoryHit(DTO):
    """A memory that matched: its slug, summary and the body lines that hold the query."""

    slug: str
    description: str
    hits: list[str]


class MemorySearch(DTO):
    """The memories of a role that matched a query."""

    role: str
    query: str
    items: list[MemoryHit]


class MemoryShowRequest(DTO):
    """Show *role*'s memory *slug*."""

    role: str
    slug: str


class Memory(DTO):
    """One memory in full."""

    slug: str
    summary: str
    created_at: str
    tags: list[str]
    body: str


class MemoryAddRequest(DTO):
    """Add a memory to *role*'s notebook, filed under *slug* or one made from *summary*."""

    role: str
    summary: str
    body: str | None = None
    slug: str | None = None


class MemoryAdded(DTO):
    """The memory written, and the role whose notebook holds it."""

    entry: Memory
    role: str


class MemoryForgetRequest(DTO):
    """Delete *role*'s memory *slug*."""

    role: str
    slug: str


class MemoryForgotten(DTO):
    """The memory as it was before it was deleted, and the role whose notebook held it."""

    entry: Memory
    role: str
