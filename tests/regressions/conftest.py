"""Squad fixtures the regression modules share."""

import pytest

from squads._paths import SquadPaths
from tests._populated import init_populated
from tests._readable import init_readable


@pytest.fixture
def populated_project(copy_squad) -> SquadPaths:
    """A copy of the populated squad as the working directory."""
    return copy_squad("populated", init_populated)


@pytest.fixture
def populated(populated_project: SquadPaths) -> SquadPaths:
    """The populated squad under the short name some modules use."""
    return populated_project


@pytest.fixture
def readable(copy_squad) -> SquadPaths:
    """A copy of the readable squad as the working directory."""
    return copy_squad("readable", init_readable)
