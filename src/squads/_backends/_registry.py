"""Name → backend lookup. New backends register here."""

import importlib

from squads._backends._base import AgentBackend
from squads._errors import SquadsError

_REGISTRY: dict[str, type[AgentBackend]] = {}

# Built-in backend packages — each is imported once for its register() side-effect.
# To add a new built-in backend: append its module path here.
_BUILTIN_BACKEND_MODULES = (
    "squads._backends._claude_code",
    "squads._backends._agents_md",
)

_loaded = False


def _load_builtins() -> None:
    global _loaded
    if _loaded:
        return
    for module_path in _BUILTIN_BACKEND_MODULES:
        importlib.import_module(module_path)
    _loaded = True


def register(cls: type[AgentBackend]) -> type[AgentBackend]:
    _REGISTRY[cls.name] = cls
    return cls


def get_backend(name: str) -> AgentBackend:
    _load_builtins()
    try:
        return _REGISTRY[name]()
    except KeyError:
        raise SquadsError(
            f"unknown backend {name!r} (available: {', '.join(_REGISTRY) or 'none'})"
        ) from None
