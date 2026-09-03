import os

# Pin a deterministic, non-terminal rendering environment BEFORE importing the CLI: both Rich
# consoles this suite captures latch their terminal/color decision from the environment at import
# time -- squads._cli._common builds a module-level Console(), and typer.rich_utils computes the
# module constants that shape every `--help` render.  Under a plain CliRunner both write plain
# text; when either is talked into "this is a terminal" they emit ANSI, and Rich's styling splits
# tokens mid-word (an option renders as `ESC[36m-ESC[0mESC[36m-unlink`), so a literal
# `"--unlink" in result.output` finds nothing.  Every knob that can force that lives here, once,
# so no individual test has to tolerate styling:
#   * FORCE_COLOR / CLICOLOR_FORCE / PY_COLORS -- exported by some CI runners and by the Claude
#     Code agent harness; Rich and typer both read them.
#   * TTY_COMPATIBLE=0 -- Rich's own "not a terminal" declaration, checked ahead of FORCE_COLOR.
#   * _TYPER_FORCE_DISABLE_TERMINAL -- typer's escape hatch for its help console, which otherwise
#     forces a terminal whenever GITHUB_ACTIONS is set (i.e. on every GitHub Actions runner).
#   * COLUMNS / TERMINAL_WIDTH -- width, the same class of ambient input as color.
# These are exported (not just set on this process) so the tests that run `sq` as a subprocess
# inherit the same rendering environment.  An autouse fixture re-applies them per test, and the
# typer constants are re-pinned below in case typer.rich_utils was imported before this conftest.
for _color_var in ("FORCE_COLOR", "CLICOLOR_FORCE", "PY_COLORS", "TERMINAL_WIDTH", "LINES"):
    os.environ.pop(_color_var, None)
os.environ["TTY_COMPATIBLE"] = "0"
os.environ["_TYPER_FORCE_DISABLE_TERMINAL"] = "1"
os.environ["COLUMNS"] = "80"

import functools  # noqa: E402
from collections.abc import Callable  # noqa: E402
from dataclasses import replace  # noqa: E402
from datetime import UTC, datetime  # noqa: E402
from typing import Any  # noqa: E402

import pytest  # noqa: E402
import rich.console  # noqa: E402
import typer.main  # noqa: E402
import typer.rich_utils  # noqa: E402
import typer.testing  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

# The COLUMNS pin above is only half a pin: `Console.__init__` latches its width as
# `COLUMNS - legacy_windows`, and `legacy_windows` is true whenever Rich cannot read console
# features off the handle it writes to -- which is precisely a captured pipe on Windows, i.e.
# every CliRunner capture and every subprocess capture on that runner.  COLUMNS=80 therefore
# rendered at 79 there, and any assertion on a line long enough to reflow failed on that one
# platform: the message wrapped a word earlier and the literal the test looked for straddled the
# inserted newline, with nothing about the platform anywhere in the assertion.
#
# Pin the detection function rather than a console attribute: the subtraction happens once, at
# construction, so patching a live console's `legacy_windows` changes nothing.  Patching the
# function covers every console built after this line -- the two module-level ones in
# `squads._cli._common`, typer's per-render help console, and any a test builds itself.
rich.console.detect_legacy_windows = lambda: False

# typer latches `FORCE_TERMINAL` into a module constant when typer.rich_utils is first imported,
# so the env pin above only lands if this conftest ran first.  Re-assert it on the module itself
# (read per call by `_get_rich_console`) so help output stays plain whatever the import order was.
# Width is deliberately NOT pinned here: it stays driven by COLUMNS, which is a per-render lookup
# a test can legitimately vary (see tests/cli/test_help_text_width_is_pinned.py).
typer.rich_utils.FORCE_TERMINAL = False

from squads import _aio  # noqa: E402
from squads._cli import app  # noqa: E402
from squads._context import RequestContext, bind_context, get_context  # noqa: E402
from squads._rendering._engine import (  # noqa: E402
    _env_cache,
    set_active_squad_dir,
)
from squads._services import _service as service  # noqa: E402

# Memoise the Typer→Click conversion: `CliRunner.invoke()` rebuilds the whole command tree on
# every call (~90ms here, ~2000 invocations), a test-harness cost a real `sq` run pays once.
# Keyed on the completion env var, which typer reads at build time to shape --show-completion.
_original_get_command = typer.main.get_command


@functools.cache
def _build_command(app_obj, _shell_detection_flag):  # 2nd arg is a cache key, not read here
    return _original_get_command(app_obj)


def _cached_get_command(app_obj):
    return _build_command(app_obj, os.environ.get("_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION"))


typer.main.get_command = _cached_get_command
# typer.testing binds its own alias at import, so patching typer.main alone misses invoke().
_typer_testing: Any = typer.testing
_typer_testing._get_command = _cached_get_command


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
    from squads._cli import _CustomTypeGroup
    from squads._cli._create import _CustomCreateGroup

    _CustomTypeGroup._custom_cmd_cache.clear()
    _CustomCreateGroup._custom_cmd_cache.clear()


#: The closed set of ambient values a real ``sq`` process establishes fresh (both start unset/
#: empty) that a fixture building a ``Service`` in-process (``project``/``svc``, via
#: ``service.init`` → ``ServiceCore.__init__`` → ``set_active_squad_dir``) can pre-seed as a
#: side effect of its own setup, letting a CLI test pass whether or not the code under test
#: established that state itself. Reset at the ``invoke`` boundary below, unconditionally, and
#: also used as the post-test backstop (``_reset_engine_state``) so neither value ever leaks
#: between tests either.
#:
#: Exhaustiveness — not just that these two reset correctly — is enforced by
#: ``tests/meta/test_ambient_render_state_reset_is_exhaustive.py``, which statically re-derives
#: this same set from ``src/squads`` and fails if a third ambient value is added there without
#: being listed (and reset) here.
_AMBIENT_RESET_TARGETS: dict[str, frozenset[str]] = {
    "src/squads/_rendering/_engine.py": frozenset({"_active_squad_dir", "_env_cache"}),
}


def _reset_ambient_render_state() -> None:
    """Reset every value named in ``_AMBIENT_RESET_TARGETS`` to what a fresh process starts
    with: ``_active_squad_dir`` unset, ``_env_cache`` empty."""
    set_active_squad_dir(None)
    _env_cache.clear()


@pytest.fixture(autouse=True)
def _reset_engine_state():  # pyright: ignore[reportUnusedFunction]  # autouse: pytest calls it
    """Reset rendering engine module-state between tests.

    ServiceCore.__init__ calls set_active_squad_dir() and never restores it, so a test that
    constructs a service leaves that squad dir active for later tests that call bare render()
    without setting it.  Clearing the ContextVar and evicting the cache after each test prevents
    order-dependent coupling.  The intra-test counterpart — resetting before each ``invoke()``
    call rather than only after the test — lives on the ``invoke`` fixture below.
    """
    yield
    _reset_ambient_render_state()


@pytest.fixture(autouse=True)
def _neutralize_forced_color(monkeypatch):  # pyright: ignore[reportUnusedFunction]  # autouse
    """Strip color-forcing env vars so terminal detection falls back to isatty().

    The suite asserts piped/plain output (CliRunner captures stdout, so isatty() is False →
    Rich emits no ANSI).  But an ambient FORCE_COLOR/CLICOLOR_FORCE/PY_COLORS (set by some CI
    runners and by the Claude Code agent harness) makes Rich force color into that captured
    output, breaking every plain-output and --json assertion.  Neutralise them per-test so the
    suite is deterministic regardless of the environment it runs in.

    Per-test backstop for the module-level pin at the top of this file — see there for what each
    variable does and why a styled render breaks plain substring assertions.
    """
    for var in ("FORCE_COLOR", "CLICOLOR_FORCE", "PY_COLORS", "TERMINAL_WIDTH"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("TTY_COMPATIBLE", "0")
    monkeypatch.setenv("_TYPER_FORCE_DISABLE_TERMINAL", "1")
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

    Resets ``_AMBIENT_RESET_TARGETS`` immediately before every call (not once, at fixture
    setup): ``_aio.to_thread`` copies the *calling* ``contextvars.Context`` into its worker, so
    whatever the ``project``/``svc`` fixtures left ambient — via their own in-process
    ``service.init(...)`` — would otherwise leak into ``invoke()`` and silently substitute for
    whatever the CLI code path under test was supposed to establish itself. A real ``sq``
    process starts each invocation with neither value set, so this makes ``invoke()`` do the
    same — for the first call in a test and for every later one, since some tests scaffold or
    edit an override *between* two ``invoke()`` calls and only a per-call reset covers that.
    """
    import functools

    def _invoke(args: list[str], **kw: Any) -> Any:
        _reset_ambient_render_state()
        return _aio.to_thread(functools.partial(runner.invoke, app, args, **kw))

    return _invoke
