"""``HttpApi``: the client of the daemon. It sends an operation as one HTTP request and turns the
answer back into the response or the error a local run would have given, on the standard library
alone.

It decides nothing about where the daemon is or how the request is spelled for a given invocation:
the caller hands it a way to connect, the headers of the call and the vocabulary the command was
parsed with.
"""

import http.client
import threading
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from squads._api._api import Api, Operation, Timeout
from squads._api._http import (
    CLIENT_HEADER,
    SCHEMA_HEADER,
    VOCABULARY_HEADER,
    encode_request,
    error_detail,
    is_retiring,
    parse_response,
)
from squads._api._response import Response
from squads._api._vocabulary import DOCUMENTS, VocabularyHash
from squads._errors import ClientInterruptedError, SquadsError
from squads._models._schema import SCHEMA_VERSION, schema_tuple

#: Seconds a connection may take to open, for every operation.
CONNECT_TIMEOUT = 5.0
#: Seconds a ``standard`` operation may take to answer; a ``long`` one is never cut off.
ANSWER_TIMEOUT = 300.0
#: Seconds a ``long`` operation waits before the caller is told it is waiting.
WAIT_NOTICE_AFTER = 10.0

#: Opens a connection to the daemon within the seconds given, or answers ``None`` when there is
#: nothing to connect to.
type Connect = Callable[[float], http.client.HTTPConnection | None]


class HttpApi:
    """Runs each operation on the daemon over HTTP.

    *local* makes the API that runs an operation the daemon never serves, and the call the daemon
    declined because its configuration changed or could not be reached, when the endpoint has a
    local mode. *restart* starts the daemon again when nothing answers at connect time, and says
    whether one now serves; it is asked once per call, before anything is sent.
    """

    def __init__(  # noqa: PLR0913 — the caller's keyword-only hooks, each one thing
        self,
        *,
        connect: Connect,
        endpoint: str,
        headers: Callable[[], dict[str, str]],
        vocabulary: Callable[[], VocabularyHash],
        package_version: str,
        local: Callable[[], Api] | None,
        waiting: Callable[[str], None] | None = None,
        resolve: Callable[[], tuple[Connect, str]] | None = None,
        restart: Callable[[], bool] | None = None,
    ) -> None:
        self._connect = connect
        self._endpoint = endpoint
        self._headers = headers
        self._vocabulary = vocabulary
        self._package_version = package_version
        self._local = local
        self._waiting = waiting
        self._resolve = resolve
        self._restart = restart
        #: Whether the last call was declined by a daemon whose configuration had changed.
        self.declined = False
        #: The handler time the daemon reported for the last call, in milliseconds.
        self.handler_ms: float | None = None

    async def call[Req: BaseModel, Res](self, op: Operation[Req, Res], req: Req) -> Response[Res]:
        """Send *op* with *req* and answer what the daemon answers. Nothing is sent twice: a
        connection lost after the request left is an error, and only a call the daemon declined
        before it ran, or that never reached a daemon, runs locally."""
        answered = self._attempt(op, req)
        return answered if answered is not None else await self._run_locally(op, req)

    def call_sync[Req: BaseModel, Res](self, op: Operation[Req, Res], req: Req) -> Response[Res]:
        """:meth:`call` for a caller with no event loop, which a call to the daemon never needs;
        only a call that runs locally starts one."""
        answered = self._attempt(op, req)
        if answered is not None:
            return answered
        import asyncio

        return asyncio.run(self._run_locally(op, req))

    def _attempt[Req: BaseModel, Res](
        self, op: Operation[Req, Res], req: Req
    ) -> Response[Res] | None:
        """The daemon's answer, or ``None`` when the call is to run locally. A refusal, a lost
        connection and a timeout raise."""
        self.declined = False
        if op.local_only:
            return None
        method, target, body = encode_request(op, req)
        sent = self._request_headers(method, body)
        retried = False
        restarted = False
        while True:
            conn = self._open()
            if conn is None and self._restart is not None and not restarted:
                # Nothing was sent, so a daemon that has gone is started again and asked once.
                restarted = True
                if self._restart():
                    continue
                return self._unreachable("no daemon is listening")
            if conn is None:
                return self._unreachable("no daemon is listening")
            try:
                status, answer = self._exchange(conn, op, method, target, body, sent)
            except OSError as exc:
                raise self._lost(exc) from exc
            finally:
                conn.close()
            if not is_retiring(status, answer):
                break
            # Nothing ran. A squad hosted elsewhere has no local mode: it is asked again, once,
            # at the endpoint resolved afresh.
            if self._local is None and self._resolve is not None and not retried:
                self._connect, self._endpoint = self._resolve()
                retried = True
                continue
            return self._declined()
        if status != 200:
            raise self._refusal(status, answer)
        return parse_response(op, status, answer)

    # ------------------------------------------------------------------------- the request

    def _request_headers(self, method: str, body: bytes | None) -> dict[str, str]:
        sent = {name: _wire(value) for name, value in self._headers().items()}
        sent[SCHEMA_HEADER] = SCHEMA_VERSION
        sent[VOCABULARY_HEADER] = self._vocabulary().hash
        if method != "GET":
            sent["Content-Type"] = "application/json"
            sent[CLIENT_HEADER] = "1"
            sent["Content-Length"] = str(len(body or b""))
        return sent

    def _open(self) -> http.client.HTTPConnection | None:
        conn = self._connect(CONNECT_TIMEOUT)
        if conn is None:
            return None
        try:
            conn.connect()
        except OSError:
            conn.close()
            return None
        return conn

    def _exchange(
        self,
        conn: http.client.HTTPConnection,
        op: Operation[Any, Any],
        method: str,
        target: str,
        body: bytes | None,
        headers: dict[str, str],
    ) -> tuple[int, bytes]:
        """One request and its whole answer, within the operation's answer timeout."""
        answer = None if op.timeout is Timeout.LONG else ANSWER_TIMEOUT
        if conn.sock is not None:
            conn.sock.settimeout(answer)
        notice: threading.Timer | None = None
        if op.timeout is Timeout.LONG and self._waiting is not None:
            notice = threading.Timer(
                WAIT_NOTICE_AFTER, self._waiting, [f"waiting for the daemon ({op.name})…"]
            )
            notice.daemon = True
            notice.start()
        try:
            conn.request(method, target, body=body, headers=headers)
            reply = conn.getresponse()
            self.handler_ms = _handler_ms(reply.getheader("Server-Timing"))
            return reply.status, reply.read()
        except TimeoutError as exc:
            raise SquadsError(
                f"no answer from the squad served at {self._endpoint} after {answer:g} s; "
                "the operation may still complete. Check its result before running it again."
            ) from exc
        except KeyboardInterrupt as exc:
            raise ClientInterruptedError(
                f"no answer from the squad served at {self._endpoint}; "
                "the operation may still complete. Check its result before running it again."
            ) from exc
        except http.client.HTTPException as exc:
            raise self._lost(exc) from exc
        finally:
            if notice is not None:
                notice.cancel()

    # ------------------------------------------------------------------------- the answer

    def _lost(self, exc: BaseException) -> SquadsError:
        return SquadsError(
            f"the connection to the squad served at {self._endpoint} was lost after the request "
            f"was sent ({exc}); the operation may still complete. Check its result before "
            "running it again."
        )

    def _refusal(self, status: int, body: bytes) -> SquadsError:
        """The error an answer other than ``200`` stands for."""
        detail = error_detail(status, body)
        if detail.type == "schema_mismatch":
            failure = SquadsError(self._schema_message(detail.details or {}))
        elif detail.type == "vocabulary_mismatch":
            failure = SquadsError(self._vocabulary_message(detail.details or {}))
        else:
            failure = SquadsError(detail.message)
        failure.warnings = tuple(detail.warnings)
        return failure

    def _schema_message(self, versions: dict[str, str]) -> str:
        ours = SCHEMA_VERSION
        theirs = versions.get("daemon", "?")
        head = (
            f"squads {self._package_version} speaks schema v{ours}, and the squad served at "
            f"{self._endpoint} runs schema v{theirs}."
        )
        if theirs != "?" and schema_tuple(ours) < schema_tuple(theirs):
            return f"{head} Install a squads release at schema v{theirs}, then re-run."
        return (
            f"{head} The squad's server must be upgraded and the squad migrated "
            "(sq migrate up) before this client can use it."
        )

    def _vocabulary_message(self, digests: dict[str, str]) -> str:
        ours = self._vocabulary().documents
        differing = [name for name in DOCUMENTS if digests.get(name) != ours.get(name)]
        named = ", ".join(differing) or "workflow.toml"
        return (
            f"this checkout's workflow vocabulary differs from the squad served at "
            f"{self._endpoint} ({named} differs). Bring this checkout in line with the squad, "
            "by pulling its configuration or installing the squads version it runs, then re-run."
        )

    # ------------------------------------------------------------------------- local mode

    async def _run_locally[Req: BaseModel, Res](
        self, op: Operation[Req, Res], req: Req
    ) -> Response[Res]:
        if self._local is None:
            raise SquadsError(f"{op.name} runs locally and this client has no local mode")
        return await self._local().call(op, req)

    def _declined(self) -> None:
        """The daemon's configuration changed and nothing ran: the call runs locally when the squad
        is here, else the server is restarting."""
        self.declined = True
        if self._local is None:
            raise SquadsError(
                f"the squad served at {self._endpoint} is restarting; "
                "re-run the command in a moment."
            )

    def _unreachable(self, cause: str) -> None:
        """Nothing was sent: the call runs locally when the squad is here, else say why not."""
        if self._local is None:
            raise SquadsError(f"cannot reach the squad served at {self._endpoint}: {cause}.")


def _handler_ms(header: str | None) -> float | None:
    """The ``handler`` duration of a ``Server-Timing`` header."""
    for entry in (header or "").split(","):
        name, _, rest = entry.strip().partition(";")
        if name == "handler" and rest.startswith("dur="):
            try:
                return float(rest[4:])
            except ValueError:
                return None
    return None


def _wire(value: str) -> str:
    """*value* as ``http.client`` sends it: it encodes header text as Latin-1, so UTF-8 bytes are
    carried as the Latin-1 characters that spell them."""
    return value.encode("utf-8").decode("latin-1")
