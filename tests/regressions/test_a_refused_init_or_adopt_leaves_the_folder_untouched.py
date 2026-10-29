"""A refused `sq init` or `sq adopt` writes nothing, so the corrected command then succeeds."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

UNKNOWN = "error: unknown backend 'bogus' (available: claude_code, agents_md)\n"


@pytest.mark.parametrize("command", ["init", "adopt"])
async def test_an_unknown_backend_leaves_the_folder_untouched_for_the_retry(
    invoke, command
) -> None:
    root = Path.cwd()
    refused = await invoke([command, "--roles", "minimal", "--backend", "bogus"])
    assert (refused.exit_code, refused.output) == (1, UNKNOWN)
    assert sorted(root.iterdir()) == []
    retried = await invoke([command, "--roles", "minimal", "--backend", "claude_code"])
    assert retried.exit_code == 0, retried.output


@pytest.mark.parametrize("folder", ["/abs", "../up", ""])
async def test_an_unusable_squad_folder_leaves_the_folder_untouched_for_the_retry(
    invoke, folder
) -> None:
    root = Path.cwd()
    refused = await invoke(["init", "--roles", "minimal", "--squad-dir", folder])
    assert refused.exit_code == 1
    assert refused.output.startswith("error: --squad-dir must ")
    assert sorted(root.iterdir()) == []
    retried = await invoke(["init", "--roles", "minimal"])
    assert retried.exit_code == 0, retried.output
