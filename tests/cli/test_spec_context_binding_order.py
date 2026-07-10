"""The per-invocation spec context handle (a threaded handle, not a module global — Pierre's
own contract for this design): the root callback binds the active `WorkflowSpec` before Typer's
own parser callbacks (`parse_type`/`parse_status`, driven by `--type`/`--status`) run, and those
parser callbacks fall back to the bundled spec gracefully when no invocation has bound one yet.
"""

import pytest

from squads._cli import app
from squads._workflow import bundled_spec


def test_the_active_spec_is_bound_before_type_and_status_parser_callbacks_run(
    runner, tmp_path, monkeypatch
):
    """Click runs the root group callback first, then parses the subcommand's own options.

    `--type`/`--status` trigger `parse_type`/`parse_status`, which call `get_active_spec()`;
    exit 0 on `sq list --type task --status InProgress` is only possible if the bundled spec
    was already bound when those parser callbacks ran (otherwise "task"/"InProgress" would be
    rejected as unknown values against an unbound spec).
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

    from squads._cli._common import get_active_spec  # pyright: ignore[reportPrivateUsage]

    result = runner.invoke(app, ["list", "--type", "task", "--status", "InProgress"])
    assert result.exit_code == 0, result.output
    assert get_active_spec() is bundled_spec()  # no project override present


def test_parse_type_falls_back_to_the_bundled_spec_when_no_spec_is_bound(tmp_path, monkeypatch):
    """Outside of any CLI invocation, `get_active_spec()`/`parse_type` fall back transparently."""
    monkeypatch.chdir(tmp_path)
    from squads._cli._common import (  # pyright: ignore[reportPrivateUsage]
        get_active_spec,
        parse_type,
        set_active_spec,
    )

    set_active_spec(None)

    assert get_active_spec() is bundled_spec()
    assert parse_type("task") == "task"


def test_parse_status_validates_loose_and_canonical_forms_against_the_active_spec(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    from squads._cli._common import (  # pyright: ignore[reportPrivateUsage]
        parse_status,
        set_active_spec,
    )
    from squads._errors import SquadsError

    set_active_spec(bundled_spec())

    assert parse_status("InProgress") == "InProgress"
    assert parse_status("inprogress") == "InProgress"
    assert parse_status("in_progress") == "InProgress"

    with pytest.raises(SquadsError, match="unknown status"):
        parse_status("Flying")
