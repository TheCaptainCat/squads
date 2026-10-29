"""The renderers under `_cli/_render/` and the terminal UI under `_tui/` display only what a DTO
carries: none of them imports the workflow spec, the path resolver, the configuration model or the
service layer, nor a CLI module that does (`_cli/_common.py` and every module still pending on the
service-import guard), at any position. Imports are read as absolute module names, relative ones
and literal `importlib.import_module` calls included."""

from tests._import_scan import SRC, imports_of, names_any
from tests.meta.test_the_cli_imports_the_service_layer_only_in_the_local_api_factory import (
    PENDING,
)

#: The directories whose modules display DTOs.
RENDER_DIRS = (SRC / "_cli" / "_render", SRC / "_tui")

#: Modules a renderer must not import, nor any submodule of them.
FORBIDDEN = (
    "squads._workflow",
    "squads._paths",
    "squads._models._config",
    "squads._services",
    "squads._cli._calls",
    *(f"squads._cli.{name.removesuffix('.py')}" for name in sorted(PENDING)),
)


def test_no_renderer_imports_the_vocabulary_or_the_configuration() -> None:
    found = {
        path.relative_to(SRC).as_posix(): hits
        for path in sorted(p for d in RENDER_DIRS for p in d.rglob("*.py"))
        if (
            hits := [(i.line, i.module) for i in imports_of(path) if names_any(i.module, FORBIDDEN)]
        )
    }
    assert not found, f"renderers read only DTOs; these import {FORBIDDEN}: {found}"
