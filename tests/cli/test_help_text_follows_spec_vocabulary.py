"""CLI help/message text agrees with the active spec's vocabulary, not a frozen bundled-
type/priority-code enumeration: retype/priority help derives from the spec, and the
cross-type list/tree/init/reflog surfaces use generic (non-enumerating) phrasing.

Cited under the ledger's CLI-output-hygiene group (root help text / COLUMNS pin); homed
here as the closest fit — its actual substance is spec-vocabulary-derivation, which overlaps
the generic-badge-axis and workflow-authoring-prose contracts homed elsewhere.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

# A custom type reusing the bundled "work" lifecycle, whose "priority" field is bound to a
# brand-new two-value collection instead of the bundled four-value priority collection —
# proves the help text follows the *bound* collection, not a hardcoded "priority" name.
_CUSTOM_PRIORITY_OVERRIDE = """\
[collections.level]
label = "Level"
ordered = true
badges = [
  { code = "high", label = "High", emoji = "\U0001f534" },
  { code = "low", label = "Low", emoji = "\U0001f7e2" },
]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
fields = [
  { code = "priority", label = "Priority", collection = "level" },
]
"""


def _write_override(squad_dir: Path, toml: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(toml, encoding="utf-8")


def _created_id(prefix: str, output: str) -> str:
    m = re.search(rf"{prefix}-(\d+)", output)
    assert m is not None, f"could not find a {prefix}-N id in:\n{output}"
    return m.group(0)


def _num(item_id: str) -> str:
    return item_id.rsplit("-", 1)[-1]


async def test_retype_help_lists_bundled_work_types_in_declared_order(project, invoke) -> None:
    created = await invoke(["create", "task", "T", "--author", "manager"])
    num = _num(_created_id("TASK", created.output))
    r = await invoke(["task", num, "retype", "--help"])
    assert r.exit_code == 0, r.output
    assert "epic|feature|task|bug|decision|review|guide" in r.output


async def test_retype_help_includes_a_custom_declared_type(project, invoke) -> None:
    _write_override(project.squad_dir, _CUSTOM_PRIORITY_OVERRIDE)
    created = await invoke(["create", "incident", "Outage", "--author", "manager"])
    assert created.exit_code == 0, created.output
    num = _num(_created_id("INC", created.output))
    r = await invoke(["incident", num, "retype", "--help"])
    assert r.exit_code == 0, r.output
    assert "incident" in r.output


async def test_create_priority_help_follows_the_bound_collection_not_the_bundled_one(
    project, invoke
) -> None:
    _write_override(project.squad_dir, _CUSTOM_PRIORITY_OVERRIDE)
    r = await invoke(["create", "incident", "--help"])
    assert r.exit_code == 0, r.output
    assert "high|low" in r.output
    assert "urgent" not in r.output
    assert "medium" not in r.output


async def test_update_priority_help_follows_the_bound_collection_not_the_bundled_one(
    project, invoke
) -> None:
    _write_override(project.squad_dir, _CUSTOM_PRIORITY_OVERRIDE)
    created = await invoke(["create", "incident", "Outage", "--author", "manager"])
    num = _num(_created_id("INC", created.output))
    r = await invoke(["incident", num, "update", "--help"])
    assert r.exit_code == 0, r.output
    assert "high|low" in r.output
    assert "urgent" not in r.output


async def test_cross_type_list_and_tree_priority_help_does_not_enumerate_bundled_codes(
    project, invoke
) -> None:
    for cmd in ("list", "tree"):
        r = await invoke([cmd, "--help"])
        assert r.exit_code == 0, r.output
        assert "urgent|high|medium|low" not in r.output
        assert "priority collection" in r.output


def test_init_success_hint_points_at_create_help_not_a_specific_type(
    runner, tmp_path, monkeypatch
) -> None:
    from squads._cli import app

    monkeypatch.chdir(tmp_path)
    r = runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    assert r.exit_code == 0, r.output
    assert 'sq create task "' not in r.output
    assert "sq create --help" in r.output
