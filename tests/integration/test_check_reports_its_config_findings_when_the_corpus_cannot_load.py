"""`sq check` must never end up reporting nothing at all.

`check` opens the service the normal way and, when the config fails to load, records that as a
finding and falls back to a spec it can still run the remaining checks against. The hole: the
fallback spec may be unable to load the index either -- it does not declare a type the board still
carries -- so the corpus scan raises, the collected config findings are discarded with it, and the
operator is shown one unrelated corpus error and a bare exit 1. Precisely when the config is broken,
the command that exists to say so says nothing about it.

Three configurations reach that, all driven below. Two need no playbook override at all, which is
why this belongs to `check`'s own resilience rather than to any one config document. The general
rule underneath: a reporter which stops at the first problem fails when it is needed most -- the
same argument already settled for the per-file case, where one corrupt file no longer aborts the
scan for the other hundreds.

So the scan's own failure becomes its own finding alongside the config ones, and the exit code is
the ordinary "errors found" 3 rather than a generic failure: report and stop, never report nothing.
"""

from pathlib import Path

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

_CUSTOM_INCIDENT_TYPE = (
    '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "work"\n'
)
#: A workflow override that declares the custom type with a lifecycle that does not exist, so the
#: spec itself fails to load.
_BROKEN_WORKFLOW = (
    '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "nosuchlifecycle"\n'
)
#: A workflow override that drops the custom type while an item of it is still on the board. The
#: spec loads fine here -- it is the live-corpus cross-check that refuses, which is the branch that
#: predates the playbook work entirely.
_KEPT_TYPES = [
    "epic",
    "feature",
    "task",
    "bug",
    "decision",
    "review",
    "guide",
    "role",
    "skill",
    "operator",
]
_DROPS_THE_CUSTOM_TYPE = f"[selected]\nitems = {_KEPT_TYPES!r}\n"
_BROKEN_PLAYBOOK = '[types.task]\noverview = ""\n'


def _write_override(squad_dir: Path, name: str, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / name).write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


async def _board_with_a_custom_type_item(project, invoke) -> None:
    """A squad carrying one item of a project-declared type -- the precondition every configuration
    below needs, since the masking only happens when the fallback spec cannot load the index."""
    _write_override(project.squad_dir, "workflow.toml", _CUSTOM_INCIDENT_TYPE)
    created = await invoke(["create", "incident", "db outage", "--author", "manager"])
    assert created.exit_code == 0, created.output


@pytest.mark.parametrize(
    ("workflow", "playbook"),
    [
        (_BROKEN_WORKFLOW, _BROKEN_PLAYBOOK),
        (_BROKEN_WORKFLOW, None),
        (_DROPS_THE_CUSTOM_TYPE, None),
    ],
    ids=["both_overrides_broken", "workflow_only", "workflow_drops_a_type_with_live_items"],
)
async def test_check_still_reports_its_config_finding_when_the_corpus_will_not_load(
    project, invoke, workflow, playbook
) -> None:
    """Parametrised over the three configurations rather than the one that motivated the fix: they
    reach the same masking through two different fallbacks (the playbook branch's inner one and the
    general `SquadsError` branch's), and a fix applied to one is not a fix for the other. The last
    id is the one reachable with no playbook override in play at all."""
    await _board_with_a_custom_type_item(project, invoke)
    _write_override(project.squad_dir, "workflow.toml", workflow)
    if playbook is not None:
        _write_override(project.squad_dir, "playbook.toml", playbook)

    result = await invoke(["check"])

    assert "config invalid" in result.output, result.output
    assert result.exit_code == 3, result.output


@pytest.mark.parametrize(
    ("workflow", "playbook"),
    [
        (_BROKEN_WORKFLOW, _BROKEN_PLAYBOOK),
        (_BROKEN_WORKFLOW, None),
        (_DROPS_THE_CUSTOM_TYPE, None),
    ],
    ids=["both_overrides_broken", "workflow_only", "workflow_drops_a_type_with_live_items"],
)
async def test_the_corpus_scan_failure_is_reported_rather_than_swallowed(
    project, invoke, workflow, playbook
) -> None:
    """The other direction, and the one that keeps this from being a fix that hides information: the
    scan genuinely could not run, so that is said too. Downgrading the raise to silence would leave
    an operator reading a config finding and reasonably concluding the rest of the board is clean.
    """
    await _board_with_a_custom_type_item(project, invoke)
    _write_override(project.squad_dir, "workflow.toml", workflow)
    if playbook is not None:
        _write_override(project.squad_dir, "playbook.toml", playbook)

    result = await invoke(["check"])

    assert "could not scan the corpus" in result.output, result.output


async def test_a_clean_squad_reports_neither(project, invoke) -> None:
    """The negative direction. A new error-level finding that fires on a healthy squad would break
    every adopter's pipeline, so the quiet case is pinned as tightly as the loud ones."""
    result = await invoke(["check"])

    assert "could not scan the corpus" not in result.output, result.output
    assert "config invalid" not in result.output, result.output
    assert result.exit_code == 0, result.output


async def test_a_broken_config_alone_does_not_claim_the_corpus_failed(project, invoke) -> None:
    """The narrow scope of the new finding: a broken override on a squad whose board the fallback
    spec *can* still read must report the config problem and nothing about the corpus -- the scan
    ran. Without this, the fix would read as "any config error means the board is unreadable"."""
    _write_override(project.squad_dir, "playbook.toml", _BROKEN_PLAYBOOK)

    result = await invoke(["check"])

    assert "playbook config invalid" in result.output, result.output
    assert "could not scan the corpus" not in result.output, result.output
