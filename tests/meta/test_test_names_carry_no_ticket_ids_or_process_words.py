"""Repo gate: a test module, class or function is named for the behaviour it holds.

A ticket id or a build-process word in a name (`test_feat12_...`, `test_phase_two_...`) goes stale
the moment the work ships and says nothing about what is pinned. Ids and process words are read
off the snake_case tokens of every module file name and every `test*` function or `Test*` class
under both test roots.
"""

import ast
import re
from pathlib import Path

from tests.meta._roots import REPO_ROOT, scanned_modules

_ID_TOKEN = re.compile(r"^(?:feat|task|bug|adr|rev|epic|mile|st|us)\d+$")
_ID_PREFIX = frozenset({"feat", "task", "bug", "adr", "rev", "epic", "mile", "st", "us"})
_NUMBERED = frozenset({"round", "pass", "step"})
_PROCESS_WORDS = frozenset({"phase", "wave", "increment", "sprint", "iteration", "followup"})


def forbidden_in(name: str) -> list[str]:
    """The ticket-id or process-word forms *name* carries, one entry per occurrence."""
    tokens = [t for t in name.lower().split("_") if t]
    found: list[str] = []
    for i, token in enumerate(tokens):
        followed_by_number = i + 1 < len(tokens) and tokens[i + 1].isdigit()
        if _ID_TOKEN.match(token) or token in _PROCESS_WORDS:
            found.append(token)
        elif (token in _ID_PREFIX or token in _NUMBERED) and followed_by_number:
            found.append(f"{token}_{tokens[i + 1]}")
    return found


def violations(repo_root: Path = REPO_ROOT) -> list[tuple[str, str, list[str]]]:
    """(file, name, forbidden forms) for every offending module, class or test function."""
    out: list[tuple[str, str, list[str]]] = []
    for path in scanned_modules(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        names = [path.stem]
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            is_def = isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            if is_def and node.name.startswith(("test", "Test")):
                names.append(node.name)
        out.extend((rel, n, forbidden_in(n)) for n in names if forbidden_in(n))
    return out


def test_no_test_name_carries_a_ticket_id_or_process_word() -> None:
    found = violations()
    assert not found, f"name tests for the behaviour, not the work that produced them: {found}"


def test_the_scan_reads_both_test_roots() -> None:
    roots = {path.relative_to(REPO_ROOT).parts[0] for path in scanned_modules()}
    assert roots >= {"tests"}


def test_a_planted_ticket_id_and_process_word_are_found(tmp_path: Path) -> None:
    planted = tmp_path / "tests" / "unit" / "test_task12_rendering.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "def test_phase_two_reads_it(): ...\n"
        "def test_a_round_trip_is_stable(): ...\n"
        "class TestStepOne:\n    def test_bug_7_stays_fixed(self): ...\n",
        encoding="utf-8",
    )
    assert violations(tmp_path) == [
        ("tests/unit/test_task12_rendering.py", "test_task12_rendering", ["task12"]),
        ("tests/unit/test_task12_rendering.py", "test_phase_two_reads_it", ["phase"]),
        ("tests/unit/test_task12_rendering.py", "test_bug_7_stays_fixed", ["bug_7"]),
    ]


def test_the_old_root_is_scanned_too(tmp_path: Path) -> None:
    planted = tmp_path / "tests" / "cli" / "test_feat9_flags.py"
    planted.parent.mkdir(parents=True)
    planted.write_text("", encoding="utf-8")
    assert [rel for rel, _name, _found in violations(tmp_path)] == ["tests/cli/test_feat9_flags.py"]
