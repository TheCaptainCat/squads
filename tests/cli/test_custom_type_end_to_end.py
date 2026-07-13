"""A fully custom work type (declared only in ``.overrides/workflow.toml``, e.g. "incident")
resolves as a first-class CLI command with zero code change: ``sq incident``/its alias, ``sq
create incident``, ``sq list -t incident`` all work, the correct spec-declared prefix is used
(never ``TYPE.upper()``), and its folder is auto-created on first write. A non-custom squad's
CLI surface stays byte-identical (built-in types, aliases, and `--help` listings unperturbed by
the existence of the custom-type machinery).
"""

import re
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.anyio

_OVERRIDE_TOML = """\
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done", "WontFix"]
Done = []
WontFix = ["Open"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
aliases = ["inc"]
"""

# Adds a sub-entity kind ("action") to the custom type, so a cold `--help` either does or
# doesn't show the resulting `add-action` surface depending on which spec built the command tree.
_OVERRIDE_TOML_WITH_SUBENTITY_KIND = """\
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done", "WontFix"]
Done = []
WontFix = ["Open"]

[lifecycles.action]
initial = "Open"
[lifecycles.action.transitions]
Open = ["Done"]
Done = []

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
aliases = ["inc"]
subentity_kind = "action"

[subentity_kinds.action]
lifecycle = "action"
completion = "Done"
plural = "actions"
local_prefix = "AC"
"""


def _write_override(squad_dir: Path, toml: str = _OVERRIDE_TOML) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(toml, encoding="utf-8")


def _created_id(output: str) -> str:
    m = re.search(r"INC-(\d+)", output)
    assert m is not None, f"could not find an INC-N id in:\n{output}"
    return m.group(0)


# --------------------------------------------------------------------------- byte-identical
# builtin surface for a non-custom squad


async def test_builtin_help_and_create_surfaces_are_unperturbed_with_no_custom_type(
    project, invoke
) -> None:
    help_result = await invoke(["--help"])
    for t in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
        assert t in help_result.output
    assert "incident" not in help_result.output

    create_help = await invoke(["create", "--help"])
    for t in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
        assert t in create_help.output
    assert "incident" not in create_help.output

    unknown = await invoke(["incident"])
    assert unknown.exit_code == 2
    assert "no such command" in unknown.output.lower()


# --------------------------------------------------------------------------- custom type
# resolves as a CLI command with zero code change


async def test_custom_type_resolves_as_a_top_level_command_and_via_its_alias(
    project, invoke
) -> None:
    _write_override(project.squad_dir)

    canonical = await invoke(["incident", "--help"])
    assert canonical.exit_code == 0, canonical.output
    assert "show" in canonical.output and "update" in canonical.output

    alias = await invoke(["inc", "--help"])
    assert alias.exit_code == 0, alias.output
    assert "incident" in alias.output

    listed = await invoke(["--help"])
    assert "incident" in listed.output

    still_unknown = await invoke(["volcano"])
    assert still_unknown.exit_code == 2
    assert "no such command" in still_unknown.output.lower()


async def test_create_incident_end_to_end_correct_prefix_folder_list_show_and_check(
    project, invoke
) -> None:
    _write_override(project.squad_dir)

    created = await invoke(["create", "incident", "DB timeout", "--author", "manager"])
    assert created.exit_code == 0, created.output
    assert "INC-" in created.output and "INCIDENT-" not in created.output
    inc_id = _created_id(created.output)
    num = inc_id.rsplit("-", 1)[-1]

    incidents_dir = project.squad_dir / "incidents"
    assert incidents_dir.is_dir()
    assert list(incidents_dir.glob("INC-*.md"))

    listed = await invoke(["list", "-t", "incident"])
    assert listed.exit_code == 0 and "DB timeout" in listed.output

    shown = await invoke(["incident", num, "show"])
    assert shown.exit_code == 0 and "DB timeout" in shown.output

    checked = await invoke(["check"])
    assert checked.exit_code == 0, checked.output


async def test_create_help_and_type_help_list_the_custom_type(project, invoke) -> None:
    _write_override(project.squad_dir)

    create_help = await invoke(["create", "--help"])
    assert "incident" in create_help.output

    incident_create_help = await invoke(["create", "incident", "--help"])
    assert incident_create_help.exit_code == 0
    assert "title" in incident_create_help.output.lower()


async def test_create_an_undeclared_type_still_errors_even_with_an_override_present(
    project, invoke
) -> None:
    _write_override(project.squad_dir)
    result = await invoke(["create", "volcano"])
    assert result.exit_code != 0


async def test_create_dispatches_through_a_builtin_or_custom_alias_to_the_canonical_id(
    project, invoke
) -> None:
    _write_override(project.squad_dir)

    builtin_alias = await invoke(["create", "feat", "Via alias", "--author", "manager"])
    assert builtin_alias.exit_code == 0 and "FEAT-" in builtin_alias.output

    custom_alias = await invoke(["create", "inc", "Via inc alias", "--author", "manager"])
    assert custom_alias.exit_code == 0
    assert "INC-" in custom_alias.output and "INCIDENT-" not in custom_alias.output


# --------------------------------------------------------------------------- P4: a real build
# error for a resolved custom type must propagate, not be swallowed into "No such command" — but
# a spec-resolution failure (before the type is even confirmed) still degrades gracefully so
# `sq --help` never crashes on a broken override.


async def test_a_genuine_build_error_for_a_resolved_custom_type_propagates_not_swallowed(
    project, invoke
) -> None:
    _write_override(project.squad_dir)

    with patch(
        "squads._cli._items.build_item_app", side_effect=RuntimeError("injected build failure")
    ):
        result = await invoke(["incident", "--help"])
    assert "No such command" not in result.output
    assert result.exit_code != 0 or result.exception is not None


async def test_an_invalid_override_still_degrades_gracefully_for_bare_help(project, invoke) -> None:
    override_dir = project.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text("[[invalid toml", encoding="utf-8")

    result = await invoke(["--help"])
    assert result.exit_code == 0, result.output


# --------------------------------------------------------------------------- a cold,
# first-in-process --help for a custom type must build from the override-merged spec, not the
# bundled spec the process starts with (Click resolves the subcommand group before the root
# callback binds the real spec) — the built command tree is then cached for the process, so a
# wrong first build stays wrong for good.


async def test_cold_first_help_on_a_custom_type_shows_its_declared_subentity_and_retype_surface(
    project, invoke
) -> None:
    _write_override(project.squad_dir, _OVERRIDE_TOML_WITH_SUBENTITY_KIND)

    # First-in-process `--help` for "incident" — nothing has resolved/cached this type's
    # command tree yet in this test. It must show the declared `add-action` sub-entity surface,
    # not just the type's plain metadata verbs.
    type_help = await invoke(["incident", "--help"])
    assert type_help.exit_code == 0, type_help.output
    assert "add-action" in type_help.output

    # retype's target-type list is built from the same spec at the same time — must include
    # "incident" itself (a valid retype source/target), not just the built-in types the bundled
    # spec knows about.
    retype_help = await invoke(["incident", "retype", "--help"])
    assert retype_help.exit_code == 0, retype_help.output
    assert "incident" in retype_help.output
