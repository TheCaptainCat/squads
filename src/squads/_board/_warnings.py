"""The multi-line-summary finding for board notices: the live notices that hold one, and the
message ``sq check`` and ``board post`` both print.
"""

from datetime import datetime

from squads._board._model import BoardNotice
from squads._board._store import BOARD_ROOT, is_expired
from squads._errors import SquadsError
from squads._paths import SquadPaths
from squads._sections import split_frontmatter
from squads._util import has_line_break


def multi_line_summary_message(n: int, notice: BoardNotice) -> str:
    """The warning for notice *n*, with the commands that repost it under a one-line summary."""
    until = f" --until {notice.until}" if notice.until else ""
    return (
        f"notice {n} ({notice.id}) has a multi-line summary; post it again with a one-line"
        f' summary: `sq board post "<summary>" --file <body> --as {notice.author}{until}`,'
        f" then `sq board clear {n}`"
    )


def live_notices(paths: SquadPaths, now: datetime) -> list[BoardNotice]:
    """The unexpired notices that can be read, in listing order (posted-at, then id)."""
    folder = paths.abspath(BOARD_ROOT)
    notices: list[BoardNotice] = []
    for path in sorted(folder.glob("*.md")):
        try:
            frontmatter, body = split_frontmatter(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, SquadsError):  # fmt: skip
            continue
        notice = BoardNotice.from_frontmatter(path.stem, frontmatter, body.strip("\n"))
        if not is_expired(notice, now):
            notices.append(notice)
    return sorted(notices, key=lambda n: (n.posted_at, n.id))


def multi_line_summary_warnings(paths: SquadPaths, now: datetime) -> list[tuple[str, str]]:
    """One ``(notice id, message)`` per live notice whose summary holds a line break."""
    return [
        (notice.id, multi_line_summary_message(n, notice))
        for n, notice in enumerate(live_notices(paths, now), start=1)
        if has_line_break(notice.summary)
    ]
