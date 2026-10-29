"""The refs DTOs: an item's refs to other items, and the refs other items carry to it."""

from typing import Any

from pydantic import ConfigDict, Field, SerializerFunctionWrapHandler, model_serializer

from squads._api._dto._base import DTO
from squads._api._dto._items import ItemAddress


class RefsRequest(ItemAddress):
    """The refs the item carries (*out*), the refs other items carry to it (*incoming*), or
    both."""

    out: bool = True
    incoming: bool = False


class RefDisplay(DTO):
    """How a ref is shown: its kind's declared label."""

    kind: str


class RefEntry(DTO):
    """One ref: the item at its other end and its kind."""

    id: str
    kind: str
    display: RefDisplay


class Refs(DTO):
    """Each direction asked for, ``out`` then ``in``; a direction not asked for is absent."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    out: list[RefEntry] | None = None
    incoming: list[RefEntry] | None = Field(default=None, alias="in")

    @model_serializer(mode="wrap")
    def _asked(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        dumped: dict[str, Any] = handler(self)
        shown = {"out": dumped.get("out"), "in": dumped.get("incoming", dumped.get("in"))}
        return {key: value for key, value in shown.items() if value is not None}
