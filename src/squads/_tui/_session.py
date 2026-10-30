"""The API session every `sq ui` screen calls through: a per-call API selector and the
workflow catalogs the screens read their choices and categories from."""

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from squads._api import _ops as ops
from squads._api._api import Api, Operation
from squads._api._dto._workflow import (
    CatalogRequest,
    CollectionCatalog,
    StatusCatalog,
    TypeCatalog,
)
from squads._api._response import Response
from squads._errors import SquadsError

#: Answers the API the next call goes through; asked again on every call.
type ApiSelector = Callable[[], Api]


@dataclass(frozen=True)
class Catalogs:
    """The workflow catalogs of the squad: its types, statuses and badge collections."""

    types: TypeCatalog
    statuses: StatusCatalog
    collections: CollectionCatalog


def categories(types: TypeCatalog) -> list[str]:
    """Every category a declared type names, ordered by the first type of each in the type
    catalog's `order`."""
    return list(dict.fromkeys(row.category for row in types.items))


def type_options(catalogs: Catalogs) -> list[tuple[str, str]]:
    """Every non-roster type, by name, as a (singular label, type) choice."""
    rows = sorted((r for r in catalogs.types.items if not r.reserved), key=lambda r: r.type)
    return [(r.labels["singular"], r.type) for r in rows]


def status_options(catalogs: Catalogs) -> list[tuple[str, str]]:
    """Every declared status, by name, as a choice."""
    return [(r.status, r.status) for r in sorted(catalogs.statuses.items, key=lambda r: r.status)]


class Session:
    """Runs each operation on the API the selector answers at that call, and holds the catalogs
    loaded at start."""

    def __init__(self, select_api: ApiSelector) -> None:
        self._select_api = select_api
        self._catalogs: Catalogs | None = None

    async def call[Req: BaseModel, Res](self, op: Operation[Req, Res], req: Req) -> Response[Res]:
        api = self._select_api()
        response = await api.call(op, req)
        if getattr(api, "declined", False) and self._catalogs is not None:
            # The daemon the session was talking to retired: the vocabulary may have changed with
            # it, and the next call reaches a daemon on the new configuration.
            await self.load_catalogs()
        return response

    async def load_catalogs(self) -> None:
        types = await self.call(ops.WORKFLOW_TYPES, CatalogRequest())
        statuses = await self.call(ops.WORKFLOW_STATUSES, CatalogRequest())
        collections = await self.call(ops.WORKFLOW_COLLECTIONS, CatalogRequest())
        self._catalogs = Catalogs(types.data, statuses.data, collections.data)

    @property
    def catalogs(self) -> Catalogs:
        if self._catalogs is None:
            raise SquadsError("the workflow catalogs are not loaded")
        return self._catalogs
