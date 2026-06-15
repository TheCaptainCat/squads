"""Result dataclasses returned by the service layer."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from squads._models._index import SquadsDB
from squads._models._item import Item
from squads._models._subentity import SubEntity
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
    """Where a scaffolded story/subtask/finding block's body lives."""

    local_id: str
    path: Path
    body_tag: str
    start_line: int | None
    end_line: int | None


@dataclass
class SubentityDetail:
    """A sub-entity's full detail for `sq <kind> show`: state + body + discussion."""

    info: SubEntity
    body: str
    discussion: str


@dataclass
class InitResult:
    paths: SquadPaths
    roles: list[Item]


@dataclass
class AdoptResult:
    paths: SquadPaths
    imported: int  # items found on disk and indexed
    roles: list[Item]  # roles newly activated


@dataclass(frozen=True)
class RetypeResult:
    """Outcome of ``Service.retype()``."""

    item: Item
    old_id: str
    old_type: str  # ItemType.value string, for display
    status_reset: bool
    old_status: str  # Status.value string (meaningful only when status_reset is True)
    rewritten: list[str]  # paths of files whose text was updated (relative display names)


@dataclass(frozen=True)
class RemoveResult:
    """Outcome of ``Service.remove_work_item()``.

    ``removed_id`` is the formatted ID of the deleted item.
    ``severed_refs`` lists the IDs of referrer items whose forward refs were severed (``--force``).
    The ``op=remove`` reflog entry with the gone-item snapshot is appended post-commit
    (FEAT-000024 / TASK-000112).
    """

    removed_id: str
    severed_refs: list[str]  # referrer IDs whose ref to removed_id was deleted


@dataclass
class RepairResult:
    """Outcome of ``Service.repair()``.

    ``missing_ids`` holds item IDs that were present in the index *before* repair but whose
    markdown files could not be found on disk — a deletion event worth surfacing to the operator.
    """

    db: SquadsDB
    missing_ids: list[str] = field(default_factory=list[str])


@dataclass
class WorkloadRow:
    """Per-assignee work counts for `sq workload` (None assignee = unassigned)."""

    assignee: str | None
    open: int
    closed: int
    total: int


@dataclass
class ReflogEntry:
    """One parsed reflog line, surfaced by ``sq reflog`` (FEAT-000024 / TASK-000113).

    The ``delta`` field is a free-form ``dict`` whose shape depends on ``op``; see
    the reflog schema documentation for the full field reference.  The ``v`` field
    carries the schema version so readers can handle future additions gracefully.

    Stability note: the *command shape* and the fields listed here are documented;
    the exact ``delta`` sub-fields are additive and evolve per FEAT-000013's freeze.
    """

    v: str
    ts: str
    actor: str
    op: str
    target: str
    delta: dict[str, Any]
