import os

# Neutralise color-forcing env vars BEFORE importing the CLI: squads._cli._common builds a
# module-level rich Console() at import time, which latches terminal/color detection from the
# environment then.  Some CI runners and the Claude Code agent harness export FORCE_COLOR, which
# makes Rich emit ANSI into CliRunner-captured output and breaks every plain-output / --json
# assertion.  Stripping these here (before the import below, and session-wide) keeps the suite
# deterministic regardless of where it runs.  An autouse fixture re-strips per test as a backstop.
for _color_var in ("FORCE_COLOR", "CLICOLOR_FORCE", "PY_COLORS"):
    os.environ.pop(_color_var, None)

from collections.abc import Callable  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from squads import _actor as actor  # noqa: E402
from squads import _aio  # noqa: E402
from squads import _clock as clock  # noqa: E402
from squads._cli import app  # noqa: E402
from squads._rendering._engine import (  # noqa: E402
    _env_cache,  # pyright: ignore[reportPrivateUsage]
    set_active_squad_dir,
)
from squads._services import _service as service  # noqa: E402


@pytest.fixture
def anyio_backend():
    """Pin the anyio test backend to asyncio (trio not needed for this project)."""
    return "asyncio"


@pytest.fixture(autouse=True)
def _reset_clock_override():  # pyright: ignore[reportUnusedFunction]  # autouse: pytest calls it
    """Ensure a forged `--at` timestamp from one test never leaks into the next."""
    yield
    clock.set_now(None)


@pytest.fixture(autouse=True)
def _reset_actor():  # pyright: ignore[reportUnusedFunction]  # autouse: pytest calls it
    """Ensure the ambient actor never leaks between tests (mirrors the clock reset)."""
    yield
    actor.set_actor(None)


@pytest.fixture(autouse=True)
def _reset_engine_state():  # pyright: ignore[reportUnusedFunction]  # autouse: pytest calls it
    """Reset rendering engine module-state between tests (REV-000093 F1).

    ServiceCore.__init__ calls set_active_squad_dir() and never restores it, so a test that
    constructs a service leaves that squad dir active for later tests that call bare render()
    without setting it.  Clearing the ContextVar and evicting the cache after each test prevents
    order-dependent coupling.
    """
    yield
    set_active_squad_dir(None)
    _env_cache.clear()


@pytest.fixture(autouse=True)
def _neutralize_forced_color(monkeypatch):  # pyright: ignore[reportUnusedFunction]  # autouse
    """Strip color-forcing env vars so terminal detection falls back to isatty().

    The suite asserts piped/plain output (CliRunner captures stdout, so isatty() is False →
    Rich emits no ANSI).  But an ambient FORCE_COLOR/CLICOLOR_FORCE/PY_COLORS (set by some CI
    runners and by the Claude Code agent harness) makes Rich force color into that captured
    output, breaking every plain-output and --json assertion.  Neutralise them per-test so the
    suite is deterministic regardless of the environment it runs in.
    """
    for var in ("FORCE_COLOR", "CLICOLOR_FORCE", "PY_COLORS"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def frozen_time(monkeypatch):
    fixed = datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(clock, "now", lambda: fixed)
    return fixed


@pytest.fixture
async def project(tmp_path, monkeypatch, frozen_time):
    """A freshly-initialized squad in a temp dir; cwd is set to it."""
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal")
    return result.paths


@pytest.fixture
def svc(project):
    return service.Service(project)


@pytest.fixture
def runner():
    return CliRunner()


def run_in_thread(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a sync function from inside an async test on a worker thread.

    Use this when a sync function (e.g. one that internally calls anyio.run())
    cannot be called directly from an async test (which already has a running loop).

    Usage in an async test::

        result = await run_in_thread(some_sync_fn, arg1, kwarg=val)
    """
    import functools

    return _aio.to_thread(functools.partial(fn, *args, **kwargs))


@pytest.fixture
def invoke(runner: CliRunner):
    """Async-safe runner.invoke wrapper for tests that mix ``await`` and CLI invocations.

    From inside an async test, ``runner.invoke(app, [...])`` fails because the CLI
    calls ``anyio.run()`` which raises ``RuntimeError: Already running asyncio in
    this thread``.  Wrapping it in a worker thread avoids that.

    Usage::

        async def test_something(invoke):
            r = await invoke(["some", "cmd"])
            assert r.exit_code == 0
    """
    import functools

    def _invoke(args: list[str], **kw: Any) -> Any:
        return _aio.to_thread(functools.partial(runner.invoke, app, args, **kw))

    return _invoke
