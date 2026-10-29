"""What an operation is, and the one protocol every API implements."""

import enum
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel

from squads._api._response import Response

type Method = Literal["GET", "POST", "PATCH", "PUT", "DELETE"]


class Mode(enum.StrEnum):
    """The composition mode the service for an operation is built in."""

    NORMAL = "normal"
    INDEX_CHECK_SKIPPED = "index-check-skipped"
    MIGRATE = "migrate"
    BUNDLED_FALLBACK = "bundled-fallback"
    #: The normal composition, else the one ``sq check`` falls back to for the refusal, which the
    #: service carries so the operation reports it as a finding.
    CHECK = "check"
    #: The workflow spec the invocation resolved, refused when the squad's override does not
    #: load; the bundled documents outside a squad. The service carries any other refusal, and
    #: its operations read the squad only when there is none.
    VOCABULARY = "vocabulary"


class Timeout(enum.StrEnum):
    """How long a remote caller waits for an operation's answer."""

    STANDARD = "standard"
    LONG = "long"


class Ground(enum.StrEnum):
    """Why an operation may run on a squad whose schema differs from the package's."""

    #: It is the migration: it advances the corpus, so it runs only on a squad that is behind.
    MIGRATION = "is the migration"
    #: It reads the package's own registry and touches no squad state.
    NO_SQUAD_STATE = "touches no squad state"
    #: It holds the reconcile licence. The reconcile is a routine, not a command.
    LICENCE = "holds the reconcile licence"


@dataclass(frozen=True)
class Grant:
    """The ground an operation or command gets past the schema gate on, and the directions."""

    ground: Ground
    behind: bool
    ahead: bool

    def covers(self, *, behind: bool) -> bool:
        return self.behind if behind else self.ahead


@dataclass(frozen=True)
class Operation[Req: BaseModel, Res]:
    """One entry of the operation table: its route, its request and response types, and how
    it runs."""

    name: str
    method: Method
    path: str
    request: type[Req]
    response: type[Res]
    mode: Mode = Mode.NORMAL
    grant: Grant | None = None
    local_only: bool = False
    timeout: Timeout = Timeout.STANDARD
    #: The field of ``data`` that ``--json`` prints, where the frozen document is not an object;
    #: ``None`` prints ``data`` whole.
    json_field: str | None = None


class Api(Protocol):
    """Runs an operation and answers with its response, in this process or over HTTP."""

    async def call[Req: BaseModel, Res](
        self, op: Operation[Req, Res], req: Req
    ) -> Response[Res]: ...
