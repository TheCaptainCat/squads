"""Committed per-role agent memory, exercised against a real git repository: memory must
merge the way the accepted branch-across-teammates storage design actually promises —

- two branches each adding a **distinct** memory: the slug-named ``.md`` content files merge
  cleanly (both facts survive, none lost) — independent files never conflict;
- two branches editing the **same** memory surface an honest, unresolved ``.md`` conflict
  (correct to resolve by hand — nothing here should silently pick a side or duplicate);
- memory files are tracked by git at all (not swallowed by a stray ``.gitignore`` rule);
- forgetting a memory is a real, trackable git deletion — history stays recoverable.

Every other memory behaviour (add/list/search/show/forget, off-counter, repair-neutral) is
covered at the service/CLI layer; this file is deliberately the one place a *real* git
merge runs, since that is the only way the git-level claims above can be pinned honestly.
"""

import subprocess
import sys
from pathlib import Path

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


def _memory_dir(tmp_path: Path, role: str = "manager") -> Path:
    return tmp_path / "squads" / "agents" / "memory" / role


def test_memory_files_are_committed_not_gitignored(tmp_path):
    _seed_git_repo(tmp_path)
    _sq(tmp_path, "memory", "manager", "add", "a fact worth keeping in git")

    md_path = _memory_dir(tmp_path) / "a-fact-worth-keeping-in.md"
    assert md_path.is_file()

    # check-ignore exits 1 (not ignored) for a tracked path; a real .gitignore rule would exit 0.
    check_ignore = subprocess.run(
        ["git", "check-ignore", "-q", str(md_path)], cwd=tmp_path, capture_output=True
    )
    assert check_ignore.returncode == 1, "memory .md file must not be gitignored"

    _git(tmp_path, "add", "-A")
    porcelain = _git(tmp_path, "status", "--porcelain").stdout
    assert "agents/memory/manager/a-fact-worth-keeping-in.md" in porcelain


def test_forgetting_a_memory_is_a_real_git_deletion_with_history_retained(tmp_path):
    """Forgetting removes the working-tree file, but the commit that added it — and its
    content — must still be recoverable from git history, i.e. this is an ordinary tracked
    delete, not something that scrubs the fact from the repo."""
    _seed_git_repo(tmp_path)
    _sq(tmp_path, "memory", "manager", "add", "a fact that will later be forgotten")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "add the fact")
    added_commit = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    memory_path = _memory_dir(tmp_path) / "a-fact-that-will-later.md"
    assert memory_path.is_file()

    _sq(tmp_path, "memory", "manager", "forget", "a-fact-that-will-later")
    assert not memory_path.is_file()

    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "forget the fact")

    rel_path = "squads/agents/memory/manager/a-fact-that-will-later.md"
    log = _git(tmp_path, "log", "--oneline", "--follow", "--", rel_path).stdout
    assert len(log.strip().splitlines()) >= 2, log  # the add commit and the delete commit

    recovered = _git(tmp_path, "show", f"{added_commit}:{rel_path}").stdout
    assert "a fact that will later be forgotten" in recovered


def test_two_branches_adding_distinct_memories_merge_the_md_files_cleanly(tmp_path):
    main = _seed_git_repo(tmp_path)
    _git(tmp_path, "branch", "branch-a")
    _git(tmp_path, "branch", "branch-b")

    _git(tmp_path, "checkout", "-q", "branch-a")
    _sq(tmp_path, "memory", "manager", "add", "distinct memory alpha")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "alpha")

    _git(tmp_path, "checkout", "-q", "branch-b")
    _sq(tmp_path, "memory", "manager", "add", "distinct memory beta")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "beta")

    _git(tmp_path, "checkout", "-q", main)
    _git(tmp_path, "merge", "--no-edit", "-q", "branch-a")  # fast-forward
    _git(tmp_path, "merge", "--no-edit", "-q", "branch-b")

    memory_dir = _memory_dir(tmp_path)
    alpha_md = memory_dir / "distinct-memory-alpha.md"
    beta_md = memory_dir / "distinct-memory-beta.md"

    # No memory lost: both content files merged cleanly, no conflict markers inside either.
    assert alpha_md.is_file()
    assert beta_md.is_file()
    assert "distinct memory alpha" in alpha_md.read_text(encoding="utf-8")
    assert "distinct memory beta" in beta_md.read_text(encoding="utf-8")
    assert "<<<<<<<" not in alpha_md.read_text(encoding="utf-8")
    assert "<<<<<<<" not in beta_md.read_text(encoding="utf-8")
    assert _git(tmp_path, "status", "--porcelain").stdout.strip() == ""


def test_two_branches_editing_the_same_memory_surface_an_honest_conflict(tmp_path):
    main = _seed_git_repo(tmp_path)
    _sq(tmp_path, "memory", "manager", "add", "a fact that will be edited on two branches")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "baseline memory")

    _git(tmp_path, "branch", "edit-a")
    _git(tmp_path, "branch", "edit-b")

    memory_path = _memory_dir(tmp_path) / "a-fact-that-will-be.md"
    baseline_text = memory_path.read_text(encoding="utf-8")

    _git(tmp_path, "checkout", "-q", "edit-a")
    memory_path.write_text(baseline_text + "\nEdited from branch A.\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "edit from a")

    _git(tmp_path, "checkout", "-q", "edit-b")
    memory_path.write_text(
        baseline_text + "\nEdited from branch B, differently.\n", encoding="utf-8"
    )
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "edit from b")

    _git(tmp_path, "checkout", "-q", main)
    _git(tmp_path, "merge", "--no-edit", "-q", "edit-a")  # fast-forward

    merge_result = subprocess.run(
        ["git", "merge", "--no-edit", "edit-b"], cwd=tmp_path, capture_output=True, text=True
    )
    assert merge_result.returncode != 0, "same-memory edits on two branches must conflict honestly"
    assert "CONFLICT" in merge_result.stdout + merge_result.stderr

    conflicted_text = memory_path.read_text(encoding="utf-8")
    assert "<<<<<<<" in conflicted_text
    assert "Edited from branch A." in conflicted_text
    assert "Edited from branch B, differently." in conflicted_text

    status = _git(tmp_path, "status", "--porcelain").stdout
    assert any(
        "a-fact-that-will-be.md" in ln and ln.startswith("UU") for ln in status.splitlines()
    ), status

    _git(tmp_path, "merge", "--abort")
