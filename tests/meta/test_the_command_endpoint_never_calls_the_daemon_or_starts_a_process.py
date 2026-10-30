"""Repo gate: the modules that serve a command import no client of the daemon and neither start a
process nor open a connection, so a served command can only run on the daemon's own operations."""

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
)

#: Calls that start a process or replace it, as `module.name` or any `module.name*`.
FORBIDDEN_CALLS = {
    "os": ("system", "popen", "posix_spawn", "spawn", "exec", "fork"),
    "asyncio": ("create_subprocess_exec", "create_subprocess_shell"),
}


def _src() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "squads"


def endpoint_modules() -> list[Path]:
    """Every module of the served path: the daemon's, but the two that own its process."""
    return sorted(p for p in (_src() / "_daemon").glob("*.py") if p.name not in PROCESS_MODULES)


def _imported(tree: ast.AST) -> list[tuple[str, int]]:
    """Every module imported, wherever the statement sits, with its line; a name in
    `from x import y` counts as `x` and as `x.y`."""
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.module, node.lineno))
            found.extend((f"{node.module}.{alias.name}", node.lineno) for alias in node.names)
    return found


def _called(tree: ast.AST) -> list[int]:
    """The lines of calls to `os.system(...)` and its kind."""
    lines: list[int] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        owner = node.func.value
        if isinstance(owner, ast.Name) and any(
            node.func.attr.startswith(name) for name in FORBIDDEN_CALLS.get(owner.id, ())
        ):
            lines.append(node.lineno)
    return lines


def breaches(source: str) -> list[int]:
    tree = ast.parse(source)
    imports = [
        line
        for name, line in _imported(tree)
        if any(name == bad or name.startswith(f"{bad}.") for bad in FORBIDDEN_MODULES)
    ]
    return sorted({*imports, *_called(tree)})


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
    "a local import": "def f():\n    import subprocess\n",
    "os.system": "import os\nos.system('x')\n",
    "os.popen": "import os\nos.popen('x')\n",
    "os.posix_spawn": "import os\nos.posix_spawn('x', [], {})\n",
    "os.execv": "import os\nos.execv('x', [])\n",
    "an asyncio subprocess call": "import asyncio\nasyncio.create_subprocess_exec('x')\n",
}


def test_every_planted_shape_is_found() -> None:
    for name, source in _PLANTED.items():
        assert breaches(source), name


def test_other_imports_and_calls_are_not_breaches() -> None:
    source = "import http.server\nimport os\nfrom squads._cli import _common\nos.getpid()\n"

    assert breaches(source) == []
