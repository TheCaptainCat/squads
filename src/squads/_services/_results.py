"""Result dataclasses returned by the service layer."""

from dataclasses import dataclass
from pathlib import Path

from squads._models._item import Item
from squads._paths import SquadPaths


@dataclass
class CreateResult:
    item: Item
    path: Path


@dataclass
class CheckIssue:
    level: str  # "error" | "warn"
    item: str  # item id or filename ("" if global)
    message: str


@dataclass
class BlockResult:
    """Where an agent should write a scaffolded story/subtask body."""

    local_id: str
    path: Path
    body_tag: str
    start_line: int | None
    end_line: int | None


@dataclass
class InitResult:
    paths: SquadPaths
    roles: list[Item]


@dataclass
class AdoptResult:
    paths: SquadPaths
    imported: int  # items found on disk and indexed
    roles: list[Item]  # roles newly activated
