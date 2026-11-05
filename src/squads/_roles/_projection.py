"""The roster projection: the role and operator entries passed to backends and views."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleView:
    """The roster entry passed to backends, decoupled from ``RoleDef`` internals.

    A view field is the declaration and generated text is output, never input: a backend that
    recovers a declaration by parsing markdown it rendered itself makes the template's formatting
    the carrier. Anything a backend renders is declared here. ``mission`` and ``responsibilities``
    are carried for the roster entries of the ``playbook`` view source.
    """

    slug: str
    full_name: str
    title: str
    is_default: bool
    mission: str = ""
    responsibilities: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    pronouns: str | None = None


@dataclass(frozen=True)
class OperatorView:
    """A human operator passed to backends for the CLAUDE.md people roster."""

    slug: str
    full_name: str
    pronouns: str | None = None
