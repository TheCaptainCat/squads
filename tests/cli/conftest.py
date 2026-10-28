"""Fixtures for tests/cli/ only; the shared ones (`project`, `seeded_project`, `copy_squad`,
`runner`, `invoke`, the frozen clock and the leak guards) live in tests/conftest.py."""

import pytest

from squads._paths import SquadPaths
from tests.cli._populated import init_populated


@pytest.fixture
def populated_project(copy_squad) -> SquadPaths:
    """A fresh copy of the squad with a feature and its stories, a task and its subtasks, and a
    review and its findings, as the working directory."""
    return copy_squad("populated", init_populated)
