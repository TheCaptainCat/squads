"""The wire form of an error: ``{"error": {"type", "message", "warnings"}}``, its type and its
HTTP status."""

from pydantic import BaseModel

from squads._errors import (
    AlreadyInitializedError,
    ChangedSinceReadError,
    CommentNotFoundError,
    IndexLockTimeoutError,
    InvalidTransitionError,
    ItemNotFoundError,
    NotInitializedError,
    RoleNotFoundError,
    SchemaGateError,
    SchemaMismatchError,
    SquadsError,
    SubentityNotFoundError,
    VocabularyMismatchError,
)

#: The error type of a ``SquadsError`` no row of :data:`ERROR_TYPES` names.
INVALID = "invalid"
#: The error type of an exception that is not a ``SquadsError``.
INTERNAL = "internal"

#: Exception class to error type, first match wins.
ERROR_TYPES: tuple[tuple[type[SquadsError], str], ...] = (
    (ItemNotFoundError, "not_found"),
    (RoleNotFoundError, "not_found"),
    (CommentNotFoundError, "not_found"),
    (SubentityNotFoundError, "not_found"),
    (InvalidTransitionError, "conflict"),
    (AlreadyInitializedError, "conflict"),
    (SchemaGateError, "conflict"),
    (IndexLockTimeoutError, "locked"),
    (ChangedSinceReadError, "changed_since_read"),
    (SchemaMismatchError, "schema_mismatch"),
    (VocabularyMismatchError, "vocabulary_mismatch"),
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
    """The machine type, the sentence the CLI prints after ``error:``, the notices the refused
    call would have answered with, and the facts a refusal adds (left out when it has none)."""

    type: str
    message: str
    warnings: list[str] = []
    details: dict[str, str] | None = None


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


def error_message(exc: SquadsError) -> str:
    """The sentence local mode prints after ``error:`` for *exc*, spelled for a caller that did
    not choose its directory with ``-C``."""
    if isinstance(exc, NotInitializedError):
        return exc.describe(named=False)
    return str(exc)


def error_body(exc: BaseException, message: str) -> ErrorBody:
    """The body answering *exc*, whose printed sentence is *message*."""
    warnings = list(exc.warnings) if isinstance(exc, SquadsError) else []
    details = exc.details if isinstance(exc, SquadsError) else None
    return ErrorBody(
        error=ErrorDetail(type=error_type(exc), message=message, warnings=warnings, details=details)
    )
