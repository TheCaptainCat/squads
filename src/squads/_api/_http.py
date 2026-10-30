"""``HttpApi``'s wire helpers: a request DTO onto a route, and an answer back into a response."""

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import quote, urlencode

from pydantic import BaseModel, ValidationError

from squads._api._api import Operation
from squads._api._errors import ErrorBody
from squads._api._response import Response
from squads._errors import SquadsError

_PATH_FIELD = re.compile(r"\{(\w+)\}")

#: The headers a request carries beside its body.
ACTOR_HEADER = "Squads-Actor"
AT_HEADER = "Squads-At"
SESSION_HEADER = "Squads-Session-Id"
PARENT_SESSION_HEADER = "Squads-Parent-Session-Id"
CLIENT_DIR_HEADER = "Squads-Client-Dir"
VOCABULARY_HEADER = "Squads-Vocabulary"
SCHEMA_HEADER = "Squads-Schema"
CLIENT_HEADER = "Squads-Client"
IF_MATCH_HEADER = "If-Match"


@dataclass(frozen=True)
class RequestMetadata:
    """What a request's headers declare: each field is ``None`` when its header is absent."""

    actor: str | None = None
    at: str | None = None
    session_id: str | None = None
    parent_session_id: str | None = None
    client_dir: str | None = None
    vocabulary: str | None = None
    schema: str | None = None
    if_match: str | None = None


def _header_text(value: str | None) -> str | None:
    """*value* as the client meant it: HTTP carries header text as Latin-1, so a value the client
    sent as UTF-8 bytes is read back from them; ``None`` for an absent or empty header."""
    if not value:
        return None
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):  # fmt: skip
        return value


def request_metadata(headers: Mapping[str, str]) -> RequestMetadata:
    """The metadata *headers* declare; *headers* looks a name up without regard to case."""
    return RequestMetadata(
        actor=_header_text(headers.get(ACTOR_HEADER)),
        at=_header_text(headers.get(AT_HEADER)),
        session_id=_header_text(headers.get(SESSION_HEADER)),
        parent_session_id=_header_text(headers.get(PARENT_SESSION_HEADER)),
        client_dir=_header_text(headers.get(CLIENT_DIR_HEADER)),
        vocabulary=_header_text(headers.get(VOCABULARY_HEADER)),
        schema=_header_text(headers.get(SCHEMA_HEADER)),
        if_match=_header_text(headers.get(IF_MATCH_HEADER)),
    )


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

    method, path = op.route
    target = _PATH_FIELD.sub(fill, path)
    if method == "GET":
        query = _query(fields)
        return method, f"{target}?{query}" if query else target, None
    return method, target, json.dumps(fields).encode("utf-8")


def parse_response[Res](op: Operation[Any, Res], status: int, body: bytes) -> Response[Res]:
    """The response a ``200`` answer carries; any other answer raises the ``SquadsError`` whose
    message the server sent."""
    if status == 200:
        return Response[op.response].model_validate_json(body)
    try:
        detail = ErrorBody.model_validate_json(body).error
    except ValidationError:
        raise SquadsError(f"the server answered {status} with no error body") from None
    failure = SquadsError(detail.message)
    failure.warnings = tuple(detail.warnings)
    raise failure
