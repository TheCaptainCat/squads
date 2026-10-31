"""The board operations of the table."""

from squads._api._api import Operation
from squads._api._dto._board import (
    BoardClearRequest,
    BoardListRequest,
    BoardPostRequest,
    NoticeList,
    NoticeWrite,
)

BOARD_LIST = Operation(
    "board.list", "GET", "/v1/board", BoardListRequest, NoticeList, json_field="items"
)
BOARD_POST = Operation("board.post", "POST", "/v1/board", BoardPostRequest, NoticeWrite)
BOARD_CLEAR = Operation("board.clear", "DELETE", "/v1/board/{n}", BoardClearRequest, NoticeWrite)
