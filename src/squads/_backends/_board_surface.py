"""Shared, backend-neutral formatting of the team bulletin board for boot surfacing.

At boot, current board notices are surfaced into every agent's context through the active
backend — the Claude Code backend folds it into the shared ``CLAUDE.md`` managed section,
the AGENTS.md backend into the shared ``AGENTS.md`` section. Unlike agent memory
(index-only, per-role, content on recall), the board is **team-scoped** and its notices are
short and prescriptive, so they are surfaced **content and all** — this module is the single
formatter both backends share, mirroring :mod:`squads._backends._memory_surface`.
"""

from squads._board import _store as board_store
from squads._paths import SquadPaths


async def board_notice_lines(paths: SquadPaths) -> list[str]:
    """One line per current (unexpired) notice: body, author, and posted-at.

    Reads through :func:`squads._board._store.list_notices`, which already excludes expired
    notices at read time (the board's own ``--until`` filter) — this formatter adds no
    filtering of its own. An empty or all-expired board yields ``[]`` so callers can render
    nothing rather than an empty header.
    """
    notices = await board_store.list_notices(paths)
    lines: list[str] = []
    for notice in notices:
        until_part = f", until {notice.until}" if notice.until else ""
        lines.append(f"- {notice.body} ({notice.author} @ {notice.posted_at}{until_part})")
    return lines
