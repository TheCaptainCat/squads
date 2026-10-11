"""The ordered schema migrations, applied by ``sq migrate up`` and surfaced by ``sq migrate
help`` / ``sq migrate chlog``.

Each :class:`Migration` ties together the **schema** transition (drives ``up`` against a squad's
on-disk ``schema_version``), the **release** that shipped it (the axis ``help``/``chlog`` report
on), a one-line ``summary``, the deterministic ``run`` step, and any ``manual`` (LLM-assisted)
steps that ``up`` can't do. Adding a step = drop a ``_vNtoM.py`` runner, append it here, and bump
``_models._schema.SCHEMA_VERSION``.

Runner functions are async — ``Callable[[MigrationContext], Awaitable[MigrationOutcome]]``, and
receive the one :class:`~squads._migrations._context.MigrationContext` the run resolved. A sync
runner that only walks files (and so takes ``SquadPaths``) is wrapped with :func:`_wrap_sync`;
an async runner that returns a plain ``int`` is wrapped with :func:`_wrap_async` at its
``MIGRATIONS`` entry instead of widening its own return type — see
:class:`~squads._migrations._outcome.MigrationOutcome`.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from squads._migrations import (
    _v0_1_to_v0_2,
    _v0_2_to_v0_3,
    _v0_3_to_v0_4,
    _v0_4_to_v0_5,
    _v0_5_to_v0_7,
    _v0_7_to_v0_8,
    _v0_8_to_v0_10,
    _v0_10_to_v0_11,
    _v0_11_to_v0_14,
    _v0_14_to_v0_15,
)
from squads._migrations._context import MigrationContext
from squads._migrations._outcome import MigrationOutcome
from squads._paths import SquadPaths


def _wrap_sync(
    fn: Callable[[SquadPaths], int],
) -> Callable[[MigrationContext], Awaitable[MigrationOutcome]]:
    """Lift a synchronous migration runner that only walks files into an async one taking the
    run's context (no IO needed)."""

    async def _async(ctx: MigrationContext) -> MigrationOutcome:
        return MigrationOutcome(count=fn(ctx.paths))

    return _async


def _wrap_async(
    fn: Callable[[MigrationContext], Awaitable[int]],
) -> Callable[[MigrationContext], Awaitable[MigrationOutcome]]:
    """Adapt an async runner that takes the run's context and still returns a bare ``int`` to
    the ``Migration.run`` contract, without widening the runner's own return type."""

    async def _async(ctx: MigrationContext) -> MigrationOutcome:
        return MigrationOutcome(count=await fn(ctx))

    return _async


@dataclass(frozen=True)
class Migration:
    version: str  # squads release that shipped this migration (the chlog axis)
    from_schema: str  # dotted alpha schema version, e.g. "0.1"
    to_schema: str
    summary: str  # one line, for `sq migrate help`
    # The deterministic step (`sq migrate up`) — see the module docstring for why most runners
    # reach this contract through _wrap_sync/_wrap_async rather than speaking it natively.
    run: Callable[[MigrationContext], Awaitable[MigrationOutcome]]
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
        run=_wrap_async(_v0_4_to_v0_5.migrate),
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
    Migration(
        version="0.8.0",
        from_schema="0.7",
        to_schema="0.8",
        summary=(
            "Bug severity moves from extra[severity] to a top-level severity: key; "
            "the extra copy is dropped."
        ),
        run=_wrap_sync(_v0_7_to_v0_8.migrate),
        manual=_v0_7_to_v0_8.MANUAL,
    ),
    Migration(
        version="0.10.0",
        from_schema="0.8",
        to_schema="0.10",
        summary=(
            "sq-memory becomes a tracked SKILL item: stamp a SKILL-… id onto the legacy "
            "agents/skills/sq-memory.md and move it to the SKILL-<NNNNNN>-sq-memory.md "
            "convention filename, like every other bundled skill."
        ),
        run=_wrap_async(_v0_8_to_v0_10.migrate),
        manual=_v0_8_to_v0_10.MANUAL,
    ),
    Migration(
        version="0.11.0",
        from_schema="0.10",
        to_schema="0.11",
        summary=(
            "Schema-stamp-only gate for the new `scopes` ref kind (custom-skill role scoping); "
            "no frontmatter shape change, no file rewrite."
        ),
        run=_wrap_sync(_v0_10_to_v0_11.migrate),
        manual=_v0_10_to_v0_11.MANUAL,
    ),
    Migration(
        version="0.14.0",
        from_schema="0.11",
        to_schema="0.14",
        summary=(
            "Two new bundled item types, contract (PRD) and milestone (MILE): create their "
            "folders on an existing squad and regenerate the managed skills, pointers and "
            "compiled CLAUDE.md/AGENTS.md regions so both appear."
        ),
        run=_wrap_async(_v0_11_to_v0_14.migrate),
        manual=_v0_11_to_v0_14.MANUAL,
    ),
    Migration(
        version="0.15.0",
        from_schema="0.14",
        to_schema="0.15",
        summary=(
            "The milestone roll-up moves off its type attachment onto a sq:view:milestone_rollup "
            "body tag: seed the tag on every existing milestone lacking one, through the tool's "
            "own marker-safe placement primitive. Also reclaims a pre-0.14 role/permanently-"
            "system-skill/sq-<type>-skill body still carrying a legacy plain-prose rendering "
            "onto its own tag."
        ),
        run=_v0_14_to_v0_15.migrate,
        manual=_v0_14_to_v0_15.MANUAL,
    ),
]
