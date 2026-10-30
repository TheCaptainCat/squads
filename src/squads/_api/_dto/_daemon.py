"""What the daemon answers about itself: its identity, listeners and vocabulary."""

from squads._api._dto._base import DTO


class VocabularyIdentity(DTO):
    """The hash of the vocabulary the daemon serves and one digest per document it covers."""

    hash: str
    documents: dict[str, str]


class ListenerIdentity(DTO):
    """One address the daemon listens on: its transport (``unix`` or ``tcp``), its address and
    the kind of client it serves (``cli`` or ``browser``)."""

    transport: str
    address: str
    kind: str


class DaemonIdentity(DTO):
    """The daemon's identity and state: its process, version, squad, schema, listeners, start time
    and idle deadline (``null`` when it never exits idle), and the vocabulary it serves."""

    pid: int
    version: str
    schema_version: str
    squad_dir: str
    started_at: str
    idle_deadline: str | None
    listeners: list[ListenerIdentity]
    vocabulary: VocabularyIdentity


class DaemonStopping(DTO):
    """The answer to a stop request: the daemon exits once the request in progress has finished."""

    stopping: bool
