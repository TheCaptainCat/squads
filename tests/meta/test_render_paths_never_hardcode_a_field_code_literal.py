"""Repo-hygiene gate: a render path must never pass a quoted field-code literal (e.g."""

import re
from pathlib import Path

_HELPER_NAMES = ("field_label", "field_default", "resolve_collection", "declared_collection")

#: Matches `<helper>(<anything>, '<code>'` or `<helper>(<anything>, "<code>"` — a quoted second
#: positional argument to one of the field-code-consuming helpers.
_LITERAL_CODE_RE = re.compile(
    r"(?:" + "|".join(_HELPER_NAMES) + r")\([^,()]*,\s*['\"][a-zA-Z_]+['\"]"
)

#: Directories (relative to the repo root) whose every source file is scanned.
_SCANNED_TREES = (
    ("src", "squads", "_rendering", "templates", "items"),
    ("src", "squads", "_tui"),
    ("src", "squads", "_cli"),
)
_SCANNED_SUFFIXES = (".md.j2", ".py")

#: (path, field code) -> reason. Nothing is exempt: a render path names no field code.
SANCTIONED: dict[tuple[str, str], str] = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _scanned_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for parts in _SCANNED_TREES:
        base = root.joinpath(*parts)
        if not base.is_dir():
            continue
        files.extend(
            p
            for p in sorted(base.rglob("*"))
            if p.is_file() and p.name.endswith(_SCANNED_SUFFIXES) and "__pycache__" not in p.parts
        )
    return files


def _scan(root: Path) -> list[tuple[str, int, str]]:
    """Every ``(relpath, lineno, field_code)`` literal hit — sanctioned or not."""
    hits: list[tuple[str, int, str]] = []
    for path in _scanned_files(root):
        rel = path.relative_to(root).as_posix()
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            match = _LITERAL_CODE_RE.search(line)
            if match is not None:
                code = match.group(0).rsplit(",", 1)[1].strip().strip("'\"")
                hits.append((rel, lineno, code))
    return hits


def _unsanctioned(hits: list[tuple[str, int, str]]) -> list[tuple[str, int, str]]:
    return [h for h in hits if (h[0], h[2]) not in SANCTIONED]


def test_no_render_path_hardcodes_a_field_code_literal() -> None:
    hits = _unsanctioned(_scan(_repo_root()))
    detail = "\n".join(f"  {path}:{lineno} -> {code!r}" for path, lineno, code in hits)
    assert not hits, (
        "a render path passes a quoted field-code literal into "
        f"{'/'.join(_HELPER_NAMES)} — derive it from the spec instead (e.g. "
        f"primary_field_code, or iterate spec.fields_for):\n{detail}"
    )


def test_the_sanctioned_list_has_no_stale_entry() -> None:
    live = {(path, code) for path, _lineno, code in _scan(_repo_root())}
    stale = sorted(set(SANCTIONED) - live)
    assert not stale, (
        "a sanctioned field-code literal no longer exists — drop the exemption rather than "
        f"letting it cover a future one: {stale}"
    )


def test_the_scan_covers_the_tui_and_cli_surfaces_that_had_the_defect() -> None:
    """The guard used to scan only the item templates."""
    scanned = {p.relative_to(_repo_root()).as_posix() for p in _scanned_files(_repo_root())}
    assert "src/squads/_tui/_reader.py" in scanned
    assert "src/squads/_cli/_items.py" in scanned
    assert "src/squads/_rendering/templates/items/review.md.j2" in scanned


def test_the_scan_would_catch_a_planted_template_literal(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_rendering" / "templates" / "items" / "_example.md.j2"
    planted.parent.mkdir(parents=True)
    planted.write_text("{{ field_label(kind, 'severity', spec) }}\n", encoding="utf-8")

    assert _unsanctioned(_scan(tmp_path)) == [
        ("src/squads/_rendering/templates/items/_example.md.j2", 1, "severity")
    ]


def test_the_scan_would_catch_a_planted_tui_literal(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_tui" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        'coll = badges.resolve_collection(item.type, "priority", spec)\n', encoding="utf-8"
    )

    assert _unsanctioned(_scan(tmp_path)) == [("src/squads/_tui/_example.py", 1, "priority")]


def test_the_scan_would_catch_a_planted_strict_resolver_literal(tmp_path: Path) -> None:
    """The strict sibling counts too."""
    planted = tmp_path / "src" / "squads" / "_cli" / "_example.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        'coll = badges.declared_collection(item_type, "severity", spec)\n', encoding="utf-8"
    )

    assert _unsanctioned(_scan(tmp_path)) == [("src/squads/_cli/_example.py", 1, "severity")]


def test_the_scan_never_flags_a_derived_field_code(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_rendering" / "templates" / "items" / "_example.md.j2"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "{% set field_code = primary_field_code(kind, spec) %}\n"
        "{{ field_label(kind, field_code, spec) }}\n",
        encoding="utf-8",
    )

    assert _scan(tmp_path) == []
