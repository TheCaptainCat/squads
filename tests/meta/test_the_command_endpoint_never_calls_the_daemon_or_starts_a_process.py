"""Repo gate: the modules that serve the command endpoint import neither the CLI's client of the
daemon, an HTTP client nor `subprocess`, so a served command can only run on the daemon's own
operations."""

import ast
from pathlib import Path

#: The modules that implement the endpoint, relative to `src/squads`.
ENDPOINT_MODULES = ("_daemon/_app.py", "_daemon/_commands.py", "_daemon/_proxies.py")

FORBIDDEN = ("squads._cli._remote", "http.client", "subprocess")


def _src() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "squads"


def _imported(source: str) -> list[tuple[str, int]]:
    """Every module a source imports, wherever the statement sits, with its line; a name in
    `from x import y` counts as `x` and as `x.y`."""
    found: list[tuple[str, int]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append((node.module, node.lineno))
            found.extend((f"{node.module}.{alias.name}", node.lineno) for alias in node.names)
    return found


def _breaches(source: str) -> list[int]:
    return [
        line
        for name, line in _imported(source)
        if any(name == bad or name.startswith(f"{bad}.") for bad in FORBIDDEN)
    ]


def test_the_endpoint_modules_import_no_client_of_the_daemon_and_no_subprocess() -> None:
    found = [
        f"src/squads/{module}:{line}"
        for module in ENDPOINT_MODULES
        for line in _breaches((_src() / module).read_text(encoding="utf-8"))
    ]
    assert not found, "the endpoint must run on the daemon's own API:\n" + "\n".join(found)


def test_every_endpoint_module_exists() -> None:
    assert all((_src() / module).is_file() for module in ENDPOINT_MODULES)


_PLANTED = {
    "the CLI's client": "from squads._cli import _remote\n",
    "the CLI's client by path": "import squads._cli._remote\n",
    "a name from the client": "from squads._cli._remote import build_http_api\n",
    "an http client": "import http.client\n",
    "a name from an http client": "from http.client import HTTPConnection\n",
    "subprocess": "import subprocess\n",
    "a name from subprocess": "from subprocess import run\n",
    "a local import": "def f():\n    import subprocess\n",
}


def test_every_planted_import_is_found() -> None:
    for name, source in _PLANTED.items():
        assert _breaches(source), name


def test_other_imports_are_not_breaches() -> None:
    assert _breaches("import http.server\nfrom squads._cli import _common\nimport sys\n") == []
