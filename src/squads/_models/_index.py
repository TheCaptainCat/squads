"""The single global index: ``<squad-dir>/.squads.json``.

Holds the global monotonic counter, the ID-padding width, and every item, **keyed by the item's
integer sequence number** (``Item.sequence_id`` — a stored field; the formatted ``id`` is derived
from it + ``type``).  The ``.md`` frontmatter is the durable truth (it persists both ``id`` and
``sequence_id``); this file is an authoritative-at-runtime index rebuildable from those files
(``sq repair``).

``padding`` is a squad-wide **filename**-width parameter: reconstructed by ``sq repair`` as
``max(stored_padding, max_filename_width)`` — like the counter, it is carried forward and never
shrinks. It is consumed only at the filename-building seam
(:meth:`SquadsDB.format_id`); display always renders unpadded (``Item.id`` formats at
:data:`~squads._models._item.DISPLAY_ID_PADDING`, a constant 0 — never this stored value).
Default is :data:`~squads._models._item.DEFAULT_ID_PADDING` (6) for pre-existing squads.
"""

from typing import Any, cast

from pydantic import BaseModel, NonNegativeInt, model_validator

from squads._errors import SquadsError
from squads._models._item import DEFAULT_ID_PADDING, Item, format_item_id, split_ref
from squads._models._schema import SCHEMA_VERSION
from squads._models._vocab import RESERVED_PREFIX
from squads._util import NonEmpty


def _seq(key: object) -> int:
    """A dict key → its int sequence: ``5`` / ``"5"`` as-is, legacy ``"PREFIX-000005"`` → ``5``."""
    if isinstance(key, int):
        return key
    s = str(key)
    return int(s) if s.isdigit() else int(s.rsplit("-", 1)[-1])


class SquadsDB(BaseModel):
    schema_version: NonEmpty = SCHEMA_VERSION
    squads_version: NonEmpty = "0.0.0"
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
            d = {**d, "items": {_seq(k): v for k, v in cast("dict[Any, Any]", items).items()}}
        return d

    def format_id(self, item_type: str, sequence_id: int, *, prefix: str = "") -> str:
        """Format a **filename stem** at this squad's current padding width.

        Display never calls this — ``Item.id`` always formats unpadded via
        :data:`~squads._models._item.DISPLAY_ID_PADDING`. This is the filename-building seam:
        used by :meth:`allocate_id` (create path) and by any other call site that needs the
        padded on-disk stem.

        ``prefix`` is the resolved ID prefix (e.g. ``"TASK"``, ``"INC"``).  When supplied
        it is used directly; when absent (empty string) the reserved built-in map is consulted
        and falls back to ``item_type.upper()`` for backward compatibility with any call site
        that has not yet been migrated to pass a prefix.

        Callers that hold a spec should resolve the prefix via
        :func:`~squads._models._vocab.prefix_for` and pass it explicitly.
        """
        effective_prefix = prefix or RESERVED_PREFIX.get(item_type, item_type.upper())
        return format_item_id(effective_prefix, sequence_id, self.padding)

    def allocate_id(self, item_type: str, *, prefix: str = "") -> str:
        """Bump the global counter and return the next ID for ``item_type``.

        ``prefix`` is the resolved ID prefix for this type (from the spec via
        :func:`~squads._models._vocab.prefix_for`).  When omitted, falls back to the reserved
        built-in map (backward-compatible for built-in callers).

        Raises :class:`~squads._errors.SquadsError` when the counter would exceed the capacity for
        the current padding (e.g. 999 999 at width 6).  Run ``sq migrate repad <width>`` to raise
        the padding and continue.
        """
        capacity = 10**self.padding - 1
        if self.counter >= capacity:
            raise SquadsError(
                f"index is full: all {capacity:,} IDs at padding {self.padding} are used up. "
                "Raise the padding with `sq migrate repad <new-width>`."
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
        """Compute (never store) the items whose forward refs point at ``item_id``.

        Comparison is by (prefix, sequence-number) so old-width ref strings
        (``"PREFIX-000007"``) and new-width item IDs (``"PREFIX-0000007"``) are treated as equal
        — file contents are never rewritten by ``sq migrate repad``, so refs keep their
        original width forever.  Type-prefix matching prevents false positives when two items
        share a sequence number (collision state during renumber).
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

    def to_json(self) -> str:
        return self.model_dump_json(indent=2, exclude_none=False)
