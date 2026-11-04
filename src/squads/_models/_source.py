"""The ``source`` record an item carries when a tracker feeds it: the tracker's own identifiers
and the facts the pull keeps, all strings."""

from pydantic import BaseModel, ConfigDict

#: The states of a record whose issue the last pull could not read as open or closed: it left the
#: source's filter, or the tracker no longer answers for it.
OUT_OF_FILTER = "out-of-filter"
GONE = "gone"
LOST_STATES = (OUT_OF_FILTER, GONE)


class SourceRecord(BaseModel):
    """Which tracker issue an item mirrors, and where that issue stood when it was last read."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    #: The source's name in ``sources.toml``.
    name: str
    #: The tracker's immutable issue ID.
    id: str
    #: The full readable key (``owner/repo#12``), never a bare number.
    key: str
    #: ``open``, ``closed``, ``out-of-filter`` or ``gone``.
    state: str
    #: The issue's last update on the tracker, ISO UTC.
    updated_at: str
    #: The issue author's immutable user ID.
    author_id: str
    #: The issue author's handle.
    author_handle: str
