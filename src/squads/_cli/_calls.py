"""How a command reaches its operation: the API an invocation selects, the call, and the
notices and omissions a response carries."""

import asyncio
import json
from typing import Any

from pydantic import BaseModel

from squads import _spans as spans
from squads._api._api import Api, Operation
from squads._api._response import Response
from squads._cli import _common as common
from squads._context import get_context


def local_api() -> Api:
    """The API that runs operations in this process; the one place the CLI reaches the service
    layer."""
    from squads._services._local_api import LocalApi

    return LocalApi(sources=common.invocation_sources)


def select_api() -> Api:
    """The API this invocation's commands call."""
    return local_api()


def call[Req: BaseModel, Res](op: Operation[Req, Res], req: Req) -> Response[Res]:
    """Make the one call a command makes, through the invocation's API."""
    api = get_context().api
    if api is None:
        api = select_api()
    with spans.span("api_call"):
        response = asyncio.run(api.call(op, req))
    spans.mark("call_done")
    return response


def print_warnings(response: Response[Any]) -> None:
    """Each warning of *response* on stderr, once per invocation."""
    common.print_notices(response.warnings)


def print_json(op: Operation[Any, Any], response: Response[Any]) -> None:
    """The one JSON document ``--json`` prints: ``data``, or the field of it *op* names. The
    response's warnings go to stderr first, so stdout holds the document alone."""
    print_warnings(response)
    data: BaseModel = response.data
    dumped = data.model_dump(mode="json")
    common.print_json_clean(json.dumps(dumped if op.json_field is None else dumped[op.json_field]))


def finish(response: Response[Any], *, json_out: bool) -> None:
    """Name what a partial read left out, then exit ``4``; nothing when it left nothing out."""
    common.report_omissions(list(response.omitted), json_out=json_out)
