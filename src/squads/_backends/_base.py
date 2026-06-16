"""Pluggable agent-backend interface. Claude Code is the first implementation."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from squads._models._item import Item
from squads._paths import SquadPaths
from squads._roles._catalog import RoleDef


@dataclass(frozen=True)
class Artifact:
    """A tool-owned file the backend generated (path is project-root-relative)."""

    path: str
    kind: str  # backend-specific category, e.g. agent | skill | config | index
    backend: str


@dataclass(frozen=True)
class RoleView:
    """The roster entry passed to backends (decoupled from RoleDef internals)."""

    slug: str
    full_name: str
    title: str
    is_default: bool


@dataclass(frozen=True)
class OperatorView:
    """A human operator passed to backends for the CLAUDE.md people roster."""

    slug: str
    full_name: str


@dataclass
class BackendContext:
    paths: SquadPaths
    version: str

    @property
    def root(self) -> Path:
        return self.paths.root

    @property
    def squad_dir(self) -> Path:
        return self.paths.squad_dir

    def rel(self, path: Path) -> str:
        """Root-relative forward-slash path (for Artifact paths and backend-owned references)."""
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def root_relative(self, item: Item) -> str:
        """Root-relative path to an item's markdown file (for backend-owned file references)."""
        return self.rel(self.paths.abspath(item.path))


class AgentBackend(ABC):
    name: str

    @abstractmethod
    def ensure_scaffold(self, ctx: BackendContext) -> list[Artifact]:
        """Create backend dirs and base config (idempotent; never clobber user content)."""

    @abstractmethod
    def write_managed(
        self, ctx: BackendContext, roster: list[RoleView], operators: list[OperatorView]
    ) -> list[Artifact]:
        """(Re)write roster/version-dependent files: skill definitions and backend config."""

    @abstractmethod
    def generate_role_entry(self, ctx: BackendContext, item: Item, role: RoleDef) -> Artifact:
        """Write the backend's entry for a role (loads the role's real definition)."""

    @abstractmethod
    def generate_skill_entry(self, ctx: BackendContext, item: Item) -> Artifact:
        """Write the backend's entry for a skill (loads the skill's real definition)."""

    @abstractmethod
    def remove_artifacts(self, ctx: BackendContext, item: Item) -> None:
        """Delete the backend entry/entries for an item."""

    @abstractmethod
    def managed_paths(self, ctx: BackendContext) -> list[str]:
        """Root-relative paths this backend owns and that sq check expects to exist.

        Read-only: must not create or modify any file.  Returns the same root-relative
        paths that ``ensure_scaffold`` / ``write_managed`` would write, without writing
        them.  Used by ``sq check`` to verify that scaffolding exists (present-only check
        — not a currency/drift check).

        Implementations should scope this to the always-present top-level files whose
        absence means the backend was never scaffolded/synced.
        """
