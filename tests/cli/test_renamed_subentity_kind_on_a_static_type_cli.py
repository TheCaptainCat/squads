"""A built-in (statically-registered) type's sub-entity kind, renamed via override, gets a
working ``add-<new-kind>`` verb — not just the bundled ``add-<old-kind>`` frozen at import
time. Statically-registered types are built once, at import time, from the bundled spec
(deliberate, for byte-identical help on a non-customized squad); a kind rename discovered only
at runtime would otherwise leave the type's sub-entity CLI surface permanently pointed at the
old kind name, exactly as the bundled help/priority literals did before they were made
spec-aware at render time.
"""

import re
from pathlib import Path

import pytest

from squads._rendering._engine import invalidate_squad_dir

pytestmark = pytest.mark.anyio

_RENAMED_KIND_OVERRIDE = """\
[subentity_kinds.scenario]
lifecycle = "subentity"
completion = "Done"
plural = "scenarios"
local_prefix = "SC"

[items.feature]
subentity_kind = "scenario"
"""


def _write_override(squad_dir: Path) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_RENAMED_KIND_OVERRIDE, encoding="utf-8")
    invalidate_squad_dir(squad_dir)


def _feature_num(create_output: str) -> str:
    m = re.search(r"FEAT-(\d+)", create_output)
    assert m is not None, f"could not find a FEAT-N id in:\n{create_output}"
    return m.group(1)


async def test_add_scenario_works_and_add_story_no_longer_creates_a_story(project, invoke) -> None:
    _write_override(project.squad_dir)
    created = await invoke(["create", "feature", "Login", "--author", "manager"])
    assert created.exit_code == 0, created.output
    num = _feature_num(created.output)

    added = await invoke(["feature", num, "add-scenario", "Happy path"])
    assert added.exit_code == 0, added.output
    assert "SC1" in added.output

    listed = await invoke(["feature", num, "scenarios", "--json"])
    assert listed.exit_code == 0, listed.output
    assert "Happy path" in listed.output

    # The old bundled kind name still dispatches (it isn't hidden from `get_command` — that
    # would hand the message to Click's own did-you-mean) but refuses accurately rather than
    # silently creating a mis-typed sub-entity.
    old_kind = await invoke(["feature", num, "add-story", "Wrong kind"])
    assert old_kind.exit_code != 0
    assert "scenario" in old_kind.output.lower()


async def test_feature_help_advertises_scenario_not_story(project, invoke) -> None:
    _write_override(project.squad_dir)
    help_result = await invoke(["feature", "--help"])
    assert help_result.exit_code == 0
    assert "add-scenario" in help_result.output
    assert "scenarios" in help_result.output
    assert "add-story" not in help_result.output
    assert "stories" not in help_result.output


async def test_a_plain_squad_keeps_the_bundled_story_kind_working(project, invoke) -> None:
    """No override at all: the dynamic fallback must be a pure no-op — the statically-built
    ``add-story`` verb (and its help ordering) stays exactly as it always was."""
    created = await invoke(["create", "feature", "Login", "--author", "manager"])
    assert created.exit_code == 0, created.output
    num = _feature_num(created.output)

    added = await invoke(["feature", num, "add-story", "As a user…"])
    assert added.exit_code == 0, added.output
    assert "US1" in added.output

    help_result = await invoke(["feature", "--help"])
    assert help_result.exit_code == 0
    assert "add-story" in help_result.output
    assert "add-scenario" not in help_result.output
