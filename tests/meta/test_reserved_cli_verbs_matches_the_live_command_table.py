"""Repo-hygiene gate: ``squads._workflow._models.RESERVED_CLI_VERBS`` — the fixed set of
top-level CLI command names a declared item type's own name/alias is refused for colliding
with (``_check_item_refs``) — must stay in lockstep with the actual registered command table
in ``squads._cli``.

``_workflow`` sits below ``_cli`` in the module layering (`_cli → _services → _models`/
`_workflow`), so the reserved set cannot be derived live at validation time without an import
cycle; it is maintained by hand instead (see the constant's own docstring). This test is the
guard against that drift: it builds the real Typer app, subtracts every name that is an item
type or item-type alias from the *bundled* spec (those are expected/legitimate — a bundled
type's own command IS the type, not a collision with something else), and asserts what is left
matches the constant exactly in both directions — a new built-in top-level command added to
``_cli/`` without updating the constant fails here, and a stale entry naming a since-removed
command fails here too.
"""

import typer.main

from squads._cli import app
from squads._workflow import bundled_spec
from squads._workflow._models import RESERVED_CLI_VERBS


def _live_non_type_command_names() -> frozenset[str]:
    spec = bundled_spec()
    type_names_and_aliases: set[str] = set()
    for item_type, item_spec in spec.items.items():
        type_names_and_aliases.add(item_type)
        type_names_and_aliases.update(item_spec.aliases)

    click_app = typer.main.get_command(app)
    all_names = frozenset(click_app.commands.keys())  # type: ignore[attr-defined]
    return all_names - type_names_and_aliases


def test_reserved_cli_verbs_is_exactly_the_live_non_type_command_set() -> None:
    live = _live_non_type_command_names()
    missing_from_constant = live - RESERVED_CLI_VERBS
    stale_in_constant = RESERVED_CLI_VERBS - live
    assert not missing_from_constant, (
        "a built-in top-level command exists that RESERVED_CLI_VERBS doesn't know about — a "
        f"type could claim it undetected; add to the constant: {sorted(missing_from_constant)}"
    )
    assert not stale_in_constant, (
        "RESERVED_CLI_VERBS names a command that no longer exists — remove the stale "
        f"entry: {sorted(stale_in_constant)}"
    )
