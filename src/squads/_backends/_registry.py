"""Name → backend lookup. New backends register here."""

from squads._backends._base import AgentBackend
from squads._errors import SquadsError

_REGISTRY: dict[str, type[AgentBackend]] = {}


def register(cls: type[AgentBackend]) -> type[AgentBackend]:
    _REGISTRY[cls.name] = cls
    return cls


def get_backend(name: str) -> AgentBackend:
    # Import for side-effect registration of the built-in backend.
    import importlib

    importlib.import_module("squads._backends._claude_code")

    try:
        return _REGISTRY[name]()
    except KeyError:
        raise SquadsError(
            f"unknown backend {name!r} (available: {', '.join(_REGISTRY) or 'none'})"
        ) from None
