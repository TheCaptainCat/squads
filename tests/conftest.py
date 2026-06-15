from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from squads import _actor as actor
from squads import _clock as clock
from squads._rendering._engine import (
    _env_cache,  # pyright: ignore[reportPrivateUsage]
    set_active_squad_dir,
)
from squads._services import _service as service


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
def project(tmp_path, monkeypatch, frozen_time):
    """A freshly-initialized squad in a temp dir; cwd is set to it."""
    monkeypatch.chdir(tmp_path)
    result = service.init(root=tmp_path, roles_spec="minimal")
    return result.paths


@pytest.fixture
def svc(project):
    return service.Service(project)


@pytest.fixture
def runner():
    return CliRunner()
