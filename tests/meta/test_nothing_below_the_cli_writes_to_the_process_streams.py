"""Repo-hygiene gate: outside the CLI, the terminal UI, ``squads.__main__``, ``_spans``, the
daemon's stream proxies and the shim, no module writes to the process's stdout or stderr. A notice
the engine raises is recorded on the request, so a daemon never prints a user's line and a remote
call's output matches a local one's."""

import ast
import shutil
from pathlib import Path

#: Modules (relative to ``src/squads``) allowed to write to the streams, as a path prefix.
#: ``_daemon/_lifecycle.py`` writes its readiness line to the pipe it inherited, no process stream.
#: ``_daemon/_proxies.py`` replaces the streams and ``_shim.py`` writes a served command's output.
_EXEMPT = (
    "_cli/",
    "_tui/",
    "__main__.py",
    "_spans.py",
    "_daemon/_lifecycle.py",
    "_daemon/_proxies.py",
    "_shim.py",
)

_STREAMS = frozenset({"stdout", "stderr", "__stdout__", "__stderr__"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


class _Scan(ast.NodeVisitor):
    """Finds a use of a standard stream, or a ``print`` to one, in one module."""

    def __init__(self) -> None:
        self.hits: list[int] = []
        self._sys = {"sys"}
        self._os = {"os"}
        self._bare = set[str]()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "sys":
                self._sys.add(alias.asname or "sys")
            elif alias.name == "os":
                self._os.add(alias.asname or "os")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module == "sys":
            self._bare.update(a.asname or a.name for a in node.names if a.name in _STREAMS)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if (
            node.attr in _STREAMS
            and isinstance(node.value, ast.Name)
            and node.value.id in self._sys
        ):
            self.hits.append(node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and node.id in self._bare:
            self.hits.append(node.lineno)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "write"
            and isinstance(func.value, ast.Name)
            and func.value.id in self._os
        ) or (
            (isinstance(func, ast.Name) and func.id == "Console")
            or (isinstance(func, ast.Attribute) and func.attr == "Console")
        ):
            self.hits.append(node.lineno)
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "print"
            and not any(k.arg == "file" for k in node.keywords)
        ):
            self.hits.append(node.lineno)
        self.generic_visit(node)


def _hits_in(source: str) -> list[int]:
    scan = _Scan()
    scan.visit(ast.parse(source))
    return scan.hits


def _scan(root: Path) -> list[tuple[str, int]]:
    base = root / "src" / "squads"
    found: list[tuple[str, int]] = []
    for path in sorted(base.rglob("*.py")):
        rel = path.relative_to(base).as_posix()
        if rel.startswith(_EXEMPT):
            continue
        found.extend((rel, line) for line in _hits_in(path.read_text(encoding="utf-8")))
    return found


def test_no_module_below_the_cli_writes_to_the_process_streams() -> None:
    hits = _scan(_repo_root())
    detail = "\n".join(f"  src/squads/{path}:{line}" for path, line in hits)
    assert not hits, (
        "a write to stdout or stderr below the CLI; record a notice with "
        f"squads._context.record_notice instead:\n{detail}"
    )


#: Each shape the scan must see.
_SHAPES = {
    "print": "def f():\n    print('x')\n",
    "print to stderr": "import sys\ndef f():\n    print('x', file=sys.stderr)\n",
    "stdout write": "import sys\ndef f():\n    sys.stdout.write('x')\n",
    "an aliased sys": "import sys as s\ndef f():\n    s.stderr.write('x')\n",
    "a bare stream": "from sys import stderr\ndef f():\n    stderr.write('x')\n",
    "a stream handed on": "import sys\ndef f(g):\n    g(sys.stdout)\n",
    "os.write": "import os\ndef f():\n    os.write(2, b'x')\n",
    "a rich console": "from rich.console import Console\ndef f():\n    Console(stderr=True)\n",
    "a qualified console": "import rich.console\ndef f():\n    rich.console.Console()\n",
    "the original stream": "import sys\ndef f():\n    sys.__stderr__.write('x')\n",
}

_NOT_WRITES = {
    "a print to a buffer": "def f(buf):\n    print('x', file=buf)\n",
    "another sys name": "import sys\ndef f():\n    return sys.argv\n",
    "os.write to a descriptor": "import os\ndef f(fd):\n    os.fsync(fd)\n",
    "an unrelated stderr": "def f(o):\n    return o.stderr\n",
}


def test_the_scan_catches_every_shape() -> None:
    for name, source in _SHAPES.items():
        assert len(_hits_in(source)) == 1, name


def test_the_scan_ignores_lookalikes() -> None:
    for name, source in _NOT_WRITES.items():
        assert _hits_in(source) == [], name


def test_every_shape_goes_red_when_injected_below_the_cli(tmp_path: Path) -> None:
    """The real tree is clean, so a shape the scan misses would pass silently there."""
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
    exempt = tmp_path / "src" / "squads" / "_cli" / "_common.py"
    exempt.write_text(exempt.read_text(encoding="utf-8") + "\nprint('x')\n", encoding="utf-8")
    assert _scan(tmp_path) == []


def test_a_sibling_of_the_exempt_daemon_modules_is_not_exempt(tmp_path: Path) -> None:
    """The proxies are exempt by name, not the daemon's other modules."""
    shutil.copytree(
        _repo_root() / "src" / "squads",
        tmp_path / "src" / "squads",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    daemon = tmp_path / "src" / "squads" / "_daemon"
    for name, exempt in (("_proxies.py", True), ("_commands.py", False), ("_app.py", False)):
        target = daemon / name
        original = target.read_text(encoding="utf-8")
        target.write_text(original + "\n\nprint('x')\n", encoding="utf-8")
        assert (_scan(tmp_path) == []) is exempt, name
        target.write_text(original, encoding="utf-8")
