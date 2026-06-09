"""The single global index: ``<squad-dir>/.squads.json``.

Holds the global monotonic counter and every item, **keyed by the item's integer sequence number**
(``Item.sequence_id`` — a stored field; the formatted ``id`` is derived from it + ``type``). The
``.md`` frontmatter is the durable truth (it persists both ``id`` and ``sequence_id``); this file is
an authoritative-at-runtime index rebuildable from those files (``sq repair``).
"""

from typing import Any, cast

from pydantic import BaseModel, NonNegativeInt, model_validator

from squads._models._enums import ItemType
from squads._models._item import Item, split_ref
from squads._models._schema import SCHEMA_VERSION
from squads._util import NonEmpty


def _seq(key: object) -> int:
    """A dict key → its int sequence: ``5`` / ``"5"`` as-is, legacy ``"TASK-000005"`` → ``5``."""
    if isinstance(key, int):
        return key
    s = str(key)
    return int(s) if s.isdigit() else int(s.rsplit("-", 1)[-1])


class SquadsDB(BaseModel):
    schema_version: NonEmpty = SCHEMA_VERSION
    squads_version: NonEmpty = "0.0.0"
    #: One global monotonic counter; numbers are unique across all types.
    counter: NonNegativeInt = 0
    #: Items keyed by their global sequence number (the int behind the id).
    items: dict[int, Item] = {}

    model_config = {"use_enum_values": False}

    @model_validator(mode="before")
    @classmethod
    def _coerce_item_keys(cls, data: Any) -> Any:
        """Tolerate item keys as ints, numeric strings, or legacy full ids — normalize to int."""
        if not isinstance(data, dict):
            return data
        d = cast("dict[str, Any]", data)
        items = d.get("items")
        if isinstance(items, dict):
            d = {**d, "items": {_seq(k): v for k, v in cast("dict[Any, Any]", items).items()}}
        return d

    def allocate_id(self, item_type: ItemType) -> str:
        """Bump the global counter and format the next ID for ``item_type``."""
        self.counter += 1
        return f"{item_type.prefix}-{self.counter:06d}"

    def add(self, item: Item) -> None:
        self.items[item.sequence_id] = item

    def get(self, item_id: str) -> Item | None:
        try:
            return self.items.get(_seq(item_id))
        except ValueError:
            return None

    def backrefs(self, item_id: str) -> list[str]:
        """Compute (never store) the items whose forward refs point at ``item_id``."""
        return sorted(
            i.id for i in self.items.values() if any(split_ref(r)[0] == item_id for r in i.refs)
        )

    def to_json(self) -> str:
        return self.model_dump_json(indent=2, exclude_none=False)
