"""Hygiene gate: a test module that marks any test ``@pytest.mark.slow`` must also keep at least one
*unmarked* test in the same module."""

import ast
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _decorator_is_pytest_mark_slow(node: ast.expr) -> bool:
    """Match ``@pytest.mark.slow`` (bare attribute — the marker takes no arguments here)."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "slow"
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "mark"
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "pytest"
    )


def _all_slow_test_modules(root: Path) -> list[str]:
    """Every ``test_*.py`` module under ``tests/`` or ``tests/`` where every test function is
    ``@pytest.mark.slow``
    (a module with no test functions at all is not a violation — there is nothing to hide)."""
    violations: list[str] = []
    paths = [p for name in ("tests",) for p in sorted((root / name).rglob("test_*.py"))]
    for path in paths:
        if "__pycache__" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # fmt: skip
            continue
        test_funcs = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name.startswith("test_")
        ]
        if not test_funcs:
            continue
        if all(
            any(_decorator_is_pytest_mark_slow(dec) for dec in func.decorator_list)
            for func in test_funcs
        ):
            violations.append(path.relative_to(root).as_posix())
    return violations


def test_no_test_module_marks_every_one_of_its_tests_slow() -> None:
    violations = _all_slow_test_modules(_repo_root())
    detail = "\n".join(f"  {path}" for path in violations)
    assert not violations, (
        "module(s) below mark every test @pytest.mark.slow, so a bare `uv run pytest` runs "
        "nothing from them and a setup-path defect stays invisible without --run-slow — keep "
        "at least one fast, unmarked canary per module:\n" + detail
    )


def test_the_scanner_flags_a_module_where_every_test_is_marked_slow(tmp_path: Path) -> None:
    planted = tmp_path / "tests" / "test_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "import pytest\n\n"
        "@pytest.mark.slow\n"
        "def test_one() -> None: ...\n\n"
        "@pytest.mark.slow\n"
        "async def test_two() -> None: ...\n",
        encoding="utf-8",
    )

    assert _all_slow_test_modules(tmp_path) == ["tests/test_example.py"]


def test_the_scanner_passes_a_module_with_at_least_one_unmarked_test(tmp_path: Path) -> None:
    planted = tmp_path / "tests" / "test_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "import pytest\n\n"
        "@pytest.mark.slow\n"
        "def test_one() -> None: ...\n\n"
        "def test_two_is_the_fast_canary() -> None: ...\n",
        encoding="utf-8",
    )

    assert _all_slow_test_modules(tmp_path) == []


def test_the_scanner_ignores_a_module_with_no_test_functions_at_all(tmp_path: Path) -> None:
    planted = tmp_path / "tests" / "test_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text("def _helper() -> None: ...\n", encoding="utf-8")

    assert _all_slow_test_modules(tmp_path) == []


def test_the_scanner_ignores_a_decorator_named_slow_from_a_different_namespace(
    tmp_path: Path,
) -> None:
    """Only the exact ``pytest.mark.slow`` attribute chain counts."""
    planted = tmp_path / "tests" / "test_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "@slow\ndef test_one() -> None: ...\n\n@other.mark.slow\ndef test_two() -> None: ...\n",
        encoding="utf-8",
    )

    assert _all_slow_test_modules(tmp_path) == []
