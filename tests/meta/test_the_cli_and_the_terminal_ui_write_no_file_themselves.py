"""No module under `_cli/` or `_tui/` writes a file, directly or through another module's
function that does, nor imports one. A function or class writes when its body uses a file-writing
primitive, calls a function that writes, or returns a class that writes or has a subclass that
does; the local API is the gated route every write takes. A module reached through
`importlib.import_module` is out of reach of this scan."""

import ast
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from tests._import_scan import SRC, module_name

DIRS = (SRC / "_cli", SRC / "_tui")

#: Path and file methods that write, remove or rename whatever their receiver is.
WRITING_METHODS = frozenset(
    {
        "write_text",
        "write_bytes",
        "unlink",
        "rmdir",
        "mkdir",
        "touch",
        "chmod",
        "rmtree",
        "symlink_to",
        "hardlink_to",
    }
)
#: Methods that move a file when given one argument (``str.replace`` takes two).
MOVING_METHODS = frozenset({"replace", "rename"})
#: Modules every call into which writes.
WRITING_MODULES = frozenset({"shutil", "tempfile"})
#: Functions of ``os`` that write, remove or rename a file or a directory.
OS_WRITERS = frozenset(
    {
        "replace",
        "rename",
        "renames",
        "remove",
        "removedirs",
        "makedirs",
        "mkdir",
        "rmdir",
        "unlink",
        "symlink",
        "link",
        "truncate",
        "chmod",
    }
)

type Name = tuple[str, str]

#: The route every write takes: the local API runs an operation past the schema gate, so a call
#: through it is not a write of the caller's own.
GATED_ROUTE: Name = ("squads._services._local_api", "LocalApi")

#: The entries that deal with the daemon's own runtime files (a socket, a record, a lock and a log
#: in the user's runtime directory), none of them squad data: running the daemon, and starting one
#: or clearing a dead one's files.
PROCESS_ENTRIES: frozenset[Name] = frozenset(
    {
        ("squads._daemon._lifecycle", "run_daemon"),
        ("squads._daemon_start", "ensure"),
        ("squads._daemon_start", "discard_stale"),
    }
)


def _dotted(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def _is_open(func: ast.AST) -> bool:
    """Whether *func* is ``open``: the builtin, or the method of a path, a module or any object."""
    return (isinstance(func, ast.Name) and func.id == "open") or (
        isinstance(func, ast.Attribute) and func.attr == "open"
    )


def _write_mode(node: ast.Call) -> bool:
    """Whether an ``open`` call, the builtin, ``io.open`` or a path's method, opens for writing; a
    mode that is not a literal counts as writing."""
    func = node.func
    method = isinstance(func, ast.Attribute) and _dotted(func) not in ("io.open", "builtins.open")
    index = 0 if method else 1
    modes = [*node.args[index : index + 1], *(k.value for k in node.keywords if k.arg == "mode")]
    if not modes:
        return False
    mode = modes[0]
    return not (isinstance(mode, ast.Constant) and set(str(mode.value)) <= {"r", "b", "t"})


def _spelled(dotted: str, aliases: dict[str, str]) -> str:
    """*dotted* with its first name replaced by what the module's imports bind it to."""
    root, dot, rest = dotted.partition(".")
    return f"{aliases.get(root, root)}{dot}{rest}"


def _direct_writes(body: ast.AST, aliases: dict[str, str]) -> list[str]:
    """The file-writing primitives *body* uses, by line; a called name is read through the
    module's imports, so ``from os import unlink`` is seen as ``os.unlink``."""
    found: list[str] = []
    for node in ast.walk(body):
        if isinstance(node, ast.Attribute) and node.attr in WRITING_METHODS:
            found.append(f"line {node.lineno}: .{node.attr}")
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = _spelled(_dotted(func) or "", aliases)
        if name.split(".")[0] in WRITING_MODULES:
            found.append(f"line {node.lineno}: {name}()")
        elif (
            isinstance(func, ast.Attribute) and func.attr in MOVING_METHODS and len(node.args) == 1
        ):
            found.append(f"line {node.lineno}: .{func.attr}()")
        elif name.startswith("os.") and name.removeprefix("os.") in OS_WRITERS:
            found.append(f"line {node.lineno}: {name}()")
        elif _is_open(func) and _write_mode(node):
            found.append(f"line {node.lineno}: {name or '.open'}() for writing")
    return found


@dataclass
class _Unit:
    """A top-level function or class, or a module's own top-level code."""

    module: str
    path: Path
    node: ast.AST
    writes: list[str] = field(default_factory=list[str])
    calls: set[Name] = field(default_factory=set[Name])
    imports: set[Name] = field(default_factory=set[Name])
    #: For a function, the names its return annotation reaches; for a class, its bases.
    types: set[Name] = field(default_factory=set[Name])


def _package(path: Path) -> str:
    name = module_name(path)
    return name if path.name == "__init__.py" else name.rpartition(".")[0]


def _aliases(tree: ast.Module, path: Path, modules: set[str]) -> dict[str, str]:
    """Each name bound by an import, to the dotted module or ``module.name`` it stands for."""
    package = _package(path)
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                found[a.asname or a.name.split(".")[0]] = (
                    a.name if a.asname else a.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = package.split(".")
                parts = parts[: len(parts) - (node.level - 1)]
                base = ".".join([*parts, node.module] if node.module else parts)
            for a in node.names:
                found[a.asname or a.name] = f"{base}.{a.name}"
    return found


def _resolve(dotted: str, aliases: dict[str, str], modules: set[str]) -> Name | None:
    """The ``(module, top-level name)`` a dotted reference reaches, or ``None``."""
    root, _, rest = dotted.partition(".")
    if root not in aliases:
        return None
    full = f"{aliases[root]}.{rest}" if rest else aliases[root]
    parts = full.split(".")
    for cut in range(len(parts) - 1, 0, -1):
        module = ".".join(parts[:cut])
        if module in modules:
            return module, parts[cut]
    return None


@dataclass(frozen=True)
class _Scope:
    """What a module's names stand for: its own top-level definitions and its imports."""

    module: str
    local: frozenset[str]
    aliases: dict[str, str]
    modules: frozenset[str]

    def target(self, dotted: str) -> Name | None:
        if dotted in self.local:
            return self.module, dotted
        return _resolve(dotted, self.aliases, set(self.modules))

    def targets(self, nodes: list[ast.expr]) -> set[Name]:
        found: set[Name] = set()
        for node in nodes:
            for sub in ast.walk(node):
                dotted = _dotted(sub) if isinstance(sub, ast.Name | ast.Attribute) else None
                if dotted is not None and (target := self.target(dotted)) is not None:
                    found.add(target)
        return found


def _typed(node: ast.AST) -> list[ast.expr]:
    """A function's return annotation, or a class's bases."""
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.returns:
        return [node.returns]
    if isinstance(node, ast.ClassDef):
        return list(node.bases)
    return []


def _module_units(path: Path, modules: frozenset[str]) -> Iterator[_Unit]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    definitions = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    defined = [n for n in tree.body if isinstance(n, definitions)]
    scope = _Scope(
        module_name(path),
        frozenset(n.name for n in defined),
        _aliases(tree, path, set(modules)),
        modules,
    )
    top = [n for n in tree.body if not isinstance(n, definitions)]
    nodes: list[tuple[str, ast.AST]] = [("<module>", ast.Module(body=top, type_ignores=[]))]
    nodes += [(n.name, n) for n in defined]
    for name, node in nodes:
        unit = _Unit(scope.module, path, node, writes=_direct_writes(node, scope.aliases))
        unit.types = scope.targets(_typed(node))
        unit.calls = scope.targets(
            [sub.func for sub in ast.walk(node) if isinstance(sub, ast.Call)]
        )
        if name == "<module>":
            for alias, full in scope.aliases.items():
                target = scope.target(alias)
                if target is not None and full == f"{target[0]}.{target[1]}":
                    unit.imports.add(target)
        yield unit


def _units(paths: list[Path]) -> Iterator[_Unit]:
    modules = frozenset(module_name(p) for p in paths)
    for path in paths:
        yield from _module_units(path, modules)


def _writers(units: list[_Unit]) -> set[Name]:
    """Every top-level name whose body writes, directly or through a call to another writer; a
    function returning a writing class, and a class a writing class derives from, write too."""
    writers = {(u.module, _unit_name(u)) for u in units if u.writes} - PROCESS_ENTRIES
    changed = True
    while changed:
        changed = False
        for u in units:
            key = (u.module, _unit_name(u))
            is_class = isinstance(u.node, ast.ClassDef)
            found = {key} if not is_class and u.types & writers else set[Name]()
            if u.calls & writers:
                found.add(key)
            if is_class and key in writers:
                found |= u.types
            new = found - writers - {GATED_ROUTE} - PROCESS_ENTRIES
            if new:
                writers |= new
                changed = True
    return writers


def _unit_name(unit: _Unit) -> str:
    return getattr(unit.node, "name", "<module>")


def _all_units() -> list[_Unit]:
    return list(_units(sorted(SRC.rglob("*.py"))))


def _offenders(units: list[_Unit]) -> dict[str, list[str]]:
    writers = _writers(units)
    offenders: dict[str, list[str]] = {}
    for u in units:
        if not any(u.path.is_relative_to(d) for d in DIRS):
            continue
        hits = list(u.writes)
        hits += [f"calls {m}.{n}" for m, n in sorted(u.calls & writers)]
        hits += [f"imports {m}.{n}" for m, n in sorted(u.imports & writers)]
        if hits:
            key = f"{u.path.relative_to(SRC).as_posix()}::{_unit_name(u)}"
            offenders[key] = hits
    return offenders


def test_the_scan_derives_the_known_writers() -> None:
    writers = _writers(_all_units())
    assert {
        ("squads._aio", "atomic_write_text"),
        ("squads._board._store", "post"),
        ("squads._memory._store", "add"),
        ("squads._index._reflog", "append_line"),
        ("squads._backends._managed_region", "inject"),
        ("squads._backends._base", "AgentBackend"),
        ("squads._backends._registry", "get_backend"),
    } <= writers


def test_no_command_or_screen_writes_a_file() -> None:
    offenders = _offenders(_all_units())
    assert not offenders, f"write through an operation instead: {offenders}"
