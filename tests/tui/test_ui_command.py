"""`sq ui` command wiring: squad resolution, the missing-`tui`-extra guard, and handing off
to the Textual app without nesting an event loop.
"""

import builtins
import subprocess
import sys
from collections.abc import Mapping, Sequence
from types import ModuleType

import pytest

pytest.importorskip("textual")

from squads import _paths
from squads._cli import app
from squads._services._service import Service
from squads._tui import _app as tui_app

pytestmark = pytest.mark.anyio


async def test_ui_reports_a_clean_error_outside_a_squad(tmp_path, monkeypatch, runner):
    monkeypatch.chdir(tmp_path)
    # `.squads.toml` resolution walks all the way up to the filesystem root, so relying on
    # ``tmp_path`` alone only proves "outside a squad" if nothing above it happens to carry a
    # config — true on a clean machine, but not guaranteed (a stray config anywhere above the
    # pytest temp root would make this resolve to a real squad instead). Cut the walk-up off
    # at the source so the test pins the command's own behaviour, not the ambient filesystem.
    monkeypatch.setattr(_paths, "find_config", lambda start=None: None)

    result = runner.invoke(app, ["ui"])

    assert result.exit_code == 1
    assert "error:" in result.output
    assert "Traceback" not in result.output


async def test_ui_reports_a_clean_error_when_the_tui_extra_is_missing(project, monkeypatch, runner):
    # Evict cached squads._tui* modules so re-importing them re-triggers `import textual`.
    real_import = builtins.__import__

    def _no_textual(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "textual" or name.startswith("textual."):
            raise ModuleNotFoundError(f"No module named {name!r}")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _no_textual)
    for name in list(sys.modules):
        if name.startswith("squads._tui"):
            monkeypatch.delitem(sys.modules, name, raising=False)

    result = runner.invoke(app, ["ui"])

    assert result.exit_code == 1
    assert "error:" in result.output
    assert "pip install squads[tui]" in result.output
    assert "Traceback" not in result.output


async def test_ui_does_not_mask_a_nested_first_party_module_not_found_error(
    project, monkeypatch, runner
):
    real_import = builtins.__import__

    def _broken_first_party_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> ModuleType:
        if name == "squads._tui._app":
            raise ModuleNotFoundError("No module named 'squads._tui._nonexistent'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _broken_first_party_import)
    for name in list(sys.modules):
        if name.startswith("squads._tui"):
            monkeypatch.delitem(sys.modules, name, raising=False)

    result = runner.invoke(app, ["ui"])

    assert "pip install squads[tui]" not in result.output
    assert isinstance(result.exception, ModuleNotFoundError)
    assert "squads._tui._nonexistent" in str(result.exception)


async def test_ui_hands_the_resolved_service_to_the_app_and_calls_its_blocking_run(
    project, monkeypatch, runner
):
    received: list[Service] = []
    monkeypatch.setattr(tui_app.SquadsApp, "run", lambda self: received.append(self._svc))

    result = runner.invoke(app, ["ui"])

    assert result.exit_code == 0, result.output
    assert len(received) == 1
    assert received[0].paths.squad_dir == project.squad_dir


async def test_ui_opens_no_read_scope_and_pins_no_service_memo(project, monkeypatch, runner):
    """``sq ui`` is a sync command that never passes through ``common.command``, so it must
    keep its always-fresh behaviour exactly: no read scope opened, and — now that
    ``get_service`` memoizes on the same root-context marker the scope uses — no ``Service``
    pinned for the session either. Both are gated on the same marker, so both are absent here.
    """
    import squads._cli._common as common
    from squads._index._store import _read_scope

    observed: dict[str, set[object] | bool | None] = {"meta_keys": None, "read_scope_bound": None}

    def _fake_run(self):
        root = common._click_root_context()
        observed["meta_keys"] = set(root.meta.keys()) if root is not None else None
        observed["read_scope_bound"] = _read_scope.get() is not None

    monkeypatch.setattr(tui_app.SquadsApp, "run", _fake_run)

    result = runner.invoke(app, ["ui"])
    assert result.exit_code == 0, result.output

    assert observed["read_scope_bound"] is False, "sq ui must never open a read scope"
    raw_meta_keys = observed["meta_keys"]
    meta_keys: set[object] = raw_meta_keys if isinstance(raw_meta_keys, set) else set()
    assert common._READ_SCOPE_META_KEY not in meta_keys
    assert common._SERVICE_META_KEY not in meta_keys
    assert common._BYPASS_SERVICE_META_KEY not in meta_keys


def test_cli_help_and_import_work_with_the_tui_extra_unimportable():
    script = (
        "import sys\n"
        "sys.modules['textual'] = None\n"
        "from squads._cli import app\n"
        "from typer.testing import CliRunner\n"
        "result = CliRunner().invoke(app, ['--help'])\n"
        "assert result.exit_code == 0, result.output\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, encoding="utf-8"
    )
    assert proc.returncode == 0, proc.stderr
