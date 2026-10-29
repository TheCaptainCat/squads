"""Repo-hygiene gate: under ``src/squads`` the process working directory is read in exactly one
place, and never changed."""

import ast
import shutil
from pathlib import Path

#: ``(file relative to the repo root, enclosing function)`` for the sanctioned read.
_ALLOWED: frozenset[tuple[str, str]] = frozenset(
    {
        ("src/squads/_paths.py", "process_dir"),
    }
)

#: Names in ``os`` that read or change the process directory.
_OS_FUNCTIONS = frozenset({"getcwd", "getcwdb", "chdir", "fchdir"})
#: Names in ``os`` that list the process directory when called with no argument.
_OS_LISTERS = frozenset({"listdir", "scandir"})
_PATH_CLASSES = frozenset({"Path", "PosixPath", "WindowsPath"})
#: Names in ``os.path`` that resolve a relative path against the process directory.
_OS_PATH_FUNCTIONS = frozenset({"abspath", "realpath"})
_MAKE_ABSOLUTE = frozenset({"resolve", "absolute"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


class _Scan(ast.NodeVisitor):
    """Finds the process-directory shapes in one module, resolving how names were imported."""

    def __init__(self) -> None:
        self.hits: list[tuple[str, int]] = []
        self._function = "<module>"
        self._os = {"os"}
        self._os_path = set[str]()
        self._path = set(_PATH_CLASSES)
        self._bare_os = set[str]()
        self._bare_os_path = set[str]()
        self._getenv = set[str]()
        self._environ = set[str]()
        self._bare_listers = set[str]()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "os":
                self._os.add(alias.asname or "os")
            elif alias.name == "os.path" and alias.asname:
                self._os_path.add(alias.asname)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            bound = alias.asname or alias.name
            if node.module == "os":
                if alias.name in _OS_FUNCTIONS:
                    self._bare_os.add(bound)
                elif alias.name == "path":
                    self._os_path.add(bound)
                elif alias.name == "getenv":
                    self._getenv.add(bound)
                elif alias.name == "environ":
                    self._environ.add(bound)
                elif alias.name in _OS_LISTERS:
                    self._bare_listers.add(bound)
            elif node.module == "os.path" and alias.name in _OS_PATH_FUNCTIONS:
                self._bare_os_path.add(bound)
            elif node.module == "pathlib" and alias.name in _PATH_CLASSES:
                self._path.add(bound)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        outer, self._function = self._function, node.name
        self.generic_visit(node)
        self._function = outer

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def _hit(self, node: ast.AST) -> None:
        self.hits.append((self._function, node.lineno))  # pyright: ignore[reportAttributeAccessIssue]

    def _is_os(self, node: ast.expr) -> bool:
        return isinstance(node, ast.Name) and node.id in self._os

    def _is_os_path(self, node: ast.expr) -> bool:
        return (isinstance(node, ast.Name) and node.id in self._os_path) or (
            isinstance(node, ast.Attribute) and node.attr == "path" and self._is_os(node.value)
        )

    def _is_path_class(self, node: ast.expr) -> bool:
        return (isinstance(node, ast.Name) and node.id in self._path) or (
            isinstance(node, ast.Attribute) and node.attr in _PATH_CLASSES
        )

    def _is_relative_path_literal(self, node: ast.expr) -> bool:
        """``Path()`` or ``Path`` of a relative string literal (``""``, ``"."``, ``"x"``)."""
        if not (isinstance(node, ast.Call) and self._is_path_class(node.func)):
            return False
        if not node.args:
            return True
        first = node.args[0]
        return (
            isinstance(first, ast.Constant)
            and isinstance(first.value, str)
            and not first.value.startswith("/")
        )

    @staticmethod
    def _is_pwd(node: ast.expr | None) -> bool:
        return isinstance(node, ast.Constant) and node.value == "PWD"

    def _is_environ(self, node: ast.expr) -> bool:
        return (isinstance(node, ast.Name) and node.id in self._environ) or (
            isinstance(node, ast.Attribute) and node.attr == "environ" and self._is_os(node.value)
        )

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self._is_environ(node.value) and self._is_pwd(node.slice):
            self._hit(node)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """``Path.cwd`` and ``os.getcwd`` etc. are flagged as references, so binding one to a
        name and calling it later is seen as well as the direct call."""
        if (self._is_path_class(node.value) and node.attr == "cwd") or (
            self._is_os(node.value) and node.attr in _OS_FUNCTIONS
        ):
            self._hit(node)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and (
            node.id in self._bare_os or node.id in self._bare_os_path
        ):
            self._hit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Name):
            if (func.id in self._getenv and self._first_is_pwd(node)) or (
                func.id in self._bare_listers and not node.args
            ):
                self._hit(node)
        elif isinstance(func, ast.Attribute):
            owner = func.value
            if (
                (self._is_os_path(owner) and func.attr in _OS_PATH_FUNCTIONS)
                or (func.attr in _MAKE_ABSOLUTE and self._is_relative_path_literal(owner))
                or (self._is_os(owner) and func.attr in _OS_LISTERS and not node.args)
                or (self._is_os(owner) and func.attr == "getenv" and self._first_is_pwd(node))
                or (self._is_environ(owner) and func.attr == "get" and self._first_is_pwd(node))
            ):
                self._hit(node)
        self.generic_visit(node)

    def _first_is_pwd(self, node: ast.Call) -> bool:
        return bool(node.args) and self._is_pwd(node.args[0])


def _hits_in(source: str) -> list[tuple[str, int]]:
    scan = _Scan()
    scan.visit(ast.parse(source))
    return scan.hits


def _scan(root: Path, allowed: frozenset[tuple[str, str]] = _ALLOWED) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for path in sorted((root / "src" / "squads").rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        try:
            hits = _hits_in(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # fmt: skip
            continue
        found.extend((rel, line) for function, line in hits if (rel, function) not in allowed)
    return found


def test_the_process_directory_is_read_only_where_it_is_sanctioned() -> None:
    hits = _scan(_repo_root())
    detail = "\n".join(f"  {path}:{line}" for path, line in hits)
    assert not hits, (
        "a read or change of the process directory outside the sanctioned site — resolve "
        f"against the request context's client_cwd instead:\n{detail}"
    )


def test_the_sanctioned_site_is_still_present() -> None:
    """An allowlist entry that matches nothing would let a renamed helper go unguarded."""
    found = {
        (path.relative_to(_repo_root()).as_posix(), function)
        for path in (_repo_root() / "src" / "squads").rglob("*.py")
        for function, _ in _hits_in(path.read_text(encoding="utf-8"))
    }
    assert found >= _ALLOWED


#: Each shape the scan must see, as the body of a function.
_SHAPES = {
    "Path.cwd": "from pathlib import Path\ndef f():\n    return Path.cwd()\n",
    "an aliased Path": "from pathlib import Path as P\ndef f():\n    return P.cwd()\n",
    "pathlib.Path.cwd": "import pathlib\ndef f():\n    return pathlib.Path.cwd()\n",
    "os.getcwd": "import os\ndef f():\n    return os.getcwd()\n",
    "os.getcwdb": "import os\ndef f():\n    return os.getcwdb()\n",
    "os.chdir": "import os\ndef f():\n    os.chdir('/')\n",
    "an aliased os": "import os as o\ndef f():\n    return o.getcwd()\n",
    "from os import getcwd": "from os import getcwd\ndef f():\n    return getcwd()\n",
    "from os import getcwd as": "from os import getcwd as g\ndef f():\n    return g()\n",
    "from os import chdir": "from os import chdir\ndef f():\n    chdir('/')\n",
    "os.path.abspath": "import os\ndef f():\n    return os.path.abspath('x')\n",
    "os.path.realpath": "import os\ndef f():\n    return os.path.realpath('x')\n",
    "from os import path": "from os import path\ndef f():\n    return path.abspath('x')\n",
    "from os.path import abspath": "from os.path import abspath\ndef f():\n    abspath('x')\n",
    'Path(".").resolve()': 'from pathlib import Path\ndef f():\n    return Path(".").resolve()\n',
    'Path("").absolute()': 'from pathlib import Path\ndef f():\n    Path("").absolute()\n',
    "Path().resolve()": "from pathlib import Path\ndef f():\n    return Path().resolve()\n",
    'os.environ["PWD"]': 'import os\ndef f():\n    return os.environ["PWD"]\n',
    'os.environ.get("PWD")': 'import os\ndef f():\n    return os.environ.get("PWD")\n',
    'os.getenv("PWD")': 'import os\ndef f():\n    return os.getenv("PWD")\n',
    "from os import getenv": 'from os import getenv\ndef f():\n    getenv("PWD")\n',
    "a relative literal": 'from pathlib import Path\ndef f():\n    Path("notes.md").resolve()\n',
    "PosixPath.cwd": "from pathlib import PosixPath\ndef f():\n    PosixPath.cwd()\n",
    "pathlib.WindowsPath.cwd": "import pathlib\ndef f():\n    pathlib.WindowsPath.cwd()\n",
    "a bound Path.cwd": "from pathlib import Path\ndef f():\n    g = Path.cwd\n    return g\n",
    "a bound os.getcwd": "import os\ndef f():\n    g = os.getcwd\n    return g\n",
    "from os import environ": 'from os import environ\ndef f():\n    return environ["PWD"]\n',
    "from os import environ get": 'from os import environ\ndef f():\n    environ.get("PWD")\n',
    "os.listdir()": "import os\ndef f():\n    return os.listdir()\n",
    "os.scandir()": "import os\ndef f():\n    return os.scandir()\n",
    "from os import listdir": "from os import listdir\ndef f():\n    return listdir()\n",
    "inside a method": "from pathlib import Path\nclass A:\n    def m(self):\n        Path.cwd()\n",
}

#: Shapes that look similar and read nothing about the process directory.
_NOT_READS = {
    "a resolved argument": "from pathlib import Path\ndef f(p):\n    return Path(p).resolve()\n",
    "an absolute literal": 'from pathlib import Path\ndef f():\n    Path("/x").resolve()\n',
    "a listing with an argument": "import os\ndef f(p):\n    return os.listdir(p)\n",
    "a relative literal not made absolute": "from pathlib import Path\nPath('x').name\n",
    "another variable": 'import os\ndef f():\n    return os.environ["HOME"]\n',
    "another variable by get": 'import os\ndef f():\n    return os.environ.get("PATH")\n',
    "an unrelated getcwd": "def f(o):\n    return o.getcwd()\n",
    "an unrelated abspath": "def f(o):\n    return o.path.abspath('x')\n",
}


def test_the_scan_catches_every_shape(tmp_path: Path) -> None:
    for name, source in _SHAPES.items():
        assert len(_hits_in(source)) == 1, name


def test_the_scan_ignores_lookalikes() -> None:
    for name, source in _NOT_READS.items():
        assert _hits_in(source) == [], name


def test_every_shape_goes_red_when_injected_into_a_copy_of_the_real_tree(tmp_path: Path) -> None:
    """The real tree is clean, so a shape that the scan misses would pass silently there."""
    shutil.copytree(
        _repo_root() / "src" / "squads",
        tmp_path / "src" / "squads",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    assert _scan(tmp_path) == []
    target = tmp_path / "src" / "squads" / "_aio.py"
    original = target.read_text(encoding="utf-8")
    for name, source in _SHAPES.items():
        target.write_text(original + "\n\n" + source, encoding="utf-8")
        assert len(_scan(tmp_path)) == 1, name
    target.write_text(original, encoding="utf-8")


def test_the_scan_allows_only_the_named_function_in_the_named_file(tmp_path: Path) -> None:
    planted = tmp_path / "src" / "squads" / "_paths.py"
    planted.parent.mkdir(parents=True)
    planted.write_text(
        "from pathlib import Path\n"
        "def process_dir():\n    return Path.cwd()\n\ndef other():\n    return Path.cwd()\n",
        encoding="utf-8",
    )
    assert _scan(tmp_path) == [("src/squads/_paths.py", 6)]
