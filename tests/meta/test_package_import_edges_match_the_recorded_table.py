"""Repo gate: the import edges between the packages of `src/squads` are a recorded table."""

import ast
import textwrap
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pytest

_ROOT_NODE = "squads"
_KINDS = ("top", "local", "typing")


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
    def __init__(self, importer: str, path: str, is_module: Iterable[str]) -> None:
        self.imports: list[Import] = []
        self._importer = importer
        self._path = path
        self._modules = frozenset(is_module)
        self._kind = "top"

    def _add(self, dotted: str, line: int) -> None:
        node = _node_of_dotted(dotted)
        if node is not None and node != self._importer:
            self.imports.append(Import(self._importer, node, self._kind, self._path, line))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._add(alias.name, node.lineno)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            raise AssertionError(f"{self._path}:{node.lineno}: relative imports are not allowed")
        module = node.module or ""
        for alias in node.names:
            submodule = f"{module}.{alias.name}"
            self._add(submodule if submodule in self._modules else module, node.lineno)

    def visit_Call(self, node: ast.Call) -> None:
        if _is_import_module_call(node) and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value.startswith("."):
                    raise AssertionError(
                        f"{self._path}:{node.lineno}: relative import_module is not allowed"
                    )
                self._add(arg.value, node.lineno)
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


def inits_with_code(src: Path) -> frozenset[str]:
    """Package ``__init__`` files whose body is more than a docstring."""
    holding = set[str]()
    for path in src.rglob("__init__.py"):
        body = ast.parse(path.read_text(encoding="utf-8")).body
        if body and not (
            len(body) == 1
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
        ):
            holding.add(path.relative_to(src.parent).as_posix())
    return frozenset(holding)


# --- the recorded tables -------------------------------------------------------------------------

#: ``importer -> imported kind``, one row per edge, sorted.
EDGES = textwrap.dedent("""\
__main__ -> _cli local
__main__ -> squads top
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
_cli -> _api top
_cli -> _badges top
_cli -> _clock local
_cli -> _context local
_cli -> _context top
_cli -> _discussion top
_cli -> _docfiles local
_cli -> _errors top
_cli -> _index top
_cli -> _interactions top
_cli -> _language top
_cli -> _migrations top
_cli -> _models local
_cli -> _models top
_cli -> _paths local
_cli -> _paths top
_cli -> _pronouns top
_cli -> _roles top
_cli -> _services local
_cli -> _services top
_cli -> _spec_documents top
_cli -> _specload top
_cli -> _tui local
_cli -> _util top
_cli -> _workflow local
_cli -> _workflow top
_cli -> squads top
_clock -> _context top
_context -> _api typing
_context -> _spec_documents typing
_context -> _workflow typing
_discussion -> _badges top
_discussion -> _errors top
_discussion -> _models top
_discussion -> _rendering top
_discussion -> _sections top
_discussion -> _workflow top
_docfiles -> _api top
_docfiles -> _errors top
_index -> _actor local
_index -> _aio local
_index -> _aio top
_index -> _clock local
_index -> _errors top
_index -> _models top
_index -> _paths top
_index -> _sections top
_index -> _workflow top
_interactions -> _badges top
_interactions -> _errors top
_interactions -> _models top
_interactions -> _overrides top
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
_migrations -> _discussion top
_migrations -> _errors top
_migrations -> _index top
_migrations -> _interactions top
_migrations -> _itemfile top
_migrations -> _models top
_migrations -> _paths local
_migrations -> _paths top
_migrations -> _rendering top
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
_overrides -> _specload top
_overrides -> _util top
_overrides -> _view_tags local
_overrides -> _workflow top
_overrides -> squads top
_paths -> _context top
_paths -> _errors top
_paths -> _models top
_paths -> _workflow top
_pronouns -> _errors top
_pronouns -> _models top
_pronouns -> _sections top
_rendering -> _badges top
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
_sections -> _errors top
_sections -> _models top
_services -> _actor top
_services -> _aio top
_services -> _api top
_services -> _backends top
_services -> _badges top
_services -> _board top
_services -> _clock top
_services -> _context top
_services -> _discussion top
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
_services -> _paths top
_services -> _pronouns top
_services -> _rendering local
_services -> _rendering top
_services -> _roles top
_services -> _sections top
_services -> _spec_documents top
_services -> _specload top
_services -> _specmerge top
_services -> _transform top
_services -> _util top
_services -> _view_remedies top
_services -> _view_tags top
_services -> _views top
_services -> _workflow top
_services -> squads top
_spec_documents -> _errors top
_spec_documents -> _interactions top
_spec_documents -> _roles top
_spec_documents -> _specload top
_spec_documents -> _workflow top
_specload -> _errors top
_specload -> _specmerge top
_specmerge -> _errors top
_specmerge -> squads top
_transform -> _errors top
_transform -> _models top
_transform -> _paths local
_transform -> _workflow typing
_tui -> _api top
_tui -> _clock top
_tui -> _errors top
_view_remedies -> _workflow top
_view_tags -> _errors top
_view_tags -> _interactions top
_view_tags -> _language top
_view_tags -> _models top
_view_tags -> _roles top
_view_tags -> _sections top
_view_tags -> _transform top
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
_views -> _workflow top
_workflow -> _errors local
_workflow -> _errors top
_workflow -> _models local
_workflow -> _models top
_workflow -> _overrides top
_workflow -> _specload top
_workflow -> _specmerge top
_workflow -> squads local
""").splitlines()

#: Nodes in the strongly connected component over the ``top`` edges.
TOP_EDGE_COMPONENT: frozenset[str] = frozenset(
    {
        "_badges",
        "_interactions",
        "_overrides",
        "_paths",
        "_rendering",
        "_workflow",
    }
)

#: Package inits that hold code, relative to ``src``.
INITS_WITH_CODE: frozenset[str] = frozenset(
    {
        "squads/__init__.py",
        "squads/_cli/__init__.py",
        "squads/_workflow/__init__.py",
    }
)


# --- the walker, on synthetic source -------------------------------------------------------------

_MODULES = ("squads.a", "squads.a.b", "squads._clock", "squads._models._item")


def _edges(source: str) -> list[tuple[str, str]]:
    return [
        (i.imported, i.kind) for i in walk_source(textwrap.dedent(source), "me", "m.py", _MODULES)
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import squads.a.b", [("a", "top")]),
        ("import squads.a as x", [("a", "top")]),
        ("from squads.a import b", [("a", "top")]),
        ("from squads.a import name", [("a", "top")]),
        ("from squads import _clock as clock", [("_clock", "top")]),
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


def test_the_package_inits_that_hold_code_are_the_recorded_ones() -> None:
    found = inits_with_code(_src())
    assert found == INITS_WITH_CODE, (
        f"inits holding code but not recorded: {sorted(found - INITS_WITH_CODE)}; "
        f"recorded but empty: {sorted(INITS_WITH_CODE - found)}"
    )
