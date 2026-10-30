"""What the daemon's application needs from the process that runs it: the squad it serves, the
identity it reports and the two callables the lifecycle supplies."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from squads._spec_documents import SpecSources

#: Whether the daemon's configuration has changed since it started, so it must answer
#: ``retiring`` instead of running anything.
type RetirementCheck = Callable[[], bool]


def never_retiring() -> bool:
    """The check of a daemon whose configuration is never compared."""
    return False


@dataclass
class Listener:
    """One address the daemon listens on."""

    transport: str
    address: str
    kind: str


@dataclass
class DaemonState:
    """The daemon's identity, which ``GET /v1/daemon`` reports, and the squad it serves.

    The lifecycle fills the listeners as it binds them and keeps ``idle_deadline`` current;
    ``stop`` asks the process to exit once the request in progress has finished.
    """

    pid: int
    version: str
    #: The project root, which holds ``.squads.toml``.
    root: Path
    #: The squad directory's real path.
    squad_dir: Path
    started_at: datetime
    #: The documents the daemon loaded at start; what it serves is read from them.
    sources: SpecSources
    listeners: list[Listener] = field(default_factory=list[Listener])
    idle_deadline: Callable[[], datetime | None] = lambda: None
    stop: Callable[[], None] = lambda: None
