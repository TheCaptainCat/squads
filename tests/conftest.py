from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from typer.testing import CliRunner

from squads import _actor as actor
from squads import _aio
from squads import _clock as clock
from squads._cli import app
from squads._rendering._engine import (
    _env_cache,  # pyright: ignore[reportPrivateUsage]
    set_active_squad_dir,
)
from squads._services import _service as service


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
