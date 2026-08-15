"""Repo-hygiene gate: ``squads._workflow._models.RESERVED_CLI_ALIASES`` — the alias ->
owning-type table the spec loader refuses collisions against, and the CLI refuses *stale*
dispatch against — must stay in lockstep with what the CLI actually registers.

It cannot be derived live for two reasons: ``_workflow`` sits below ``_cli`` in the layering
(same import-cycle bar as ``RESERVED_CLI_VERBS``), and it is consulted while the bundled spec
is still being validated, so it cannot read that spec either. Hand-maintained, pinned here,
in both directions: an alias added to (or renamed in) ``workflow.toml`` without a matching
entry fails, and a stale entry naming an alias nothing registers fails too.
"""

import typer.main

from squads._cli import app
from squads._workflow import bundled_spec
from squads._workflow._models import RESERVED_CLI_ALIASES, reserved_alias_owner


def _bundled_alias_owners() -> set[tuple[str, str]]:
    spec = bundled_spec()
    return {
        (alias, item_type)
        for item_type, item_spec in spec.items.items()
        for alias in item_spec.aliases
    }


def test_the_table_is_exactly_the_bundled_specs_own_alias_declarations() -> None:
    declared = _bundled_alias_owners()
    listed = set(RESERVED_CLI_ALIASES)
    assert listed == declared, (
        "RESERVED_CLI_ALIASES has drifted from the bundled spec's `aliases` declarations "
        f"(missing: {sorted(declared - listed)}; stale: {sorted(listed - declared)})"
    )


def test_every_listed_alias_is_a_live_root_command() -> None:
    """The whole reason the table exists: these names ARE registered at ``sq``'s root by the
    import-time loop, so they answer before any spec resolution does."""
    click_app = typer.main.get_command(app)
    registered = set(click_app.commands.keys())  # type: ignore[attr-defined]
    missing = {alias for alias, _owner in RESERVED_CLI_ALIASES if alias not in registered}
    assert not missing, f"listed alias is not a registered root command: {sorted(missing)}"


def test_every_listed_alias_is_also_a_live_create_subcommand() -> None:
    click_app = typer.main.get_command(app)
    create_group = click_app.commands["create"]  # type: ignore[attr-defined]
    registered = set(create_group.commands.keys())  # type: ignore[attr-defined]
    missing = {alias for alias, _owner in RESERVED_CLI_ALIASES if alias not in registered}
    assert not missing, f"listed alias is not a registered `sq create` command: {sorted(missing)}"


def test_the_table_is_sorted_and_free_of_duplicate_aliases() -> None:
    aliases = [alias for alias, _owner in RESERVED_CLI_ALIASES]
    assert aliases == sorted(aliases), "keep the table sorted so a diff reads cleanly"
    assert len(aliases) == len(set(aliases)), "an alias may only route to one type"


def test_owner_lookup_answers_for_aliases_and_not_for_type_names() -> None:
    assert reserved_alias_owner("feat") == "feature"
    assert reserved_alias_owner("feature") is None
    assert reserved_alias_owner("definitely-not-an-alias") is None
