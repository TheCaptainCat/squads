"""Repo gate: `tests/` prose is short and carries no ticket ids or release versions.

A test docstring is one line; any other docstring is at most five non-blank lines; no comment or
docstring names a ticket, finding or story id or a release version, except in a migration
subject, whose file name carries `migrat`. Docstrings are read whole with whitespace collapsed,
comments through `tokenize`.
"""

import ast
import io
import re
import tokenize
from pathlib import Path

from tests.meta._roots import REPO_ROOT

MAX_OTHER_DOCSTRING_LINES = 5

_TICKET = re.compile(
    r"\b(?:TASK|FEAT|BUG|REV|ADR|EPIC|MILE|SKILL|DOC)-[0-9]+\b|\b(?:F[0-9]{1,2}|ST[0-9]+|US[0-9]+)\b"
)
_VERSION = re.compile(
    r"\bv[0-9]+\.[0-9]+(?:\.[0-9]+)?\b"
    r"|\b[0-9]+\.[0-9]+\.[0-9]+\b"
    r"|\b[0-9]+\.[0-9]+\.x\b"
    r"|\b(?:squads|release|schema|since|until)\s*(?:<=|>=|==|<|>)?\s*[0-9]+\.[0-9]+\b",
    re.IGNORECASE,
)


def _prose_findings(text: str, check_versions: bool) -> list[str]:
    flat = " ".join(text.split())
    found = [m.group() for m in _TICKET.finditer(flat)]
    if check_versions:
        found += [m.group() for m in _VERSION.finditer(flat)]
    return found


def violations(source: str, *, migration_subject: bool = False) -> list[str]:
    """One message per breach of the prose rule in *source*."""
    out: list[str] = []
    versions = not migration_subject
    for node in ast.walk(ast.parse(source)):
        is_def = isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        if not isinstance(node, ast.Module | ast.ClassDef) and not is_def:
            continue
        doc = ast.get_docstring(node, clean=False)
        if doc is None:
            continue
        line = 1 if isinstance(node, ast.Module) else node.body[0].lineno
        lines = [ln for ln in doc.splitlines() if ln.strip()]
        if is_def and node.name.startswith("test"):
            if len(lines) > 1:
                out.append(f"{line}: test docstring is {len(lines)} lines, not one")
        elif len(lines) > MAX_OTHER_DOCSTRING_LINES:
            out.append(f"{line}: docstring is {len(lines)} non-blank lines")
        out.extend(f"{line}: {f!r} in a docstring" for f in _prose_findings(doc, versions))
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            out.extend(
                f"{tok.start[0]}: {f!r} in a comment" for f in _prose_findings(tok.string, versions)
            )
    return out


def scan(root: Path = REPO_ROOT) -> list[str]:
    """Every breach under `tests/`, as `path:line: message`."""
    base = root / "tests"
    out: list[str] = []
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        found = violations(
            path.read_text(encoding="utf-8"), migration_subject="migrat" in path.name
        )
        out.extend(f"{path.relative_to(root).as_posix()}:{v}" for v in found)
    return out


def test_new_root_prose_follows_the_comment_rule() -> None:
    found = scan()
    assert not found, "shorten the prose and drop ids and versions:\n" + "\n".join(found)


def test_a_multi_line_test_docstring_is_found() -> None:
    src = 'def test_a():\n    """One.\n\n    Two."""\n'
    assert violations(src) == ["2: test docstring is 2 lines, not one"]


def test_an_over_long_helper_module_and_class_docstring_is_found() -> None:
    body = "\n".join(f"line {i}" for i in range(6))
    for src in (
        f'def helper():\n    """{body}"""\n',
        f'"""{body}"""\n',
        f'class C:\n    """{body}"""\n',
    ):
        assert any("6 non-blank lines" in v for v in violations(src))


def test_a_docstring_of_five_lines_and_a_one_line_test_pass() -> None:
    body = "\n".join(f"line {i}" for i in range(5))
    assert violations(f'def helper():\n    """{body}"""\n\ndef test_a():\n    """One."""\n') == []


def test_ticket_ids_are_found_in_docstrings_and_comments() -> None:
    src = '"""Covers TASK-12."""\n# see F3\nx = 1  # ST2\n'
    assert violations(src) == [
        "1: 'TASK-12' in a docstring",
        "2: 'F3' in a comment",
        "3: 'ST2' in a comment",
    ]


def test_a_ticket_id_in_a_wrapped_docstring_is_found() -> None:
    assert violations('"""Covers TASK-12\nonly."""\n') == ["1: 'TASK-12' in a docstring"]


def test_release_versions_are_found_except_in_a_migration_subject() -> None:
    src = '"""Needs v1.2.0."""\n# schema < 0.4\n'
    assert violations(src) == ["1: 'v1.2.0' in a docstring", "2: 'schema < 0.4' in a comment"]
    assert violations(src, migration_subject=True) == []


def test_plain_numbers_and_string_literals_are_not_prose() -> None:
    assert violations('x = "TASK-9 v1.2.3"\n"""Takes 2.5 seconds."""\n') == []
