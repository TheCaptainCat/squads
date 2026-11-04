"""Tolerant readers of a tracker's JSON answers: a value of the wrong shape reads as absent."""

from collections.abc import Iterator, Mapping
from typing import Any, cast


def mapping(value: object) -> Mapping[str, Any]:
    """*value* when it is a JSON object, else an empty one."""
    return cast("Mapping[str, Any]", value) if isinstance(value, Mapping) else {}


def is_object(value: object) -> bool:
    """Whether *value* is a JSON object."""
    return isinstance(value, Mapping)


def text(record: Mapping[str, Any], key: str) -> str:
    """The scalar under *key* of *record* as text, or an empty string."""
    value = record.get(key)
    return "" if value is None or isinstance(value, Mapping | list) else str(value)


def records(value: object) -> Iterator[Mapping[str, Any]]:
    """The objects of a JSON array; anything else, and any element that is not an object, yields
    nothing."""
    if isinstance(value, list):
        for element in cast("list[Any]", value):
            if isinstance(element, Mapping):
                yield cast("Mapping[str, Any]", element)


def names(value: object, key: str = "name") -> tuple[str, ...]:
    """The strings of a JSON array, or the *key* of each of its objects; blanks are dropped."""
    found: list[str] = []
    if isinstance(value, list):
        for element in cast("list[Any]", value):
            label = element if isinstance(element, str) else text(mapping(element), key)
            if label:
                found.append(label)
    return tuple(found)
