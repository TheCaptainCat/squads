"""`sq --show-completion <shell>` emits a non-empty, well-formed, shell-specific script."""

import os

from squads._cli import app


def test_bash_and_zsh_completion_scripts_are_non_empty_and_distinct(runner):
    # Disable Typer's shell auto-detection so the explicit shell name is always honoured,
    # regardless of the host shell the suite happens to run under.
    os.environ["_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION"] = "1"
    try:
        bash_result = runner.invoke(app, ["--show-completion", "bash"])
        zsh_result = runner.invoke(app, ["--show-completion", "zsh"])
    finally:
        os.environ.pop("_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION", None)

    assert bash_result.exit_code == 0, bash_result.output
    assert zsh_result.exit_code == 0, zsh_result.output

    assert "_sq_completion" in bash_result.output
    assert "complete_bash" in bash_result.output
    assert len(bash_result.output.strip()) > 0

    assert "#compdef sq" in zsh_result.output
    assert "complete_zsh" in zsh_result.output
    assert len(zsh_result.output.strip()) > 0

    assert bash_result.output != zsh_result.output
