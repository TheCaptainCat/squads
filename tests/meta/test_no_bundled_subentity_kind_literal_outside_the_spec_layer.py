"""Repo-hygiene gate: none of the bundled sub-entity kind names — ``story``, ``subtask``,
``finding`` — nor their container plurals — ``stories``, ``subtasks``, ``findings`` — may appear
as a bare Python string-constant literal anywhere under ``src/squads/`` outside two legitimate
exceptions:"""

import ast
from pathlib import Path

import pytest

from squads._workflow import bundled_spec

#: The bundled sub-entity vocabulary — the literal-value floor this scan protects.
_KIND_LITERALS: frozenset[str] = frozenset(
    {"story", "subtask", "finding", "stories", "subtasks", "findings"}
)

#: Directories under src/squads/ exempt from the scan, for the two reasons in the module
#: docstring above.
_EXEMPT_DIR_NAMES: frozenset[str] = frozenset({"_specs", "_migrations"})

#: ``(path, literal)`` -> why that file legitimately holds it. Per file and literal, not per
#: line, so an edit elsewhere in the file does not move the exemption.
_ALLOWED: dict[tuple[str, str], str] = {
    ("src/squads/_cli/_items.py", "story"): "the `--story` option name, a field not a kind",
    ("src/squads/_models/_subentity.py", "story"): "the `story` frontmatter field key",
    ("src/squads/_services/_validators.py", "story"): "the fallback kind of a missing declaration",
    **{
        ("src/squads/_services/_import.py", kind): "the per-kind events of the import format"
        for kind in ("story", "subtask", "finding")
    },
    **{
        ("src/squads/_services/_import_model.py", kind): "the per-kind events of the import format"
        for kind in ("story", "subtask", "finding")
    },
    **{
        ("src/squads/_workflow/_models.py", literal): (
            "the bundled container heading table, which only applies while a kind's declared "
            "plural matches it"
        )
        for literal in ("story", "subtask", "finding", "stories", "subtasks", "findings")
    },
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _scan(
    root: Path, allowed: frozenset[tuple[str, str]] | None = None
) -> list[tuple[str, int, str]]:
    allowed = frozenset(_ALLOWED) if allowed is None else allowed
    hits: list[tuple[str, int, str]] = []
    base = root / "src" / "squads"
    if not base.is_dir():
        return hits
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts or any(part in _EXEMPT_DIR_NAMES for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # fmt: skip
            continue
        rel = path.relative_to(root).as_posix()
        hits.extend(
            (rel, node.lineno, node.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value in _KIND_LITERALS
            and (rel, node.value) not in allowed
        )
    return hits


def test_no_bundled_subentity_kind_literal_appears_outside_the_spec_layer() -> None:
    hits = _scan(_repo_root())
    detail = "\n".join(f"  {path}:{lineno}: {value!r}" for path, lineno, value in hits)
    assert not hits, (
        "bundled sub-entity kind literal(s) found outside _specs/ and _migrations/ — resolve "
        f"the kind from the spec and compose a tag with markers.subentity_tag instead:\n{detail}"
    )


def test_kind_literals_are_pinned_to_the_bundled_spec() -> None:
    """``_KIND_LITERALS`` must equal the bundled kinds and their plurals."""
    kinds = bundled_spec().subentity_kinds
    declared = frozenset(kinds) | frozenset(spec.plural for spec in kinds.values())
    assert declared == _KIND_LITERALS


def test_every_allowed_pair_is_still_produced_by_the_scan_without_it() -> None:
    """A dead entry silently excuses whatever lands on that file later."""
    root = _repo_root()
    for entry in _ALLOWED:
        hits = _scan(root, allowed=frozenset(_ALLOWED) - {entry})
        assert any((path, value) == entry for path, _lineno, value in hits), (
            f"allowed pair {entry!r} is dead — the scan no longer produces it; remove it"
        )


def test_the_scan_would_catch_a_planted_kind_literal(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text('kind = "subtask"\n', encoding="utf-8")

    assert _scan(tmp_path) == [("src/squads/_example.py", 1, "subtask")]


@pytest.mark.parametrize("exempt_dir", sorted(_EXEMPT_DIR_NAMES))
def test_the_scan_exempts_the_spec_layer_directories(tmp_path: Path, exempt_dir: str) -> None:
    planted = tmp_path / "src" / "squads" / exempt_dir / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text('_SUBTASKS = "subtasks"\n', encoding="utf-8")

    assert _scan(tmp_path) == []


def test_the_scan_never_flags_prose_that_merely_contains_a_kind_name(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text('"""Each story holds its subtasks."""\n', encoding="utf-8")

    assert _scan(tmp_path) == []
