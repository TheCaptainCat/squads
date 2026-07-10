"""Proves the cli layer collects, runs, and can invoke the real Typer app; delete once real
cli tests land in Phase 2.
"""


async def test_cli_directory_collects_and_reaches_runner(invoke, project):
    result = await invoke(["list"])
    assert result.exit_code == 0
