"""The reflog DTOs: the log of every command that changed the squad, filtered."""

from pydantic import JsonValue

from squads._api._dto._base import DTO


class ReflogRequest(DTO):
    """Read the reflog: every filter given must match; *tail* keeps the latest entries, all of
    them when ``None``."""

    item: str | None = None
    actor: str | None = None
    op: str | None = None
    since: str | None = None
    tail: int | None = None


class ReflogEntryRow(DTO):
    """One logged command: the schema version, time, actor, operation, target and change, and
    the session lineage the actor declared."""

    v: str
    ts: str
    actor: str
    op: str
    target: str
    delta: dict[str, JsonValue]
    session_id: str | None
    parent_session_id: str | None


class Reflog(DTO):
    """The entries that matched, oldest first."""

    items: list[ReflogEntryRow]
