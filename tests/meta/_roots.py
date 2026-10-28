"""The test roots a tree-scanning guard covers."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOTS: tuple[str, ...] = ("tests",)


def scanned_modules(repo_root: Path = REPO_ROOT) -> list[Path]:
    """Every `test_*.py` module under the test roots that exist under *repo_root*."""
    return [
        path
        for root in TEST_ROOTS
        if (repo_root / root).is_dir()
        for path in sorted((repo_root / root).rglob("test_*.py"))
        if "__pycache__" not in path.parts
    ]
