"""Repo-hygiene gate: a backend must not recover data by reading back a file it generated."""

import ast
from pathlib import Path

#: Backend module -> the module-level constant naming a directory that backend generates into
#: and must never read from.
_WRITE_ONLY_OUTPUT_DIRS = {
    Path("_agents_md") / "_backend.py": "_STAGING_DIR",
}

#: Attribute names that read a path's contents. ``path_exists`` counts: probing for a
#: generated file is how a re-parse begins, and a backend has no reason to ask whether its own
#: output is there — it either just wrote it or is about to.
_READ_ATTRS = frozenset({"read_text", "read_bytes", "open", "path_exists", "glob", "rglob"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _names_used(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _reads_naming(tree: ast.Module, constant: str) -> list[str]:
    """Every ``<something>.read_text(<expr mentioning *constant*>)``-shaped call, as
    ``function::attribute`` labels."""
    offenders: list[str] = []
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for call in ast.walk(func):
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)):
                continue
            if call.func.attr not in _READ_ATTRS:
                continue
            mentions = any(constant in _names_used(arg) for arg in call.args)
            mentions = mentions or constant in _names_used(call.func)
            if mentions:
                offenders.append(f"{func.name}::{call.func.attr}")
    return offenders


def test_no_backend_reads_from_a_directory_it_generates_into() -> None:
    backends = _repo_root() / "src" / "squads" / "_backends"
    for rel, constant in _WRITE_ONLY_OUTPUT_DIRS.items():
        path = backends / rel
        source = path.read_text(encoding="utf-8")
        assert f"{constant} =" in source, f"{rel} no longer defines {constant} — guard is stale"
        offenders = _reads_naming(ast.parse(source), constant)
        assert not offenders, (
            f"{rel} reads back its own generated output under {constant} ({offenders}) — "
            "carry the value on the view the service passes in; generated text is output, "
            "never an input"
        )


def test_the_roster_view_carries_every_role_field_the_compiled_section_renders() -> None:
    """The other half of the same property: the re-parse existed."""
    from squads._roles._projection import RoleView

    section = (
        _repo_root()
        / "src"
        / "squads"
        / "_rendering"
        / "templates"
        / "agents_md"
        / "agents_section.md.j2"
    ).read_text(encoding="utf-8")

    fields = {f.name for f in RoleView.__dataclass_fields__.values()}
    rendered = {name for name in fields | {"mission", "responsibilities"} if f"r.{name}" in section}
    assert {"mission", "responsibilities"} <= rendered, (
        "the section stopped rendering mission/responsibilities — if that is deliberate, "
        "retire this guard along with the view fields"
    )
    assert rendered <= fields, f"the section renders role fields RoleView does not carry: {
        sorted(rendered - fields)
    }"
