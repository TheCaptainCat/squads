"""Repo-hygiene gate: a concrete squad-item ID reference (``FEAT-<n>``-shaped, ``US<n>``-shaped,
…) must never leak into ``src/`` or ``docs/`` (full file text — production code and shipped
docs have no legitimate reason to cite a real backlog number) other than the designated
illustrative-walkthrough docs, which cite fictional self-consistent ids by design. It must
also never appear in a new-suite test file's own *name* or *docstring* (a test's assertion
*data* legitimately manufactures items and asserts on rendered ids or local sub-entity ids —
that's the feature under test, not a citation, so plain assertion data is deliberately left
alone; only the identifier/documentation surface is scanned). Placeholder shapes and
incidental substrings never match either way.

This is the new-suite's own permanent home for the invariant the pre-rebuild
``tests/test_squad_ref_hygiene.py`` protects for ``src/``+``docs/`` (that file also
allowlists all of ``tests/`` wholesale, since the old flat suite predates this rule and is
retired wholesale in Phase 3 rather than fixed up). This scan is scoped narrower on purpose:
it must never walk the old flat ``tests/test_*.py`` files (several intentionally carry a
ticket-ID in their own filename, a known legacy violation Phase 3 deletes) or this suite's
own governance docs (``tests/CONVENTIONS.md``, which legitimately cites this rebuild's own
ticket and row numbers by design).
"""

import ast
import re
from pathlib import Path

import pytest

REFERENCE_PATTERN = re.compile(r"\b(?:ADR|FEAT|TASK|REV|BUG|EPIC)-[0-9]|\bUS[0-9]|\bST[0-9]|§[0-9]")

#: Full-file-text scan — production code and docs have no legitimate reason to cite a real
#: backlog number as data.
_FULL_TEXT_ROOTS: tuple[str, ...] = ("src", "docs")

#: Designated illustrative walkthroughs under docs/ — self-consistent fictional examples that
#: legitimately cite item-shaped ids by design (mirrors the pre-rebuild scan's own allowlist).
_ALLOWED_DOC_FILES: frozenset[str] = frozenset(
    {"docs/tutorial.md", "docs/recipes.md", "docs/adoption.md"}
)

#: Identifier/docstring-only scan — these dirs are test *data* generators (rendered ids,
#: local sub-entity ids) legitimately appear in assertions, so only names/docs are checked.
_NAME_AND_DOCSTRING_ROOTS: tuple[str, ...] = (
    "tests/unit",
    "tests/service",
    "tests/cli",
    "tests/integration",
    "tests/tui",
    "tests/meta",
)

#: (path, matched token) pairs allowlisted because the docstring documents a *synthetic*
#: fixture-seeded id for the reader's benefit, not a real backlog citation — analogous to the
#: full-text scan's own doc allowlist above, kept explicit rather than loosening the pattern.
#: Every token on the surface must be listed individually — findall (below) checks each one.
_ALLOWED_NAME_DOCSTRING_HITS: frozenset[tuple[str, str]] = frozenset(
    {
        ("tests/cli/test_json_output_shape.py", "FEAT-2"),
        ("tests/cli/test_json_output_shape.py", "TASK-3"),
        ("tests/cli/test_json_output_shape.py", "BUG-4"),
        ("tests/cli/test_json_output_shape.py", "ADR-5"),
        ("tests/cli/test_json_output_shape.py", "REV-6"),
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _full_text_violations(root: Path) -> list[tuple[str, int, str]]:
    violations: list[tuple[str, int, str]] = []
    for rel_root in _FULL_TEXT_ROOTS:
        base = root / rel_root
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(root).as_posix()
            if rel in _ALLOWED_DOC_FILES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):  # fmt: skip
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                match = REFERENCE_PATTERN.search(line)
                if match:
                    violations.append((rel, lineno, match.group(0)))
    return violations


def _identifiers_and_docstrings(path: Path) -> list[str]:
    """Every checkable name/doc surface in a test module: its filename stem, module
    docstring, and every function/class name + docstring."""
    surfaces = [path.stem]
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):  # fmt: skip
        return surfaces
    module_doc = ast.get_docstring(tree)
    if module_doc:
        surfaces.append(module_doc)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            surfaces.append(node.name)
            doc = ast.get_docstring(node)
            if doc:
                surfaces.append(doc)
    return surfaces


def _name_and_docstring_violations(root: Path) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for rel_root in _NAME_AND_DOCSTRING_ROOTS:
        base = root / rel_root
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(root).as_posix()
            for surface in _identifiers_and_docstrings(path):
                # findall (not search) so a second, non-allowlisted token later in the same
                # surface is never masked by an earlier allowlisted one.
                tokens = REFERENCE_PATTERN.findall(surface)
                violations.extend(
                    (rel, token)
                    for token in tokens
                    if (rel, token) not in _ALLOWED_NAME_DOCSTRING_HITS
                )
    return violations


def test_source_and_docs_have_no_stray_ticket_references_anywhere_in_their_text() -> None:
    violations = _full_text_violations(_repo_root())
    detail = "\n".join(f"  {path}:{lineno}: {matched!r}" for path, lineno, matched in violations)
    assert not violations, f"squad-item reference(s) found in src/ or docs/:\n{detail}"


def test_the_new_test_tree_has_no_ticket_reference_in_a_filename_or_docstring() -> None:
    violations = _name_and_docstring_violations(_repo_root())
    detail = "\n".join(f"  {path}: {matched!r}" for path, matched in violations)
    assert not violations, f"ticket-ID reference(s) found in the new test tree:\n{detail}"


def test_the_pattern_ignores_placeholder_shapes_and_incidental_substrings() -> None:
    placeholders = "See FEAT-<n>, TASK-<n>, ADR-…, USn, PREFIX-NNNNNN, and §N for the shape."
    incidental = "STATUS1 costs FOCUS2 nothing; PLUS100 and TESTBED9 are fine, so is campus3."
    assert REFERENCE_PATTERN.search(placeholders) is None
    assert REFERENCE_PATTERN.search(incidental) is None


def test_the_full_text_scan_would_catch_a_real_reference_planted_in_src_or_docs(
    tmp_path: Path,
) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text("# see FEAT-123 for context\n", encoding="utf-8")

    violations = _full_text_violations(tmp_path)
    assert {path for path, _, _ in violations} == {"src/squads/_example.py"}


def test_the_full_text_scan_never_flags_a_designated_illustrative_walkthrough_doc(
    tmp_path: Path,
) -> None:
    walkthrough = tmp_path / "docs" / "tutorial.md"
    walkthrough.parent.mkdir(parents=True)
    walkthrough.write_text("Create EPIC-1, then FEAT-2 underneath it.\n", encoding="utf-8")

    assert _full_text_violations(tmp_path) == []


def test_the_identifier_scan_would_catch_a_reference_in_a_docstring_but_not_in_assertion_data(
    tmp_path: Path,
) -> None:
    planted = tmp_path / "tests" / "unit" / "test_something.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "def test_x() -> None:\n"
        '    """See TASK-999 for background."""\n'
        '    assert "TASK-000001" == "TASK-000001"  # legitimate rendered-id assertion data\n',
        encoding="utf-8",
    )

    violations = _name_and_docstring_violations(tmp_path)
    assert violations == [("tests/unit/test_something.py", "TASK-9")]


def test_an_allowlisted_token_never_masks_a_later_non_allowlisted_token_on_the_same_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second, non-allowlisted ticket ref appended after an allowlisted one in the same
    docstring must still be caught — the allowlist checks every match, not just the first."""
    import sys

    rel = "tests/unit/test_multi_ref_docstring.py"
    planted = tmp_path / rel
    planted.parent.mkdir(parents=True)
    planted.write_text(
        'def test_x() -> None:\n    """FEAT-2 is allowlisted; TASK-3 is not."""\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys.modules[__name__], "_ALLOWED_NAME_DOCSTRING_HITS", frozenset({(rel, "FEAT-2")})
    )

    violations = _name_and_docstring_violations(tmp_path)
    assert violations == [(rel, "TASK-3")]
