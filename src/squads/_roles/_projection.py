"""The roster projection: the role and operator entries passed to backends and views."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleView:
    """The roster entry passed to backends (decoupled from RoleDef internals).

    Carries every role field a backend renders into a compiled managed region — explicitly,
    ``mission`` and ``responsibilities`` included — because a view field is the declaration and
    generated text is output, never an input. A backend that recovers a declaration by parsing
    markdown it rendered itself makes a template's formatting the carrier of that declaration,
    over a template that is meant to be editable: relabel the line and the field empties out of
    the compiled file silently, with nothing reporting it. Anything a backend renders is
    therefore declared here rather than read back off the page.
    """

    slug: str
    full_name: str
    title: str
    is_default: bool
    mission: str = ""
    responsibilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class OperatorView:
    """A human operator passed to backends for the CLAUDE.md people roster."""

    slug: str
    full_name: str
