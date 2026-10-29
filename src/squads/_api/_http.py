"""``HttpApi``'s wire helpers: a request DTO onto a route, and an answer back into a response."""

import json
import re
from typing import Any, cast
from urllib.parse import quote, urlencode

from pydantic import BaseModel, ValidationError

from squads._api._api import Operation
from squads._api._errors import ErrorBody
from squads._api._response import Response
from squads._errors import SquadsError

_PATH_FIELD = re.compile(r"\{(\w+)\}")


def _query_value(value: object) -> str:
    """A scalar as a query parameter spells it."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _query(fields: dict[str, Any]) -> str:
    """The query string of a flat request: ``None`` is left out and a list repeats its key."""
    pairs: list[tuple[str, str]] = []
    for name, value in fields.items():
        if value is None:
            continue
        values = cast(list[Any], value) if isinstance(value, list) else [value]
        pairs.extend((name, _query_value(v)) for v in values)
    return urlencode(pairs)


def encode_request(op: Operation[Any, Any], req: BaseModel) -> tuple[str, str, bytes | None]:
    """The method, target and body that put *req* on *op*'s route.

    Each ``{field}`` of the path takes that field's value; the other fields go in the query
    string of a ``GET`` and in a UTF-8 JSON body otherwise.
    """
    fields: dict[str, Any] = req.model_dump(mode="json")

    def fill(match: re.Match[str]) -> str:
        return quote(str(fields.pop(match[1])), safe="")

    target = _PATH_FIELD.sub(fill, op.path)
    if op.method == "GET":
        query = _query(fields)
        return op.method, f"{target}?{query}" if query else target, None
    return op.method, target, json.dumps(fields).encode("utf-8")


def parse_response[Res](op: Operation[Any, Res], status: int, body: bytes) -> Response[Res]:
    """The response a ``200`` answer carries; any other answer raises the ``SquadsError`` whose
    message the server sent."""
    if status == 200:
        return Response[op.response].model_validate_json(body)
    try:
        detail = ErrorBody.model_validate_json(body).error
    except ValidationError:
        raise SquadsError(f"the server answered {status} with no error body") from None
    raise SquadsError(detail.message)
