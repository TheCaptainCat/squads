"""The item write DTOs: creating an item, changing its fields, body, type, refs and views,
removing it, and the same writes on its sub-entities."""

from typing import Any, ClassVar

from pydantic import Field, SerializerFunctionWrapHandler, model_serializer

from squads._api._dto._base import DTO
from squads._api._dto._display import Display
from squads._api._dto._items import ItemAddress, ItemRow
from squads._api._dto._subentities import SubentityRequest, SubentityShow

# --- items ----------------------------------------------------------------------------------------


class ItemCreateRequest(DTO):
    """Create an item of *type*, written by *author*; *refs* are ``ID`` or ``ID:kind`` tokens,
    *fields* badge codes by field code, *attributes* stored attributes by key."""

    type: str
    title: str
    author: str
    parent: str | None = None
    description: str = ""
    labels: list[str] = Field(default_factory=list[str])
    refs: list[str] = Field(default_factory=list[str])
    assignee: str | None = None
    priority: str | None = None
    fields: dict[str, str] = Field(default_factory=dict[str, str])
    attributes: dict[str, str | list[str]] = Field(default_factory=dict[str, str | list[str]])
    body: str | None = None


class CreatedDisplay(Display):
    """How a created item is displayed: its display plus the file it was written to."""

    file: str


class ItemCreated(ItemRow):
    """The created item's row, with the advisory naming an out-of-lane author when there is
    one."""

    TRAILING: ClassVar[tuple[str, ...]] = ("lane_warning", "badges", "display")
    OMITTED_WHEN_NONE: ClassVar[tuple[str, ...]] = ("lane_warning",)

    lane_warning: str | None = None
    display: CreatedDisplay  # pyright: ignore[reportIncompatibleVariableOverride]


class ItemUpdateRequest(ItemAddress):
    """Change the fields given; a ``clear_*`` flag empties its field, ``set_attributes`` holds
    ``key: value`` pairs and ``force`` makes a status transition the lifecycle does not allow."""

    title: str | None = None
    description: str | None = None
    author: str | None = None
    status: str | None = None
    force: bool = False
    parent: str | None = None
    clear_parent: bool = False
    assignee: str | None = None
    clear_assignee: bool = False
    priority: str | None = None
    clear_priority: bool = False
    add_labels: list[str] = Field(default_factory=list[str])
    rm_labels: list[str] = Field(default_factory=list[str])
    set_attributes: dict[str, str] = Field(default_factory=dict[str, str])
    unset_attributes: list[str] = Field(default_factory=list[str])


class ItemWritten(DTO):
    """The item a write changed, as its row after the write."""

    entry: ItemRow


class ItemUpdated(ItemWritten):
    """The item after an update, and whether the update was only an assignee to clear on an item
    that had none, so nothing was written."""

    nothing_to_clear: bool


class ItemBodyRequest(ItemAddress):
    """Set the item's body to *text*, or append it; *force* replaces prose someone wrote."""

    text: str
    append: bool = False
    force: bool = False


class ItemRetypeRequest(ItemAddress):
    """Reclassify the item to the type *target*, keeping its number."""

    target: str


class ItemRetyped(ItemWritten):
    """The item under its new type, its id and status before, whether the status was reset, and
    the files whose refs to it were rewritten."""

    old_id: str
    old_status: str
    status_reset: bool
    rewritten: list[str]


class ItemRemoveRequest(ItemAddress):
    """Delete the item; *force* cuts the refs other items carry to it instead of refusing."""

    force: bool = False


class ItemRemoved(DTO):
    """The id of the removed item, and the items whose refs to it were cut."""

    removed_id: str
    severed_refs: list[str]


class ItemRefRequest(ItemAddress):
    """Add a ref to *target* (``ID`` or ``ID:kind``); *kind*, when the target names none, else
    the default kind."""

    target: str
    kind: str = ""


class ItemRefRemoveRequest(ItemAddress):
    """Remove the item's refs to *target*."""

    target: str


class ItemRefAdded(ItemWritten):
    """The item after a ref was added, the target's id and the ref's kind."""

    target: str
    kind: str


class ItemRefRemoved(ItemWritten):
    """The item after its refs to a target were removed, the target's id and the kind of each
    ref removed, in stored order."""

    target: str
    kinds: list[str]


class ItemViewRequest(ItemAddress):
    """Place, re-enable or disable the view tag *name* in the item's body."""

    name: str


class ItemViewChanged(ItemWritten):
    """The item after a view tag change, the view, whether the tag changed, and whether it was in
    the body before."""

    view: str
    changed: bool
    was_present: bool


# --- sub-entities ---------------------------------------------------------------------------------


class SubentityAddRequest(ItemAddress):
    """Add a sub-entity of *kind* to the item; *fields* holds the badge codes given by field code,
    *story* the parent story's local id and *deferred_to* the item carrying deferred work."""

    kind: str
    title: str = ""
    fields: dict[str, str] = Field(default_factory=dict[str, str])
    story: str | None = None
    assignee: str | None = None
    status: str | None = None
    deferred_to: str | None = None
    body: str | None = None


class AddedDisplay(DTO):
    """How an added sub-entity is announced: its item and the command that sets its body."""

    item: str
    body_command: str


class SubentityAdded(DTO):
    """Where the new sub-entity's body lives: its local id, file, body region and line span, and
    the advisory on an over-long title when there is one."""

    local_id: str
    path: str
    region: str
    start_line: int | None
    end_line: int | None
    title_advisory: str | None = None
    display: AddedDisplay

    @model_serializer(mode="wrap")
    def _without_advisory(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        dumped: dict[str, Any] = handler(self)
        if dumped.get("title_advisory") is None:
            dumped.pop("title_advisory", None)
        return dumped


class SubentityUpdateRequest(SubentityRequest):
    """Change the sub-entity's fields given; ``fields`` holds badge codes by field code."""

    title: str | None = None
    fields: dict[str, str] = Field(default_factory=dict[str, str])
    story: str | None = None
    clear_story: bool = False
    assignee: str | None = None
    clear_assignee: bool = False
    status: str | None = None
    deferred_to: str | None = None
    force: bool = False


class SubentityWritten(DTO):
    """The sub-entity a write changed, as ``show`` prints it after the write."""

    entry: SubentityShow


class SubentityUpdated(SubentityWritten):
    """The sub-entity after an update, and whether the update was only an assignee to clear on a
    sub-entity that had none, so nothing was written."""

    nothing_to_clear: bool


class SubentityBodyRequest(SubentityRequest):
    """Set the sub-entity's body to *text*, or append it; *force* replaces prose someone
    wrote."""

    text: str
    append: bool = False
    force: bool = False


class SubentityRemoveRequest(SubentityRequest):
    """Delete the sub-entity with its body and discussion."""


class SubentityRemoved(DTO):
    """The removed sub-entity, as its kind and local id, and the item it was removed from."""

    removed: str
    item: str
