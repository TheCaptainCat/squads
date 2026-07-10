"""``sq workflow`` prints the cheatsheet, and the root ``--help`` points an agent at it."""

import pytest

from squads._cli import app

pytestmark = pytest.mark.anyio


async def test_workflow_command_prints_the_team_workflow_cheatsheet(project, invoke):
    result = await invoke(["workflow"])
    assert result.exit_code == 0
    assert "Team workflow" in result.output
    assert "parent" in result.output and "feature" in result.output


def test_root_help_points_to_the_workflow_command(runner):
    result = runner.invoke(app, ["--help"])
    assert "sq workflow" in result.output
