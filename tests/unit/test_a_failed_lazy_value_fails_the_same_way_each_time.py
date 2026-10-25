"""A ``Lazy`` whose build failed builds once and raises the same error on every later call,
with a traceback that does not grow."""

import pytest

from squads._errors import SquadsError
from squads._specload import Lazy


def _depth(error: BaseException) -> int:
    depth, tb = 0, error.__traceback__
    while tb is not None:
        depth, tb = depth + 1, tb.tb_next
    return depth


def test_a_failed_build_runs_once_and_keeps_one_traceback_depth() -> None:
    builds: list[int] = []

    def build() -> int:
        builds.append(1)
        raise SquadsError("broken")

    lazy = Lazy(build)
    depths = []
    for _ in range(4):
        with pytest.raises(SquadsError, match="broken") as raised:
            lazy()
        depths.append(_depth(raised.value))

    assert len(builds) == 1
    assert len(set(depths)) == 1


def test_a_successful_build_runs_once() -> None:
    builds: list[int] = []
    lazy = Lazy(lambda: builds.append(1) or len(builds))

    assert [lazy(), lazy()] == [1, 1]
    assert len(builds) == 1
