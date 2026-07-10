"""``sq workflow show`` CLI smoke: a custom type declared via ``.overrides/workflow.toml``
appears in the rendered output alongside its alias, the static sections still print, and a
non-custom squad's output carries every built-in type with zero custom-type leakage.
"""

import pytest

pytestmark = pytest.mark.anyio


def _write_override(squad_dir) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        """
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
""",
        encoding="utf-8",
    )


async def test_a_custom_type_and_its_alias_appear_in_the_output(project, invoke):
    _write_override(project.squad_dir)
    result = await invoke(["workflow", "show"])
    assert result.exit_code == 0
    assert "incident" in result.output
    assert "inc" in result.output


async def test_static_sections_are_present_alongside_the_custom_type(project, invoke):
    _write_override(project.squad_dir)
    result = await invoke(["workflow", "show"])
    assert result.exit_code == 0
    assert "Retype" in result.output
    assert "Remove" in result.output
    assert "Ref kinds" in result.output


async def test_a_non_custom_squad_carries_every_builtin_type_with_no_custom_leakage(
    project, invoke
):
    result = await invoke(["workflow", "show"])
    assert result.exit_code == 0
    for t in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
        assert t in result.output
    assert "incident" not in result.output
