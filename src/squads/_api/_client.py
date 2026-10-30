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

    *local* runs an operation the daemon never serves, and the call the daemon declined because
    its configuration changed or could not be reached, when the endpoint has a local mode.
    """

    def __init__(
        self,
        *,
        connect: Connect,
        endpoint: str,
        headers: Callable[[], dict[str, str]],
        vocabulary: Callable[[], VocabularyHash],
        package_version: str,
        local: Api | None,
        waiting: Callable[[str], None] | None = None,
    ) -> None:
        self._connect = connect
        self._endpoint = endpoint
        self._headers = headers
        self._vocabulary = vocabulary
        self._package_version = package_version
        self._local = local
        self._waiting = waiting

    async def call[Req: BaseModel, Res](self, op: Operation[Req, Res], req: Req) -> Response[Res]:
        """Send *op* with *req* and answer what the daemon answers. Nothing is sent twice: a
        connection lost after the request left is an error, and only a call the daemon declined
        before it ran, or that never reached a daemon, runs locally."""
        if op.local_only:
            return await self._run_locally(op, req)
        method, target, body = encode_request(op, req)
        sent = self._request_headers(method, body)
        conn = self._open()
        if conn is None:
            return await self._unreachable(op, req, "no daemon is listening")
        try:
            status, answer = self._exchange(conn, op, method, target, body, sent)
        except OSError as exc:
            raise self._lost(exc) from exc
        finally:
            conn.close()
        if is_retiring(status, answer):
            return await self._declined(op, req)
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
        return await self._local.call(op, req)

    async def _declined[Req: BaseModel, Res](
        self, op: Operation[Req, Res], req: Req
    ) -> Response[Res]:
        """The daemon's configuration changed and nothing ran: run the call locally when the
        squad is here, else say the server is restarting."""
        if self._local is not None:
            return await self._local.call(op, req)
        raise SquadsError(
            f"the squad served at {self._endpoint} is restarting; re-run the command in a moment."
        )

    async def _unreachable[Req: BaseModel, Res](
        self, op: Operation[Req, Res], req: Req, cause: str
    ) -> Response[Res]:
        """Nothing was sent: run the call locally when the squad is here, else say why not."""
        if self._local is not None:
            return await self._local.call(op, req)
        raise SquadsError(f"cannot reach the squad served at {self._endpoint}: {cause}.")


def _wire(value: str) -> str:
    """*value* as ``http.client`` sends it: it encodes header text as Latin-1, so UTF-8 bytes are
    carried as the Latin-1 characters that spell them."""
    return value.encode("utf-8").decode("latin-1")
