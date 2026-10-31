"""Process-wide pytest setup shared by every test root: the rendering pins, the memoised Typer
command tree, `--run-slow` with its skip hook, and the opt-in shuffled collection order."""

import functools
import os
import random
from typing import Any

import pytest
import rich.console
import typer.main
import typer.rich_utils
import typer.testing

# Rich and typer latch their terminal, colour and width decisions from the environment at import
# time, so the pins land here, before any test module imports the CLI. Exported (not only set on
# this process) so a test that runs `sq` as a subprocess inherits the same rendering environment.
for _var in ("FORCE_COLOR", "CLICOLOR_FORCE", "PY_COLORS", "TERMINAL_WIDTH", "LINES"):
    os.environ.pop(_var, None)
os.environ["TTY_COMPATIBLE"] = "0"
os.environ["_TYPER_FORCE_DISABLE_TERMINAL"] = "1"
os.environ["COLUMNS"] = "80"

# `Console.__init__` subtracts one column when it believes it is a legacy Windows console, which a
# captured pipe on Windows always looks like; pin the detection so every platform renders at 80.
rich.console.detect_legacy_windows = lambda: False

# typer latches FORCE_TERMINAL into a module constant on first import; re-assert it on the module.
typer.rich_utils.FORCE_TERMINAL = False

# `CliRunner.invoke()` rebuilds the whole command tree on every call; a real `sq` run pays that
# once. Keyed on the completion env var, which typer reads at build time.
_original_get_command = typer.main.get_command


@functools.cache
def _build_command(
    app_obj: Any, _shell_detection_flag: str | None
) -> Any:  # 2nd arg is a cache key, not read here
    return _original_get_command(app_obj)


def _cached_get_command(app_obj: Any) -> Any:
    return _build_command(app_obj, os.environ.get("_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION"))


typer.main.get_command = _cached_get_command
_cached_get_command.cache_clear = _build_command.cache_clear  # type: ignore[attr-defined]
# typer.testing binds its own alias at import, so patching typer.main alone misses invoke().
_typer_testing: Any = typer.testing
_typer_testing._get_command = _cached_get_command


@pytest.fixture
def fresh_command_tree():
    """Drop the memoised command tree around a test, so it builds its own and leaves none that
    an override squad shaped."""
    _build_command.cache_clear()
    yield
    _build_command.cache_clear()


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--squad",
        action="store",
        default=os.environ.get("SQUADS_TEST_SQUAD", "bundled"),
        choices=("bundled", "override"),
        help="the squad the tests/cli surface suite runs on: the bundled one, or the override "
        "test squad that shares none of its vocabulary (default: $SQUADS_TEST_SQUAD, else bundled)",
    )
    parser.addoption(
        "--api-mode",
        action="store",
        default=os.environ.get("SQUADS_TEST_MODE", "local"),
        choices=("local", "remote", "routes"),
        help="how the tests/cli surface suite runs its commands: in this process (local), through "
        "the command endpoint of the daemon's application served on a thread (remote), or in this "
        "process with the operations sent to that application over HTTP (routes); it combines "
        "with --squad (default: $SQUADS_TEST_MODE, else local)",
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="run tests marked @pytest.mark.slow (the wall-clock-bound scale tests), "
        "skipped by default",
    )
    parser.addoption(
        "--shuffle-seed",
        action="store",
        default=None,
        type=int,
        help="reorder the collected tests with this seed, to prove they do not depend on order",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Publish the selected squad to the modules that read it at import time."""
    os.environ["SQUADS_TEST_SQUAD"] = str(config.getoption("--squad"))
    os.environ["SQUADS_TEST_MODE"] = str(config.getoption("--api-mode"))
    # No test starts a daemon unless it says so; one that exercises the daemon sets it itself.
    os.environ["SQUADS_DAEMON"] = "off"


def _skip_other_squad(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip a case about the other squad's own spelling; its marker states why."""
    selected = config.getoption("--squad")
    for item in items:
        for squad in ("bundled", "override"):
            marker = item.get_closest_marker(f"{squad}_only")
            if marker is None:
                continue
            if not marker.args or not isinstance(marker.args[0], str) or not marker.args[0]:
                pytest.fail(f"{item.nodeid}: {squad}_only needs a reason", pytrace=False)
            if squad != selected:
                item.add_marker(pytest.mark.skip(reason=f"{squad} squad only: {marker.args[0]}"))


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip slow tests unless `--run-slow`, and shuffle by seed when `--shuffle-seed` is given
    (the same seed gives every xdist worker the same order)."""
    _skip_other_squad(config, items)
    seed = config.getoption("--shuffle-seed")
    if seed is not None:
        random.Random(seed).shuffle(items)
    if config.getoption("--run-slow"):
        return
    skip_slow = pytest.mark.skip(reason="slow: use --run-slow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
