"""Resolve an ID to its item record and on-disk markdown path."""

from pathlib import Path

from squads._errors import ItemNotFoundError
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._paths import SquadPaths, number_for_id


def require_item(db: SquadsDB, item_id: str) -> Item:
    item = db.get(item_id)
    if item is None:
        raise ItemNotFoundError(f"no item {item_id!r} in the index")
    return item


def item_file(sp: SquadPaths, item: Item) -> Path:
    return sp.abspath(item.path)


def seq_for_id(item_id: str) -> int:
    """Extract the sequence number (the item's true identity) from any width-variant ID string.

    ``"TASK-000007"`` and ``"TASK-0000007"`` both return ``7``.  All ID-equality checks must
    route through this rather than comparing full-ID strings directly — file contents are never
    rewritten by ``sq migrate repad``, so refs and parent fields keep their old width forever.
    Centralised here (FEAT-000019 shared resolver) so there is one normalisation point.
    """
    return number_for_id(item_id)
