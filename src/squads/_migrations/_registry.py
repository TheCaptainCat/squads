"""The ordered schema migrations, applied by ``sq migrate up`` and surfaced by ``sq migrate
help`` / ``sq migrate chlog``.

Each :class:`Migration` ties together the **schema** transition (drives ``up`` against a squad's
on-disk ``schema_version``), the **release** that shipped it (the axis ``help``/``chlog`` report
on), a one-line ``summary``, the deterministic ``run`` step, and any ``manual`` (LLM-assisted)
steps that ``up`` can't do. Adding a step = drop a ``_vNtoM.py`` runner, append it here, and bump
``_models._schema.SCHEMA_VERSION``.

Runner functions are async — ``Callable[[SquadPaths], Awaitable[int]]``.  Sync runners that need
no IO can be wrapped with :func:`_wrap_sync`.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from squads._migrations import (
    _v0_1_to_v0_2,
    _v0_2_to_v0_3,
    _v0_3_to_v0_4,
    _v0_4_to_v0_5,
    _v0_5_to_v0_7,
)
from squads._paths import SquadPaths


def _wrap_sync(fn: Callable[[SquadPaths], int]) -> Callable[[SquadPaths], Awaitable[int]]:
    """Lift a synchronous migration runner into an async one (no IO needed)."""

    async def _async(paths: SquadPaths) -> int:
        return fn(paths)

    return _async


@dataclass(frozen=True)
class Migration:
    version: str  # squads release that shipped this migration (the chlog axis)
    from_schema: str  # dotted alpha schema version, e.g. "0.1"
    to_schema: str
    summary: str  # one line, for `sq migrate help`
    run: Callable[[SquadPaths], Awaitable[int]]  # the deterministic step (`sq migrate up`)
    manual: str = ""  # markdown manual steps (LLM runbook); "" if fully automatic


MIGRATIONS: list[Migration] = [
    Migration(
        version="0.2.0",
        from_schema="0.1",
        to_schema="0.2",
        summary="Inline ref kinds; subtask/story/finding status machines; sq-managed summaries.",
        run=_wrap_sync(_v0_1_to_v0_2.migrate),
        manual=_v0_1_to_v0_2.MANUAL,
    ),
    Migration(
        version="0.3.0",
        from_schema="0.2",
        to_schema="0.3",
        summary="Backfill the human-readable :head region (status/assignee/severity/story badges).",
        run=_wrap_sync(_v0_2_to_v0_3.migrate),
        manual=_v0_2_to_v0_3.MANUAL,
    ),
    Migration(
        version="0.5.0",
        from_schema="0.3",
        to_schema="0.4",
        summary=(
            "Additive session lineage fields: optional session_id/parent_session_id on reflog "
            "lines and created_session/modified_session on item frontmatter. "
            "Best-effort, untrusted, observability-only — no file rewrite required."
        ),
        run=_wrap_sync(_v0_3_to_v0_4.migrate),
        manual=_v0_3_to_v0_4.MANUAL,
    ),
    Migration(
        version="0.5.0",
        from_schema="0.4",
        to_schema="0.5",
        summary=(
            "SKILL ids for bundled skills: stamp SKILL-… frontmatter onto every existing "
            "agents/skills/*.md body file in lexical-by-slug order."
        ),
        run=_v0_4_to_v0_5.migrate,
        manual=_v0_4_to_v0_5.MANUAL,
    ),
    Migration(
        version="0.7.0",
        from_schema="0.5",
        to_schema="0.7",
        summary=(
            "Unpadded display IDs: rewrite every frontmatter id/ref/parent and body-prose "
            "ID mention to the unpadded form; filenames stay padded, untouched."
        ),
        run=_wrap_sync(_v0_5_to_v0_7.migrate),
        manual=_v0_5_to_v0_7.MANUAL,
    ),
]
