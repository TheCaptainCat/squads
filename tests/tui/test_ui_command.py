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

from squads._cli import app
from squads._services._service import Service
from squads._tui import _app as tui_app

pytestmark = pytest.mark.anyio


async def test_ui_reports_a_clean_error_outside_a_squad(tmp_path, monkeypatch, runner):
    monkeypatch.chdir(tmp_path)

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


async def test_ui_hands_the_resolved_service_to_the_app_and_calls_its_blocking_run(
    project, monkeypatch, runner
):
    received: list[Service] = []
    monkeypatch.setattr(tui_app.SquadsApp, "run", lambda self: received.append(self._svc))

    result = runner.invoke(app, ["ui"])

    assert result.exit_code == 0, result.output
    assert len(received) == 1
    assert received[0].paths.squad_dir == project.squad_dir


def test_cli_help_and_import_work_with_the_tui_extra_unimportable():
    script = (
        "import sys\n"
        "sys.modules['textual'] = None\n"
        "from squads._cli import app\n"
        "from typer.testing import CliRunner\n"
        "result = CliRunner().invoke(app, ['--help'])\n"
        "assert result.exit_code == 0, result.output\n"
    )
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
