"""The imports of a source module as absolute module names, for the import guards.

Relative imports are resolved against the module's own package, and a literal
`importlib.import_module` or `__import__` call counts as an import. Each import is reported with
the outermost function it sits in.

A re-exported name is also reported as the module defining it (`squads._cli._app` for `main`).
"""

import ast
import functools
from dataclasses import dataclass
from pathlib import Path

import squads

SRC = Path(squads.__file__).parent


@dataclass(frozen=True)
class Imported:
    """One module an import statement or call names."""

    module: str
    line: int
    function: str | None


def module_name(path: Path) -> str:
    """The dotted name of the module at *path* under the `squads` package."""
    parts = path.relative_to(SRC.parent).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _package(path: Path) -> str:
    name = module_name(path)
    return name if path.name == "__init__.py" else name.rpartition(".")[0]


def _from_base(node: ast.ImportFrom, package: str) -> str:
    if not node.level:
        return node.module or ""
    base = package.split(".")
    base = base[: len(base) - (node.level - 1)]
    return ".".join([*base, node.module] if node.module else base)


def _literal_import(node: ast.Call) -> str | None:
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
    if name not in ("import_module", "__import__") or not node.args:
        return None
    arg = node.args[0]
    return arg.value if isinstance(arg, ast.Constant) and isinstance(arg.value, str) else None


@functools.cache
def reexports(module: str) -> dict[str, tuple[str, str | None]]:
    """What *module* re-exports with the explicit ``import name as name`` spelling (a package init
    also binds a child module under another name): each bound name with the module it comes from
    and the name it has there (None for a module bound under another name)."""
    base = SRC.parent.joinpath(*module.split("."))
    path = next((p for p in (base / "__init__.py", base.with_suffix(".py")) if p.is_file()), None)
    if path is None:
        return {}
    found: dict[str, tuple[str, str | None]] = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if not isinstance(node, ast.ImportFrom) or node.level:
            continue
        for alias in node.names:
            if node.module == module and alias.asname and alias.asname != alias.name:
                found[alias.asname] = (f"{module}.{alias.name}", None)
            elif alias.asname == alias.name:
                found[alias.name] = (node.module or "", alias.name)
    return found


def resolved(module: str, name: str) -> list[str]:
    """The modules defining *name* as *module* exports it, nearest child first."""
    source = reexports(module).get(name)
    if source is None:
        return []
    child, original = source
    if original is None:
        return [child]
    return [child, f"{child}.{original}", *resolved(child, original)]


def defining(module: str, rest: list[str]) -> tuple[str, list[str]]:
    """The module and attribute path that define ``module.rest[0]``, following each package's
    re-exports; a namespace re-export (a module bound under another name) is stepped into."""
    while rest and (source := reexports(module).get(rest[0])) is not None:
        child, original = source
        module, rest = (child, rest[1:]) if original is None else (child, [original, *rest[1:]])
    return module, rest


def _named(node: ast.AST, package: str) -> list[str]:
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    if isinstance(node, ast.ImportFrom):
        base = _from_base(node, package)
        named = [base, *(f"{base}.{a.name}" for a in node.names)]
        return [*named, *(m for a in node.names for m in resolved(base, a.name))]
    if isinstance(node, ast.Call):
        literal = _literal_import(node)
        return [literal] if literal is not None else []
    return []


def _is_type_checking(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False
    test = node.test
    name = test.attr if isinstance(test, ast.Attribute) else getattr(test, "id", None)
    return name == "TYPE_CHECKING"


def imports_of(path: Path, *, typing: bool = True) -> list[Imported]:
    """Every module *path* imports, by statement or by a literal import call, at any position;
    with *typing* false, the body of an ``if TYPE_CHECKING:`` block is left out."""
    return imports_in(path.read_text(encoding="utf-8"), _package(path), typing=typing)


def imports_in(source: str, package: str, *, typing: bool = True) -> list[Imported]:
    """The imports of *source*, a module of *package*, as `imports_of` reports them."""
    found: list[Imported] = []

    def visit(child: ast.AST, function: str | None) -> None:
        if not typing and isinstance(child, ast.If) and _is_type_checking(child):
            for other in child.orelse:
                visit(other, function)
            return
        found.extend(
            Imported(name, getattr(child, "lineno", 0), function) for name in _named(child, package)
        )
        inner = function
        if function is None and isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            inner = child.name
        walk(child, inner)

    def walk(node: ast.AST, function: str | None) -> None:
        for child in ast.iter_child_nodes(node):
            visit(child, function)

    walk(ast.parse(source), None)
    return found


def names_any(module: str, prefixes: tuple[str, ...]) -> bool:
    """Whether *module* is one of *prefixes* or a submodule of one."""
    return any(module == p or module.startswith(f"{p}.") for p in prefixes)
