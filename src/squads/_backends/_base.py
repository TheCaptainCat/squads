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
    kind: str  # agent | skill | settings | claude_md
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
        """Project-root-relative, forward-slash path (for pointers and Artifact paths)."""
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def root_relative(self, item: Item) -> str:
        """Root-relative path to an item's markdown file (for pointer references)."""
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
        """(Re)write roster/version-dependent tool files: the skill + CLAUDE.md section."""

    @abstractmethod
    def generate_role_pointer(self, ctx: BackendContext, item: Item, role: RoleDef) -> Artifact:
        """Write the thin pointer file that loads a role's real definition."""

    @abstractmethod
    def generate_skill_pointer(self, ctx: BackendContext, item: Item) -> Artifact:
        """Write the thin pointer file that loads a skill's real definition."""

    @abstractmethod
    def remove_artifacts(self, ctx: BackendContext, item: Item) -> None:
        """Delete the pointer file(s) for an item."""
