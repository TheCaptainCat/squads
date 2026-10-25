"""Every command word in a bundled ref-kind hint is a registered command or group."""

import re

import typer.main

from squads._cli import app
from squads._workflow import bundled_spec


def test_every_command_a_bundled_hint_names_is_registered() -> None:
    registered = set(typer.main.get_command(app).commands)  # type: ignore[attr-defined]
    named = {
        word
        for spec_type in bundled_spec().items.values()
        for rule in spec_type.ref_rules
        for word in re.findall(r"`sq ([a-z][a-z-]*)", rule.hint)
    }

    assert named
    assert named <= registered
