"""Agent memory: thin service-layer wrapper over :mod:`squads._memory._store`.

Deliberately outside the ``IndexStore``/counter machinery every other mixin builds on — memory
is off the global counter and outside ``.squads.json`` (see the module docstring on
``_memory/_store.py``). This mixin only exists so the ``sq memory ...`` CLI commands call
through the service layer like every other command, per the ``_cli -> _services -> ...``
architecture; it adds no behaviour of its own beyond passing ``self.paths`` to the storage
functions.
"""

from squads._memory import _store as memory_store
from squads._memory._model import MemoryEntry
from squads._services._base import ServiceCore


class MemoryMixin(ServiceCore):
    async def memory_add(
        self,
        role_slug: str,
        fact: str,
        *,
        body: str | None = None,
        tags: list[str] | None = None,
    ) -> MemoryEntry:
        return await memory_store.add(self.paths, role_slug, fact, body=body, tags=tags)

    async def memory_show(self, role_slug: str, slug: str) -> MemoryEntry:
        return await memory_store.read(self.paths, role_slug, slug)

    async def memory_list(self, role_slug: str) -> list[MemoryEntry]:
        return await memory_store.list_entries(self.paths, role_slug)

    async def memory_forget(self, role_slug: str, slug: str) -> None:
        await memory_store.forget(self.paths, role_slug, slug)
