"""A request onto its operation's request DTO: the query string of a ``GET``, the JSON body of any
other method, and the fields the route's path names."""

import json
from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError
from starlette.requests import Request

from squads._api._api import Operation
from squads._errors import SquadsError


def is_list(annotation: Any) -> bool:
    """Whether *annotation* is a list, or a union that admits one."""
    if get_origin(annotation) is list:
        return True
    if get_origin(annotation) in (Union, UnionType):
        return any(get_origin(arg) is list for arg in get_args(annotation))
    return False


def _query_fields(op: Operation[Any, Any], request: Request) -> dict[str, Any]:
    """The request's query string as fields: a repeated key is a list when its field is one and
    is refused otherwise."""
    declared = op.request.model_fields
    fields: dict[str, Any] = {}
    for key in dict.fromkeys(request.query_params.keys()):
        if key in declared and is_list(declared[key].annotation):
            fields[key] = request.query_params.getlist(key)
        else:
            values = request.query_params.getlist(key)
            if len(values) > 1:
                raise SquadsError(f"invalid request: {key} takes one value, got {len(values)}")
            fields[key] = values[0]
    return fields


async def _body_fields(request: Request) -> dict[str, Any]:
    """The JSON object a request carries as its body; no body is an empty object."""
    raw = await request.body()
    if not raw.strip():
        return {}
    try:
        decoded: Any = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:  # fmt: skip
        raise SquadsError(f"the request body is not valid JSON: {exc}") from exc
    if not isinstance(decoded, dict):
        raise SquadsError("the request body must be a JSON object")
    return {str(k): v for k, v in decoded.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]


def _problem(exc: ValidationError) -> str:
    """The first problems of a failed validation, one per field."""
    parts = [
        f"{'.'.join(str(p) for p in err['loc']) or 'body'}: {err['msg']}" for err in exc.errors()
    ]
    return "invalid request: " + "; ".join(parts)


async def request_dto[Req: BaseModel](op: Operation[Req, Any], request: Request) -> Req:
    """The request DTO of *op* that *request* carries. A field the DTO does not declare, a body
    that is not a JSON object and a value of the wrong type are refused as an invalid request; the
    route's path fields take the path's value."""
    fields = _query_fields(op, request) if op.method == "GET" else await _body_fields(request)
    fields.update(request.path_params)
    unknown = sorted(set(fields) - set(op.request.model_fields))
    if unknown:
        raise SquadsError(f"invalid request: unknown field(s) {', '.join(unknown)}")
    try:
        return op.request.model_validate(fields)
    except ValidationError as exc:
        raise SquadsError(_problem(exc)) from exc
