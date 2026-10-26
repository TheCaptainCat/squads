"""File I/O for the team bulletin board: one short-hash-named ``.md`` per notice under
``squads/board/``.

The board is off the global counter and outside ``.squads.json``: nothing here allocates an
id, opens ``IndexStore`` or touches an index, so ``sq repair`` has nothing to rebuild (as in
:mod:`squads._memory._store`). Content files are marker-free (see
:mod:`squads._board._model`).

Unlike memory, which has a durable slug, a notice is addressed by an ephemeral positional
ordinal: its position in the freshly computed live listing (:func:`list_notices`, sorted and
unexpired, read from the ``.md`` files), with no committed roll-up behind it.
"""

import hashlib
from datetime import datetime
from pathlib import Path

from squads import _aio
from squads import _clock as clock
from squads._board._model import BoardNotice
from squads._errors import SquadsError
from squads._models._omission import Omission
from squads._paths import SquadPaths
from squads._sections import join_frontmatter, split_frontmatter

#: One :class:`Omission` per unreadable file, as :func:`_all_notices` returns it — named so
#: :func:`list_notices`/:func:`clear` don't repeat the shape.
type UnreadableNotices = list[Omission]

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
    await _aio.atomic_write_text(folder / f"{notice_id}.md", file_text)
    return notice


async def _all_notices(paths: SquadPaths) -> tuple[list[BoardNotice], UnreadableNotices]:
    """Every notice on disk (expired or not), unordered, plus one message per unreadable file.

    A bad notice (merge conflict, invalid UTF-8, an OS permission error) raises
    :class:`SquadsError` from the read-path guards and is caught per file, so one bad notice never
    takes the board down, the reporter-stops-at-the-first-problem shape ``sq check`` rejects;
    agents run ``sq board list`` every session.

    A ``FileNotFoundError`` on a dirent this call's glob just saw is a present-versus-absent
    question: a broken symlink is present (the read failed on its target) and is reported like a
    decode failure, while a dirent that vanished between glob and read is skipped silently.
    """
    out: list[BoardNotice] = []
    unreadable: list[Omission] = []
    for path in await _content_files(board_folder(paths)):
        source = str(path.relative_to(paths.squad_dir))
        try:
            text = await _aio.read_text(path)
            frontmatter, body = split_frontmatter(text, source=str(path))
        except FileNotFoundError:
            if await _aio.path_is_symlink(path):
                message = f"{path} is a broken symlink (its target does not exist)"
                unreadable.append(Omission(source=source, message=message))
            continue
        except SquadsError as exc:
            unreadable.append(Omission(source=source, message=str(exc)))
            continue
        out.append(BoardNotice.from_frontmatter(path.stem, frontmatter, body.strip("\n")))
    return out, unreadable


async def list_notices(paths: SquadPaths) -> tuple[list[BoardNotice], UnreadableNotices]:
    """Unexpired notices in listing order: by posted-at, then id as a tiebreak.

    ``posted_at`` has one-second resolution, so two notices posted in the same second tie on it;
    the id tiebreak keeps the order deterministic across re-reads, with no chronological meaning.
    A read never mutates anything: expiry is filtered here, not removed (see :func:`clear`). An
    empty board gives ``([], [])``; the second element names every file :func:`_all_notices` could
    not read.
    """
    now = clock.now()
    all_notices, unreadable = await _all_notices(paths)
    notices = [n for n in all_notices if not _is_expired(n, now)]
    return sorted(notices, key=lambda n: (n.posted_at, n.id)), unreadable


async def clear(paths: SquadPaths, n: int) -> BoardNotice:
    """Resolve ordinal *n* against the live listing (1-based) and delete that notice's file.

    Raises ``SquadsError`` on an out-of-range ordinal. Removal is a real file deletion (history
    retained in git), never a side effect of a read. Resolving the ordinal only ever considers
    the notices that could actually be read — an unreadable one has no ordinal to hold anyway.
    """
    notices, _unreadable = await list_notices(paths)
    if n < 1 or n > len(notices):
        raise SquadsError(
            f"no notice at position {n} (the board currently lists {len(notices)} notice(s))"
        )
    notice = notices[n - 1]
    await _aio.path_unlink(notice_path(paths, notice.id))
    return notice
