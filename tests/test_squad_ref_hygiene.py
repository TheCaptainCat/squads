"""Repo-wide gate: a concrete squad-item ID reference may live only in the dogfood squad's
own item files.

Detects concrete-digit tokens — ``FEAT-3``, ``TASK-12``, ``ADR-1``, ``REV-4``, ``BUG-9``,
``EPIC-2``, ``US3``, ``ST1``, ``§5`` — on any other surface in the repo (source, docs, README,
shipped markdown, CLI strings, bundled prose). Placeholder shapes produced by hygiene sweeps
(``FEAT-<n>``, ``USn``, ellipsis templates like ``FEAT-…``) never match, so they pass without
any special-casing, and neither do ordinary words that merely contain a matching substring
(the leading ``\\b`` requires a real token boundary before the prefix/letters).
"""

import re
import subprocess
from collections.abc import Iterable
from pathlib import Path

#: One concrete-digit token: a real citation, never a placeholder shape.
REFERENCE_PATTERN = re.compile(r"\b(?:ADR|FEAT|TASK|REV|BUG|EPIC)-[0-9]|\bUS[0-9]|\bST[0-9]|§[0-9]")

#: Directory names skipped everywhere — build/VCS/tooling noise, never source content.
_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "node_modules",
        "dist",
        "build",
        ".vscode",
        ".idea",
        "tmp",
    }
)

#: Item-type folders under the dogfood squad directory — the sole legitimate home for a
#: real citation. Deliberately excludes ``agents/roles`` and ``agents/skills``: those hold
#: rendered bundled prose, which must itself stay reference-free.
_ITEM_FOLDERS = frozenset(
    {
        "epics",
        "features",
        "tasks",
        "bugs",
        "adrs",
        "reviews",
        "guides",
        "operators",
    }
)

#: Individual files exempt as designated illustrative walkthroughs (self-consistent fictional
#: examples, by design) or a historical release log (out of scope for this invariant).
_ALLOWED_FILES = frozenset(
    {
        "docs/tutorial.md",
        "docs/recipes.md",
        "docs/adoption.md",
        "CHANGELOG.md",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def is_allowlisted(rel_posix: str) -> bool:
    """Return True when *rel_posix* (repo-root-relative, ``/``-separated) may carry a reference."""
    if rel_posix in _ALLOWED_FILES:
        return True
    if rel_posix.startswith("squads/"):
        rest = rel_posix.removeprefix("squads/")
        if rest == ".squads.json":  # the rebuildable index — mirrors the item files 1:1
            return True
        return rest.split("/", 1)[0] in _ITEM_FOLDERS
    # Test names/docstrings citing AC or ticket numbers are a separate, already-scoped
    # concern; this gate does not police them.
    return rel_posix.startswith("tests/")


def _git_tracked_files(root: Path) -> list[Path] | None:
    """Return every file git knows about under *root* (tracked + untracked-but-not-ignored).

    Deliberately excludes gitignored content (build artifacts, the per-clone reflog, ``.venv``,
    …) without hand-maintaining a directory skip-list. Returns ``None`` when *root* isn't inside
    a git checkout (e.g. a synthetic tree built by a test), so the caller can fall back.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=root,
            capture_output=True,
            check=True,
            timeout=30,
        )
    except OSError, subprocess.CalledProcessError:
        return None
    names = result.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    return [root / name for name in names if name]


def _iter_files(root: Path) -> Iterable[Path]:
    tracked = _git_tracked_files(root)
    if tracked is not None:
        yield from (path for path in tracked if path.is_file())
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts[:-1]
        if any(part in _SKIP_DIR_NAMES or part.endswith(".egg-info") for part in parts):
            continue
        yield path


def find_violations(root: Path) -> list[tuple[str, int, str]]:
    """Scan *root* for concrete squad-item references outside the allowlist.

    Returns ``(repo_relative_path, line_number, matched_text)`` for every hit.
    """
    violations: list[tuple[str, int, str]] = []
    for path in _iter_files(root):
        rel_posix = path.relative_to(root).as_posix()
        if is_allowlisted(rel_posix):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError, OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = REFERENCE_PATTERN.search(line)
            if match:
                violations.append((rel_posix, lineno, match.group(0)))
    return violations


def test_no_squad_item_references_outside_allowlist() -> None:
    violations = find_violations(_repo_root())
    detail = "\n".join(f"  {path}:{lineno}: {matched!r}" for path, lineno, matched in violations)
    assert not violations, f"squad-item reference(s) found outside squads/** item files:\n{detail}"


def test_pattern_ignores_placeholder_and_template_shapes() -> None:
    sample = "See FEAT-<n>, TASK-<n>, ADR-…, USn, PREFIX-NNNNNN, and §N for the shape."
    assert REFERENCE_PATTERN.search(sample) is None


def test_pattern_ignores_words_that_merely_contain_a_matching_substring() -> None:
    sample = "STATUS1 costs FOCUS2 nothing; PLUS100 and TESTBED9 are fine, so is campus3."
    assert REFERENCE_PATTERN.search(sample) is None


def test_pattern_matches_each_concrete_reference_shape() -> None:
    for sample in ("FEAT-1", "TASK-12", "ADR-3", "REV-4", "BUG-5", "EPIC-6", "US1", "ST2", "§3"):
        assert REFERENCE_PATTERN.search(sample), f"expected a match in {sample!r}"


def test_gate_flags_a_planted_reference_outside_the_allowlist(tmp_path: Path) -> None:
    # Forbidden surface: an ordinary source file outside squads/**.
    forbidden = tmp_path / "src" / "squads" / "_example.py"
    forbidden.parent.mkdir(parents=True)
    forbidden.write_text("# see FEAT-123 for context\n", encoding="utf-8")

    # Allowed surfaces: a dogfood item file and a designated illustrative doc.
    item_file = tmp_path / "squads" / "features" / "FEAT-000001-example.md"
    item_file.parent.mkdir(parents=True)
    item_file.write_text("refs: FEAT-123\n", encoding="utf-8")

    doc = tmp_path / "docs" / "tutorial.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("sq create feature --parent EPIC-000009\n", encoding="utf-8")

    violations = find_violations(tmp_path)

    flagged_paths = {path for path, _, _ in violations}
    assert "src/squads/_example.py" in flagged_paths
    assert "squads/features/FEAT-000001-example.md" not in flagged_paths
    assert "docs/tutorial.md" not in flagged_paths
