"""The single global index: ``<squad-dir>/.squads.json``.

Holds the global monotonic counter and every item, keyed by ID. The ``.md`` frontmatter is
the durable source of truth; this file is an authoritative-at-runtime index rebuildable from
those files via ``sq repair``.
"""

from pydantic import BaseModel, Field

from squads.models.enums import ItemType
from squads.models.item import Item


class SquadsDB(BaseModel):
    schema_version: int = 1
    squads_version: str = "0.0.0"
    #: One global monotonic counter; numbers are unique across all types.
    counter: int = 0
    items: dict[str, Item] = Field(default_factory=dict)

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
        return sorted(i.id for i in self.items.values() if item_id in i.refs)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2, exclude_none=False)
