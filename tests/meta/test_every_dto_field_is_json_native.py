"""Every DTO field holds JSON-native values only (strings, numbers, booleans, null, lists,
string-keyed objects, nested DTOs), computed fields included, so the local object renders as the
parsed HTTP body does. Extra keys are allowed only on the item row and the show document."""

import importlib
import pkgutil
import types
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, JsonValue

import squads._api._dto as dto_package
from squads._api._dto._base import DTO

#: The DTOs whose model accepts extra keys: the item fields, and the rows and show document built
#: on them.
EXTRA_ALLOWED = frozenset(
    {
        "ItemFields",
        "ItemRow",
        "ItemShow",
        "ItemShowWithSpec",
        "MineRow",
    }
)

_SCALARS = (str, int, float, bool, type(None))


def json_native(annotation: Any) -> bool:
    """Whether every value *annotation* admits is JSON-native."""
    if annotation in _SCALARS or annotation is JsonValue:
        return True
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, types.UnionType):
        return all(json_native(a) for a in args)
    if origin is list:
        return json_native(args[0])
    if origin is dict:
        return args[0] is str and json_native(args[1])
    return isinstance(annotation, type) and issubclass(annotation, DTO)


def _dto_classes() -> list[type[BaseModel]]:
    found: list[type[BaseModel]] = []
    for info in pkgutil.iter_modules(dto_package.__path__, f"{dto_package.__name__}."):
        module = importlib.import_module(info.name)
        found += [
            value
            for value in vars(module).values()
            if isinstance(value, type)
            and issubclass(value, BaseModel)
            and value.__module__ == module.__name__
        ]
    return found


def test_the_scan_finds_the_dto_modules() -> None:
    assert {"ItemRow", "Display"} <= {cls.__name__ for cls in _dto_classes()}


def test_every_dto_field_is_json_native() -> None:
    offenders = [
        f"{cls.__module__}.{cls.__name__}.{name}: {field.annotation}"
        for cls in _dto_classes()
        for name, field in cls.model_fields.items()
        if not json_native(field.annotation)
    ] + [
        f"{cls.__module__}.{cls.__name__}.{name} (computed): {field.return_type}"
        for cls in _dto_classes()
        for name, field in cls.model_computed_fields.items()
        if not json_native(field.return_type)
    ]
    assert not offenders, "DTO fields must hold JSON-native values:\n" + "\n".join(offenders)


def test_only_the_item_row_accepts_extra_keys() -> None:
    extra = {c.__name__ for c in _dto_classes() if c.model_config.get("extra") == "allow"}
    assert extra <= EXTRA_ALLOWED, (
        f"extra keys escape the field check: {sorted(extra - EXTRA_ALLOWED)}"
    )
