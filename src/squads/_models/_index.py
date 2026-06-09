"""The single global index: ``<squad-dir>/.squads.json``.

Holds the global monotonic counter and every item, keyed by ID. The ``.md`` frontmatter is
the durable source of truth; this file is an authoritative-at-runtime index rebuildable from
those files via ``sq repair``.
"""

from pydantic import BaseModel, NonNegativeInt, PositiveInt

from squads._models._enums import ItemType
from squads._models._item import Item, split_ref
from squads._models._schema import SCHEMA_VERSION
from squads._util import NonEmpty


class SquadsDB(BaseModel):
    schema_version: PositiveInt = SCHEMA_VERSION
    squads_version: NonEmpty = "0.0.0"
    #: One global monotonic counter; numbers are unique across all types.
    counter: NonNegativeInt = 0
    items: dict[str, Item] = {}

    model_config = {"use_enum_values": False}

    def allocate_id(self, item_type: ItemType) -> str:
        """Bump the global counter and format the next ID for ``item_type``."""
        self.counter += 1
        return f"{item_type.prefix}-{self.counter:06d}"

    def add(self, item: Item) -> None:
        self.items[item.id] = item

    def get(self, item_id: str) -> Item | None:
        return self.items.get(item_id)

    def backrefs(self, item_id: str) -> list[str]:
        """Compute (never store) the items whose forward refs point at ``item_id``."""
        return sorted(
            i.id for i in self.items.values() if any(split_ref(r)[0] == item_id for r in i.refs)
        )

    def to_json(self) -> str:
        return self.model_dump_json(indent=2, exclude_none=False)
