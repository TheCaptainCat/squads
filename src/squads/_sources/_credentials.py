"""The credential store: one TOML file per user of the serving process, outside every repository.

An entry is keyed by the normalised base URL of the tracker and holds the fields its connector
names. The file is read at the moment a command needs it and never kept; on POSIX it is created
with mode ``0600`` in a ``0700`` directory, and one that others can read is refused. No value is
ever returned to a caller that only asks whether an entry exists.
"""

import json
import os
import re
import sys
import tomllib
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from squads._errors import SquadsError

STORE_FILENAME = "credentials.toml"

_BARE_KEY = re.compile(r"[A-Za-z0-9_-]+")


def normalise_base_url(url: str) -> str:
    """*url* as its entry key spells it: scheme and host in lower case, the port and path kept,
    no trailing slash, no query or fragment."""
    parts = urlsplit(url.strip())
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}{parts.path.rstrip('/')}"


def _refuse_readable_by_others(path: Path) -> None:
    if sys.platform == "win32":
        return
    if path.stat().st_mode & 0o077:
        raise SquadsError(
            f"the credential store {path} can be read by other users; "
            f"run `chmod 600 {path}` and try again"
        )


def _read(path: Path) -> dict[str, dict[str, str]]:
    """The whole store; an absent file is an empty one."""
    if not path.exists():
        return {}
    _refuse_readable_by_others(path)
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:  # fmt: skip
        raise SquadsError(f"cannot read the credential store {path}: {type(exc).__name__}") from exc
    store: dict[str, dict[str, str]] = {}
    for url, entry in parsed.items():
        if not isinstance(entry, dict) or not all(
            isinstance(value, str) for value in cast("dict[str, Any]", entry).values()
        ):
            raise SquadsError(
                f"the credential store {path} is malformed: the entry for {url!r} must be a "
                "table of strings"
            )
        store[url] = dict(cast("dict[str, str]", entry))
    return store


def _quote(text: str) -> str:
    return json.dumps(text, ensure_ascii=False).replace("\x7f", "\\u007f")


def _dump(store: dict[str, dict[str, str]]) -> str:
    lines: list[str] = []
    for url in sorted(store):
        lines.append(f"[{_quote(url)}]")
        for key, value in store[url].items():
            name = key if _BARE_KEY.fullmatch(key) else _quote(key)
            lines.append(f"{name} = {_quote(value)}")
        lines.append("")
    return "\n".join(lines)


def _private_directory(directory: Path) -> None:
    """Create *directory* ``0700``, and tighten one that exists and is ours."""
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if sys.platform != "win32":
        info = directory.stat()
        if info.st_uid == os.getuid() and info.st_mode & 0o077:
            directory.chmod(0o700)


def _write(path: Path, store: dict[str, dict[str, str]]) -> None:
    """Replace the file with *store*: written to a fresh sibling created ``0600`` that is never a
    followed link, synced, then moved over."""
    _private_directory(path.parent)
    scratch = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    scratch.unlink(missing_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(scratch, flags, 0o600)
    try:
        if sys.platform != "win32":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_dump(store))
            handle.flush()
            os.fsync(handle.fileno())
        scratch.replace(path)
    except BaseException:
        scratch.unlink(missing_ok=True)
        raise


@contextmanager
def _locked(path: Path) -> Generator[None]:
    """Hold the store's lock, so two writers do not lose each other's entry."""
    from filelock import FileLock

    _private_directory(path.parent)
    with FileLock(path.with_name(f".{path.name}.lock"), mode=0o600):
        yield


class CredentialStore:
    """The per-user credential file: read, write, remove and test entries by tracker base URL.

    It holds no state; the file is located and read at each call.
    """

    def path(self) -> Path:
        """The credential file of the user running this process."""
        if sys.platform == "win32":
            base = os.environ.get("APPDATA")
            root = Path(base) if base else Path.home() / "AppData" / "Roaming"
        elif sys.platform == "darwin":
            root = Path.home() / "Library" / "Application Support"
        else:
            base = os.environ.get("XDG_CONFIG_HOME")
            root = Path(base) if base else Path.home() / ".config"
        return root / "squads" / STORE_FILENAME

    def read_entry(self, base_url: str) -> dict[str, str] | None:
        """The fields stored for *base_url*, or ``None`` when there is no entry."""
        return _read(self.path()).get(normalise_base_url(base_url))

    def has_entry(self, base_url: str) -> bool:
        """Whether an entry exists for *base_url*."""
        return normalise_base_url(base_url) in _read(self.path())

    def write_entry(self, base_url: str, values: dict[str, str]) -> Path:
        """Store *values* as the entry for *base_url*, replacing the one there; returns the file."""
        path = self.path()
        with _locked(path):
            store = _read(path)
            store[normalise_base_url(base_url)] = dict(values)
            _write(path, store)
        return path

    def remove_entry(self, base_url: str) -> bool:
        """Delete the entry for *base_url*; ``False`` when there was none, and then nothing is
        written."""
        path = self.path()
        with _locked(path):
            store = _read(path)
            if store.pop(normalise_base_url(base_url), None) is None:
                return False
            _write(path, store)
        return True
