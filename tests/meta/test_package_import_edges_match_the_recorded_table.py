"""Repo gate: the import edges between the packages of `src/squads` are a recorded table, and every
private package re-exports exactly the names other packages import from it: its
init holds only re-export statements, no module outside it reaches a module path inside it, no
module imports a name from its own or an enclosing package's init, and each re-export is imported
from the package by some module outside it. Each package level is acyclic over top-level imports."""

import ast
import re
import textwrap
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pytest

_ROOT_NODE = "squads"
_KINDS = ("top", "local", "typing")


@dataclass(frozen=True)
class Statement:
    """One bound import: the module path it names and, for a name taken from it, the name."""

    importer: str
    target: str
    name: str | None
    kind: str
    path: str
    line: int


@dataclass(frozen=True)
class Import:
    """One import statement reduced to its edge."""

    importer: str
    imported: str
    kind: str
    path: str
    line: int


def _src() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "squads"


def _node_of_dotted(dotted: str) -> str | None:
    """The node a dotted module name belongs to, or None when it is not under ``squads``."""
    parts = dotted.split(".")
    if parts[0] != "squads":
        return None
    return parts[1] if len(parts) > 1 else _ROOT_NODE


def _is_type_checking(test: ast.expr) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _is_import_module_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr == "import_module"
    return isinstance(func, ast.Name) and func.id == "import_module"


class _Walker(ast.NodeVisitor):
    def __init__(
        self, importer: str, path: str, is_module: Iterable[str], module: str | None = None
    ) -> None:
        self.imports: list[Import] = []
        self.statements: list[Statement] = []
        self.module = module or importer
        self._importer = importer
        self._path = path
        self._modules = frozenset(is_module)
        self._kind = "top"

    def _add(self, dotted: str, line: int) -> None:
        node = _node_of_dotted(dotted)
        if node is not None and node != self._importer:
            self.imports.append(Import(self._importer, node, self._kind, self._path, line))

    def _bind(self, target: str, name: str | None, line: int) -> None:
        self.statements.append(Statement(self.module, target, name, self._kind, self._path, line))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._add(alias.name, node.lineno)
            self._bind(alias.name, None, node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            raise AssertionError(f"{self._path}:{node.lineno}: relative imports are not allowed")
        module = node.module or ""
        for alias in node.names:
            submodule = f"{module}.{alias.name}"
            self._add(submodule if submodule in self._modules else module, node.lineno)
            if submodule in self._modules:
                self._bind(submodule, None, node.lineno)
            else:
                self._bind(module, alias.name, node.lineno)

    def visit_Call(self, node: ast.Call) -> None:
        if _is_import_module_call(node) and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value.startswith("."):
                    raise AssertionError(
                        f"{self._path}:{node.lineno}: relative import_module is not allowed"
                    )
                self._add(arg.value, node.lineno)
                self._bind(arg.value, None, node.lineno)
        self.generic_visit(node)

    def _enter(self, node: ast.AST, kind: str) -> None:
        saved, self._kind = self._kind, kind
        self.generic_visit(node)
        self._kind = saved

    def _function(self, node: ast.AST) -> None:
        self._enter(node, self._kind if self._kind == "typing" else "local")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._function(node)

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking(node.test):
            saved, self._kind = self._kind, "typing"
            for child in node.body:
                self.visit(child)
            self._kind = saved
            for child in node.orelse:
                self.visit(child)
        else:
            self.generic_visit(node)


def walk_source(source: str, importer: str, path: str, modules: Iterable[str] = ()) -> list[Import]:
    """The imports of one module's source, each reduced to an edge from ``importer``."""
    walker = _Walker(importer, path, modules)
    walker.visit(ast.parse(source))
    return walker.imports


def walk_statements(
    source: str, module: str, path: str, modules: Iterable[str] = ()
) -> list[Statement]:
    """The bound imports of the module *module*, from its source."""
    node = _node_of_dotted(module) or _ROOT_NODE
    walker = _Walker(node, path, modules, module)
    walker.visit(ast.parse(source))
    return walker.statements


def _module_names(src: Path) -> frozenset[str]:
    names = set[str]()
    for path in src.rglob("*.py"):
        rel = path.relative_to(src).with_suffix("")
        parts = rel.parts[:-1] if rel.name == "__init__" else rel.parts
        names.add(".".join(("squads", *parts)))
    return frozenset(names)


def _importer_of(rel: Path) -> str:
    parts = rel.parts
    if len(parts) == 1:
        return _ROOT_NODE if rel.stem == "__init__" else parts[0].removesuffix(".py")
    return parts[0]


def measure(src: Path) -> list[Import]:
    """Every cross-node import under ``src``."""
    modules = _module_names(src)
    found: list[Import] = []
    for path in sorted(src.rglob("*.py")):
        rel = path.relative_to(src)
        found += walk_source(
            path.read_text(encoding="utf-8"),
            _importer_of(rel),
            f"src/squads/{rel.as_posix()}",
            modules,
        )
    return found


def _module_of(rel: Path) -> str:
    parts = rel.with_suffix("").parts
    return ".".join(("squads", *(parts[:-1] if parts[-1] == "__init__" else parts)))


def statements_under(root: Path, modules: frozenset[str], label: str) -> list[Statement]:
    """Every bound import of the modules under *root*, each path shown under *label*."""
    found: list[Statement] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        module = _module_of(rel) if label.startswith("src") else f"tests.{'.'.join(rel.parts)}"
        found += walk_statements(
            path.read_text(encoding="utf-8"), module, f"{label}/{rel.as_posix()}", modules
        )
    return found


def components(edges: Iterable[tuple[str, str]]) -> list[frozenset[str]]:
    """Strongly connected components of size above one, by Tarjan's algorithm."""
    graph: dict[str, set[str]] = {}
    for a, b in edges:
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set())
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack = set[str]()
    found: list[frozenset[str]] = []

    def visit(v: str) -> None:
        index[v] = low[v] = len(index)
        stack.append(v)
        on_stack.add(v)
        for w in graph[v]:
            if w not in index:
                visit(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            group = set[str]()
            while True:
                w = stack.pop()
                on_stack.discard(w)
                group.add(w)
                if w == v:
                    break
            if len(group) > 1:
                found.append(frozenset(group))

    for v in sorted(graph):
        if v not in index:
            visit(v)
    return found


# --- the recorded tables -------------------------------------------------------------------------

#: ``importer -> imported kind``, one row per edge, sorted.
EDGES = textwrap.dedent("""\
__main__ -> _shim top
_actor -> _context top
_aio -> _errors top
_api -> _errors top
_api -> _models top
_backends -> _aio top
_backends -> _errors top
_backends -> _interactions local
_backends -> _interactions top
_backends -> _language top
_backends -> _models top
_backends -> _paths top
_backends -> _rendering top
_backends -> _roles top
_backends -> _sections top
_backends -> _view_tags top
_backends -> _views top
_backends -> _workflow top
_badges -> _workflow top
_board -> _aio top
_board -> _clock top
_board -> _errors top
_board -> _models top
_board -> _paths top
_board -> _sections top
_cli -> _actor top
_cli -> _api local
_cli -> _api top
_cli -> _badges top
_cli -> _clock local
_cli -> _config top
_cli -> _context local
_cli -> _context top
_cli -> _daemon local
_cli -> _daemon_link top
_cli -> _daemon_start top
_cli -> _discussion top
_cli -> _docfiles local
_cli -> _endpoint top
_cli -> _errors top
_cli -> _index top
_cli -> _migrations top
_cli -> _models local
_cli -> _models top
_cli -> _paths local
_cli -> _paths top
_cli -> _pronouns top
_cli -> _roles top
_cli -> _services local
_cli -> _spans top
_cli -> _spec_documents top
_cli -> _specload top
_cli -> _tui local
_cli -> _util top
_cli -> _workflow local
_cli -> _workflow top
_cli -> squads top
_clock -> _context top
_config -> _endpoint top
_config -> _models top
_config -> _util top
_context -> _api typing
_context -> _parse_cache typing
_context -> _spec_documents typing
_context -> _workflow typing
_daemon -> _aio top
_daemon -> _api top
_daemon -> _cli top
_daemon -> _clock top
_daemon -> _context top
_daemon -> _endpoint top
_daemon -> _errors top
_daemon -> _models top
_daemon -> _parse_cache top
_daemon -> _services top
_daemon -> _shim top
_daemon -> _spec_documents top
_daemon -> squads top
_daemon_link -> _endpoint top
_daemon_start -> _daemon_link top
_daemon_start -> _endpoint top
_discussion -> _badges top
_discussion -> _errors top
_discussion -> _models top
_discussion -> _rendering local
_discussion -> _sections top
_discussion -> _view_bodies top
_discussion -> _workflow top
_docfiles -> _api top
_docfiles -> _errors top
_endpoint -> _windows_owner local
_endpoint -> squads local
_index -> _actor local
_index -> _aio local
_index -> _aio top
_index -> _clock local
_index -> _context top
_index -> _errors top
_index -> _models top
_index -> _paths top
_index -> _sections top
_index -> _workflow top
_interactions -> _badges top
_interactions -> _errors top
_interactions -> _models top
_interactions -> _overrides local
_interactions -> _roles top
_interactions -> _specload top
_interactions -> _specmerge top
_interactions -> _workflow top
_interactions -> squads local
_itemfile -> _aio top
_itemfile -> _errors top
_itemfile -> _models top
_itemfile -> _sections top
_memory -> _aio top
_memory -> _clock top
_memory -> _errors top
_memory -> _models top
_memory -> _paths top
_memory -> _sections top
_memory -> _util top
_migrations -> _actor top
_migrations -> _aio top
_migrations -> _api top
_migrations -> _backends top
_migrations -> _clock top
_migrations -> _config top
_migrations -> _discussion top
_migrations -> _endpoint top
_migrations -> _errors top
_migrations -> _index top
_migrations -> _interactions top
_migrations -> _itemfile top
_migrations -> _models top
_migrations -> _paths local
_migrations -> _paths top
_migrations -> _roles top
_migrations -> _sections top
_migrations -> _util top
_migrations -> _view_tags top
_migrations -> _views top
_migrations -> _workflow top
_models -> _clock top
_models -> _errors top
_models -> _util top
_overrides -> _aio top
_overrides -> _errors top
_overrides -> _interactions top
_overrides -> _models top
_overrides -> _paths top
_overrides -> _rendering top
_overrides -> _roles local
_overrides -> _roles top
_overrides -> _sections top
_overrides -> _sources top
_overrides -> _specload top
_overrides -> _util top
_overrides -> _view_tags local
_overrides -> _workflow top
_overrides -> squads top
_paths -> _config top
_paths -> _context top
_paths -> _endpoint top
_paths -> _errors top
_paths -> _models top
_paths -> _workflow top
_pronouns -> _errors top
_pronouns -> _models top
_pronouns -> _sections top
_rendering -> _badges top
_rendering -> _clock top
_rendering -> _errors top
_rendering -> _interactions top
_rendering -> _models top
_rendering -> _paths top
_rendering -> _sections top
_rendering -> _specload top
_rendering -> _util top
_rendering -> _workflow top
_roles -> _api top
_roles -> _errors top
_roles -> _models top
_roles -> _pronouns top
_roles -> _specload top
_roles -> _specmerge top
_roles -> _util top
_sections -> _context top
_sections -> _errors top
_sections -> _models top
_services -> _actor top
_services -> _aio top
_services -> _api top
_services -> _backends top
_services -> _badges top
_services -> _board top
_services -> _clock top
_services -> _config top
_services -> _context top
_services -> _discussion top
_services -> _endpoint top
_services -> _errors local
_services -> _errors top
_services -> _index local
_services -> _index top
_services -> _interactions top
_services -> _itemfile top
_services -> _language top
_services -> _memory top
_services -> _migrations top
_services -> _models top
_services -> _overrides local
_services -> _overrides top
_services -> _parse_cache top
_services -> _paths top
_services -> _pronouns top
_services -> _rendering local
_services -> _rendering top
_services -> _roles top
_services -> _sections top
_services -> _sources top
_services -> _spans top
_services -> _spec_documents top
_services -> _specload top
_services -> _specmerge top
_services -> _transform top
_services -> _util top
_services -> _view_bodies top
_services -> _view_remedies top
_services -> _view_tags top
_services -> _views top
_services -> _workflow top
_services -> squads local
_services -> squads top
_shim -> _cli local
_shim -> _daemon_start local
_shim -> _endpoint top
_shim -> squads local
_sources -> _clock top
_sources -> _errors top
_sources -> _models top
_sources -> _specload top
_sources -> _specmerge top
_sources -> _workflow top
_spans -> _context top
_spec_documents -> _api top
_spec_documents -> _errors top
_spec_documents -> _interactions top
_spec_documents -> _roles top
_spec_documents -> _sources top
_spec_documents -> _specload top
_spec_documents -> _workflow top
_specload -> _errors top
_specload -> _specmerge top
_specmerge -> _errors top
_specmerge -> squads local
_transform -> _errors top
_transform -> _models top
_transform -> _paths local
_transform -> _workflow typing
_tui -> _api top
_tui -> _clock top
_tui -> _errors top
_view_bodies -> _models top
_view_bodies -> _sections top
_view_remedies -> _workflow top
_view_tags -> _errors top
_view_tags -> _interactions top
_view_tags -> _language top
_view_tags -> _models top
_view_tags -> _roles top
_view_tags -> _sections top
_view_tags -> _transform top
_view_tags -> _view_bodies top
_view_tags -> _view_remedies top
_view_tags -> _views top
_view_tags -> _workflow top
_view_transforms -> _models top
_view_transforms -> _workflow top
_views -> _errors top
_views -> _interactions top
_views -> _language top
_views -> _models top
_views -> _paths top
_views -> _rendering top
_views -> _roles top
_views -> _sections top
_views -> _transform top
_views -> _view_bodies top
_views -> _workflow top
_workflow -> _context local
_workflow -> _errors local
_workflow -> _errors top
_workflow -> _migrations local
_workflow -> _models local
_workflow -> _models top
_workflow -> _overrides local
_workflow -> _parse_cache local
_workflow -> _parse_cache typing
_workflow -> _specload top
_workflow -> _specmerge top
_workflow -> squads local
""").splitlines()

#: Nodes in the strongly connected component over the ``top`` edges.
TOP_EDGE_COMPONENT: frozenset[str] = frozenset()


# --- the re-export rules -------------------------------------------------------------------------

#: The aliases an init may bind a child module under, for a module read as ``ns.NAME``.
NAMESPACE_ALIASES = {"ops": "_ops", "markers": "_markers", "attrs": "_attributes"}

#: Where modules and packages selected by name at run time are named.
BY_NAME_TABLES = (
    "LAZY_GROUPS (src/squads/_cli/_app.py)",
    "CONNECTORS (src/squads/_sources/_registry.py)",
    "CONVERTERS (src/squads/_sources/_converters.py)",
)
_BY_NAME_FILES = ("_cli/_app.py", "_sources/_registry.py", "_sources/_converters.py")
_BY_NAME_ALSO = ("squads._cli._remote",)
_DOTTED = re.compile(r"squads(?:\.[A-Za-z0-9_]+)+")


def _inside(module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


def _packages(src: Path) -> frozenset[str]:
    """Every package under ``src`` except the top-level one."""
    return frozenset(_module_of(p.relative_to(src)) for p in src.rglob("__init__.py")) - {
        _ROOT_NODE
    }


def _parent(module: str) -> str:
    return module.rpartition(".")[0]


def reach_in(statements: Iterable[Statement], packages: frozenset[str]) -> list[str]:
    """Imports of a module path inside a package, from a module outside it."""
    return [
        f"{s.path}:{s.line} reaches into {s.target}; import the name from {package} instead"
        for s in statements
        for package in sorted(packages)
        if s.target.startswith(f"{package}.") and not _inside(s.importer, package)
    ]


def reach_in_from_tests(
    statements: Iterable[Statement],
    packages: frozenset[str],
    modules: frozenset[str],
) -> list[str]:
    """Name imports from a module path inside a package, in a test."""
    return [
        f"{s.path}:{s.line} takes {s.name} from {s.target}; "
        f"import it from {package}, or import the module object"
        for s in statements
        if s.name is not None and s.target in modules
        for package in sorted(packages)
        if s.target.startswith(f"{package}.") and s.target not in packages
    ]


def reach_out(statements: Iterable[Statement], packages: frozenset[str]) -> list[str]:
    """Names imported from the init of the importer's own package or an enclosing one."""
    return [
        f"{s.path}:{s.line} imports {s.name} from {s.target}, a package it belongs to; "
        f"import the sibling module directly"
        for s in statements
        if s.name is not None and s.target in packages and s.importer.startswith(f"{s.target}.")
    ]


def _body(init: Path) -> list[ast.stmt]:
    body = ast.parse(init.read_text(encoding="utf-8")).body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        return body[1:]
    return body


def init_shape(src: Path, packages: frozenset[str], modules: frozenset[str]) -> list[str]:
    """Init statements other than a docstring and the permitted re-export forms."""
    found: list[str] = []
    for package in sorted(packages):
        init = src.parent.joinpath(*package.split("."), "__init__.py")
        where = init.relative_to(src.parent.parent).as_posix()
        for node in _body(init):
            if not isinstance(node, ast.ImportFrom) or node.level or node.module is None:
                found.append(f"{where}:{node.lineno} holds a statement other than a re-export")
                continue
            for alias in node.names:
                if node.module == package:
                    ok = NAMESPACE_ALIASES.get(alias.asname or "") == alias.name
                    ok = ok and f"{package}.{alias.name}" in modules
                else:
                    ok = alias.asname == alias.name and _parent(node.module) == package
                    ok = ok and node.module in modules
                    if ok and alias.name.startswith("_"):
                        found.append(
                            f"{where}:{node.lineno} re-exports the underscore name {alias.name}; "
                            "an init re-exports public names only"
                        )
                        continue
                if not ok:
                    found.append(
                        f"{where}:{node.lineno} re-exports {alias.name} in a form other than "
                        f"`from {package}.<child> import Name as Name`"
                    )
    return found


def by_name_modules(src: Path, modules: frozenset[str]) -> frozenset[str]:
    """The modules and packages the tables name as strings, other than the table's own file."""
    found = set(_BY_NAME_ALSO)
    for name in _BY_NAME_FILES:
        own = _module_of(Path(name))
        for node in ast.walk(ast.parse((src / name).read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                found.update(m for m in _DOTTED.findall(node.value) if m in modules and m != own)
    return frozenset(found)


def _reexports(src: Path, package: str) -> list[tuple[str, str, str]]:
    """Each ``(bound name, child module, name in the child)`` an init re-exports."""
    init = src.parent.joinpath(*package.split("."), "__init__.py")
    return [
        (alias.asname or alias.name, node.module, alias.name)
        for node in _body(init)
        if isinstance(node, ast.ImportFrom) and node.module and not node.level
        for alias in node.names
    ]


def exact_surface(
    src: Path,
    statements: list[Statement],
    packages: frozenset[str],
    by_name: frozenset[str],
) -> list[str]:
    """Re-exports no module outside the package imports, and re-exports of by-name modules."""
    reexported = {p: _reexports(src, p) for p in packages}

    def used(package: str, name: str) -> bool:
        if any(
            s.target == package
            and s.name == name
            and not _inside(s.importer, package)
            and not s.path.endswith("__init__.py")
            for s in statements
        ):
            return True
        parent = _parent(package)
        return parent in packages and any(
            child == package and original == name and used(parent, bound)
            for bound, child, original in reexported[parent]
        )

    found: list[str] = []
    for package in sorted(packages):
        for bound, child, _ in reexported[package]:
            if child in by_name or any(
                _inside(child, m) and not _inside(package, m) for m in by_name
            ):
                found.append(
                    f"{package} re-exports from {child}, which is selected by name at run time "
                    f"(see {', '.join(BY_NAME_TABLES)})"
                )
            elif package not in by_name and not used(package, bound):
                found.append(f"{package} re-exports {bound}, which no module outside it imports")
    return found


def level_cycles(statements: Iterable[Statement], packages: frozenset[str]) -> list[str]:
    """Cycles among the direct children of each package, over top-level imports."""
    levels = [_ROOT_NODE, *sorted(packages)]
    found: list[str] = []
    top = [s for s in statements if s.kind == "top"]
    for level in levels:
        edges = set[tuple[str, str]]()
        for s in top:
            if not (_inside(s.importer, level) and _inside(s.target, level)):
                continue
            a, b = (_child_of(m, level) for m in (s.importer, s.target))
            if a is not None and b is not None and a != b:
                edges.add((a, b))
        found += [f"{level}: {sorted(g)} import each other" for g in components(edges)]
    return found


def _child_of(module: str, package: str) -> str | None:
    rest = module.removeprefix(f"{package}.") if module != package else ""
    return rest.split(".")[0] if rest else None


# --- the walker, on synthetic source -------------------------------------------------------------

_SYNTHETIC = ("squads.a", "squads.a.b", "squads._clock", "squads._models._item")


def _edges(source: str) -> list[tuple[str, str]]:
    return [
        (i.imported, i.kind) for i in walk_source(textwrap.dedent(source), "me", "m.py", _SYNTHETIC)
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import squads.a.b", [("a", "top")]),
        ("import squads.a as x", [("a", "top")]),
        ("from squads.a import b", [("a", "top")]),
        ("from squads.a import name", [("a", "top")]),
        ("from squads import _clock as squads_clock", [("_clock", "top")]),
        ("from squads import something", [("squads", "top")]),
        ("from squads._models._item import Item", [("_models", "top")]),
        ("import os\nfrom pathlib import Path", []),
        ("from squads.me import x", []),
        ('import importlib\nimportlib.import_module("squads.a")', [("a", "top")]),
        ("import importlib\nimportlib.import_module(name)", []),
    ],
    ids=[
        "import-dotted",
        "import-alias",
        "from-import-module",
        "from-import-name",
        "root-import-module",
        "root-import-name",
        "from-import-class",
        "foreign",
        "self-edge",
        "dynamic-literal",
        "dynamic-computed",
    ],
)
def test_walker_reduces_each_import_form_to_one_edge(
    source: str, expected: list[tuple[str, str]]
) -> None:
    assert _edges(source) == expected


@pytest.mark.parametrize(
    ("template", "kind"),
    [
        ("import squads.a", "top"),
        ("def f():\n    import squads.a", "local"),
        ("async def f():\n    import squads.a", "local"),
        ("class C:\n    import squads.a", "top"),
        ("class C:\n    def m(self):\n        import squads.a", "local"),
        ("from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import squads.a", "typing"),
        ("import typing\nif typing.TYPE_CHECKING:\n    import squads.a", "typing"),
        ("if TYPE_CHECKING:\n    pass\nelse:\n    import squads.a", "top"),
        ("if TYPE_CHECKING:\n    def f():\n        import squads.a", "typing"),
        ("try:\n    import squads.a\nexcept ImportError:\n    pass", "top"),
        ("try:\n    pass\nexcept ImportError:\n    import squads.a", "top"),
        ("def f():\n    if TYPE_CHECKING:\n        import squads.a", "typing"),
    ],
    ids=[
        "module",
        "function",
        "async-function",
        "class-body",
        "method",
        "type-checking-name",
        "type-checking-attribute",
        "type-checking-else",
        "function-in-type-checking",
        "try",
        "except",
        "type-checking-in-function",
    ],
)
def test_walker_tags_each_edge_with_where_it_runs(template: str, kind: str) -> None:
    assert _edges(template) == [("a", kind)]


def test_walker_refuses_a_relative_dynamic_import() -> None:
    with pytest.raises(AssertionError, match="relative import_module is not allowed"):
        walk_source('import importlib\nimportlib.import_module("._base", "squads.a")', "me", "m.py")


def test_walker_refuses_a_relative_import() -> None:
    with pytest.raises(AssertionError, match="relative imports are not allowed"):
        walk_source("from . import a", "me", "m.py")


# --- the measured tree ---------------------------------------------------------------------------

_MEASURED = measure(_src())
_MODULES = _module_names(_src())
_PACKAGES = _packages(_src())
_STATEMENTS = statements_under(_src(), _MODULES, "src/squads")
_TEST_STATEMENTS = statements_under(_src().parents[1] / "tests", _MODULES, "tests")


@pytest.mark.parametrize(
    ("importer", "imported", "kind"),
    [
        ("_services", "_roles", "top"),
        ("_models", "_clock", "top"),
        ("_backends", "_views", "top"),
        ("_backends", "_interactions", "local"),
        ("_context", "_workflow", "typing"),
    ],
)
def test_walker_finds_the_known_edges_of_the_tree(importer: str, imported: str, kind: str) -> None:
    assert any((i.importer, i.imported, i.kind) == (importer, imported, kind) for i in _MEASURED)


def test_every_edge_kind_is_one_the_table_knows() -> None:
    assert {i.kind for i in _MEASURED} <= set(_KINDS)


def test_the_tree_imports_exactly_the_recorded_edges() -> None:
    recorded = set(EDGES)
    seen: dict[str, Import] = {}
    for i in _MEASURED:
        seen.setdefault(f"{i.importer} -> {i.imported} {i.kind}", i)
    problems = [
        f"{i.path}:{i.line} imports {i.imported} ({i.kind}); add the row {row!r} to EDGES"
        for row, i in sorted(seen.items())
        if row not in recorded
    ]
    problems += [
        f"EDGES row {row!r} matches no import; delete it" for row in sorted(recorded - seen.keys())
    ]
    assert not problems, "\n".join(problems)
    assert sorted(EDGES) == EDGES, "EDGES rows must stay sorted"


def test_a_backend_does_not_import_the_index() -> None:
    assert not [row for row in EDGES if row.startswith("_backends -> _index ")]


def test_the_top_edge_component_is_the_recorded_one() -> None:
    top = {(i.importer, i.imported) for i in _MEASURED if i.kind == "top"}
    found = components(top)
    assert found == [TOP_EDGE_COMPONENT] or (not TOP_EDGE_COMPONENT and not found), (
        f"strongly connected over top-level edges: {[sorted(g) for g in found]}"
    )


# --- the rules, on the tree ----------------------------------------------------------------------


def test_every_init_holds_only_re_exports() -> None:
    assert not init_shape(_src(), _PACKAGES, _MODULES)


def test_no_source_module_reaches_into_a_package() -> None:
    assert not reach_in(_STATEMENTS, _PACKAGES)


def test_no_test_takes_a_name_from_a_module_inside_a_package() -> None:
    assert not reach_in_from_tests(_TEST_STATEMENTS, _PACKAGES, _MODULES)


def test_no_module_imports_a_name_from_a_package_it_belongs_to() -> None:
    assert not reach_out(_STATEMENTS, _PACKAGES)


def test_every_re_export_is_imported_from_outside_its_package() -> None:
    by_name = by_name_modules(_src(), _MODULES)
    assert not exact_surface(_src(), _STATEMENTS, _PACKAGES, by_name)


def test_every_package_level_is_acyclic() -> None:
    assert not level_cycles(_STATEMENTS, _PACKAGES)


def test_the_by_name_modules_include_the_lazy_groups_and_the_connectors() -> None:
    found = by_name_modules(_src(), _MODULES)
    assert {"squads._cli._create", "squads._cli._remote", "squads._sources._gitlab"} <= found


# --- the rules, on synthetic statements ----------------------------------------------------------


def _stmt(
    importer: str, target: str, name: str | None = None, kind: str = "top", path: str = "m.py"
) -> Statement:
    return Statement(importer, target, name, kind, path, 1)


_SYNTH_PACKAGES = frozenset({"squads.p", "squads.p.q"})
_SYNTH_MODULES = frozenset({"squads.p", "squads.p.q", "squads.p.q.m", "squads.p.n"})


def test_reach_in_finds_a_module_path_import_from_outside() -> None:
    outside = _stmt("squads.o", "squads.p.n", "X")
    inside = _stmt("squads.p.k", "squads.p.n", "X")
    nested = _stmt("squads.p.k", "squads.p.q.m", "X")

    assert len(reach_in([outside], _SYNTH_PACKAGES)) == 1
    assert reach_in([inside], _SYNTH_PACKAGES) == []
    assert len(reach_in([nested], _SYNTH_PACKAGES)) == 1


def test_reach_in_from_a_test_finds_a_name_but_not_a_module_object() -> None:
    name = _stmt("tests.t", "squads.p.n", "X")
    module = _stmt("tests.t", "squads.p.n", None)
    init = _stmt("tests.t", "squads.p.q", "X")

    found = reach_in_from_tests([name, module, init], _SYNTH_PACKAGES, _SYNTH_MODULES)
    assert len(found) == 1


def test_reach_out_finds_a_name_taken_from_an_enclosing_init() -> None:
    from_own = _stmt("squads.p.k", "squads.p", "X")
    from_enclosing = _stmt("squads.p.q.m", "squads.p", "X")
    sibling_object = _stmt("squads.p.k", "squads.p.n", None)
    outside = _stmt("squads.o", "squads.p", "X")

    found = reach_out([from_own, from_enclosing, sibling_object, outside], _SYNTH_PACKAGES)
    assert len(found) == 2


def test_the_cycle_check_finds_two_siblings_importing_each_other() -> None:
    cycle = [_stmt("squads.p.a", "squads.p.b", "X"), _stmt("squads.p.b", "squads.p.a", "Y")]
    chain = [_stmt("squads.p.a", "squads.p.b", "X"), _stmt("squads.p.b", "squads.p.c", "Y")]
    local = [
        _stmt("squads.p.a", "squads.p.b", "X"),
        _stmt("squads.p.b", "squads.p.a", "Y", "local"),
    ]

    assert len(level_cycles(cycle, frozenset({"squads.p"}))) == 1
    assert level_cycles(chain, frozenset({"squads.p"})) == []
    assert level_cycles(local, frozenset({"squads.p"})) == []


def _package_tree(root: Path, files: dict[str, str]) -> Path:
    src = root / "src" / "squads"
    for name, text in files.items():
        path = src / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return src


def test_the_init_shape_rule_accepts_re_exports_and_refuses_code(tmp_path: Path) -> None:
    src = _package_tree(
        tmp_path,
        {
            "__init__.py": "",
            "p/__init__.py": '"""Doc."""\nfrom squads.p._a import X as X\n',
            "p/_a.py": "X = 1\n",
            "r/__init__.py": "from squads.r._a import X\nY = 1\nimport os\n",
            "r/_a.py": "X = 1\n",
            "s/__init__.py": (
                "from squads.s._a import _hidden as _hidden\n"
                "from squads.s._a import _inner as _inner\n"
            ),
            "s/_a.py": "_hidden = 1\n_inner = 2\n",
        },
    )
    modules = _module_names(src)
    packages = _packages(src)

    found = init_shape(src, packages, modules)
    assert len([f for f in found if "r/__init__.py" in f]) == 3
    assert len([f for f in found if "s/__init__.py" in f and "underscore name" in f]) == 2
    assert len(found) == 5


def test_reach_in_finds_a_literal_import_module_call_from_outside() -> None:
    walker = _Walker("squads.o", "src/squads/o.py", _SYNTH_MODULES)
    walker.visit(ast.parse('importlib.import_module("squads.p.n")\n'))

    assert len(reach_in(walker.statements, _SYNTH_PACKAGES)) == 1


def test_the_exact_surface_rule_finds_an_unused_re_export_and_a_by_name_child(
    tmp_path: Path,
) -> None:
    src = _package_tree(
        tmp_path,
        {
            "__init__.py": "",
            "p/__init__.py": "from squads.p._a import X as X\nfrom squads.p._b import Y as Y\n",
            "p/_a.py": "X = 1\n",
            "p/_b.py": "Y = 1\n",
        },
    )
    statements = [_stmt("squads.o", "squads.p", "X", path="src/squads/o.py")]
    packages = _packages(src)

    unused = exact_surface(src, statements, packages, frozenset())
    by_name = exact_surface(src, statements, packages, frozenset({"squads.p._b"}))
    assert len(unused) == 1 and "re-exports Y" in unused[0]
    assert len(by_name) == 1 and "selected by name" in by_name[0]
