"""File I/O for the team bulletin board: one short-hash-named ``.md`` per notice under
``squads/board/``.

The board is **off the global counter and outside ``.squads.json``**: nothing here allocates a
counter id, opens ``IndexStore``, or touches an index — ``sq repair`` has nothing to rebuild
because there is nothing here for it to know about (mirrors :mod:`squads._memory._store`).
Content files are marker-free (freeform, author-owned body — see :mod:`squads._board._model`).

Unlike memory (addressed by a durable, meaningful slug), the board is addressed by an
**ephemeral positional ordinal** that is the notice's position in the freshly-computed live
listing (:func:`list_notices`, sorted and unexpired, read straight from the ``.md`` files) —
there is no committed roll-up backing that ordinal.
"""

import hashlib
from datetime import datetime
from pathlib import Path

from squads import _aio
from squads import _clock as clock
from squads._board._model import BoardNotice
from squads._errors import SquadsError
from squads._paths import SquadPaths
from squads._sections import join_frontmatter, split_frontmatter

#: Squad-relative root for the board's notice pool: ``<squad_dir>/board/``.
BOARD_ROOT = "board"

#: Short-hash id length (hex chars) — human-meaningful and collision-resistant enough for a
#: content-derived id; not a security hash, just a stable filename/reference.
_HASH_LEN = 10


def board_folder(paths: SquadPaths) -> Path:
    """The folder holding every posted notice."""
    return paths.abspath(BOARD_ROOT)


def notice_path(paths: SquadPaths, notice_id: str) -> Path:
    """The ``.md`` file for one notice, addressed by its stable short-hash id."""
    return paths.abspath(f"{BOARD_ROOT}/{notice_id}.md")


def _hash_id(author: str, posted_at: str, body: str) -> str:
    """A stable short hash derived from content + author + posted-at.

    Deterministic and collision-resistant for the low-frequency, human-scale posting rate the
    board is designed for; two distinct posts (different text, author, or timestamp) get
    distinct ids, and the same inputs always hash to the same id.
    """
    digest = hashlib.sha256(f"{author}\n{posted_at}\n{body}".encode()).hexdigest()
    return digest[:_HASH_LEN]


async def _unique_id(folder: Path, base_id: str) -> str:
    """*base_id* if free, else the first ``<base_id>-2``, ``-3``, ... not already on disk.

    Guards the pathological case of two posts hashing identically (e.g. the same author
    posting the same text within the same clock second) without ever silently clobbering an
    existing notice file.
    """
    if not await _aio.path_exists(folder / f"{base_id}.md"):
        return base_id
    n = 2
    while await _aio.path_exists(folder / f"{base_id}-{n}.md"):
        n += 1
    return f"{base_id}-{n}"


async def _content_files(folder: Path) -> list[Path]:
    """Every notice ``.md`` in *folder*. Empty if the folder is absent."""
    if not await _aio.path_exists(folder):
        return []
    return await _aio.to_thread(lambda: list(folder.glob("*.md")))


def _is_expired(notice: BoardNotice, now: datetime) -> bool:
    """True once *now* is at/after the notice's ``until`` expiry; never-expires when unset."""
    if not notice.until:
        return False
    return clock.parse_iso(notice.until) <= now


async def post(
    paths: SquadPaths, author: str, text: str, *, until: str | None = None
) -> BoardNotice:
    """Write a new notice: ``<hash-id>.md`` (id derived from content).

    *text* is both the source of the hash and the notice body itself — a notice has no
    separate summary field; it is short and prescriptive by design. *until*, if
    given, is parsed via the shared ISO helper and stored normalised. No counter id is
    allocated and ``.squads.json`` is never touched.
    """
    text = text.strip()
    if not text:
        raise SquadsError("a board notice needs non-empty text")
    author = author.strip()
    if not author:
        raise SquadsError("a board notice needs a non-empty author")

    until_iso: str | None = None
    if until:
        try:
            until_iso = clock.iso(clock.parse_iso(until))
        except ValueError as exc:
            raise SquadsError(f"invalid --until value {until!r}: {exc}") from exc

    posted_at = clock.iso(clock.now())
    folder = board_folder(paths)
    notice_id = await _unique_id(folder, _hash_id(author, posted_at, text))
    notice = BoardNotice(
        id=notice_id, author=author, posted_at=posted_at, body=text, until=until_iso
    )

    file_text = join_frontmatter(notice.to_frontmatter_dict(), notice.body)
    await _aio.mkdir(folder, parents=True, exist_ok=True)
    await _aio.write_text(folder / f"{notice_id}.md", file_text)
    return notice


async def _all_notices(paths: SquadPaths) -> list[BoardNotice]:
    """Every notice on disk (expired or not), in no particular order."""
    out: list[BoardNotice] = []
    for path in await _content_files(board_folder(paths)):
        text = await _aio.read_text(path)
        frontmatter, body = split_frontmatter(text)
        out.append(BoardNotice.from_frontmatter(path.stem, frontmatter, body.strip("\n")))
    return out


async def list_notices(paths: SquadPaths) -> list[BoardNotice]:
    """Unexpired notices, in listing order: chronological by posted-at, then id as a tiebreak.

    ``posted_at`` has one-second resolution (the shared clock, project-wide), so two notices
    posted within the same second by a low-frequency, effectively single-writer board tie on
    it; the id tiebreak keeps the order deterministic across re-reads even then, though it has
    no chronological meaning in that rare case.

    A read never mutates anything — expiry is filtered here, not physically removed (see
    :func:`clear`). Empty/never-posted board -> ``[]``, no error.
    """
    now = clock.now()
    notices = [n for n in await _all_notices(paths) if not _is_expired(n, now)]
    return sorted(notices, key=lambda n: (n.posted_at, n.id))


async def clear(paths: SquadPaths, n: int) -> BoardNotice:
    """Resolve ordinal *n* against the live listing (1-based) and delete that notice's file.

    Raises ``SquadsError`` on an out-of-range ordinal. Removal is a real file deletion (history
    retained in git), never a side effect of a read.
    """
    notices = await list_notices(paths)
    if n < 1 or n > len(notices):
        raise SquadsError(
            f"no notice at position {n} (the board currently lists {len(notices)} notice(s))"
        )
    notice = notices[n - 1]
    await _aio.path_unlink(notice_path(paths, notice.id))
    return notice
