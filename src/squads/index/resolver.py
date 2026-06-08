"""Resolve an ID to its item record and on-disk markdown path."""

from pathlib import Path

from squads.errors import ItemNotFoundError
from squads.models.index import SquadsDB
from squads.models.item import Item
from squads.paths import SquadPaths


def require_item(db: SquadsDB, item_id: str) -> Item:
    item = db.get(item_id)
    if item is None:
        raise ItemNotFoundError(f"no item {item_id!r} in the index")
    return item


def item_file(sp: SquadPaths, item: Item) -> Path:
    return sp.abspath(item.path)
