"""Name → backend lookup. New backends register here."""

from squads.backends.base import AgentBackend
from squads.errors import SquadsError

_REGISTRY: dict[str, type[AgentBackend]] = {}


def register(cls: type[AgentBackend]) -> type[AgentBackend]:
    _REGISTRY[cls.name] = cls
    return cls


def get_backend(name: str) -> AgentBackend:
    # Import for side-effect registration of the built-in backend.
    import importlib

    importlib.import_module("squads.backends.claude_code")

    try:
        return _REGISTRY[name]()
    except KeyError:
        raise SquadsError(
            f"unknown backend {name!r} (available: {', '.join(_REGISTRY) or 'none'})"
        ) from None
