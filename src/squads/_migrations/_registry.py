"""The ordered schema migrations, applied by ``sq migrate up`` and surfaced by ``sq migrate
help`` / ``sq migrate chlog``.

Each :class:`Migration` ties together the **schema** transition (drives ``up`` against a squad's
on-disk ``schema_version``), the **release** that shipped it (the axis ``help``/``chlog`` report
on), a one-line ``summary``, the deterministic ``run`` step, and any ``manual`` (LLM-assisted)
steps that ``up`` can't do. Adding a step = drop a ``_vNtoM.py`` runner, append it here, and bump
``_models._schema.SCHEMA_VERSION``.
"""

from collections.abc import Callable
from dataclasses import dataclass

from squads._migrations import _v1_to_v2
from squads._paths import SquadPaths


@dataclass(frozen=True)
class Migration:
    version: str  # squads release that shipped this migration (the chlog axis)
    from_schema: int
    to_schema: int
    summary: str  # one line, for `sq migrate help`
    run: Callable[[SquadPaths], int]  # the deterministic step (`sq migrate up`)
    manual: str = ""  # markdown manual steps (LLM runbook); "" if fully automatic


MIGRATIONS: list[Migration] = [
    Migration(
        version="0.2.0",
        from_schema=1,
        to_schema=2,
        summary="Inline ref kinds; subtask/story/finding status machines; sq-managed summaries.",
        run=_v1_to_v2.migrate,
        manual=_v1_to_v2.MANUAL,
    ),
]
