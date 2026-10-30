"""The daemon's cache of parsed files, keyed by the content a read has just produced.

An entry is a path and the BLAKE2b digest of the text read from it; a read still reads the file
and skips only the parse when the digest matches, so a change by any writer is seen by the next
read. Entries hold pickled values and hand out a fresh copy, so nothing a caller receives can
alter one.
"""

import hashlib
import pickle
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePath


def digest_of(text: str) -> bytes:
    """The BLAKE2b digest of *text*."""
    return hashlib.blake2b(text.encode("utf-8", "surrogatepass"), digest_size=16).digest()


@dataclass(slots=True)
class _Entry:
    digest: bytes
    pickled: bytes
    scan: int


@dataclass(frozen=True, slots=True)
class _Check:
    """The outcome of one override check: for the index state *digest* and the two specs it was
    run against (held, so identity cannot be reused), no refusal or the refusal's text."""

    digest: bytes
    spec: object
    bundled: object
    refusal: str | None


class ParseCache:
    """Parsed files and override-check outcomes kept across the requests of one daemon."""

    def __init__(self, squad_dir: Path) -> None:
        # A file is named by its absolute path in a corpus walk and relative to the squad in a
        # check rule; both spellings of the squad directory map onto one key.
        self._bases = tuple({PurePath(squad_dir), PurePath(squad_dir.resolve())})
        self._lock = threading.Lock()
        self._index: dict[str, _Entry] = {}
        self._frontmatter: dict[str, _Entry] = {}
        self._check: _Check | None = None
        self._scan = 0

    def index[T](self, key: str, text: str, parse: Callable[[], T]) -> T:
        """The index read from the file *key*, as :meth:`_parsed` returns it."""
        return self._parsed(self._index, key, text, parse)

    def frontmatter[T](self, key: str, text: str, parse: Callable[[], T]) -> T:
        """The frontmatter read from the file *key* (absolute, or relative to the squad), as
        :meth:`_parsed` returns it."""
        return self._parsed(self._frontmatter, self._file_key(key), text, parse)

    def _file_key(self, label: str) -> str:
        """*label* as a path relative to the squad, with ``/`` separators, whatever the platform
        spelled it with; a path outside the squad keeps its own spelling."""
        path = PurePath(label)
        if path.is_absolute():
            for base in self._bases:
                if path.is_relative_to(base):
                    return path.relative_to(base).as_posix()
            return label
        return path.as_posix()

    def _parsed[T](
        self, entries: dict[str, _Entry], key: str, text: str, parse: Callable[[], T]
    ) -> T:
        """The value *parse* makes from *text*: a copy of the kept one when *text* has the digest
        the entry holds, else *parse*'s own result, which replaces the entry. A *parse* that
        raises keeps nothing."""
        digest = digest_of(text)
        with self._lock:
            entry = entries.get(key)
            if entry is not None and entry.digest == digest:
                entry.scan = self._scan
                pickled = entry.pickled
            else:
                pickled = None
        if pickled is not None:
            # A copy per hit: a caller that edits what it got must not edit the entry.
            return pickle.loads(pickled)
        value = parse()
        kept = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        with self._lock:
            entries[key] = _Entry(digest, kept, self._scan)
        return value

    def checked(self, digest: bytes, spec: object, bundled: object) -> tuple[bool, str | None]:
        """Whether the check of *spec* against the index state *digest* has an outcome, and the
        refusal text it ended in (``None`` for a pass)."""
        with self._lock:
            kept = self._check
        if kept is None or kept.digest != digest:
            return False, None
        return kept.spec is spec and kept.bundled is bundled, kept.refusal

    def keep_check(self, digest: bytes, spec: object, bundled: object, refusal: str | None) -> None:
        """Keep the outcome of the check of *spec* against the index state *digest*; it replaces
        the previous one."""
        with self._lock:
            self._check = _Check(digest, spec, bundled, refusal)

    def begin_scan(self) -> None:
        """Start a walk of the corpus: the item files it reads are the ones to keep."""
        with self._lock:
            self._scan += 1

    def end_scan(self) -> None:
        """End a walk that reached every item file: an entry it did not read is for a file that is
        no longer there, and is dropped."""
        with self._lock:
            current = self._scan
            for key in [k for k, e in self._frontmatter.items() if e.scan < current]:
                del self._frontmatter[key]
