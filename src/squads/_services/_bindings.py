"""The binding table: the ``Service`` method that handles each operation.

Each resource group has its own section, matching the operation table's.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import cast

from pydantic import BaseModel

from squads._api import _ops as ops
from squads._api._api import Operation
from squads._api._response import Response
from squads._services._service import Service

type Handler[Req, Res] = Callable[[Service, Req], Awaitable[Response[Res]]]


@dataclass(frozen=True)
class Binding[Req: BaseModel, Res]:
    """An operation and the method that handles it."""

    op: Operation[Req, Res]
    handler: Handler[Req, Res]


def bind[Req: BaseModel, Res](
    op: Operation[Req, Res], handler: Handler[Req, Res]
) -> Binding[Req, Res]:
    """Pair *op* with *handler*, whose request and response types must be the operation's."""
    return Binding(op, handler)


#: Left unannotated, so pyright checks each pair against its own operation rather than ``Any``.
BINDINGS = (
    # --- items
    bind(ops.ITEMS_LIST, Service.list_item_rows),
    # --- item reads
    bind(ops.ITEM_SHOW, Service.show_item),
    # --- item writes
    bind(ops.ITEM_STATUS, Service.move_item_status),
    # --- roster
    # --- squad state
    # --- corpus-wide
)


def handler_for[Req: BaseModel, Res](op: Operation[Req, Res]) -> Handler[Req, Res]:
    """The method bound to *op*."""
    for binding in BINDINGS:
        if binding.op is op:
            return cast(Handler[Req, Res], binding.handler)
    raise LookupError(f"no handler is bound to the operation {op.name!r}")
