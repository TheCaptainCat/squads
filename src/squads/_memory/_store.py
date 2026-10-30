"""File I/O for agent memory: one slug-named ``.md`` per memory under
``squads/agents/memory/<role-slug>/``.

Memory is off the global counter and outside ``.squads.json``: nothing here allocates an id,
opens ``IndexStore`` or touches an index, so ``sq repair`` has nothing to rebuild. Content
files are marker-free (see :mod:`squads._memory._model`). There is no roll-up; every read
(`list_entries`/`search`/`read`) globs and reads the files live.
"""

from pathlib import Path

from squads import _aio
from squads import _clock as clock
from squads._errors import SquadsError
from squads._memory._model import MemoryEntry
from squads._models._omission import Omission
from squads._paths import SquadPaths
from squads._sections import join_frontmatter, split_frontmatter
from squads._util import slugify

#: One :class:`Omission` per unreadable memory file — see :func:`list_entries`.
type UnreadableMemories = list[Omission]

#: Squad-relative root for every role's memory pool: ``<squad_dir>/agents/memory/<role-slug>/``.
MEMORY_ROOT = "agents/memory"

#: Cap on a derived slug's word count and character length (see :func:`_short_slug`).
_SLUG_MAX_WORDS = 5
_SLUG_MAX_CHARS = 40


class MemoryNotFoundError(SquadsError):
    """Raised when a memory slug does not exist in a role's pool."""


def role_folder(paths: SquadPaths, role_slug: str) -> Path:
    """The folder holding one role's memory pool."""
    return paths.abspath(f"{MEMORY_ROOT}/{role_slug}")


def memory_path(paths: SquadPaths, role_slug: str, slug: str) -> Path:
    """The ``.md`` file for one memory, addressed by its stable slug."""
    return paths.abspath(f"{MEMORY_ROOT}/{role_slug}/{slug}.md")


async def _content_files(folder: Path) -> list[Path]:
    """Every memory ``.md`` in *folder*, sorted by filename. Empty if the folder is absent."""
    if not await _aio.path_exists(folder):
        return []
    return await _aio.to_thread(lambda: sorted(folder.glob("*.md")))


async def _unique_slug(folder: Path, base_slug: str) -> str:
    """*base_slug* if free, else the first ``<base_slug>-2``, ``-3``, ... not already on disk.

    A memory file is addressed purely by its slug (no counter prefix disambiguates it the way
    an item's ``<id>-<slug>.md`` does), so a same-slug second fact gets a numeric suffix rather
    than clobbering or hard-erroring — still a human-meaningful id, never a sequence number.
    """
    if not await _aio.path_exists(folder / f"{base_slug}.md"):
        return base_slug
    n = 2
    while await _aio.path_exists(folder / f"{base_slug}-{n}.md"):
        n += 1
    return f"{base_slug}-{n}"


def _short_slug(fact: str) -> str:
    """A short, human-typeable handle for *fact*: its leading words, capped at
    :data:`_SLUG_MAX_WORDS` words and :data:`_SLUG_MAX_CHARS` characters, cut at a word
    boundary (never mid-word). The full fact remains in the entry's summary/body — this is
    only a short address for it, not a restatement of its content.
    """
    words = slugify(fact).split("-")
    kept: list[str] = []
    length = 0
    for word in words:
        if len(kept) >= _SLUG_MAX_WORDS:
            break
        next_length = length + len(word) + (1 if kept else 0)
        if kept and next_length > _SLUG_MAX_CHARS:
            break
        kept.append(word)
        length = next_length
    return "-".join(kept) or "untitled"


async def add(
    paths: SquadPaths,
    role_slug: str,
    fact: str,
    *,
    body: str | None = None,
    tags: list[str] | None = None,
    slug: str | None = None,
) -> MemoryEntry:
    """Write a new memory, ``<slug>.md``.

    *fact* is the frontmatter one-line ``summary`` and the default slug source. *body* is the
    freeform body (``--file`` content at the CLI edge), defaulting to *fact* so a bare
    ``add "<fact>"`` is readable. The slug is a short handle derived from *fact*'s leading words
    (:func:`_short_slug`) or, if *slug* is passed, that name slugified; :func:`_unique_slug`
    disambiguates a collision with ``-2``, ``-3``, …
    """
    fact = fact.strip()
    if not fact:
        raise SquadsError("a memory needs a non-empty fact/summary")
    folder = role_folder(paths, role_slug)
    base_slug = slugify(slug) if slug else _short_slug(fact)
    slug = await _unique_slug(folder, base_slug)
    entry = MemoryEntry(
        slug=slug,
        summary=fact,
        created_at=clock.iso(clock.now()),
        body=(body if body is not None else fact).strip(),
        tags=tuple(tags or ()),
    )
    text = join_frontmatter(entry.to_frontmatter_dict(), entry.body)
    await _aio.mkdir(folder, parents=True, exist_ok=True)
    await _aio.atomic_write_text(folder / f"{slug}.md", text)
    return entry


async def read(paths: SquadPaths, role_slug: str, slug: str) -> MemoryEntry:
    """Read one memory back by slug. A read never mutates anything."""
    path = memory_path(paths, role_slug, slug)
    if not await _aio.path_exists(path):
        raise MemoryNotFoundError(f"no memory {slug!r} for role {role_slug!r}")
    text = await _aio.read_text(path)
    frontmatter, body = split_frontmatter(text, source=str(path))
    return MemoryEntry.from_frontmatter(slug, frontmatter, body.strip("\n"))


async def list_entries(
    paths: SquadPaths, role_slug: str
) -> tuple[list[MemoryEntry], UnreadableMemories]:
    """All memories in a role's pool in slug order, plus one message per unreadable file.

    An empty pool gives ``([], [])``. A bad memory (merge conflict, invalid UTF-8, an OS
    permission error) raises :class:`SquadsError` from the read-path guards and is caught per
    file, so one bad memory never takes the whole listing down, the reporter-stops-at-the-first-
    problem shape ``sq check`` rejects; agents run ``sq memory <role> list`` every session.

    A ``FileNotFoundError`` on a dirent this call's glob just saw is a present-versus-absent
    question: a broken symlink is present (the read failed on its target) and is reported like a
    decode failure, while a dirent that vanished between glob and read is skipped silently.
    """
    folder = role_folder(paths, role_slug)
    out: list[MemoryEntry] = []
    unreadable: list[Omission] = []
    for path in await _content_files(folder):
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
        out.append(MemoryEntry.from_frontmatter(path.stem, frontmatter, body.strip("\n")))
    return out, unreadable


async def search(
    paths: SquadPaths, role_slug: str, query: str
) -> tuple[list[tuple[MemoryEntry, list[str]]], UnreadableMemories]:
    """Memories whose summary or body contains *query* (case-insensitive substring).

    A plain content grep over the role's ``.md`` files, shaped like
    :meth:`squads._services._collab.CollabMixin.search` (entry, matching lines). An unknown or
    empty pool yields no matches. Like :func:`list_entries`, an unreadable memory contributes no
    hits and is named in the second return value instead of aborting the search.
    """
    needle = query.strip().lower()
    if not needle:
        raise SquadsError("search needs a non-empty query")
    entries, unreadable = await list_entries(paths, role_slug)
    out: list[tuple[MemoryEntry, list[str]]] = []
    for entry in entries:
        candidates = [entry.summary, *entry.body.splitlines()]
        hits = list(dict.fromkeys(ln.strip() for ln in candidates if ln and needle in ln.lower()))
        if hits:
            out.append((entry, hits))
    return out, unreadable


async def forget(paths: SquadPaths, role_slug: str, slug: str) -> None:
    """Delete a memory's file for real (history retained in git).

    Raises :class:`MemoryNotFoundError` if *slug* doesn't exist — forgetting is not a silent
    no-op on an already-gone memory.
    """
    path = memory_path(paths, role_slug, slug)
    if not await _aio.path_exists(path):
        raise MemoryNotFoundError(f"no memory {slug!r} for role {role_slug!r}")
    await _aio.path_unlink(path)
