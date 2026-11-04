"""Thin service-layer wrapper over :class:`squads._memory.MemoryStore`: memory sits outside the
index and the global counter, so this mixin only routes the `sq memory` commands through the
service layer.
"""

from squads._memory import MemoryEntry, UnreadableMemories
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
        return await self.memory.add(role_slug, fact, body=body, tags=tags, slug=slug)

    async def memory_show(self, role_slug: str, slug: str) -> MemoryEntry:
        return await self.memory.read(role_slug, slug)

    async def memory_list(self, role_slug: str) -> tuple[list[MemoryEntry], UnreadableMemories]:
        return await self.memory.list_entries(role_slug)

    async def memory_search(
        self, role_slug: str, query: str
    ) -> tuple[list[tuple[MemoryEntry, list[str]]], UnreadableMemories]:
        return await self.memory.search(role_slug, query)

    async def memory_forget(self, role_slug: str, slug: str) -> None:
        await self.memory.forget(role_slug, slug)
