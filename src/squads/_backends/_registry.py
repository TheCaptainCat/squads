"""Name → backend lookup: a literal table of the built-in backends. A new backend is a row here."""

from collections.abc import Mapping
from types import MappingProxyType

from squads._backends._agents_md._backend import AgentsMdBackend
from squads._backends._base import AgentBackend
from squads._backends._claude_code._backend import ClaudeCodeBackend
from squads._errors import SquadsError

_BACKENDS: Mapping[str, type[AgentBackend]] = MappingProxyType(
    {
        ClaudeCodeBackend.name: ClaudeCodeBackend,
        AgentsMdBackend.name: AgentsMdBackend,
    }
)


def get_backend(name: str) -> AgentBackend:
    try:
        return _BACKENDS[name]()
    except KeyError:
        raise SquadsError(
            f"unknown backend {name!r} (available: {', '.join(_BACKENDS) or 'none'})"
        ) from None
