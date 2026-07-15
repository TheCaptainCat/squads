"""Shared, backend-neutral formatting of a role's memory index for boot surfacing.

At role-boot, a role's own agent memory ``.index.jsonl`` (see :mod:`squads._memory._store`)
is surfaced into its context through the active backend — the Claude Code backend folds it
into that role's pointer file, the AGENTS.md backend into that role's section. Both need the
same index-only (slug + one-line summary, never full bodies) line format, so this module is
the single formatter they share — mirroring how ``_managed_region.py`` is the one shared
managed-section mechanism every backend inherits, rather than each backend re-deriving (and
possibly drifting on) the same rendering.
"""

from squads._memory import _store as memory_store
from squads._paths import SquadPaths


async def memory_index_lines(paths: SquadPaths, role_slug: str) -> list[str]:
    """One line per memory in *role_slug*'s pool: ``- `slug`: summary``.

    Reads only the generated ``.index.jsonl`` roll-up — slugs and one-line descriptions,
    never memory bodies (index in, content on recall; full text comes back via
    ``sq memory <role> show <slug>``). An empty or absent pool yields ``[]`` so callers can
    render nothing rather than an empty header.
    """
    entries = await memory_store.read_index(paths, role_slug)
    return [f"- `{entry.slug}`: {entry.description}" for entry in entries]
