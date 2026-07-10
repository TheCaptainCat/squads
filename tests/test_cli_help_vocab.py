"""CLI help/message text must agree with the active spec's vocabulary, not a frozen
bundled-type/priority-code enumeration — proves the retype/priority help derivation and the
generic (non-enumerating) phrasing on the cross-type list/tree/init/reflog surfaces.
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


async def test_retype_help_lists_bundled_work_types_in_order(project, invoke) -> None:
    """No override: the retype help enumeration matches the bundled work types, in their
    declared display order — the derivation reproduces today's text exactly."""
    created = await invoke(["create", "task", "T", "--author", "manager"])
    num = _num(_created_id("TASK", created.output))
    r = await invoke(["task", num, "retype", "--help"])
    assert r.exit_code == 0, r.output
    assert "epic|feature|task|bug|decision|review|guide" in r.output


async def test_retype_help_includes_a_custom_type(project, invoke) -> None:
    """A project-declared custom work type shows up as a valid retype target in the help —
    proving the enumeration is spec-derived, not the frozen 7-type list. Exercised on the
    custom type's own (lazily-built) command tree — the statically-registered built-in
    types are, by design (AC#7 byte-identical --help), snapshotted at import time and can
    never reflect a type a project's override adds later."""
    _write_override(project.squad_dir, _CUSTOM_PRIORITY_OVERRIDE)
    created = await invoke(["create", "incident", "Outage", "--author", "manager"])
    assert created.exit_code == 0, created.output
    num = _num(_created_id("INC", created.output))
    r = await invoke(["incident", num, "retype", "--help"])
    assert r.exit_code == 0, r.output
    assert "incident" in r.output


async def test_create_priority_help_follows_the_bound_collection(project, invoke) -> None:
    """`sq create incident --help`'s --priority help shows the custom-collection codes
    ("high"/"low"), not the bundled priority codes."""
    _write_override(project.squad_dir, _CUSTOM_PRIORITY_OVERRIDE)
    r = await invoke(["create", "incident", "--help"])
    assert r.exit_code == 0, r.output
    assert "high|low" in r.output
    assert "urgent" not in r.output
    assert "medium" not in r.output


async def test_update_priority_help_follows_the_bound_collection(project, invoke) -> None:
    """`sq incident <n> update --help`'s --priority help shows the same custom-collection
    codes as create, not the bundled priority codes."""
    _write_override(project.squad_dir, _CUSTOM_PRIORITY_OVERRIDE)
    created = await invoke(["create", "incident", "Outage", "--author", "manager"])
    assert created.exit_code == 0, created.output
    num = _num(_created_id("INC", created.output))
    r = await invoke(["incident", num, "update", "--help"])
    assert r.exit_code == 0, r.output
    assert "high|low" in r.output
    assert "urgent" not in r.output
    assert "medium" not in r.output


async def test_list_and_tree_priority_help_does_not_enumerate(project, invoke) -> None:
    """`list`/`tree` are cross-type: their static --priority help drops the hardcoded
    bundled enumeration rather than asserting a fixed grammar."""
    for cmd in ("list", "tree"):
        r = await invoke([cmd, "--help"])
        assert r.exit_code == 0, r.output
        assert "urgent|high|medium|low" not in r.output
        assert "priority collection" in r.output


def test_init_hint_does_not_name_a_specific_type(runner, tmp_path, monkeypatch) -> None:
    """The `sq init` success hint points at `sq create --help` rather than a hardcoded
    `sq create task`, so it stays accurate under a spec that drops/renames `task`."""
    from squads._cli import app

    monkeypatch.chdir(tmp_path)
    r = runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    assert r.exit_code == 0, r.output
    assert 'sq create task "' not in r.output
    assert "sq create --help" in r.output
