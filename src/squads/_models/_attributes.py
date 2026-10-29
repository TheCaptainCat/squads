"""Names of the declared attributes the engine reads, and the typed accessors over them.

An attribute is any frontmatter key that is not a core key. Internals read one through
:class:`AttributeKey` and ``Item.attribute``; the typed accessors here read a value of the wrong
kind as unset, so a malformed stored value never reaches a caller as the wrong type.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict

from squads._errors import SquadsError

if TYPE_CHECKING:
    from squads._models._item import Item


type AttributeKind = Literal["str", "list", "bool", "date"]


class AttributeSpec(BaseModel):
    """One declared attribute of an item type: the kind of value it holds, whether ``sq check``
    requires it, whether ``sq update --set`` may write it, and the label it is shown under."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: AttributeKind
    required: bool = False
    settable: bool = True
    #: The name ``show`` displays the attribute under; an attribute without one is not displayed.
    label: str | None = None


class AttributeKey:
    # agent roles
    MODEL = "model"
    IS_DEFAULT = "is_default"
    # a role built from a template: the template's name and its parameter
    TEMPLATE = "template"
    TECH = "tech"
    # a role defined in its own item
    JOB_TITLE = "job_title"
    MISSION = "mission"
    RESPONSIBILITIES = "responsibilities"
    AGREEMENTS = "agreements"
    COLOR = "color"
    CAN_SPAWN = "can_spawn"
    CAPABILITIES = "capabilities"
    # roles and skills
    ORIGIN = "origin"
    # roles and operators
    PRONOUNS = "pronouns"
    # skills
    WHEN_TO_USE = "when_to_use"
    ALLOWED_TOOLS = "allowed_tools"
    OPERATOR_INVOCABLE = "operator_invocable"
    # guides
    TAGS = "tags"
    # reviews
    TARGET_REF = "target_ref"


#: The two values of a role's or skill's ``origin``: shipped with the tool or generated from the
#: spec, versus authored by the project.
ORIGIN_SYSTEM = "system"
ORIGIN_PROJECT = "project"
ORIGIN_VALUES: tuple[str, ...] = (ORIGIN_SYSTEM, ORIGIN_PROJECT)

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
ROW_ADDED_KEYS: tuple[str, ...] = (
    "badges",
    "body",
    "discussion",
    "display",
    "matched_subentities",
    "views",
)

#: Names a ``--json`` sub-entity object adds on top of the entry's own keys. A field code named like
#: one would be hidden by it.
SUBENTITY_ROW_ADDED_KEYS: tuple[str, ...] = ("badges", "body", "discussion", "display")

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


#: The three texts ``--operator-invocable`` accepts, and what each stores (``None`` removes).
INVOCABLE_CHOICES: Mapping[str, bool | None] = MappingProxyType(
    {"yes": True, "no": False, "default": None}
)


def parse_invocable_choice(raw: str) -> bool | None:
    """The stored value a ``--operator-invocable`` text stands for (``None`` removes the stored
    value). Anything but ``yes``, ``no`` or ``default`` is refused."""
    if raw not in INVOCABLE_CHOICES:
        raise SquadsError(f"--operator-invocable takes yes, no or default, not {raw!r}")
    return INVOCABLE_CHOICES[raw]


def template(item: Item) -> str | None:
    """The name of the role template *item* was built from, ``None`` for any other role."""
    return string_attribute(item, AttributeKey.TEMPLATE)


def origin(item: Item) -> str | None:
    """The stored origin when it is one of the two known values, else ``None``."""
    value = string_attribute(item, AttributeKey.ORIGIN)
    return value if value in ORIGIN_VALUES else None


def is_default(item: Item) -> bool | None:
    """The stored default designation, ``None`` when the item stores none."""
    return flag_attribute(item, AttributeKey.IS_DEFAULT)


def tech(item: Item) -> str | None:
    return string_attribute(item, AttributeKey.TECH)


def model(item: Item) -> str | None:
    return string_attribute(item, AttributeKey.MODEL)


def job_title(item: Item) -> str | None:
    return string_attribute(item, AttributeKey.JOB_TITLE)


def mission(item: Item) -> str | None:
    return string_attribute(item, AttributeKey.MISSION)


def responsibilities(item: Item) -> list[str] | None:
    return list_attribute(item, AttributeKey.RESPONSIBILITIES)


def agreements(item: Item) -> list[str] | None:
    return list_attribute(item, AttributeKey.AGREEMENTS)


def color(item: Item) -> str | None:
    return string_attribute(item, AttributeKey.COLOR)


def can_spawn(item: Item) -> bool | None:
    return flag_attribute(item, AttributeKey.CAN_SPAWN)


def capabilities(item: Item) -> list[str] | None:
    return list_attribute(item, AttributeKey.CAPABILITIES)
