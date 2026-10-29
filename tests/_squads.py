"""Build a squad once per module and copy it per test, so a row pays a directory copy, not an init.

`build_squad` runs a builder against an empty directory under the frozen clock and restores the
process state it touched. `restore` copies the built squad into a test's own directory, so a
destructive verb never sees another test's leftovers.
"""

import asyncio
import os
import shutil
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from squads._context import bind_context, get_context
from squads._paths import SquadPaths, resolve
from squads._services import _service as service

FROZEN = datetime(2026, 6, 7, 10, 0, 0, tzinfo=UTC)

type Builder = Callable[[Path], None]


def build_squad(root: Path, builder: Builder) -> Path:
    """Run *builder* on the empty directory *root* under the frozen clock; return *root*."""
    previous = Path.cwd()
    prior = get_context()
    bind_context(replace(prior, clock_override=FROZEN))
    os.chdir(root)
    try:
        builder(root)
    finally:
        os.chdir(previous)
        bind_context(prior)
    return root


def init_minimal(root: Path) -> None:
    """The unseeded `minimal` squad: one role, no bundled skills, so the counter starts at 1."""
    asyncio.run(service.init(root=root, roles_spec="minimal", _skip_skill_seed=True))


def init_seeded(root: Path) -> None:
    """The `minimal` squad with the bundled skills seeded, as `sq init` leaves it."""
    asyncio.run(service.init(root=root, roles_spec="minimal"))


def init_full(root: Path) -> None:
    """The squad with every bundled role and the bundled skills seeded."""
    asyncio.run(service.init(root=root, roles_spec="all"))


def init_overridden(root: Path, source: Path) -> None:
    """The `minimal` squad, bundled skills seeded, initialised under the override documents in the
    directory *source*, stamped as the current release writes them."""
    from squads import __version__

    overrides = root / "squads" / ".overrides"
    overrides.mkdir(parents=True)
    for document in sorted(source.glob("*.toml")):
        (overrides / document.name).write_text(
            f"# squads:override-base:{__version__}\n" + document.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    init_seeded(root)


def restore(template: Path, dest: Path) -> Path:
    """Copy the built squad to *dest* (a fresh directory) and return it."""
    shutil.copytree(template, dest, symlinks=True, dirs_exist_ok=True)
    return dest


def paths_of(root: Path) -> SquadPaths:
    """The resolved squad paths of the squad rooted at *root*."""
    return resolve(client_cwd=root)
