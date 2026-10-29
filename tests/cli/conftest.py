"""Fixtures for tests/cli/ only; the shared ones (`project`, `seeded_project`, `copy_squad`,
`runner`, `invoke`, the frozen clock and the leak guards) live in tests/conftest.py."""

import pytest

from squads._paths import SquadPaths
from tests._override_populated import init_override_populated
from tests._populated import init_populated
from tests._squads import init_full


@pytest.fixture
def populated_project(copy_squad) -> SquadPaths:
    """A fresh copy of the squad with a feature and its stories, a task and its subtasks, and a
    review and its findings, as the working directory."""
    return copy_squad("populated", init_populated)


@pytest.fixture
def override_project(copy_squad) -> SquadPaths:
    """A fresh copy of the override test squad, populated with its own vocabulary, as the working
    directory."""
    return copy_squad("override-populated", init_override_populated)


@pytest.fixture
def full_project(copy_squad) -> SquadPaths:
    """A fresh squad with every bundled role and the bundled skills seeded, as the working
    directory."""
    return copy_squad("full", init_full)
