"""The OpenAPI 3.1 document of the daemon's API, built from the operation table: each operation's
route, its parameters and body from the request DTO, its answer from the response DTO and the
error envelope of every status it can answer with (ADR-1225, section 6).

Schemas are taken in validation mode. The item and sub-entity rows serialise through a model
serializer typed ``dict[str, Any]``, which leaves their serialization-mode schema an opaque
object, while the validation-mode schema lists every key and admits the flat stored attributes.
The document names no squad's vocabulary: badge fields, kinds and attributes travel in maps and
flat attributes, so one document describes every squad.
"""

from typing import Any, cast

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

from squads._api._api import Operation
from squads._api._dto._daemon import DaemonIdentity, DaemonStopping
from squads._api._errors import HTTP_STATUS, ErrorBody
from squads._api._http import (
    ACTOR_HEADER,
    AT_HEADER,
    CLIENT_DIR_HEADER,
    CLIENT_HEADER,
    IF_MATCH_HEADER,
    PARENT_SESSION_HEADER,
    SCHEMA_HEADER,
    SESSION_HEADER,
    VOCABULARY_HEADER,
)
from squads._api._ops import CONDITIONAL_WRITES, OPERATIONS
from squads._api._response import Response
from squads._daemon._request import is_list

_REF = "#/components/schemas/{model}"

#: The headers a request may carry, and what each means.
_HEADERS: tuple[tuple[str, str], ...] = (
    (ACTOR_HEADER, "The actor to record, as the declared slug; never verified."),
    (AT_HEADER, "The ISO 8601 time to record instead of now."),
    (SESSION_HEADER, "The caller's session id, recorded in the reflog."),
    (PARENT_SESSION_HEADER, "The caller's parent session id, recorded in the reflog."),
    (
        CLIENT_DIR_HEADER,
        "The directory paths in messages are spelled from; absent, the squad's root.",
    ),
    (VOCABULARY_HEADER, "The hash of the workflow vocabulary the caller parsed its command with."),
    (SCHEMA_HEADER, "The schema version of the caller's package; this document's info.version."),
    (CLIENT_HEADER, "Required with the value 1 on every request that is not a GET."),
)

_ERROR_DESCRIPTIONS = {
    400: "invalid: the request or the operation was refused.",
    404: "not_found: no such item, role, comment or sub-entity.",
    409: "conflict, vocabulary_mismatch, schema_mismatch or changed_since_read.",
    423: "locked: the index lock stayed held by another process.",
    500: "internal: an unexpected failure; the daemon's log holds the traceback.",
}


def _ref_name(ref: dict[str, Any]) -> str:
    return str(ref["$ref"]).rsplit("/", 1)[-1]


def _header_parameter(name: str, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "in": "header",
        "required": False,
        "description": description,
        "schema": {"type": "string"},
    }


def _parameters(
    op: Operation[Any, Any], schema: dict[str, Any], path_fields: set[str]
) -> list[dict[str, Any]]:
    """The path parameters of *op*, then, for a ``GET``, a query parameter per other field."""
    properties: dict[str, Any] = schema.get("properties", {})
    required = set(schema.get("required", []))
    found: list[dict[str, Any]] = []
    for name, prop in properties.items():
        if name in path_fields:
            found.append({"name": name, "in": "path", "required": True, "schema": prop})
        elif op.method == "GET":
            param: dict[str, Any] = {
                "name": name,
                "in": "query",
                "required": name in required,
                "schema": prop,
            }
            if is_list(op.request.model_fields[name].annotation):
                param.update(style="form", explode=True)
            found.append(param)
    return found


def _body(schema: dict[str, Any], path_fields: set[str]) -> dict[str, Any] | None:
    """The request body of an operation: its request DTO without the fields the path names."""
    properties = {k: v for k, v in schema.get("properties", {}).items() if k not in path_fields}
    if not properties:
        return None
    body: dict[str, Any] = {"type": "object", "properties": properties}
    required = [name for name in schema.get("required", []) if name not in path_fields]
    if required:
        body["required"] = required
    return {"required": bool(required), "content": {"application/json": {"schema": body}}}


def _responses(op: Operation[Any, Any], answer: dict[str, Any]) -> dict[str, Any]:
    headers: dict[str, Any] = {"Server-Timing": {"schema": {"type": "string"}}}
    if op.method != "DELETE":
        headers["ETag"] = {
            "description": "The strong ETag of the item the operation addressed, when it did.",
            "schema": {"type": "string"},
        }
    responses: dict[str, Any] = {
        "200": {
            "description": "The operation ran.",
            "headers": headers,
            "content": {"application/json": {"schema": answer}},
        }
    }
    statuses = sorted({status for _, status in HTTP_STATUS})
    for status in statuses:
        responses[str(status)] = {
            "description": _ERROR_DESCRIPTIONS[status],
            "content": {"application/json": {"schema": {"$ref": _REF.format(model="ErrorBody")}}},
        }
    responses["503"] = {
        "description": "retiring: the daemon's configuration changed and nothing ran.",
        "content": {"application/json": {"schema": {"$ref": _REF.format(model="NotExecuted")}}},
    }
    return responses


def _operation(
    op: Operation[Any, Any], definitions: dict[str, Any], mapping: dict[Any, dict[str, Any]]
) -> dict[str, Any]:
    request_schema = definitions[_ref_name(mapping[(op.request, "validation")])]
    path_fields = {part[1:-1] for part in op.path.split("/") if part.startswith("{")}
    doc = (op.request.__doc__ or "").strip().split("\n\n")[0].replace("\n", " ")
    described: dict[str, Any] = {
        "operationId": op.name,
        "summary": doc,
        "parameters": [
            *_parameters(op, request_schema, path_fields),
            *({"$ref": f"#/components/parameters/{h}"} for h, _ in _HEADERS),
            *(
                [{"$ref": f"#/components/parameters/{IF_MATCH_HEADER}"}]
                if op.name in CONDITIONAL_WRITES
                else []
            ),
        ],
        "responses": _responses(op, mapping[(Response[op.response], "validation")]),
    }
    if op.method != "GET":
        body = _body(request_schema, path_fields)
        if body is not None:
            described["requestBody"] = body
    return described


def build_document(schema_version: str) -> dict[str, Any]:
    """The OpenAPI document of every operation in the table, whose ``info.version`` is
    *schema_version*."""
    models: list[tuple[type[BaseModel], str]] = []
    for op in OPERATIONS:
        models.append((op.request, "validation"))
        models.append((cast(type[BaseModel], Response[op.response]), "validation"))
    extra: tuple[type[BaseModel], ...] = (ErrorBody, DaemonIdentity, DaemonStopping)
    models += [(model, "validation") for model in extra]
    mapping, schemas = models_json_schema(
        cast(Any, models), ref_template=_REF, title="squads daemon"
    )
    definitions: dict[str, Any] = dict(schemas.get("$defs", {}))
    definitions["NotExecuted"] = {
        "type": "object",
        "properties": {"not_executed": {"const": "retiring"}},
        "required": ["not_executed"],
    }
    paths: dict[str, dict[str, Any]] = {}
    for op in OPERATIONS:
        paths.setdefault(op.path, {})[op.method.lower()] = _operation(op, definitions, mapping)
    paths["/v1/daemon"] = {
        "get": {
            "operationId": "daemon.identity",
            "summary": "The daemon's identity and state.",
            "responses": {
                "200": {
                    "description": "The daemon's identity.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": _REF.format(model="DaemonIdentity")}
                        }
                    },
                }
            },
        }
    }
    paths["/v1/daemon/stop"] = {
        "post": {
            "operationId": "daemon.stop",
            "summary": "Ask the daemon to exit once the request in progress has finished.",
            "responses": {
                "200": {
                    "description": "The daemon will exit.",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": _REF.format(model="DaemonStopping")}
                        }
                    },
                }
            },
        }
    }
    parameters = {name: _header_parameter(name, text) for name, text in _HEADERS}
    parameters[IF_MATCH_HEADER] = _header_parameter(
        IF_MATCH_HEADER, "The ETag of the item the write addresses, when the caller read it first."
    )
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "squads daemon",
            "version": schema_version,
            "description": "The operations of one squad, served by its daemon.",
        },
        "paths": paths,
        "components": {"schemas": definitions, "parameters": parameters},
    }
