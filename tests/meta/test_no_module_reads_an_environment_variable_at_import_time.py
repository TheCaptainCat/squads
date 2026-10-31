"""Repo gate: no module of `squads` reads an environment variable while it is imported. A daemon
imports its modules once, so a value read then is the daemon's own and never a request's."""

import ast
from pathlib import Path

_READERS = frozenset({"environ", "environb", "getenv", "getenvb"})


def _src() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "squads"


class _Scan(ast.NodeVisitor):
    """Finds an environment read in the code a module runs when it is imported: its body, its
    class bodies, and the decorators and defaults of its functions. A function body or a lambda
    runs later, and is left alone."""

    def __init__(self) -> None:
        self.hits: list[int] = []
        self._os = {"os"}
        self._bare = set[str]()

    def visit_Import(self, node: ast.Import) -> None:
        self._os.update(a.asname or a.name for a in node.names if a.name == "os")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "os":
            self._bare.update(a.asname or a.name for a in node.names if a.name in _READERS)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in _READERS and isinstance(node.value, ast.Name) and node.value.id in self._os:
            self.hits.append(node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and node.id in self._bare:
            self.hits.append(node.lineno)

    def _definition(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for expression in (
            *node.decorator_list,
            *node.args.defaults,
            *(d for d in node.args.kw_defaults if d is not None),
        ):
            self.visit(expression)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._definition(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._definition(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for default in (*node.args.defaults, *(d for d in node.args.kw_defaults if d is not None)):
            self.visit(default)


def _hits_in(source: str) -> list[int]:
    scan = _Scan()
    scan.visit(ast.parse(source))
    return scan.hits


def test_no_module_reads_an_environment_variable_at_import_time() -> None:
    found = [
        f"src/squads/{path.relative_to(_src()).as_posix()}:{line}"
        for path in sorted(_src().rglob("*.py"))
        for line in _hits_in(path.read_text(encoding="utf-8"))
    ]
    assert not found, "move the read into the code that needs it:\n" + "\n".join(found)


_READS = {
    "a module constant": "import os\nSWITCH = os.environ.get('X', '')\n",
    "an aliased os": "import os as o\nSWITCH = o.getenv('X')\n",
    "a bare name": "from os import environ\nSWITCH = environ['X']\n",
    "a class attribute": "import os\nclass C:\n    switch = os.environ.get('X')\n",
    "a default argument": "import os\ndef f(x=os.environ.get('X')):\n    return x\n",
    "a decorator": "import os\n@g(os.getenv('X'))\ndef f():\n    pass\n",
    "a conditional": "import os\nif True:\n    SWITCH = os.getenv('X')\n",
}

_DEFERRED = {
    "a function body": "import os\ndef f():\n    return os.environ.get('X')\n",
    "a method body": "import os\nclass C:\n    def m(self):\n        return os.getenv('X')\n",
    "a lambda": "import os\nread = lambda: os.environ['X']\n",
    "a parameter named environ": "def f(environ):\n    return environ.get('X')\n",
}


def test_every_shape_of_an_import_time_read_is_found() -> None:
    for name, source in _READS.items():
        assert len(_hits_in(source)) == 1, name


def test_a_read_deferred_to_a_call_is_not_one() -> None:
    for name, source in _DEFERRED.items():
        assert _hits_in(source) == [], name
