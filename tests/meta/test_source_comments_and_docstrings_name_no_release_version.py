"""Source prose never names a release version under ``src/squads/``, outside ``_migrations/`` where
a runner legitimately names the release it belongs to."""

import ast
import io
import re
import tokenize
from pathlib import Path

import pytest

_VERSION = re.compile(
    r"\bv[0-9]+\.[0-9]+(?:\.[0-9]+)?\b"
    r"|\b[0-9]+\.[0-9]+\.[0-9]+\b"
    r"|\b[0-9]+\.[0-9]+\.x\b"
    r"|\b(?:squads|release|schema|since|until)\s*(?:<=|>=|==|<|>)?\s*[0-9]+\.[0-9]+\b",
    re.IGNORECASE,
)

_SRC = Path(__file__).resolve().parents[2] / "src" / "squads"


def _prose_versions(source: str) -> list[tuple[int, str]]:
    """Every ``(line, version)`` found in a comment or docstring of *source*."""
    found: set[tuple[int, str]] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                line = node.body[0].lineno
                found.update((line, m.group()) for m in _VERSION.finditer(" ".join(doc.split())))
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            text = " ".join(node.value.value.split())
            found.update((node.lineno, m.group()) for m in _VERSION.finditer(text))
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type == tokenize.COMMENT:
            found.update((tok.start[0], m.group()) for m in _VERSION.finditer(tok.string))
    return sorted(found)


def _source_files() -> list[Path]:
    return [
        path
        for path in sorted(_SRC.rglob("*.py"))
        if "_migrations" not in path.relative_to(_SRC).parts
    ]


def test_no_source_comment_or_docstring_names_a_release_version() -> None:
    hits = [
        f"{path.relative_to(_SRC).as_posix()}:{line}: {version}"
        for path in _source_files()
        for line, version in _prose_versions(path.read_text(encoding="utf-8"))
    ]
    assert hits == [], "name no release version in source prose; describe the behaviour instead"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param('"""Since v0.4.0."""\n', ["v0.4.0"], id="module-docstring"),
        pytest.param('def f():\n    """Needs 0.14.2."""\n', ["0.14.2"], id="function-docstring"),
        pytest.param(
            'class C:\n    """Shipped in release\n    0.14."""\n', ["0.14"], id="wrapped-docstring"
        ),
        pytest.param("x = 1  # added in 0.9.2\n", ["0.9.2"], id="trailing-comment"),
        pytest.param("# squads 0.12 behaviour\nx = 1\n", ["0.12"], id="comment-line"),
        pytest.param('x = 1\n"""Changed in v1.4."""\n', ["v1.4"], id="attribute-docstring"),
        pytest.param('"""Shipped since v1.2.0."""\n', ["v1.2.0"], id="major-one-with-v"),
        pytest.param("# introduced in release 2.10\n", ["2.10"], id="release-word"),
        pytest.param('"""Needs schema 0.4."""\n', ["0.4"], id="schema-word"),
        pytest.param("# legacy lines (schema < 0.4) have none\n", ["0.4"], id="schema-operator"),
        pytest.param("# scaffolded on 0.14.x\n", ["0.14.x"], id="dot-x"),
        pytest.param('"""Present since 0.15."""\n', ["0.15"], id="since"),
        pytest.param('"""Kept until 0.16."""\n', ["0.16"], id="until"),
        pytest.param("# waits in 0.5 s\n", [], id="in-fraction-of-second"),
        pytest.param('"""Scores from 0.1 to 0.9."""\n', [], id="from-fractions"),
        pytest.param('x = "v0.5.1"\n', [], id="string-literal-is-not-prose"),
        pytest.param('"""Needs Python 3.14."""\n', [], id="runtime-version"),
        pytest.param('"""Rounds to 1.5 and 10.4."""\n', [], id="other-numbers"),
        pytest.param('"""Keeps 0.5 of the rows."""\n', [], id="ratio"),
        pytest.param("# waits 0.25 s\n", [], id="seconds"),
        pytest.param('"""Done in 2.5 seconds."""\n', [], id="in-duration"),
        pytest.param('"""Ranges from 1.0 to 2.0."""\n', [], id="from-range"),
        pytest.param('"""Reads TOML version 1.0."""\n', [], id="format-version"),
    ],
)
def test_the_scan_sees_a_planted_version_in_prose_and_only_there(
    source: str, expected: list[str]
) -> None:
    assert [version.split()[-1] for _, version in _prose_versions(source)] == expected


def test_the_scan_covers_the_source_tree_and_skips_migration_runners() -> None:
    files = {path.relative_to(_SRC).as_posix() for path in _source_files()}
    assert "_services/_base.py" in files
    assert not any(name.startswith("_migrations/") for name in files)
