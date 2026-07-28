"""A squad-data file that isn't valid UTF-8 -- a stray byte from a hand-edit, a bad merge, or
a restore from a partial patch, inserted into otherwise-intact prose -- must fail with a single
clean `error: ...` line naming the file, never a raw interpreter traceback.

This is one layer below the YAML/TOML *parse* guards: those wrap an already-decoded string, so
they never see a decode failure. Pins the user-visible outcome (what reaches the terminal), not
just the exception type -- a test asserting only that a `SquadsError` was raised would pass even
if the CLI still printed a traceback around it.
"""

from pathlib import Path

import pytest

from squads._board._store import board_folder
from squads._memory._store import role_folder

pytestmark = pytest.mark.anyio

#: Frames that must never reach the terminal once an undecodable file is guarded.
_FORBIDDEN_SNIPPETS = ("Traceback", "site-packages", ".venv", "UnicodeDecodeError")


def _assert_clean_failure(output: str, *, names: str) -> None:
    for snippet in _FORBIDDEN_SNIPPETS:
        assert snippet not in output, f"{snippet!r} leaked into output:\n{output}"
    assert "error:" in output
    # Rich hard-wraps a long unbroken path at the console width with a bare newline (no
    # inserted space) -- flatten before searching so a wrap point isn't mistaken for a miss.
    # Normalise separators on both sides (not just the output): a posix-relative Item.path
    # never carries a backslash, but a native str(Path) name does on Windows, so the raw
    # name must be normalised too or a genuinely-missing path could slip past unnoticed.
    flattened = output.replace("\n", "").replace("\\", "/")
    assert names.replace("\\", "/") in flattened


def _insert_invalid_byte(path: Path) -> None:
    """Corrupt *path* by inserting one non-UTF-8 lead byte into otherwise-intact prose --
    corruption by insertion, not truncation, matching how this actually reaches a user."""
    data = path.read_bytes()
    mid = len(data) // 2
    path.write_bytes(data[:mid] + b"\x80" + data[mid:])


# --------------------------------------------------------------------------- item / notice / memory


async def test_check_fails_cleanly_on_an_undecodable_item_file(svc, invoke):
    task = (await svc.create("task", "Undecodable-file target")).item
    _insert_invalid_byte(svc.paths.abspath(task.path))

    result = await invoke(["check"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=task.path)


async def test_repair_fails_cleanly_on_an_undecodable_item_file(svc, invoke):
    task = (await svc.create("task", "Undecodable-file target")).item
    _insert_invalid_byte(svc.paths.abspath(task.path))

    result = await invoke(["repair"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=task.path)


async def test_board_list_fails_cleanly_on_an_undecodable_notice(project, invoke):
    posted = await invoke(["board", "post", "-m", "a notice", "--as", "manager"])
    assert posted.exit_code == 0, posted.output
    notice_path = next(iter(board_folder(project).glob("*.md")))
    _insert_invalid_byte(notice_path)

    result = await invoke(["board", "list"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=str(notice_path))


async def test_memory_list_fails_cleanly_on_an_undecodable_entry(project, invoke):
    added = await invoke(["memory", "manager", "add", "a remembered fact"])
    assert added.exit_code == 0, added.output
    memory_path = next(iter(role_folder(project, "manager").glob("*.md")))
    _insert_invalid_byte(memory_path)

    result = await invoke(["memory", "manager", "list"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=str(memory_path))


# --------------------------------------------------------------------------- config


async def test_an_ordinary_command_fails_cleanly_on_an_undecodable_config(project, invoke):
    """Config resolution runs before command dispatch -- this is the worst case: an ordinary,
    non-diagnostic command fails the same clean way as `check`/`repair`, and so would the
    diagnostic commands themselves."""
    _insert_invalid_byte(project.config_path)

    result = await invoke(["list"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=str(project.config_path))


async def test_check_fails_cleanly_on_an_undecodable_config(project, invoke):
    _insert_invalid_byte(project.config_path)

    result = await invoke(["check"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=str(project.config_path))


# --------------------------------------------------------------------------- index


async def test_an_undecodable_index_reports_the_corrupt_index_message_with_its_repair_remedy(
    project, invoke
):
    """An undecodable `.squads.json` is just as unreadable as a schema-invalid one -- it must
    reach the same "corrupt index ... run `sq repair`" wording, not the generic decode message,
    or the one piece of advice that actually resolves it is lost."""
    _insert_invalid_byte(project.index_path)

    result = await invoke(["list"])
    assert result.exit_code == 1, result.output
    assert "corrupt index" in result.output
    assert "sq repair" in result.output.replace("\n", " ")
    for snippet in _FORBIDDEN_SNIPPETS:
        assert snippet not in result.output


# --------------------------------------------------------------------------- negative case


async def test_a_clean_board_is_unaffected_across_the_same_commands(project, svc, invoke):
    task = (await svc.create("task", "Healthy target")).item
    posted = await invoke(["board", "post", "-m", "a notice", "--as", "manager"])
    assert posted.exit_code == 0, posted.output
    remembered = await invoke(["memory", "manager", "add", "a remembered fact"])
    assert remembered.exit_code == 0, remembered.output

    for args in (
        ["check"],
        ["repair"],
        ["board", "list"],
        ["memory", "manager", "list"],
    ):
        result = await invoke(args)
        assert result.exit_code == 0, (args, result.output)
        for snippet in _FORBIDDEN_SNIPPETS:
            assert snippet not in result.output

    assert task.id  # sanity: the target item survived every pass above
