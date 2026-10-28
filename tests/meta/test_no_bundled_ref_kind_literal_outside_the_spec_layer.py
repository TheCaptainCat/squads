"""Repo-hygiene gate: none of the bundled ``[ref_kinds]`` names — ``related``, ``blocks``,
``depends-on``, ``implements``, ``fixes``, ``addresses``, ``supersedes``, ``duplicates``,
``scopes``, ``targets`` — may appear as a bare Python string-constant literal anywhere under
``src/squads/`` outside two legitimate exceptions:"""

import ast
from pathlib import Path

import pytest

from squads._workflow import bundled_spec

#: The bundled ``[ref_kinds]`` vocabulary — the literal-value floor this scan protects.
_REF_KIND_LITERALS: frozenset[str] = frozenset(
    {
        "related",
        "blocks",
        "depends-on",
        "implements",
        "fixes",
        "addresses",
        "supersedes",
        "duplicates",
        "scopes",
        "targets",
    }
)

#: Directories under src/squads/ exempt from the scan, for the two reasons in the module
#: docstring above.
_EXEMPT_DIR_NAMES: frozenset[str] = frozenset({"_specs", "_migrations"})

#: (path, lineno, value) hits allowlisted because they are not a ref-kind literal comparison at
#: all — each entry would carry its own one-line reason. Empty: every conversion this scan
#: enforces resolves through the declared semantic instead, with nothing left to excuse. See
#: ``test_every_allowlisted_hit_is_still_produced_by_the_scan_without_it`` below for what an
#: entry here would have to satisfy if one is ever added.
_ALLOWED_HITS: frozenset[tuple[str, int, str]] = frozenset()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _scan(
    root: Path, allowed: frozenset[tuple[str, int, str]] = _ALLOWED_HITS
) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    base = root / "src" / "squads"
    if not base.is_dir():
        return hits
    for path in base.rglob("*.py"):
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
            and node.value in _REF_KIND_LITERALS
            and (rel, node.lineno, node.value) not in allowed
        )
    return hits


def test_no_bundled_ref_kind_literal_appears_outside_the_spec_layer() -> None:
    hits = _scan(_repo_root())
    detail = "\n".join(f"  {path}:{lineno}: {value!r}" for path, lineno, value in hits)
    assert not hits, (
        f"bundled ref-kind literal(s) found outside _specs/ and _migrations/ — resolve through "
        f"the declared semantic (WorkflowSpec.dependency_ref_kind(s)/preload_ref_kind/"
        f"supersession_ref_kinds) instead:\n{detail}"
    )


def test_ref_kind_literals_are_pinned_to_the_bundled_spec() -> None:
    """``_REF_KIND_LITERALS`` must equal the bundled spec's declared ``[ref_kinds]`` codes."""
    declared = frozenset(bundled_spec().ref_kinds)
    missing = sorted(declared - _REF_KIND_LITERALS)
    extra = sorted(_REF_KIND_LITERALS - declared)
    assert declared == _REF_KIND_LITERALS, (
        "_REF_KIND_LITERALS has drifted from the bundled spec's declared [ref_kinds] -- "
        f"missing (spec declares, scan does not protect): {missing}; "
        f"extra (scan protects a name the spec no longer declares): {extra}"
    )


def test_the_scan_would_catch_a_planted_ref_kind_literal(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text('kind = "scopes"\n', encoding="utf-8")

    assert _scan(tmp_path) == [("src/squads/_example.py", 1, "scopes")]


@pytest.mark.parametrize("exempt_dir", sorted(_EXEMPT_DIR_NAMES))
def test_the_scan_exempts_the_spec_layer_directories(tmp_path: Path, exempt_dir: str) -> None:
    planted = tmp_path / "src" / "squads" / exempt_dir / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text('_KIND_SCOPES = "scopes"\n', encoding="utf-8")

    assert _scan(tmp_path) == []


def test_the_scan_never_flags_a_longer_string_merely_containing_the_substring(
    tmp_path: Path,
) -> None:
    """Docstring/prose text discussing the declared semantic ("the preload kind."""
    planted = tmp_path / "src" / "squads" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        '"""Resolved through the declared preload semantic, bundled as scopes."""\n',
        encoding="utf-8",
    )

    assert _scan(tmp_path) == []


def test_an_allowlisted_hit_does_not_mask_a_second_unallowlisted_literal_on_the_same_line(
    tmp_path: Path,
) -> None:
    """Two distinct constants on the same line are two distinct AST nodes — allowlisting one."""
    planted = tmp_path / "src" / "squads" / "_cli" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text('cols = ("scopes", "supersedes")\n', encoding="utf-8")

    synthetic_allowlist = frozenset({("src/squads/_cli/_example.py", 1, "scopes")})
    hits = _scan(tmp_path, allowed=synthetic_allowlist)
    assert ("src/squads/_cli/_example.py", 1, "supersedes") in hits
    assert ("src/squads/_cli/_example.py", 1, "scopes") not in hits


def test_every_allowlisted_hit_is_still_produced_by_the_scan_without_it() -> None:
    """A dead allowlist entry — one the scan would no longer actually produce."""
    root = _repo_root()
    for entry in _ALLOWED_HITS:
        without_this_entry = _ALLOWED_HITS - {entry}
        assert entry in _scan(root, allowed=without_this_entry), (
            f"allowlist entry {entry!r} is dead — the scan no longer produces it; remove it"
        )
