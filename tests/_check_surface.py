"""The declarations the check rule tests owe: one per rule, one `:param` per parameterised member
and one `@level` per member a selection can move to another level, all derived from the tables
that drive `sq check`.

A declaration is the literal a ``breaches`` marker carries: ``rule``, ``rule:param`` or
``rule@<level>``.
"""

import re
from dataclasses import dataclass

from squads._services._check_rules import BINDING_RULES
from squads._services._validators import CATALOG, SQUAD_GLOBAL_CATALOG
from squads._workflow._validator_names import (
    DEFAULT_SQUAD_GLOBAL_LEVEL,
    DEFAULT_VALIDATOR_LEVEL,
    LEVEL_RANK,
    PARAMETERIZED_VALIDATOR_NAMES,
    REQUIRED_PARAM_VALIDATOR_NAMES,
    SELECTABLE_SQUAD_GLOBAL_NAMES,
    SQUAD_GLOBAL_PARAM_MINIMUM,
    VALIDATOR_LEVEL_FLOOR,
    VALIDATOR_LEVELS,
)

PARAM = ":param"

_DECLARATION = re.compile(r"^(?P<rule>[a-z_]+)(?::(?P<param>param)|@(?P<level>[a-z]+))?$")


@dataclass(frozen=True)
class Declaration:
    """One parsed ``breaches`` argument."""

    rule: str
    param: bool = False
    level: str | None = None


def parse_declaration(text: str) -> Declaration | None:
    """The declaration *text* spells, ``None`` when it is none of the three forms."""
    match = _DECLARATION.match(text)
    if match is None:
        return None
    return Declaration(match["rule"], match["param"] is not None, match["level"])


def breach_declarations() -> frozenset[str]:
    """One declaration per rule `sq check` can report: every catalog member and binding rule."""
    return frozenset(set(CATALOG) | set(SQUAD_GLOBAL_CATALOG) | set(BINDING_RULES))


def param_declarations() -> frozenset[str]:
    """One ``rule:param`` per member that takes a parameter."""
    names = PARAMETERIZED_VALIDATOR_NAMES | SQUAD_GLOBAL_PARAM_MINIMUM.keys()
    return frozenset(f"{name}{PARAM}" for name in names)


def required_param_members() -> frozenset[str]:
    """The members whose param is required: a bare member cannot load, so the param case is the
    breach case and one marker declares both."""
    return frozenset(REQUIRED_PARAM_VALIDATOR_NAMES | SQUAD_GLOBAL_PARAM_MINIMUM.keys())


def other_level(default: str, floor: str | None) -> str | None:
    """The level a selection can give a member besides its *default*, ``None`` when *floor*
    forbids it."""
    (other,) = VALIDATOR_LEVELS - {default}
    return other if LEVEL_RANK[other] >= LEVEL_RANK[floor or "warn"] else None


def level_declarations() -> frozenset[str]:
    """One ``rule@<level>`` per selectable member, at the level that is not its default and that
    its floor allows."""
    found: set[str] = set()
    for name in CATALOG:
        level = other_level(DEFAULT_VALIDATOR_LEVEL[name], VALIDATOR_LEVEL_FLOOR.get(name))
        if level is not None:
            found.add(f"{name}@{level}")
    for name in SELECTABLE_SQUAD_GLOBAL_NAMES:
        level = other_level(DEFAULT_SQUAD_GLOBAL_LEVEL[name], None)
        if level is not None:
            found.add(f"{name}@{level}")
    return frozenset(found)


def required_declarations() -> frozenset[str]:
    """Every declaration the check rule tests owe."""
    return breach_declarations() | param_declarations() | level_declarations()
