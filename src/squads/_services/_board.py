"""Thin service-layer wrapper over :mod:`squads._board._store`: the board sits outside the index and
the global counter, so this mixin only routes the `sq board` commands through the service layer.
"""

from squads._board import _store as board_store
from squads._board._model import BoardNotice
from squads._board._store import UnreadableNotices
from squads._models._participants import refuse_system_actor
from squads._services._base import ServiceCore


class BoardMixin(ServiceCore):
    async def board_post(self, author: str, text: str, *, until: str | None = None) -> BoardNotice:
        refuse_system_actor(author)
        return await board_store.post(self.paths, author, text, until=until)

    async def board_list(self) -> tuple[list[BoardNotice], UnreadableNotices]:
        """Unexpired notices, plus one message per notice file that could not be read."""
        return await board_store.list_notices(self.paths)

    async def board_clear(self, n: int) -> BoardNotice:
        return await board_store.clear(self.paths, n)
