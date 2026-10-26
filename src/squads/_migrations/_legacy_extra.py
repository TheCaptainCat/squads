"""The nested ``extra`` mapping that item files carried before the frontmatter was flat. A runner
for an earlier schema reads and writes the old file shape through these helpers; the current model
keeps ``extra`` as an ordinary attribute, which is how the old shape loads.
"""

from typing import Any, cast

from squads._models._item import Item

LEGACY_KEY = "extra"


def legacy_extra(item: Item) -> dict[str, Any]:
    """The item's nested ``extra`` mapping, empty when the file has none or it is not a mapping."""
    raw = item.attributes.get(LEGACY_KEY)
    return cast("dict[str, Any]", raw) if isinstance(raw, dict) else {}


def with_legacy_extra(extra: dict[str, Any]) -> dict[str, Any]:
    """*extra* as the attribute mapping of an item that stores it in the nested block."""
    return {LEGACY_KEY: extra}


def read_flat(item: Item) -> Item:
    """The item as it reads once its ``extra`` block is flat: the block's keys beside the others.

    For a reader of a squad not yet migrated that asks about stored values (a custom badge code
    an old release kept under ``extra``); the item is not changed."""
    block = legacy_extra(item)
    if not block:
        return item
    flat = {k: v for k, v in item.attributes.items() if k != LEGACY_KEY}
    return item.model_copy(update={"attributes": {**flat, **block}})
