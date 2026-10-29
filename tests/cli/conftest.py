"""Fixtures for tests/cli/ only; the shared ones (`copy_squad`, `runner`, `invoke`, the frozen clock
and the leak guards) live in tests/conftest.py.

The squad fixtures give the squad the run is on (`pytest --squad override` selects the override
test squad): the same fixture name builds the same shape of squad on either.
"""

from pathlib import Path

import pytest

from squads._paths import SquadPaths
from tests import _profile
from tests._override_populated import OVERRIDE, init_override_populated, init_override_surface
from tests._populated import init_populated
from tests._squads import init_full, init_minimal, init_overridden, init_seeded

_ON_OVERRIDE = _profile.selected().squad == "override"


def _override_minimal(root: Path) -> None:
    init_overridden(root, OVERRIDE, seed_skills=False)


def _override_seeded(root: Path) -> None:
    init_overridden(root, OVERRIDE)


def _override_full(root: Path) -> None:
    init_overridden(root, OVERRIDE, roles_spec="all")


@pytest.fixture
def profile() -> _profile.Profile:
    """The names the squad this run is on gives to the things the cases reach."""
    return _profile.selected()


@pytest.fixture
def project(copy_squad) -> SquadPaths:
    """A fresh unseeded `minimal` squad in the test's directory, which is the cwd."""
    if _ON_OVERRIDE:
        return copy_squad("override-minimal", _override_minimal)
    return copy_squad("minimal", init_minimal)


@pytest.fixture
def seeded_project(copy_squad) -> SquadPaths:
    """A fresh `minimal` squad with the bundled skills seeded, as `sq init` leaves it."""
    if _ON_OVERRIDE:
        return copy_squad("override-seeded", _override_seeded)
    return copy_squad("seeded", init_seeded)


@pytest.fixture
def populated_project(copy_squad) -> SquadPaths:
    """A fresh copy of the squad with a host and its target-kind entries, a reference item under
    it with sub-entities and a third item with sub-entities that carry a field."""
    if _ON_OVERRIDE:
        return copy_squad("override-surface", init_override_surface)
    return copy_squad("populated", init_populated)


@pytest.fixture
def override_project(copy_squad) -> SquadPaths:
    """A fresh copy of the override test squad, populated with its own vocabulary, as the working
    directory, whichever squad the run is on."""
    return copy_squad("override-populated", init_override_populated)


@pytest.fixture
def full_project(copy_squad) -> SquadPaths:
    """A fresh squad with every role of the catalog and the bundled skills seeded."""
    if _ON_OVERRIDE:
        return copy_squad("override-full", _override_full)
    return copy_squad("full", init_full)
