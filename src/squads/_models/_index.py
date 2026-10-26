"""The single global index, ``<squad-dir>/.squads.json``: the global monotonic counter, the
ID-padding width and every item, keyed by integer sequence number (``Item.sequence_id``; the
formatted ``id`` is derived from it and ``type``). The ``.md`` frontmatter is the durable truth and
this file is rebuildable from it (``sq repair``). ``padding`` is a squad-wide filename width,
rebuilt as ``max(stored_padding, max_filename_width)`` and never shrinking like the counter,
defaulting to :data:`~squads._models._item.DEFAULT_ID_PADDING` (6); it is consumed only by
:meth:`SquadsDB.format_id`, while display is always unpadded.
"""

from typing import Any, cast

from pydantic import BaseModel, NonNegativeInt, model_validator

from squads._errors import IndexFullError
from squads._models._item import (
    DEFAULT_ID_PADDING,
    Item,
    effective_prefix,
    format_item_id,
    ref_id_matches,
    split_ref,
)
from squads._models._schema import SCHEMA_VERSION
from squads._util import NonEmpty


def _seq(key: object) -> int:
    """A dict key → its int sequence: ``5`` / ``"5"`` as-is, legacy ``"PREFIX-000005"`` → ``5``."""
    if isinstance(key, int):
        return key
    s = str(key)
    return int(s) if s.isdigit() else int(s.rsplit("-", 1)[-1])


def _entry_with_attributes(entry: Any) -> Any:
    """An index entry written with a nested ``extra`` mapping is read with that mapping as the
    attribute named ``extra``, where a migration runner finds it."""
    if not isinstance(entry, dict):
        return entry
    row = cast("dict[str, Any]", entry)
    block = row.get("extra")
    if "extra" not in row or "attributes" in row:
        return row
    rest = {k: v for k, v in row.items() if k != "extra"}
    return {**rest, "attributes": {"extra": block} if block else {}}


class SquadsDB(BaseModel):
    schema_version: NonEmpty = SCHEMA_VERSION
    #: One global monotonic counter; numbers are unique across all types.
    counter: NonNegativeInt = 0
    #: Zero-pad width for item **filenames** in this squad (e.g. 6 → ``PREFIX-000007-slug.md``).
    #: Never used for display — ``Item.id`` is always unpadded.
    #: Authoritative index state.  Never shrinks.
    padding: NonNegativeInt = DEFAULT_ID_PADDING
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
            d = {
                **d,
                "items": {
                    _seq(k): _entry_with_attributes(v)
                    for k, v in cast("dict[Any, Any]", items).items()
                },
            }
        return d

    def format_id(self, item_type: str, sequence_id: int, *, prefix: str = "") -> str:
        """Format a filename stem at this squad's padding width: the filename-building seam used by
        :meth:`allocate_id` and any caller needing the padded on-disk stem (display never calls it,
        ``Item.id`` being unpadded). *prefix* is the resolved ID prefix
        (:func:`~squads._models._vocab.prefix_for`); empty degrades to
        :data:`~squads._models._item.UNRESOLVED_PREFIX`, never a ``item_type.upper()`` guess.
        """
        return format_item_id(effective_prefix(prefix), sequence_id, self.padding)

    def allocate_id(self, item_type: str, *, prefix: str = "") -> str:
        """Bump the global counter and return the next ID for ``item_type``, with *prefix* resolved
        by the caller (empty degrades to the :data:`~squads._models._item.UNRESOLVED_PREFIX`
        sentinel). Raises :class:`~squads._errors.SquadsError` when the counter would exceed the
        current padding's capacity (999 999 at width 6); raising the padding (``sq migrate repad
        <width>``) lifts it.
        """
        capacity = 10**self.padding - 1
        if self.counter >= capacity:
            raise IndexFullError(
                f"index is full: all {capacity:,} IDs at padding {self.padding} are used up. "
                "Raise the padding with `sq migrate repad <new-width>`.",
                capacity=capacity,
                padding=self.padding,
            )
        self.counter += 1
        return self.format_id(item_type, self.counter, prefix=prefix)

    def add(self, item: Item) -> None:
        self.items[item.sequence_id] = item

    def get(self, item_id: str) -> Item | None:
        try:
            return self.items.get(_seq(item_id))
        except ValueError:
            return None

    def children(self, item_id: str) -> list[str]:
        """Return the IDs of items whose ``parent`` field equals *item_id* (direct children only).

        Comparison uses the stored ``parent`` string, which may carry any padding width after
        a ``sq migrate repad``.  We match against both *item_id* as supplied and the item's
        own ``item.id`` (reflecting the current squad padding) so cross-width lookups resolve
        correctly.
        """
        return sorted(i.id for i in self.items.values() if i.parent == item_id)

    def backrefs(self, item_id: str) -> list[str]:
        """Compute (never store) the items whose forward refs point at ``item_id``, comparing by
        (prefix, sequence number) so an old-width ref (``"PREFIX-000007"``) matches a new-width id,
        since ``sq migrate repad`` never rewrites file contents, and so items sharing a sequence
        number (during renumber) do not collide.
        """
        target_seq = _seq(item_id)
        # Extract the type prefix from item_id (e.g. "PREFIX" from "PREFIX-000007").
        target_prefix, _, _ = item_id.rpartition("-")
        target_prefix = target_prefix.upper()

        def _ref_matches(r: str) -> bool:
            rid = split_ref(r)[0]
            head, _, digits = rid.rpartition("-")
            return bool(
                digits.isdigit() and head.upper() == target_prefix and int(digits) == target_seq
            )

        return sorted(i.id for i in self.items.values() if any(_ref_matches(r) for r in i.refs))

    def deferral_holders(self, item_id: str) -> list[str]:
        """Compute (never store) the items with a sub-entity whose ``deferred_to`` names
        ``item_id``, compared by (prefix, sequence number) like :meth:`backrefs`."""
        head, _, _ = item_id.rpartition("-")
        prefix, seq = head.upper(), _seq(item_id)
        return sorted(
            i.id
            for i in self.items.values()
            if any(
                s.deferred_to and ref_id_matches(s.deferred_to, prefix, seq) for s in i.subentities
            )
        )

    def to_json(self) -> str:
        return self.model_dump_json(indent=2, exclude_none=False)
