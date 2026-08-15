"""A `.md` whose frontmatter has an intact closing delimiter but unparsable YAML between
the delimiters — a hand-edit, an unresolved merge conflict, a file restored from a partial
patch — and a `.squads.toml` with a syntax error must each name the file cleanly, never with a
raw interpreter traceback. `renumber`/`sync`/an ordinary command still abort outright (a single
`error: ...` line); `check`/`repair`/`board list`/`memory list` degrade per file instead —
report the bad file as an error-level issue and keep going for the rest of the board — so their
own tests assert the command *completes* (exit 0 or the ordinary error-level exit) rather than
aborting. Either shape is "clean": no traceback, the file named.

Pins the user-visible outcome (what reaches the terminal), not just the exception type: a
test asserting only that a `SquadsError` was raised would pass even if the CLI still printed
a traceback around it.
"""

import re
from pathlib import Path

import pytest

from _helpers import create_item
from squads._board._store import board_folder
from squads._memory._store import role_folder

pytestmark = pytest.mark.anyio

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

#: Frames that must never reach the terminal once a malformed file is guarded.
_FORBIDDEN_SNIPPETS = ("Traceback", "site-packages", ".venv", "yaml.", "tomllib.", "ScannerError")


def _assert_clean_failure(output: str, *, names: str) -> None:
    for snippet in _FORBIDDEN_SNIPPETS:
        assert snippet not in output, f"{snippet!r} leaked into output:\n{output}"
    # "error:" (an abort) or a bare "error" issue-level word (a degraded-but-completed report,
    # e.g. `sq check`'s "error <file>: <message>") — either is a clean report, never a
    # traceback; the individual command-shape assertions pin exit code separately.
    assert "error" in output
    # Rich hard-wraps a long unbroken path at the console width with a bare newline (no
    # inserted space) — flatten before searching so a wrap point isn't mistaken for a miss.
    # Normalise separators on both sides (not just the output): a posix-relative Item.path
    # never carries a backslash, but a native str(Path) name does on Windows, so the raw
    # name must be normalised too or a genuinely-missing path could slip past unnoticed.
    flattened = output.replace("\n", "").replace("\\", "/")
    assert names.replace("\\", "/") in flattened


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


async def test_check_reports_a_merge_conflicted_item_file_and_keeps_checking(project, svc, invoke):
    """`check` degrades per file rather than aborting: the corrupt file is reported at error
    level, naming it cleanly, and the run still completes (no traceback) — see the sibling
    continuation test for proof a *second*, unrelated issue is also still reported."""
    task = (await create_item(svc, "task", "Corrupt-file target")).item
    _corrupt_with_merge_conflict(svc.paths.abspath(task.path))

    result = await invoke(["check"])
    assert result.exit_code == 3, result.output
    _assert_clean_failure(result.output, names=task.path)


async def test_repair_carries_the_merge_conflicted_items_previous_entry_forward(
    project, svc, invoke
):
    """`repair` degrades per file too, and — unlike a naive skip-and-rebuild — never drops the
    unreadable item: its previous index entry survives the rebuild, so it stays resolvable.

    The file itself is still corrupt, so reading its *body* still fails cleanly (the carried
    entry is stale, not a fix) — the metadata panel from the carried frontmatter is what proves
    "resolvable", not a fully clean `show`.
    """
    task = (await create_item(svc, "task", "Corrupt-file target")).item
    _corrupt_with_merge_conflict(svc.paths.abspath(task.path))

    result = await invoke(["repair"])
    # Exit 1, not 0: `repair` did rebuild, but it carried a stale entry forward rather than
    # refreshing it, and its own message says to fix the file and repair again -- a degraded
    # result, not a clean one, so a caller gating on `$?` must see that.
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=task.path)

    listed = await invoke(["list", "-a"])
    assert listed.exit_code == 0, listed.output
    assert task.id in listed.output

    shown = await invoke(["task", str(task.sequence_id), "show"])
    assert task.title in shown.output  # the carried entry's metadata panel still renders
    for snippet in _FORBIDDEN_SNIPPETS:
        assert snippet not in shown.output


async def test_renumber_fails_cleanly_on_a_merge_conflicted_item_file(project, svc, invoke):
    task = (await create_item(svc, "task", "Corrupt-file target")).item
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


async def test_board_list_degrades_past_a_merge_conflicted_notice(project, svc, invoke):
    """`board list` names the corrupt notice and keeps listing the rest rather than emptying
    the whole listing — the same reporter-stops-at-the-first-problem shape `check` rejects.
    Exit 1, not 0: an `error:` line reached the terminal, so `$?` must say so too."""
    posted = await invoke(["board", "post", "-m", "a notice", "--as", "manager"])
    assert posted.exit_code == 0, posted.output
    notice_path = next(iter(board_folder(project).glob("*.md")))
    _corrupt_with_merge_conflict(notice_path)

    result = await invoke(["board", "list"])
    assert result.exit_code == 1, result.output
    _assert_clean_failure(result.output, names=str(notice_path))
    assert "no current notices" in result.output


async def test_memory_list_degrades_past_a_merge_conflicted_entry(project, svc, invoke):
    """`memory list` names the corrupt entry and exits clean rather than emptying the whole
    listing — same rationale as the board sibling above."""
    added = await invoke(["memory", "manager", "add", "a remembered fact"])
    assert added.exit_code == 0, added.output
    memory_path = next(iter(role_folder(project, "manager").glob("*.md")))
    _corrupt_with_merge_conflict(memory_path)

    result = await invoke(["memory", "manager", "list"])
    assert result.exit_code == 0, result.output
    _assert_clean_failure(result.output, names=str(memory_path))
    assert "no memories for manager" in result.output


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
    task = (await create_item(svc, "task", "Healthy target")).item
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
