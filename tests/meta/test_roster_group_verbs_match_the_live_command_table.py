"""Repo-hygiene gate: the group verbs a role or skill slug may not take
(``ROLE_GROUP_VERBS``, ``SKILL_GROUP_VERBS``) stay in lockstep with the commands registered on
``sq role`` and ``sq skill``, and no ``sq operator`` verb can collide with an ``op-`` slug.

The models sit below the CLI and cannot read the Typer app, so the sets are kept by hand and this
test is the guard against drift in both directions."""

import typer.main

from squads._cli import app
from squads._models._participants import (
    OPERATOR_SLUG_PREFIX,
    ROLE_GROUP_VERBS,
    SKILL_GROUP_VERBS,
)


def _verbs(group: str) -> frozenset[str]:
    commands = typer.main.get_command(app).commands[group].commands  # type: ignore[attr-defined]
    return frozenset(name for name in commands if not name.startswith("_"))


def test_the_role_group_verbs_are_the_registered_commands() -> None:
    assert _verbs("role") == ROLE_GROUP_VERBS


def test_the_skill_group_verbs_are_the_registered_commands() -> None:
    assert _verbs("skill") == SKILL_GROUP_VERBS


def test_no_operator_group_verb_starts_with_the_operator_prefix() -> None:
    assert not [v for v in _verbs("operator") if v.startswith(OPERATOR_SLUG_PREFIX)]
