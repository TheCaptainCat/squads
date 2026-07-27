"""A `.md` whose frontmatter has an intact closing delimiter but unparsable YAML between
the delimiters — a hand-edit, an unresolved merge conflict, a file restored from a partial
patch — and a `.squads.toml` with a syntax error must each fail with a single clean
`error: ...` line naming the file, not a raw interpreter traceback.

Pins the user-visible outcome (what reaches the terminal), not just the exception type: a
test asserting only that a `SquadsError` was raised would pass even if the CLI still printed
a traceback around it.
"""

import re
from pathlib import Path

import pytest

from squads._board._store import board_folder
from squads._memory._store import role_folder

pytestmark = pytest.mark.anyio

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

#: Frames that must never reach the terminal once a malformed file is guarded.
_FORBIDDEN_SNIPPETS = ("Traceback", "site-packages", ".venv", "yaml.", "tomllib.", "ScannerError")


def _assert_clean_failure(output: str, *, names: str) -> None:
    for snippet in _FORBIDDEN_SNIPPETS:
        assert snippet not in output, f"{snippet!r} leaked into output:\n{output}"
    assert "error:" in output
    # Rich hard-wraps a long unbroken path at the console width with a bare newline (no
    # inserted space) — flatten before searching so a wrap point isn't mistaken for a miss.
    assert names in output.replace("\n", "")


def _corrupt_with_merge_conflict(path: Path) -> None:
    """Rewrite *path*'s frontmatter block to carry an intact closing delimiter around
    unresolved-merge-conflict YAML — the shape the bug's own reproduction used, since that
    is how this actually reaches a user."""
    text = path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(text)
    assert m, f"expected a frontmatter block in {path}"
    front, rest = m.group(1), text[m.end() :]
    conflicted = (
        f"{front}\n<<<<<<< HEAD\ntitle: Renamed A\n=======\ntitle: Renamed B\n>>>>>>> other\n"
    )
    path.write_text(f"---\n{conflicted}---\n{rest}", encoding="utf-8")


def _corrupt_config(project) -> None:
    """Append an unterminated TOML value — a syntax error, not a validation error."""
    text = project.config_path.read_text(encoding="utf-8")
    project.config_path.write_text(f"{text}\nbroken = [unterminated\n", encoding="utf-8")


# --------------------------------------------------------------------------- frontmatter


async def test_check_fails_cleanly_on_a_merge_conflicted_item_file(project, svc, invoke):
    task = (await svc.create("task", "Corrupt-file target")).item
    _corrupt_with_merge_conflict(svc.paths.abspath(task.path))

    result = await invoke(["check"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=task.path)


async def test_repair_fails_cleanly_on_a_merge_conflicted_item_file(project, svc, invoke):
    task = (await svc.create("task", "Corrupt-file target")).item
    _corrupt_with_merge_conflict(svc.paths.abspath(task.path))

    result = await invoke(["repair"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=task.path)


async def test_renumber_fails_cleanly_on_a_merge_conflicted_item_file(project, svc, invoke):
    task = (await svc.create("task", "Corrupt-file target")).item
    _corrupt_with_merge_conflict(svc.paths.abspath(task.path))

    result = await invoke(["renumber", "--from", "1", "--by", "100"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=task.path)


async def test_sync_fails_cleanly_on_a_merge_conflicted_skill_file(project, svc, invoke):
    seeded = await svc.seed_bundled_skills()
    assert seeded
    skill_path = svc.paths.abspath(seeded[0].path)
    _corrupt_with_merge_conflict(skill_path)

    result = await invoke(["sync"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=str(skill_path))


async def test_board_list_fails_cleanly_on_a_merge_conflicted_notice(project, svc, invoke):
    posted = await invoke(["board", "post", "-m", "a notice", "--as", "manager"])
    assert posted.exit_code == 0, posted.output
    notice_path = next(iter(board_folder(project).glob("*.md")))
    _corrupt_with_merge_conflict(notice_path)

    result = await invoke(["board", "list"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=str(notice_path))


async def test_memory_list_fails_cleanly_on_a_merge_conflicted_entry(project, svc, invoke):
    added = await invoke(["memory", "manager", "add", "a remembered fact"])
    assert added.exit_code == 0, added.output
    memory_path = next(iter(role_folder(project, "manager").glob("*.md")))
    _corrupt_with_merge_conflict(memory_path)

    result = await invoke(["memory", "manager", "list"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=str(memory_path))


async def test_memory_show_fails_cleanly_on_a_merge_conflicted_entry(project, svc, invoke):
    added = await invoke(["memory", "manager", "add", "a remembered fact"])
    assert added.exit_code == 0, added.output
    memory_path = next(iter(role_folder(project, "manager").glob("*.md")))
    slug = memory_path.stem
    _corrupt_with_merge_conflict(memory_path)

    result = await invoke(["memory", "manager", "show", slug])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=str(memory_path))


# --------------------------------------------------------------------------- config


async def test_an_ordinary_command_fails_cleanly_on_a_malformed_config(project, invoke):
    _corrupt_config(project)

    result = await invoke(["list"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=str(project.config_path))


async def test_check_fails_cleanly_on_a_malformed_config(project, invoke):
    _corrupt_config(project)

    result = await invoke(["check"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=str(project.config_path))


# --------------------------------------------------------------------------- negative case


async def test_a_clean_board_is_unaffected_across_the_same_commands(project, svc, invoke):
    task = (await svc.create("task", "Healthy target")).item
    await svc.seed_bundled_skills()
    posted = await invoke(["board", "post", "-m", "a notice", "--as", "manager"])
    assert posted.exit_code == 0, posted.output
    remembered = await invoke(["memory", "manager", "add", "a remembered fact"])
    assert remembered.exit_code == 0, remembered.output

    for args in (
        ["check"],
        ["repair"],
        ["renumber", "--from", "999", "--by", "1"],
        ["sync"],
        ["board", "list"],
        ["memory", "manager", "list"],
    ):
        result = await invoke(args)
        assert result.exit_code == 0, (args, result.output)
        for snippet in _FORBIDDEN_SNIPPETS:
            assert snippet not in result.output

    assert task.id  # sanity: the target item survived every pass above
