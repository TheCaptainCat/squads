"""The always-on `sq check` rules over the overrides and the configuration load: they cannot be
selected, so each has a breach case only."""

import tomllib
from pathlib import Path

import pytest

from squads._interactions._loader import PLAYBOOK_OVERRIDE_FILENAME
from squads._overrides._manifest import WORKFLOW_KEY
from squads._workflow._loader import WORKFLOW_OVERRIDE_FILENAME
from tests.check._arrange import (
    activate,
    active_spec,
    address,
    create,
    issue,
    ok,
    stale_base,
    unchanged_base,
    write_override,
)

pytestmark = pytest.mark.anyio

# a valid override that redeclares a bundled key
_SHADOWING = "[items.task]\norder = 31\n"
_TASK_TEMPLATE = "templates/items/task.md.j2"
_NOTE_TYPE = (
    "[items.note]\n"
    'prefix = "NOTE"\n'
    'folder = "notes"\n'
    'lifecycle = "work"\n'
    "parents = []\n"
    "order = 95\n"
    'category = "work"\n'
)


def _workflow_refused(path: Path) -> dict[str, str]:
    """The `workflow_loads` issue for the override at *path* declaring an unknown lifecycle."""
    return issue(
        "workflow_loads",
        "error",
        "workflow",
        "workflow config invalid: Invalid workflow spec: item 'task': lifecycle 'unknown' not "
        f"declared in lifecycles ({path}) — run `sq workflow lint`",
    )


@pytest.mark.breaches("override_stamped")
async def test_a_workflow_override_shadowing_the_bundled_spec_without_a_stamp_is_an_error(
    project, invoke, check_json
) -> None:
    # no command removes a stamp, and the override commands write one: write the file unstamped
    write_override(project, "workflow.toml", _NOTE_TYPE, stamp=None)
    assert await check_json() == ([], 0)

    write_override(project, "workflow.toml", _NOTE_TYPE + _SHADOWING, stamp=None)

    assert await check_json() == (
        [
            issue(
                "override_stamped",
                "error",
                WORKFLOW_OVERRIDE_FILENAME,
                "shadowing workflow override has no squads:override-base stamp; run "
                "`sq override update workflow` to re-stamp",
            )
        ],
        3,
    )


@pytest.mark.breaches("override_current")
async def test_a_workflow_override_stamped_before_a_change_of_the_bundled_spec_is_a_warning(
    project, invoke, check_json
) -> None:
    # the override commands stamp the running version: write an older stamp
    write_override(project, "workflow.toml", _SHADOWING, stamp=unchanged_base(WORKFLOW_KEY))
    assert await check_json() == ([], 0)

    base = stale_base(WORKFLOW_KEY)
    write_override(project, "workflow.toml", _SHADOWING, stamp=base)

    assert await check_json() == (
        [
            issue(
                "override_current",
                "warn",
                WORKFLOW_OVERRIDE_FILENAME,
                f"workflow override may be stale: bundled workflow.toml changed since v{base}; "
                "run `sq override diff workflow` to review, then `sq override update workflow` "
                "to re-stamp",
            )
        ],
        0,
    )


@pytest.mark.breaches("override_loads")
async def test_an_item_template_override_without_the_required_regions_is_an_error(
    project, invoke, check_json
) -> None:
    assert await check_json() == ([], 0)

    # no command writes an override template: write the file
    write_override(project, _TASK_TEMPLATE, "no regions here\n")

    assert await check_json() == (
        [
            issue(
                "override_loads",
                "error",
                f".overrides/{_TASK_TEMPLATE}",
                "override is missing required sq marker(s): <!-- sq:body -->, "
                "<!-- sq:discussion --> (breaks marker-safe editing; add the missing regions)",
            )
        ],
        3,
    )


@pytest.mark.breaches("workflow_loads")
async def test_a_workflow_override_the_loader_refuses_is_an_error(
    project, invoke, check_json
) -> None:
    write_override(project, "workflow.toml", _SHADOWING)
    assert await check_json() == ([], 0)

    write_override(project, "workflow.toml", '[items.task]\nlifecycle = "unknown"\n')

    path = project.squad_dir / WORKFLOW_OVERRIDE_FILENAME
    assert await check_json() == ([_workflow_refused(path)], 3)


@pytest.mark.breaches("workflow_loads")
async def test_a_workflow_override_that_is_not_valid_toml_is_an_error(
    project, invoke, check_json
) -> None:
    write_override(project, "workflow.toml", _SHADOWING)
    assert await check_json() == ([], 0)

    write_override(project, "workflow.toml", "[items.task\n")

    path = project.squad_dir / WORKFLOW_OVERRIDE_FILENAME
    with pytest.raises(tomllib.TOMLDecodeError) as parse_error:
        tomllib.loads(path.read_text(encoding="utf-8"))
    assert await check_json() == (
        [
            issue(
                "workflow_loads",
                "error",
                "workflow",
                f"workflow config invalid: Malformed workflow override {path}: {parse_error.value}"
                " \u2014 run `sq workflow lint`",
            )
        ],
        3,
    )


@pytest.mark.breaches("playbook_loads")
async def test_a_playbook_override_the_loader_refuses_is_an_error(
    project, invoke, check_json
) -> None:
    write_override(project, "playbook.toml", "[types.task]\nroles = []\n")
    assert await check_json() == ([], 0)

    write_override(project, "playbook.toml", "[types.task]\nroles = 5\n")

    path = project.squad_dir / PLAYBOOK_OVERRIDE_FILENAME
    assert await check_json() == (
        [
            issue(
                "playbook_loads",
                "error",
                "playbook",
                f"playbook config invalid: {path}: types.task.roles must be an array of tables "
                "(got int) — declare it as roles = [{ \u2026 }, \u2026]",
            )
        ],
        3,
    )


@pytest.mark.breaches("corpus_scans")
async def test_a_board_item_of_a_type_the_fallback_spec_lacks_makes_the_scan_an_error(
    project, invoke, check_json
) -> None:
    await activate(invoke, "manager")
    write_override(project, "workflow.toml", _NOTE_TYPE)
    note = await create(invoke, "note", "Remember the milk", "manager")
    # no live role authors the new type, which would warn about an open item
    note_words = address(note, active_spec(project))
    await ok(invoke, *note_words, "update", "--status", "Cancelled")
    assert await check_json() == ([], 0)

    # the workflow override stops loading, so the check falls back to the bundled spec
    write_override(project, "workflow.toml", '[items.task]\nlifecycle = "unknown"\n')

    path = project.squad_dir / WORKFLOW_OVERRIDE_FILENAME
    assert await check_json() == (
        [
            issue(
                "corpus_scans",
                "error",
                "corpus",
                f"could not scan the corpus: item {note} has type 'note', which the active spec "
                "no longer declares; migrate or re-type this item before it can load again (or "
                "run `sq repair` if the index itself is merely stale)",
            ),
            _workflow_refused(path),
        ],
        3,
    )
