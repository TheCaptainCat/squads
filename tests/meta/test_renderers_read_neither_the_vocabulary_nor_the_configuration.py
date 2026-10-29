"""The renderers under `_cli/_render/` and the terminal UI under `_tui/` import neither the workflow
spec, the path resolver, the configuration model, the service layer nor the CLI module that reaches
them (`_cli/_common.py`). The terminal UI is also held through every module it loads, outside
`TYPE_CHECKING` blocks and with package `__init__` files, which must reach none of those nor
`squads._cli`. Relative imports and literal `importlib.import_module` calls count."""

from pathlib import Path

from tests._import_scan import SRC, imports_of, module_name, names_any

RENDER_DIR = SRC / "_cli" / "_render"
TUI_DIR = SRC / "_tui"

#: Modules a renderer must not import, nor any submodule of them.
FORBIDDEN = (
    "squads._workflow",
    "squads._paths",
    "squads._models._config",
    "squads._services",
    "squads._cli._calls",
    "squads._cli._common",
)

#: Modules the terminal UI must not load, directly or through another module.
TUI_FORBIDDEN = (*FORBIDDEN, "squads._cli")


def test_no_renderer_imports_the_vocabulary_or_the_configuration() -> None:
    found = {
        path.relative_to(SRC).as_posix(): hits
        for path in sorted(p for d in (RENDER_DIR, TUI_DIR) for p in d.rglob("*.py"))
        if (
            hits := [(i.line, i.module) for i in imports_of(path) if names_any(i.module, FORBIDDEN)]
        )
    }
    assert not found, f"renderers read only DTOs; these import {FORBIDDEN}: {found}"


def _source(name: str) -> Path | None:
    """The file of module *name* under `squads`, or None when it names no module (an attribute
    of one, or a module outside the package)."""
    if name != "squads" and not name.startswith("squads."):
        return None
    base = SRC.parent.joinpath(*name.split("."))
    for path in (base.with_suffix(".py"), base / "__init__.py"):
        if path.is_file():
            return path
    return None


def _with_packages(name: str) -> list[str]:
    """*name* and every package above it, whose `__init__` runs when it is imported."""
    parts = name.split(".")
    return [".".join(parts[:i]) for i in range(1, len(parts) + 1)]


def _loaded_by(start: Path) -> dict[str, str | None]:
    """Every module importing *start* loads, each with the module that imported it."""
    first = module_name(start)
    seen: dict[str, str | None] = dict.fromkeys(_with_packages(first))
    queue = [first]
    while queue:
        current = queue.pop()
        path = _source(current)
        if path is None:
            continue
        for imported in imports_of(path, typing=False):
            for name in _with_packages(imported.module):
                if name not in seen and _source(name) is not None:
                    seen[name] = current
                    queue.append(name)
    return seen


def _chain(seen: dict[str, str | None], name: str) -> str:
    steps = [name]
    while (parent := seen[steps[-1]]) is not None:
        steps.append(parent)
    return " <- ".join(steps)


def test_the_terminal_ui_loads_neither_the_vocabulary_nor_the_cli() -> None:
    found: dict[str, list[str]] = {}
    for path in sorted(TUI_DIR.rglob("*.py")):
        seen = _loaded_by(path)
        hits = [_chain(seen, name) for name in sorted(seen) if names_any(name, TUI_FORBIDDEN)]
        if hits:
            found[path.relative_to(SRC).as_posix()] = hits
    assert not found, f"the terminal UI reads only DTOs; these load {TUI_FORBIDDEN}: {found}"
