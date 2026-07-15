"""Team bulletin board: thin service-layer wrapper over :mod:`squads._board._store`.

Deliberately outside the ``IndexStore``/counter machinery every other mixin builds on — the
board is off the global counter and outside ``.squads.json`` (see the module docstring on
``_board/_store.py``). This mixin only exists so the ``sq board ...`` CLI commands call
through the service layer like every other command, per the ``_cli -> _services -> ...``
architecture; it adds no behaviour of its own beyond passing ``self.paths`` to the storage
functions.
"""

from squads._board import _store as board_store
from squads._board._model import BoardNotice
from squads._services._base import ServiceCore


class BoardMixin(ServiceCore):
    async def board_post(self, author: str, text: str, *, until: str | None = None) -> BoardNotice:
        return await board_store.post(self.paths, author, text, until=until)

    async def board_list(self) -> list[BoardNotice]:
        return await board_store.list_notices(self.paths)

    async def board_clear(self, n: int) -> BoardNotice:
        return await board_store.clear(self.paths, n)
