"""Shared test fixtures.

The rendering pins, `--run-slow` and the shuffled order live in the repository root conftest.py.
The leak guards are autouse; the squad fixtures copy a template built once per module.
"""

import functools
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from squads import _aio
from squads._cli import app
from squads._context import RequestContext, bind_context, get_context
from squads._paths import SquadPaths
from squads._rendering._engine import _env_cache
from squads._workflow import bundled_spec
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import WorkflowSpec
from tests import _cli_surface as cli_surface
from tests import _write_guard
from tests._helpers import make_service
from tests._squads import (
    FROZEN,
    Builder,
    build_squad,
    init_minimal,
    init_seeded,
    paths_of,
    restore,
)

#: The ambient values a real `sq` process establishes fresh that an in-process fixture could
#: pre-seed as a side effect, letting a CLI test pass without the code under test setting them.
#: The renderer takes its squad directory as an argument, so nothing ambient remains.
_AMBIENT_RESET_TARGETS: dict[str, frozenset[str]] = {}


@pytest.fixture
def anyio_backend():
    """Pin the anyio test backend to asyncio."""
    return "asyncio"


@pytest.fixture(autouse=True)
def _reset_context():  # pyright: ignore[reportUnusedFunction]  # autouse: pytest calls it
    """Reset the ambient `RequestContext` and the custom-command caches around every test."""
    bind_context(RequestContext())
    yield
    bind_context(RequestContext())
    from squads._cli import _CustomTypeGroup
    from squads._cli._create import _CustomCreateGroup

    _CustomTypeGroup._custom_cmd_cache.clear()
    _CustomCreateGroup._custom_cmd_cache.clear()


@pytest.fixture(autouse=True)
def _reset_engine_state():  # pyright: ignore[reportUnusedFunction]  # autouse: pytest calls it
    """Evict the compiled-template cache after each test so an override never outlives it."""
    yield
    _env_cache.clear()


@pytest.fixture(autouse=True)
def _neutralize_forced_color(monkeypatch):  # pyright: ignore[reportUnusedFunction]  # autouse
    """Re-apply the plain-output environment per test, whatever the runner exports."""
    for var in ("FORCE_COLOR", "CLICOLOR_FORCE", "PY_COLORS", "TERMINAL_WIDTH"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("TTY_COMPATIBLE", "0")
    monkeypatch.setenv("_TYPER_FORCE_DISABLE_TERMINAL", "1")
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.delenv("LINES", raising=False)


@pytest.fixture(autouse=True)
def _run_outside_this_repositorys_squad(  # pyright: ignore[reportUnusedFunction]  # autouse
    tmp_path_factory, monkeypatch
):
    """Start every test in an empty directory, never inside this repository's own squad."""
    monkeypatch.chdir(tmp_path_factory.mktemp("cwd"))


@pytest.fixture(autouse=True)
def write_ledger(monkeypatch):
    """Fail at teardown when a committed unit wrote one item file twice or wrote one after the
    index commit."""
    ledger = _write_guard.install(monkeypatch)
    yield ledger
    violations = ledger.take_violations()
    if violations:
        pytest.fail("item-file write rule broken: " + "; ".join(violations), pytrace=False)


@pytest.fixture
def frozen_time():
    """Freeze `clock.now()` through the ambient context, the seam a real `--at` run uses."""
    prior = get_context()
    bind_context(replace(prior, clock_override=FROZEN))
    yield FROZEN
    bind_context(prior)


@pytest.fixture(scope="module")
def _templates() -> dict[str, Path]:  # pyright: ignore[reportUnusedFunction]  # a fixture
    """The squads built so far in this module, by key."""
    return {}


@pytest.fixture
def copy_squad(
    _templates, tmp_path, tmp_path_factory, monkeypatch, frozen_time
) -> Callable[..., SquadPaths]:
    """Return a function that gives this test its own copy of a squad built once per module.

    `copy_squad(key, builder)` builds `builder` into a module-wide template the first time `key`
    is asked for, copies it into the test's directory, changes into it and returns its paths.
    """

    def _copy(key: str, builder: Builder) -> SquadPaths:
        if key not in _templates:
            _templates[key] = build_squad(tmp_path_factory.mktemp(f"template-{key}"), builder)
        restore(_templates[key], tmp_path)
        monkeypatch.chdir(tmp_path)
        return paths_of(tmp_path)

    return _copy


@pytest.fixture
def project(copy_squad) -> SquadPaths:
    """A fresh unseeded `minimal` squad in the test's directory, which is the cwd."""
    return copy_squad("minimal", init_minimal)


@pytest.fixture
def seeded_project(copy_squad) -> SquadPaths:
    """A fresh `minimal` squad with the bundled skills seeded, as `sq init` leaves it."""
    return copy_squad("seeded", init_seeded)


@pytest.fixture
def serve():
    """Serve a squad's daemon application on a thread, as `serve(paths)`; every one is stopped at
    the end of the test."""
    from contextlib import ExitStack

    from tests._daemon_harness import serve_squad

    with ExitStack() as stack:
        yield lambda paths, **kw: stack.enter_context(serve_squad(paths, **kw))


@pytest.fixture
def daemon_runtime(monkeypatch):
    """A runtime directory of the test's own, short enough for a socket path, that the endpoint
    resolution picks up in place of the user's."""
    import sys
    import tempfile

    variable = {"win32": "LOCALAPPDATA", "darwin": "TMPDIR"}.get(sys.platform, "XDG_RUNTIME_DIR")
    with tempfile.TemporaryDirectory(prefix="sqd") as base:
        monkeypatch.setenv(variable, base)
        yield Path(base)


@pytest.fixture
def run_daemon(daemon_runtime):
    """Run a squad's daemon, lifecycle and listeners included, as `run_daemon(paths)`; every one is
    stopped at the end of the test."""
    from contextlib import ExitStack

    from tests._daemon_process import running_daemon

    with ExitStack() as stack:
        yield lambda paths: stack.enter_context(running_daemon(paths))


@pytest.fixture
def svc(project):
    """A `Service` over the `project` squad."""
    return make_service(project)


@pytest.fixture
def runner():
    """A `CliRunner`."""
    return CliRunner()


def _declared_pairs(node: pytest.Item) -> set[cli_surface.Pair]:
    """The pairs the `covers` markers of *node* declare; a marker that is not made of string
    literals fails the test."""
    declared: set[cli_surface.Pair] = set()
    for marker in node.iter_markers("covers"):
        if not marker.args or marker.kwargs or not all(isinstance(a, str) for a in marker.args):
            pytest.fail(
                f"covers{marker.args!r} must name a key and string parameters", pytrace=False
            )
        declared |= cli_surface.declared_pairs(tuple(marker.args))
    return declared


@pytest.fixture(autouse=True)
def _covers_markers_need_invoke(request: pytest.FixtureRequest):  # pyright: ignore[reportUnusedFunction]  # autouse
    """Fail a test that declares `covers` without the `invoke` fixture that checks the claim."""
    if request.node.get_closest_marker("covers") and "invoke" not in request.fixturenames:
        pytest.fail(
            "a test that declares `covers` must call the CLI through `invoke`", pytrace=False
        )


def _squad_spec() -> WorkflowSpec:
    """The workflow spec of the squad in the working directory, the bundled one outside a squad."""
    try:
        return load_workflow_spec(paths_of(Path.cwd()).squad_dir)
    except Exception:  # pylint: disable=broad-except  # no squad here, or its override is broken
        return bundled_spec()


def _reached(
    args: list[str], spec: WorkflowSpec, refusal: str | None = None
) -> set[cli_surface.Pair]:
    """The pairs *args* reach on the tree, read with *spec* as the active spec as a run binds it."""
    prior = get_context()
    bind_context(replace(prior, active_spec=spec))
    try:
        known = None if spec == bundled_spec() else cli_surface.bundled_known()
        return cli_surface.reached_pairs(args, spec, refusal, known=known)
    finally:
        bind_context(prior)


@pytest.fixture
def invoke(request: pytest.FixtureRequest, runner: CliRunner):
    """`runner.invoke` on a worker thread with a fresh template cache, so an async test can call
    the CLI.

    Each call records the pairs it reaches (`reached_pairs`, given a failed call's output too);
    at teardown the test fails when a pair its `covers` markers declare was not reached.
    """
    reached: set[cli_surface.Pair] = set()

    async def _invoke(args: list[str], **kw: Any) -> Any:
        spec = _squad_spec()
        reached.update(_reached(args, spec))
        _env_cache.clear()
        result = await _aio.to_thread(functools.partial(runner.invoke, app, args, **kw))
        if result.exit_code != 0:
            reached.update(_reached(args, spec, result.output))
        return result

    yield _invoke
    missing = _declared_pairs(request.node) - reached
    if missing:
        listed = ", ".join(
            f"sq {k} {p}" if p else f"sq {k}"
            for k, p in sorted(missing, key=lambda m: (m[0], m[1] or ""))
        )
        pytest.fail(f"covers declares pairs no call reached: {listed}", pytrace=False)
