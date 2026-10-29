"""A refused `sq init` or `sq adopt` writes nothing, so the corrected command then succeeds."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio


REFUSED_FOLDERS = [
    ("/abs", "error: --squad-dir must be relative to the project root, got '/abs'\n"),
    ("../up", "error: --squad-dir must stay inside the project root, got '../up'\n"),
    ("", "error: --squad-dir must name a folder, not an empty value\n"),
]
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


@pytest.mark.parametrize(("folder", "message"), REFUSED_FOLDERS)
async def test_an_unusable_squad_folder_leaves_the_folder_untouched_for_the_retry(
    invoke, folder, message
) -> None:
    root = Path.cwd()
    refused = await invoke(["init", "--roles", "minimal", "--squad-dir", folder])
    assert (refused.exit_code, refused.output) == (1, message)
    assert sorted(root.iterdir()) == []
    retried = await invoke(["init", "--roles", "minimal"])
    assert retried.exit_code == 0, retried.output


async def test_init_over_files_sharing_a_number_leaves_no_configuration_behind(
    populated, invoke
) -> None:
    squad = populated.squad_dir
    original = (squad / "tasks/TASK-000003-build-the-query-parser.md").read_text(encoding="utf-8")
    (squad / "features/FEAT-000003-twin.md").write_text(
        original.replace("id: TASK-3", "id: FEAT-3"), encoding="utf-8"
    )
    (populated.root / ".squads.toml").unlink()
    refused = await invoke(["init", "--roles", "minimal"])
    assert (refused.exit_code, refused.output) == (
        1,
        "error: refusing to rebuild the index: it keys items by number:\n"
        "  - 2 files carry number 3 under different ids "
        "(features/FEAT-000003-twin.md, tasks/TASK-000003-build-the-query-parser.md); "
        "run `sq repair --renumber` to give one of them a new number\n",
    )
    assert not (populated.root / ".squads.toml").exists()
