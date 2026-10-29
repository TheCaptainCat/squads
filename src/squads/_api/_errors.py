"""The wire form of an error: ``{"error": {"type", "message"}}``, its type and its HTTP status."""

from pydantic import BaseModel

from squads._errors import (
    AlreadyInitializedError,
    IndexLockTimeoutError,
    InvalidTransitionError,
    ItemNotFoundError,
    RoleNotFoundError,
    SchemaGateError,
    SquadsError,
)

#: The error type of a ``SquadsError`` no row of :data:`ERROR_TYPES` names.
INVALID = "invalid"
#: The error type of an exception that is not a ``SquadsError``.
INTERNAL = "internal"

#: Exception class to error type, first match wins.
ERROR_TYPES: tuple[tuple[type[SquadsError], str], ...] = (
    (ItemNotFoundError, "not_found"),
    (RoleNotFoundError, "not_found"),
    (InvalidTransitionError, "conflict"),
    (AlreadyInitializedError, "conflict"),
    (SchemaGateError, "conflict"),
    (IndexLockTimeoutError, "locked"),
)

#: Error type to HTTP status.
HTTP_STATUS: tuple[tuple[str, int], ...] = (
    ("not_found", 404),
    ("conflict", 409),
    ("vocabulary_mismatch", 409),
    ("schema_mismatch", 409),
    ("changed_since_read", 409),
    ("locked", 423),
    (INVALID, 400),
    (INTERNAL, 500),
)


class ErrorDetail(BaseModel, frozen=True):
    """The machine type and the sentence the CLI prints after ``error:``."""

    type: str
    message: str


class ErrorBody(BaseModel, frozen=True):
    """The body of every answer that is not a success."""

    error: ErrorDetail


def error_type(exc: BaseException) -> str:
    """The wire type of *exc*."""
    if not isinstance(exc, SquadsError):
        return INTERNAL
    return next((name for cls, name in ERROR_TYPES if isinstance(exc, cls)), INVALID)


def http_status(type_: str) -> int:
    """The HTTP status an error of *type_* answers with; an unknown type is a 400."""
    return next((status for name, status in HTTP_STATUS if name == type_), 400)


def error_body(exc: BaseException, message: str) -> ErrorBody:
    """The body answering *exc*, whose printed sentence is *message*."""
    return ErrorBody(error=ErrorDetail(type=error_type(exc), message=message))
