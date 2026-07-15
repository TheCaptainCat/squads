"""The team bulletin board, exercised against a real git repository — the board reuses the
same file-per-entry + committed generated ``.index.jsonl`` idiom as agent memory (the accepted
board-storage design), so it must merge the way that design actually promises:

- two branches each posting a **distinct** notice: the hash-named ``.md`` notice files merge
  cleanly (both notices survive, distinct ids, none lost); the committed ``board/.index.jsonl``
  roll-up *does* conflict (both branches rewrote it whole from a shared base) — the accepted
  trade-off, not a bug — and ``sq sync``/``sq repair`` mechanically regenerates it, resolving
  the conflict with both entries present in the correct (chronological) listing order;
- clearing a notice is a real, trackable git deletion — history stays recoverable;
- listing is read-only at the git level too: it never leaves a tracked file dirty.

Every other board behaviour (post/list/clear, expiry filter, ordinal resolution, off-counter,
repair-neutral) is covered at the service/CLI layer; this file is deliberately the one place a
*real* git merge runs on the board, mirroring ``test_memory_git_merge_behavior.py``.
"""

import json
import subprocess
import sys
from pathlib import Path

import yaml

SQ = (sys.executable, "-m", "squads")


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
    assert result.returncode == 0, (
        f"{' '.join(args)!r} failed (exit {result.returncode}):\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


def _sq(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(cwd, *SQ, *args)


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(cwd, "git", *args)


def _seed_git_repo(tmp_path: Path) -> str:
    """Init a squad + a real git repo around it, one commit. Returns the branch name."""
    _sq(
        tmp_path,
        "init",
        "--backend",
        "none",
        "--roles",
        "minimal",
        "--no-seed-skills",
        "--default-names",
    )
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.invalid")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "seed squad")
    return _git(tmp_path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def _board_dir(tmp_path: Path) -> Path:
    return tmp_path / "squads" / "board"


def _board_json(tmp_path: Path) -> list[dict[str, str]]:
    result = _sq(tmp_path, "board", "list", "--json")
    return json.loads(result.stdout)


def test_two_branches_posting_distinct_notices_merge_md_files_but_conflict_on_the_index(
    tmp_path,
):
    main = _seed_git_repo(tmp_path)
    _git(tmp_path, "branch", "branch-alpha")
    _git(tmp_path, "branch", "branch-beta")

    _git(tmp_path, "checkout", "-q", "branch-alpha")
    _sq(tmp_path, "board", "post", "-m", "notice posted from branch alpha")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "alpha notice")

    _git(tmp_path, "checkout", "-q", "branch-beta")
    _sq(tmp_path, "board", "post", "-m", "notice posted from branch beta")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "beta notice")

    _git(tmp_path, "checkout", "-q", main)
    _git(tmp_path, "merge", "--no-edit", "-q", "branch-alpha")  # fast-forward, no conflict yet

    merge_result = subprocess.run(
        ["git", "merge", "--no-edit", "branch-beta"], cwd=tmp_path, capture_output=True, text=True
    )
    assert merge_result.returncode != 0, "expected the committed index to conflict"
    assert "CONFLICT" in merge_result.stdout + merge_result.stderr

    board_dir = _board_dir(tmp_path)
    index_path = board_dir / ".index.jsonl"
    notice_files = [p for p in board_dir.glob("*.md")]

    # No notice lost: both content files merged cleanly, no conflict markers inside either.
    assert len(notice_files) == 2
    contents = {p.read_text(encoding="utf-8") for p in notice_files}
    assert any("notice posted from branch alpha" in c for c in contents)
    assert any("notice posted from branch beta" in c for c in contents)
    for c in contents:
        assert "<<<<<<<" not in c

    hash_ids = {p.stem for p in notice_files}
    assert len(hash_ids) == 2, "the two notices must get distinct hash ids"

    status_lines = _git(tmp_path, "status", "--porcelain").stdout.splitlines()
    index_status = next(ln for ln in status_lines if ln.endswith(".index.jsonl"))
    assert index_status.startswith("AA"), index_status

    # The committed roll-up genuinely conflicts (both branches rewrote it whole).
    conflicted_text = index_path.read_text(encoding="utf-8")
    assert "<<<<<<<" in conflicted_text
    assert "=======" in conflicted_text
    assert ">>>>>>>" in conflicted_text

    # `sq board list` still works mid-conflict — it reads the .md files directly, never the
    # (currently conflicted) committed index.
    live_listing = _board_json(tmp_path)
    assert {row["body"] for row in live_listing} == {
        "notice posted from branch alpha",
        "notice posted from branch beta",
    }

    # Mechanical resolution: sq sync rebuilds the index whole from the .md files.
    _sq(tmp_path, "sync")

    resolved_text = index_path.read_text(encoding="utf-8")
    assert "<<<<<<<" not in resolved_text
    lines = [ln for ln in resolved_text.splitlines() if ln.strip()]
    header = json.loads(lines[0])
    assert header["schema"] == "squads.index/1"
    entries = [json.loads(ln) for ln in lines[1:]]
    assert {e["slug"] for e in entries} == hash_ids

    # Correct listing order: entries come out chronological by posted-at (id as tiebreak,
    # matching squads._board._store.list_notices), the same order `sq board list`/`clear <n>`
    # resolve against.
    def _posted_at(slug: str) -> str:
        text = (board_dir / f"{slug}.md").read_text(encoding="utf-8")
        front = yaml.safe_load(text.split("---\n")[1])
        return str(front["posted_at"])

    assert [e["slug"] for e in entries] == sorted(hash_ids, key=lambda s: (_posted_at(s), s))

    # The merge can now be completed cleanly.
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "merge branch-beta")
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""


def test_clearing_a_notice_is_a_real_git_deletion_with_history_retained(tmp_path):
    _seed_git_repo(tmp_path)
    _sq(tmp_path, "board", "post", "-m", "a notice that will later be cleared")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "post the notice")
    posted_commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    board_dir = _board_dir(tmp_path)
    notice_path = next(p for p in board_dir.glob("*.md"))
    rel_path = f"squads/board/{notice_path.name}"

    _sq(tmp_path, "board", "clear", "1")
    assert not notice_path.exists()

    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "clear the notice")

    log = _git(tmp_path, "log", "--oneline", "--follow", "--", rel_path).stdout
    assert len(log.strip().splitlines()) >= 2, log  # the post commit and the clear commit

    recovered = _git(tmp_path, "show", f"{posted_commit}:{rel_path}").stdout
    assert "a notice that will later be cleared" in recovered


def test_listing_after_a_clean_merge_leaves_no_git_tracked_file_dirty(tmp_path):
    _seed_git_repo(tmp_path)
    _sq(tmp_path, "board", "post", "-m", "a notice to read back")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "post a notice")
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""

    _sq(tmp_path, "board", "list")
    _sq(tmp_path, "board", "list", "--json")

    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""
