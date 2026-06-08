"""Resolve an ID to its item record and on-disk markdown path."""

from pathlib import Path

from squads._errors import ItemNotFoundError
from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._paths import SquadPaths


def require_item(db: SquadsDB, item_id: str) -> Item:
    item = db.get(item_id)
    if item is None:
        raise ItemNotFoundError(f"no item {item_id!r} in the index")
    return item


def item_file(sp: SquadPaths, item: Item) -> Path:
    return sp.abspath(item.path)
