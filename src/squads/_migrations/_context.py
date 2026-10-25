"""What ``sq migrate up`` hands every runner: the squad's paths and the one vocabulary the run
resolved, so no runner resolves its own or falls back to the bundled one.

A leaf module (no dependency on ``_registry``/``_services``) so a runner can import it without
a cycle.
"""

from dataclasses import dataclass

from squads._interactions._models import PlaybookSpec
from squads._paths import SquadPaths
from squads._roles._models import CatalogSource
from squads._workflow._models import WorkflowSpec


@dataclass(frozen=True)
class MigrationContext:
    """The squad's paths, the workflow spec, the playbook and the role catalog the run resolved,
    built once."""

    paths: SquadPaths
    spec: WorkflowSpec
    playbook: PlaybookSpec
    catalog: CatalogSource
