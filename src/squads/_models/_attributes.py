"""Names of the declared attributes the engine reads, and the typed accessors over them.

An attribute is any frontmatter key that is not a core key. Internals read one through
:class:`AttributeKey` and ``Item.attribute``; the typed accessors here read a value of the wrong
kind as unset, so a malformed stored value never reaches a caller as the wrong type.
"""

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from squads._models._item import Item


type AttributeKind = Literal["str", "list", "bool", "date"]


class AttributeSpec(BaseModel):
    """One declared attribute of an item type: the kind of value it holds, whether ``sq check``
    requires it, and whether ``sq update --set`` may write it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: AttributeKind
    required: bool = False
    settable: bool = True


class AttributeKey:
    # agent roles
    MODEL = "model"
    IS_DEFAULT = "is_default"
    # developers
    IS_DEV = "is_dev"
    TECH = "tech"
    # skills
    WHEN_TO_USE = "when_to_use"
    ALLOWED_TOOLS = "allowed_tools"
    # guides
    TAGS = "tags"
    # reviews
    TARGET_REF = "target_ref"
    # milestones
    TARGET_DATE = "target_date"


#: Frontmatter keys of the model itself. Every other key in a frontmatter mapping is an attribute.
CORE_KEYS: tuple[str, ...] = (
    "id",
    "sequence_id",
    "type",
    "title",
    "slug",
    "status",
    "description",
    "parent",
    "author",
    "assignee",
    "priority",
    "severity",
    "labels",
    "refs",
    "subentities",
    "created_at",
    "updated_at",
    "created_session",
    "modified_session",
)

#: Names a ``--json`` item row adds on top of the item's own keys. An attribute named like one is
#: kept in the file and left out of the row.
ROW_ADDED_KEYS: tuple[str, ...] = ("badges", "body", "discussion", "matched_subentities")

#: Model fields that are not frontmatter: refused as declared attribute names. A hand-added key of
#: such a name is kept like any unknown key and left out of a ``--json`` row.
NON_FRONTMATTER_KEYS: tuple[str, ...] = ("path", "prefix")


def string_attribute(item: Item, key: str) -> str | None:
    """The attribute *key* when it is a non-empty string, else ``None``."""
    value = item.attribute(key)
    return value if isinstance(value, str) and value else None


def flag_attribute(item: Item, key: str) -> bool | None:
    """The attribute *key* when it is a bool, else ``None`` (unset or of another kind)."""
    value = item.attribute(key)
    return value if isinstance(value, bool) else None


def list_attribute(item: Item, key: str) -> list[str] | None:
    """The attribute *key* when it is a list of strings, else ``None``."""
    value: Any = item.attribute(key)
    if isinstance(value, list) and all(isinstance(v, str) for v in value):  # pyright: ignore[reportUnknownVariableType]
        return list(value)  # pyright: ignore[reportUnknownArgumentType]
    return None


def is_dev(item: Item) -> bool:
    return flag_attribute(item, AttributeKey.IS_DEV) is True


def is_default(item: Item) -> bool | None:
    """The stored default designation, ``None`` when the item stores none."""
    return flag_attribute(item, AttributeKey.IS_DEFAULT)


def tech(item: Item) -> str | None:
    return string_attribute(item, AttributeKey.TECH)


def model(item: Item) -> str | None:
    return string_attribute(item, AttributeKey.MODEL)
