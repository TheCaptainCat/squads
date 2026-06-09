from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from squads import _clock as clock
from squads._services import _service as service


@pytest.fixture(autouse=True)
def _reset_clock_override():  # pyright: ignore[reportUnusedFunction]  # autouse: pytest calls it
    """Ensure a forged `--at` timestamp from one test never leaks into the next."""
    yield
    clock.set_now(None)


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
