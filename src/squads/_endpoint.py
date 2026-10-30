"""Which squad a command addresses and how its daemon is reached.

The one place that turns the client directory and the ``-C`` values into the squad directory and
an :class:`Endpoint`. The CLI, the daemon and ``SquadsConfig``'s reading of ``[daemon]`` all call
it, so they cannot resolve differently. It is standard library only and reads nothing but
``SQUADS_DAEMON``, the ``.squads.toml`` the walk-up finds (``squad_dir`` and ``[daemon]``), the
squad directory's real path and the daemon's files in the runtime directory.
"""

import hashlib
import json
import os
import stat
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePath
from typing import Any, Literal, NamedTuple, cast

CONFIG_FILENAME = ".squads.toml"
DEFAULT_SQUAD_DIR = "squads"

#: The environment variable that overrides ``[daemon] enabled``.
DAEMON_ENV = "SQUADS_DAEMON"

#: ``sun_path`` holds this many bytes, the terminating NUL left out.
_MACOS_SOCKET_PATH_LIMIT = 103
_SOCKET_PATH_LIMIT = 107

_LOCAL_MODE = "every command runs in local mode until it is fixed"


@dataclass(frozen=True)
class DaemonSettings:
    """The ``[daemon]`` table of ``.squads.toml``."""

    #: ``false``: local mode only; the CLI never starts or contacts a daemon.
    enabled: bool = True
    #: Exit after this long without a request; ``0`` is never.
    idle_timeout_minutes: int = 30
    #: Also open the browser listener.
    browser: bool = False


class DaemonProblem(NamedTuple):
    """Something unusable in the ``[daemon]`` table: a line for ``sq check``, and whether it puts
    the CLI in local mode (an unknown key is reported and otherwise ignored)."""

    text: str
    fatal: bool
    #: The key that is unusable; ``None`` when the whole table is.
    key: str | None = None


def parse_daemon(raw: Any) -> tuple[DaemonSettings, list[DaemonProblem]]:
    """The settings *raw* declares, with a problem for each part that is not usable.

    Never raises: an unknown key, a boolean that is not ``true`` or ``false``, a timeout that is
    not a non-negative integer, or a ``[daemon]`` that is not a table falls back to the default
    and is returned as a problem for ``sq check`` to report.
    """
    if not isinstance(raw, dict):
        return DaemonSettings(), [
            DaemonProblem(
                f"[daemon] must be a table, got {type(raw).__name__}; {_LOCAL_MODE}", fatal=True
            )
        ]
    table = cast("dict[str, Any]", raw)
    usable: dict[str, Any] = {}
    problems: list[DaemonProblem] = []
    for key, value in table.items():
        if key == "idle_timeout_minutes":
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                usable[key] = value
            else:
                text = (
                    f"[daemon] {key} must be a whole number of minutes, 0 or more, got {value!r}; "
                    + _LOCAL_MODE
                )
                problems.append(DaemonProblem(text, fatal=True, key=key))
        elif key in ("enabled", "browser"):
            if isinstance(value, bool):
                usable[key] = value
            else:
                text = f"[daemon] {key} must be true or false, got {value!r}; {_LOCAL_MODE}"
                problems.append(DaemonProblem(text, fatal=True, key=key))
        else:
            text = f"[daemon] has an unknown key {key!r}; it is ignored"
            problems.append(DaemonProblem(text, fatal=False, key=key))
    return DaemonSettings(**usable), problems


def daemon_override(environ: Mapping[str, str]) -> tuple[bool | None, str | None]:
    """What ``SQUADS_DAEMON`` says: ``True`` for ``on``, ``False`` for ``off``, ``None`` when it is
    unset or empty, and a problem when it holds anything else."""
    value = environ.get(DAEMON_ENV, "").strip()
    if not value:
        return None, None
    if value.lower() in ("on", "off"):
        return value.lower() == "on", None
    return None, f"{DAEMON_ENV} must be on or off, got {value!r}; {_LOCAL_MODE}"


class ChangeDirError(Exception):
    """A ``-C`` value that ``chdir`` would refuse; the message names the path and the reason."""


def _enter(path: Path, part: str) -> Path:
    """Step from *path* into *part* the way ``chdir`` does, one component at a time."""
    if part == "..":
        return path.parent
    candidate = path / part
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        raise ChangeDirError(f"{candidate} does not exist") from None
    except OSError as exc:
        reason = "permission denied" if isinstance(exc, PermissionError) else exc.strerror
        raise ChangeDirError(f"{candidate} cannot be entered: {reason}") from None
    if not resolved.is_dir():
        raise ChangeDirError(f"{candidate} is not a directory")
    if not os.access(resolved, os.X_OK):
        raise ChangeDirError(f"{candidate} cannot be entered: permission denied")
    return resolved


def change_directory(start: Path, values: Sequence[str]) -> Path:
    """The directory the ``-C`` *values* select from *start*: each value entered in order as
    ``chdir`` would (an absolute value replaces what came before, an empty one changes nothing, a
    link is followed before a ``..``). Raises :class:`ChangeDirError` for a component that is
    missing, not a directory, or not searchable."""
    path = start.resolve()
    for value in values:
        pure = PurePath(value)
        parts = pure.parts
        if pure.is_absolute():
            path, parts = Path(pure.anchor), parts[1:]
        for part in parts:
            if part != ".":
                path = _enter(path, part)
    return path


def find_config(start: Path) -> Path | None:
    """The ``.squads.toml`` the walk-up from *start* finds first."""
    cur = start.resolve()
    for d in (cur, *cur.parents):
        candidate = d / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


Transport = Literal["unix", "tcp"]


@dataclass(frozen=True)
class EndpointFiles:
    """The four files a daemon keeps per key in the runtime directory."""

    socket: Path
    info: Path
    lock: Path
    log: Path

    def all(self) -> tuple[Path, ...]:
        return (self.socket, self.info, self.lock, self.log)


@dataclass(frozen=True)
class Endpoint:
    """Where a squad's daemon lives and how a client reaches and recognises it."""

    #: The project root, which holds ``.squads.toml``.
    root: Path
    #: The squad directory's real path.
    squad_dir: Path
    key: str
    runtime_dir: Path
    files: EndpointFiles
    #: ``unix`` (a socket in the runtime directory) or ``tcp`` (a loopback port ``<key>.json``
    #: lists).
    transport: Transport
    #: How a client recognises its daemon: ``socket`` (the socket is the identity) or
    #: ``pid-and-path`` (a port may be reused, so the answer is checked against ``<key>.json``).
    identity_check: Literal["socket", "pid-and-path"]
    #: Whether the squad is present locally, so a command can run without the daemon.
    local_mode: bool
    settings: DaemonSettings
    #: Whether the daemon may be started or contacted: the table and ``SQUADS_DAEMON`` decide.
    enabled: bool
    #: What is unusable in the settings, one line each; local mode applies for the cause.
    problems: tuple[str, ...] = ()


@dataclass(frozen=True)
class DaemonRecord:
    """What ``<key>.json`` says about the daemon that wrote it."""

    pid: int
    version: str
    squad_dir: str
    listeners: tuple[tuple[str, str, str], ...]

    def address(self, transport: str, kind: str) -> str | None:
        """The address of the first listener of *transport* serving *kind*, or ``None``."""
        for t, address, k in self.listeners:
            if t == transport and k == kind:
                return address
        return None


def squad_key(squad_dir: Path, version: str, package_dir: Path) -> str:
    """A short hash of the squad directory's real path, the squads version and the installed
    package's directory: a symlink, a ``-C`` path and a walk-up reach the same daemon, and two
    installations never share one."""
    material = "\0".join((str(squad_dir), version, str(package_dir)))
    return hashlib.sha256(material.encode()).hexdigest()[:12]


def runtime_directory(environ: Mapping[str, str], platform: str) -> Path:
    """The per-user directory daemon files live in, never inside the squad."""
    if platform == "win32":
        base = environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "squads"
    elif platform == "darwin":
        base = environ.get("TMPDIR")
        if base:
            return Path(base) / "squads"
    else:
        base = environ.get("XDG_RUNTIME_DIR")
        if base:
            return Path(base) / "squads"
    cache = environ.get("XDG_CACHE_HOME")
    home = environ.get("HOME") or environ.get("USERPROFILE") or str(Path("~").expanduser())
    return (Path(cache) if cache else Path(home) / ".cache") / "squads" / "run"


def _read_config_table(config_path: Path) -> dict[str, Any] | None:
    try:
        with config_path.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError):  # fmt: skip
        return None


def endpoint_for(
    start: Path,
    *,
    environ: Mapping[str, str] | None = None,
    platform: str | None = None,
    version: str | None = None,
    package_dir: Path | None = None,
) -> Endpoint | None:
    """The endpoint of the squad the walk-up from *start* finds, or ``None`` when there is no
    squad. A ``.squads.toml`` that cannot be read gives a disabled endpoint naming why, so local
    mode reports the file itself."""
    env = os.environ if environ is None else environ
    plat = sys.platform if platform is None else platform
    config_path = find_config(start)
    if config_path is None:
        return None
    if version is None:
        import squads

        version = squads.__version__
    package = package_dir if package_dir is not None else Path(__file__).resolve().parent
    root = config_path.parent
    table = _read_config_table(config_path)
    fatal: list[str] = []
    if table is None:
        fatal.append(f"{CONFIG_FILENAME} cannot be read")
        table = {}
    squad_name = table.get("squad_dir")
    squad_dir = (
        root / (squad_name if isinstance(squad_name, str) else DEFAULT_SQUAD_DIR)
    ).resolve()
    settings, setting_problems = parse_daemon(table.get("daemon", {}))
    fatal.extend(p.text for p in setting_problems if p.fatal)
    forced, env_problem = daemon_override(env)
    if env_problem is not None:
        fatal.append(env_problem)
    # An unusable setting puts every command in local mode: nothing is started or contacted.
    enabled = not fatal and (settings.enabled if forced is None else forced)
    key = squad_key(squad_dir, version, package)
    runtime = runtime_directory(env, plat)
    files = EndpointFiles(
        socket=runtime / f"{key}.sock",
        info=runtime / f"{key}.json",
        lock=runtime / f"{key}.lock",
        log=runtime / f"{key}.log",
    )
    on_windows = plat == "win32"
    return Endpoint(
        root=root,
        squad_dir=squad_dir,
        key=key,
        runtime_dir=runtime,
        files=files,
        transport="tcp" if on_windows else "unix",
        identity_check="pid-and-path" if on_windows else "socket",
        local_mode=True,
        settings=settings,
        enabled=enabled,
        problems=tuple(fatal),
    )


def _posix_dir_problem(directory: Path, socket_path: Path, platform: str) -> str | None:
    try:
        info = directory.stat()
    except OSError as exc:
        return f"cannot use {directory}: {exc.strerror}"
    if not stat.S_ISDIR(info.st_mode):
        return f"{directory} is not a directory"
    if info.st_uid != os.getuid():
        return f"{directory} is not owned by the current user"
    if stat.S_IMODE(info.st_mode) & 0o077:
        return f"{directory} is accessible to other users (mode {stat.S_IMODE(info.st_mode):04o})"
    limit = _MACOS_SOCKET_PATH_LIMIT if platform == "darwin" else _SOCKET_PATH_LIMIT
    if len(os.fsencode(socket_path)) > limit:
        return f"the socket path {socket_path} is longer than {limit} bytes"
    return None


def runtime_dir_problem(endpoint: Endpoint, *, platform: str | None = None) -> str | None:
    """Why the runtime directory cannot hold the daemon's files, or ``None`` when it can. It is
    created (mode ``0700``) when missing; a directory that cannot be created, is not owned by the
    user, is open to others or leaves the socket path too long is unusable."""
    plat = sys.platform if platform is None else platform
    directory = endpoint.runtime_dir
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        return f"cannot create {directory}: {exc.strerror}"
    if plat == "win32":
        return None if directory.is_dir() else f"{directory} is not a directory"
    return _posix_dir_problem(directory, endpoint.files.socket, plat)


def read_record(endpoint: Endpoint) -> DaemonRecord | None:
    """``<key>.json`` as the daemon wrote it, or ``None`` when it is missing or unreadable."""
    try:
        raw = json.loads(endpoint.files.info.read_text(encoding="utf-8"))
        listeners = tuple(
            (str(ln["transport"]), str(ln["address"]), str(ln["kind"])) for ln in raw["listeners"]
        )
        return DaemonRecord(
            pid=int(raw["pid"]),
            version=str(raw["version"]),
            squad_dir=str(raw["squad_dir"]),
            listeners=listeners,
        )
    except OSError, ValueError, KeyError, TypeError:
        return None
