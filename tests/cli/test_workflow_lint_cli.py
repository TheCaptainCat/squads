"""``sq workflow lint`` reaches the merge-error lint from the CLI: exit 0/"OK" clean, exit 1 +
error text on a broken override; ``sq workflow``/``sq workflow show`` keep printing the
cheatsheet regardless. The lint logic itself is proven once at the unit layer
(tests/unit/test_workflow_lint_merge_errors.py) — this only proves the CLI reaches it.
"""

import pytest

pytestmark = pytest.mark.anyio


def _write_override(project, content: str) -> None:
    override_dir = project.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


async def test_lint_exits_0_with_ok_when_no_override_exists(project, invoke) -> None:
    result = await invoke(["workflow", "lint"])
    assert result.exit_code == 0
    assert "OK" in result.output


async def test_lint_exits_0_with_ok_on_a_valid_override(project, invoke) -> None:
    _write_override(project, "[statuses.ExtraLintStatus]\nterminal = false\n")
    result = await invoke(["workflow", "lint"])
    assert result.exit_code == 0
    assert "OK" in result.output


async def test_lint_exits_1_with_error_text_on_an_invalid_override(project, invoke) -> None:
    _write_override(
        project,
        '[items.broken_lint]\nprefix = "BRL"\nfolder = "broken_lints"\n'
        'lifecycle = "no_such_lifecycle"\n',
    )
    result = await invoke(["workflow", "lint"])
    assert result.exit_code == 1
    assert "error" in result.output.lower()


async def test_bare_workflow_command_still_prints_the_cheatsheet(project, invoke) -> None:
    result = await invoke(["workflow"])
    assert result.exit_code == 0
    assert result.output


async def test_workflow_show_subcommand_also_prints_the_cheatsheet(project, invoke) -> None:
    result = await invoke(["workflow", "show"])
    assert result.exit_code == 0
    assert result.output
