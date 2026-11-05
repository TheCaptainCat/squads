"""Thin service-layer wrapper over :class:`squads._board.BoardStore`: the board sits outside the
index and the global counter, so this mixin only routes the `sq board` commands through the
service layer.
"""

from squads._board import BoardNotice, UnreadableNotices
from squads._models import refuse_system_actor
from squads._services._base import ServiceCore


class BoardMixin(ServiceCore):
    async def board_post(
        self, author: str, summary: str, body: str | None = None, *, until: str | None = None
    ) -> BoardNotice:
        refuse_system_actor(author)
        return await self.board.post(author, summary, body, until=until)

    async def board_list(self) -> tuple[list[BoardNotice], UnreadableNotices]:
        """Unexpired notices, plus one message per notice file that could not be read."""
        return await self.board.list_notices()

    async def board_show(self, n: int) -> BoardNotice:
        return await self.board.show(n)

    async def board_clear(self, n: int) -> BoardNotice:
        return await self.board.clear(n)
