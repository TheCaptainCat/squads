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
from dataclasses import replace  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from squads import _aio  # noqa: E402
from squads._cli import app  # noqa: E402
from squads._context import RequestContext, bind_context, get_context  # noqa: E402
from squads._rendering._engine import (  # noqa: E402
    _env_cache,  # pyright: ignore[reportPrivateUsage]
    set_active_squad_dir,
)
from squads._services import _service as service  # noqa: E402


def pytest_addoption(parser):
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="run tests marked @pytest.mark.slow (the wall-clock-bound scale tests), "
        "skipped by default",
    )


def pytest_collection_modifyitems(config, items):
    """Skip @pytest.mark.slow tests unless --run-slow is given (collection-time, so it composes
    with both -n auto and -n0)."""
    if config.getoption("--run-slow"):
        return
    skip_slow = pytest.mark.skip(reason="slow: use --run-slow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture
def anyio_backend():
    """Pin the anyio test backend to asyncio (trio not needed for this project)."""
    return "asyncio"


@pytest.fixture(autouse=True)
def _reset_context():  # pyright: ignore[reportUnusedFunction]  # autouse: pytest calls it
    """Ensure the ambient `RequestContext` (forged time, actor, session lineage, active
    spec/dir, client cwd) never leaks between tests. One fixture for the whole object —
    now that every ambient value lives in this one `RequestContext`, resetting it wholesale
    is resetting all of them at once, replacing what used to be several per-field leak-guards.

    Reset at both ends: before, so a prior test's leftover state never reaches this test's own
    fixture setup (e.g. `project`, which calls `service.init()` directly and so never
    re-seeds the session itself the way a real CLI invocation's root callback would); after,
    as the usual backstop.

    Also clears the two lazy-dispatch custom-command caches (`_CustomTypeGroup._custom_cmd_cache`
    in `_cli/__init__.py`, `_CustomCreateGroup._custom_cmd_cache` in `_cli/_create.py`) — both are
    process-global `ClassVar` dicts keyed by canonical type name that a real `sq <custom-type>` /
    `sq create <custom-type>` invocation populates permanently for the process. A prior test's
    custom type (e.g. "incident") otherwise stays cached and short-circuits a later test that
    monkey-patches the build function to assert on error propagation.
    """
    bind_context(RequestContext())
    yield
    bind_context(RequestContext())
    from squads._cli import _CustomTypeGroup  # pyright: ignore[reportPrivateUsage]
    from squads._cli._create import _CustomCreateGroup  # pyright: ignore[reportPrivateUsage]

    _CustomTypeGroup._custom_cmd_cache.clear()  # pyright: ignore[reportPrivateUsage]
    _CustomCreateGroup._custom_cmd_cache.clear()  # pyright: ignore[reportPrivateUsage]


@pytest.fixture(autouse=True)
def _reset_engine_state():  # pyright: ignore[reportUnusedFunction]  # autouse: pytest calls it
    """Reset rendering engine module-state between tests.

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
    # Pin console width too, so Rich/Typer help text wraps identically regardless of the
    # invoking terminal's/worker's inherited COLUMNS (the width analogue of the color pin above).
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.delenv("LINES", raising=False)


@pytest.fixture
def frozen_time():
    """Freeze `clock.now()` for this test by rebinding the ambient context's clock field
    (rather than monkeypatching `clock.now` itself), so the frozen time is visible through
    the same seam a real `--at` invocation uses and propagates across `invoke`/`run_in_thread`
    the same way. Restores the prior context after."""
    fixed = datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC)
    prior = get_context()
    bind_context(replace(prior, clock_override=fixed))
    yield fixed
    bind_context(prior)


@pytest.fixture
async def project(tmp_path, monkeypatch, frozen_time):
    """A freshly-initialized squad in a temp dir; cwd is set to it.

    Skill seeding is intentionally skipped here so existing tests are not
    disrupted by the global-counter shift that seeding causes.  Tests that specifically
    exercise skill seeding use a dedicated ``project_with_skills`` fixture or call
    ``svc.seed_bundled_skills()`` directly.
    """
    monkeypatch.chdir(tmp_path)
    result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
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
