"""Repo-hygiene gate: the modules a remote command runs on (the root callback, every command
module, `HttpApi`, the renderers) load none of the service layer, the index store, the template
engine, the daemon's server or the file lock, and no markdown renderer before a body is shown."""

import json
import subprocess
import sys

#: Imported in a fresh interpreter, as a remote `sq` imports them.
_IMPORTS = (
    "import squads._cli, squads._cli._remote, squads._cli._main, squads._cli._items, "
    "squads._api._client, squads._daemon_link, squads._daemon_start"
)

#: A module that must not be loaded, as an exact name or a package prefix.
_FORBIDDEN = (
    "squads._services",
    "squads._daemon",
    "squads._tui",
    "jinja2",
    "yaml",
    "anyio",
    "filelock",
    "starlette",
    "uvicorn",
    "h11",
    "click",
    "rich.markdown",
    "textual",
)

#: The index modules a client may load: the reflog's operation vocabulary is plain data.
_INDEX_ALLOWED = ("squads._index", "squads._index._reflog")


def _loaded() -> list[str]:
    probe = f"{_IMPORTS}\nimport sys, json\nprint(json.dumps(sorted(sys.modules)))"
    done = subprocess.run(
        [sys.executable, "-I", "-c", probe], capture_output=True, text=True, check=True
    )
    return json.loads(done.stdout)


def _breaches(loaded: list[str]) -> list[str]:
    found = [
        name
        for name in loaded
        for banned in _FORBIDDEN
        if name == banned or name.startswith(banned + ".")
    ]
    found += [
        name for name in loaded if name.startswith("squads._index") and name not in _INDEX_ALLOWED
    ]
    return sorted(set(found))


def test_the_remote_client_loads_none_of_the_server_side() -> None:
    assert _breaches(_loaded()) == []


def test_the_scan_names_what_it_finds() -> None:
    sample = ["squads._cli", "jinja2.environment", "squads._index._store", "squads._index._reflog"]
    assert _breaches(sample) == ["jinja2.environment", "squads._index._store"]
