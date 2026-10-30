"""Repo gate: no module of the daemon's served path imports a client of the daemon, a socket or
subprocess module, or names a call that starts a process, however the name is spelled (an import
alias, a `from` import, a dotted use). It reads the modules' own statements: a name reached
through `getattr` or `importlib`, or through a module outside the served path, is not seen."""

import ast
from pathlib import Path

#: The daemon's modules that own its process and sockets, and so are not the served path.
PROCESS_MODULES = frozenset({"_lifecycle.py", "_listeners.py"})

FORBIDDEN_MODULES = (
    "squads._cli._remote",
    "squads._api._client",
    "squads._daemon_link",
    "squads._daemon_start",
    "http.client",
    "urllib",
    "socket",
    "subprocess",
    "multiprocessing",
    "asyncio.subprocess",
    "pty",
)

#: Callables that start a process or replace it, by qualified name prefix.
FORBIDDEN_CALLS = (
    "os.system",
    "os.popen",
    "os.posix_spawn",
    "os.spawn",
    "os.exec",
    "os.fork",
    "asyncio.create_subprocess_",
    "pty.spawn",
    "pty.fork",
)

#: Event-loop methods that start a process, whatever the loop is called.
FORBIDDEN_METHODS = frozenset({"subprocess_exec", "subprocess_shell"})


def _src() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "squads"


def endpoint_modules() -> list[Path]:
    """Every module of the served path: the daemon's, but the two that own its process."""
    return sorted(p for p in (_src() / "_daemon").glob("*.py") if p.name not in PROCESS_MODULES)


def _bindings(tree: ast.AST) -> dict[str, str]:
    """The qualified name each imported local name stands for, wherever the import sits."""
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound[alias.asname or alias.name.split(".")[0]] = (
                    alias.name if alias.asname else alias.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                bound[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return bound


def _imported(tree: ast.AST) -> list[tuple[str, int]]:
    """Every module or name imported with its line; a name in `from x import y` counts as `x`
    and as `x.y`."""
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.module, node.lineno))
            found.extend((f"{node.module}.{alias.name}", node.lineno) for alias in node.names)
    return found


def _dotted(node: ast.expr, bound: dict[str, str]) -> str | None:
    """The qualified name an expression spells (`o.system` with `import os as o` is `os.system`)."""
    if isinstance(node, ast.Name):
        return bound.get(node.id)
    if isinstance(node, ast.Attribute):
        owner = _dotted(node.value, bound)
        return None if owner is None else f"{owner}.{node.attr}"
    return None


def _named(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name.startswith(prefix) for prefix in prefixes)


def breaches(source: str) -> list[int]:
    """The lines that import a forbidden module or name, or call a forbidden callable."""
    tree = ast.parse(source)
    bound = _bindings(tree)
    lines = {
        line
        for name, line in _imported(tree)
        if any(name == bad or name.startswith(f"{bad}.") for bad in FORBIDDEN_MODULES)
        or _named(name, FORBIDDEN_CALLS)
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = _dotted(node.func, bound)
        method = node.func.attr if isinstance(node.func, ast.Attribute) else None
        if (target is not None and _named(target, FORBIDDEN_CALLS)) or method in FORBIDDEN_METHODS:
            lines.add(node.lineno)
    return sorted(lines)


def test_the_served_path_imports_no_client_of_the_daemon_and_starts_no_process() -> None:
    found = [
        f"{path.relative_to(_src().parent.parent).as_posix()}:{line}"
        for path in endpoint_modules()
        for line in breaches(path.read_text(encoding="utf-8"))
    ]
    assert not found, "a served command must run on the daemon's own API:\n" + "\n".join(found)


def test_the_served_path_is_found_by_listing_the_daemon_not_by_name() -> None:
    names = {p.name for p in endpoint_modules()}

    assert {"_app.py", "_commands.py", "_proxies.py"} <= names
    assert not names & PROCESS_MODULES


_PLANTED = {
    "the CLI's client": "from squads._cli import _remote\n",
    "the CLI's client by path": "import squads._cli._remote\n",
    "the HTTP client of the API": "from squads._api._client import HttpApi\n",
    "a module of it": "from squads._api import _client\n",
    "the daemon's link": "from squads._daemon_link import connection\n",
    "an http client": "import http.client\n",
    "a name from an http client": "from http.client import HTTPConnection\n",
    "urllib": "import urllib.request\n",
    "a socket": "import socket\n",
    "subprocess": "import subprocess\n",
    "a name from subprocess": "from subprocess import run\n",
    "multiprocessing": "import multiprocessing\n",
    "an asyncio subprocess": "import asyncio.subprocess\n",
    "pty": "import pty\n",
    "a local import": "def f():\n    import subprocess\n",
    "os.system": "import os\nos.system('x')\n",
    "os.popen": "import os\nos.popen('x')\n",
    "os.posix_spawn": "import os\nos.posix_spawn('x', [], {})\n",
    "os.execv": "import os\nos.execv('x', [])\n",
    "a from import of os.system": "from os import system\nsystem('x')\n",
    "an aliased os": "import os as o\no.system('x')\n",
    "an aliased from import": "from os import system as run\nrun('x')\n",
    "an asyncio subprocess call": "import asyncio\nasyncio.create_subprocess_exec('x')\n",
    "a from import of it": "from asyncio import create_subprocess_exec\n",
    "a loop method": "def f(loop):\n    return loop.subprocess_exec(None, 'x')\n",
    "a shell method": "async def f(loop):\n    await loop.subprocess_shell(None, 'x')\n",
    "pty.spawn": "import pty\npty.spawn('x')\n",
    "pty.spawn from import": "from pty import spawn\nspawn('x')\n",
}


def test_every_planted_shape_is_found() -> None:
    for name, source in _PLANTED.items():
        assert breaches(source), name


def test_the_call_alone_is_found_where_the_import_is_not_a_breach() -> None:
    assert breaches("import os as o\nx = o.popen\n") == []
    assert breaches("import os as o\no.popen('x')\n") == [2]


def test_other_imports_and_calls_are_not_breaches() -> None:
    source = "import http.server\nimport os\nfrom squads._cli import _common\nos.getpid()\n"

    assert breaches(source) == []
