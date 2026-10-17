"""The squad-global catalog is partitioned into always-on and selectable members, every member
has one declared default level, and no member writes a level literal of its own."""

import ast
import inspect

from squads._services import _validators
from squads._services._validators import SQUAD_GLOBAL_CATALOG
from squads._workflow import bundled_spec
from squads._workflow._models import (
    ALWAYS_ON_SQUAD_GLOBAL_NAMES,
    DEFAULT_SQUAD_GLOBAL_LEVEL,
    SELECTABLE_SQUAD_GLOBAL_NAMES,
    SQUAD_GLOBAL_VALIDATOR_NAMES,
    VALIDATOR_LEVELS,
    VALIDATOR_NAMES,
)

_ALWAYS_ON_LEVELS = {
    "index_reconciled": "error",
    "backend_reconciled": "error",
    "roster_config_integrity": "error",
    "default_designation_duplicated": "error",
    "roster_slug_valid": "error",
    "playbook_guide_role_live": "warn",
    "display_config_valid": "warn",
}


def test_the_two_tiers_are_disjoint_and_their_union_is_the_squad_global_catalog() -> None:
    assert ALWAYS_ON_SQUAD_GLOBAL_NAMES.isdisjoint(SELECTABLE_SQUAD_GLOBAL_NAMES)
    assert (
        ALWAYS_ON_SQUAD_GLOBAL_NAMES | SELECTABLE_SQUAD_GLOBAL_NAMES == SQUAD_GLOBAL_VALIDATOR_NAMES
    )
    assert set(SQUAD_GLOBAL_CATALOG) == SQUAD_GLOBAL_VALIDATOR_NAMES
    assert SQUAD_GLOBAL_VALIDATOR_NAMES.isdisjoint(VALIDATOR_NAMES)


def test_the_selectable_tier_is_exactly_the_five_opt_in_members() -> None:
    assert {
        "children_settled_with_parent",
        "dependency_acyclic",
        "wip_limit",
        "unassigned_active",
        "stale_active",
    } == SELECTABLE_SQUAD_GLOBAL_NAMES


def test_every_squad_global_member_declares_one_default_level() -> None:
    assert set(DEFAULT_SQUAD_GLOBAL_LEVEL) == SQUAD_GLOBAL_VALIDATOR_NAMES
    assert set(DEFAULT_SQUAD_GLOBAL_LEVEL.values()) <= VALIDATOR_LEVELS


def test_always_on_members_keep_their_levels_and_the_selectable_ones_default_to_warn() -> None:
    assert {k: DEFAULT_SQUAD_GLOBAL_LEVEL[k] for k in ALWAYS_ON_SQUAD_GLOBAL_NAMES} == (
        _ALWAYS_ON_LEVELS
    )
    assert {DEFAULT_SQUAD_GLOBAL_LEVEL[k] for k in SELECTABLE_SQUAD_GLOBAL_NAMES} == {"warn"}


def test_the_bundled_document_selects_nothing() -> None:
    assert bundled_spec().squad.validators == []


def _level_literals(func: object) -> list[str]:
    """The string literals a member passes as the first argument of ``CheckIssue(...)``."""
    tree = ast.parse(inspect.getsource(func))  # pyright: ignore[reportArgumentType]
    return [
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "CheckIssue"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ]


def test_no_squad_global_member_writes_a_level_literal() -> None:
    offenders = {
        name: literals
        for name, member in SQUAD_GLOBAL_CATALOG.items()
        if (literals := _level_literals(member))
    }
    assert offenders == {}


def test_the_confirm_predicates_of_the_index_member_take_their_level_from_the_caller() -> None:
    assert _level_literals(_validators.on_disk_not_indexed) == []
    assert _level_literals(_validators.not_on_disk) == []
