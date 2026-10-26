"""Thin service-layer wrapper over :mod:`squads._memory._store`: memory sits outside the index and
the global counter, so this mixin only routes the `sq memory` commands through the service layer.
"""

from squads._memory import _store as memory_store
from squads._memory._model import MemoryEntry
from squads._memory._store import UnreadableMemories
from squads._services._base import ServiceCore


class MemoryMixin(ServiceCore):
    async def memory_add(
        self,
        role_slug: str,
        fact: str,
        *,
        body: str | None = None,
        tags: list[str] | None = None,
        slug: str | None = None,
    ) -> MemoryEntry:
        return await memory_store.add(self.paths, role_slug, fact, body=body, tags=tags, slug=slug)

    async def memory_show(self, role_slug: str, slug: str) -> MemoryEntry:
        return await memory_store.read(self.paths, role_slug, slug)

    async def memory_list(self, role_slug: str) -> tuple[list[MemoryEntry], UnreadableMemories]:
        return await memory_store.list_entries(self.paths, role_slug)

    async def memory_search(
        self, role_slug: str, query: str
    ) -> tuple[list[tuple[MemoryEntry, list[str]]], UnreadableMemories]:
        return await memory_store.search(self.paths, role_slug, query)

    async def memory_forget(self, role_slug: str, slug: str) -> None:
        await memory_store.forget(self.paths, role_slug, slug)
