"""Append-only JSONL operation log (reflog): writer, line model and path. One line per mutating
``sq`` operation, written after the index ``os.replace`` commit while still holding the file lock,
so applied-without-logged is the tolerated failure and logged-without-applied is designed out.

Line shape (``v`` is the dotted ``SCHEMA_VERSION``, ``ts`` an ISO-8601 UTC string from
``clock.iso(clock.now())``, ``actor`` a bare slug string from :func:`squads._actor.current_actor`,
``target`` the formatted item id, ``delta`` a before/after summary whose shape depends on ``op``):

.. code-block:: json

    {"v": "<schema>", "ts": "2026-06-15T10:00:00Z", "actor": "python-dev",
     "session_id": "sid-abc", "parent_session_id": "sid-xyz",
     "op": "status", "target": "TASK-XXXXXX", "delta": {"status": ["Draft", "InProgress"]}}

``op`` is from the closed vocabulary :data:`REFLOG_OPS`, which is the only place the names are
listed, since hand-kept copies drifted. ``session_id`` and ``parent_session_id`` are optional
(omitted when ``None``), best-effort, untrusted and observability-only: squads reads
``SQUADS_SESSION_ID`` and ``SQUADS_PARENT_SESSION_ID`` from its own invocation and never mints,
injects or verifies them, so a forged or absent id is indistinguishable from a real one. Only the
immediate parent is stored.

Append is one ``O_APPEND`` ``write`` of a newline-terminated line, atomic on POSIX at these sizes,
with no fsync since the reflog is advisory. A reader skips a trailing partial line silently and
warn-skips interior bad lines, a missing file is an empty log, and lines without the session fields
parse with both as ``None``.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from squads._models._schema import SCHEMA_VERSION

#: The closed ``op`` vocabulary, the one list every surface naming reflog operations (this
#: docstring, ``sq reflog --op``'s help, the workflow guide's table) reads or is checked against. It
#: is ordered narrative-first (item-life ops, then squad maintenance) because ``sq reflog --help``
#: prints it verbatim, and hand-maintained because ``store.log(...)`` call sites are bare literals;
#: an AST guard in ``tests/meta`` pins it in both directions, which makes "closed" true.
#: ``link`` has no CLI verb but is emitted by the service, so it stays.
REFLOG_OPS: tuple[str, ...] = (
    "create",
    "status",
    "update",
    "body",
    "view",
    "comment",
    "comment_edit",
    "comment_remove",
    "subentity",
    "ref",
    "link",
    "retype",
    "default_role",
    "remove",
    "repair",
    "renumber",
    "migrate",
    "rename-type",
    "rename-status",
    "rename-field",
    "rename-kind",
)


@dataclass
class ReflogLine:
    """One parsed reflog entry.

    ``session_id`` and ``parent_session_id`` are ``None`` for lines that carry no
    session fields; absence and ``None`` map to the same in-memory value.
    """

    v: str
    ts: str
    actor: str
    op: str
    target: str
    delta: dict[str, Any]
    session_id: str | None = None
    parent_session_id: str | None = None


def reflog_path(squad_dir: Path) -> Path:
    """Canonical path for the reflog file: ``<squad_dir>/.reflog.jsonl``."""
    return squad_dir / ".reflog.jsonl"


async def append_line(
    path: Path,
    *,
    ts: str,
    actor: str,
    op: str,
    target: str,
    delta: dict[str, Any],
    session_id: str | None = None,
    parent_session_id: str | None = None,
) -> None:
    """Append one compact JSON line to the reflog file on a worker thread. ``session_id`` and
    ``parent_session_id`` are omitted when ``None``, and the reader defaults both to ``None``. The
    swallow of ``(OSError, TypeError, ValueError)`` stays inside the threaded closure so no
    exception crosses the loop boundary (the reflog never-raise contract).
    """
    from squads import _aio

    record: dict[str, Any] = {
        "v": SCHEMA_VERSION,
        "ts": ts,
        "actor": actor,
    }
    # Additive optional siblings — omit when None to keep lines small.
    if session_id is not None:
        record["session_id"] = session_id
    if parent_session_id is not None:
        record["parent_session_id"] = parent_session_id
    record.update(
        {
            "op": op,
            "target": target,
            "delta": delta,
        }
    )

    def _write() -> None:
        try:
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            with path.open("a", encoding="utf-8", newline="") as fh:
                fh.write(line)
        except (OSError, TypeError, ValueError) as exc:
            print(
                f"[squads reflog] warning: could not append to {path}: {exc}",
                file=sys.stderr,
            )

    await _aio.to_thread(_write)


async def read_lines(path: Path) -> list[ReflogLine]:
    """Read and parse the reflog file on a worker thread, tolerating missing/partial files.

    - A missing file returns an empty list (back-compat: squads without a reflog).
    - A trailing partial line (no terminating ``\\n``) is skipped silently.
    - An interior unparseable line is warn-skipped; the rest of the log is returned.
    """
    from squads import _aio

    if not await _aio.path_exists(path):
        return []

    try:
        raw = await _aio.read_text(path)
    except OSError:
        return []

    lines = raw.split("\n")
    # The last element after split on "\n" is always "" for a well-formed file
    # (every complete line ends in "\n", so split yields a trailing empty string).
    # A partial/truncated last line is anything non-empty after the last "\n".
    if lines and lines[-1] == "":
        lines = lines[:-1]  # drop the trailing empty string from a well-formed file
    elif lines and lines[-1]:
        # Trailing partial line (no terminating "\n") — skip silently.
        lines = lines[:-1]

    out: list[ReflogLine] = []
    for i, raw_line in enumerate(lines):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            data = json.loads(raw_line)
            raw_sid = data.get("session_id")
            raw_pid = data.get("parent_session_id")
            out.append(
                ReflogLine(
                    v=str(data.get("v", "")),
                    ts=str(data.get("ts", "")),
                    actor=str(data.get("actor", "")),
                    op=str(data.get("op", "")),
                    target=str(data.get("target", "")),
                    delta=data.get("delta", {}),
                    # A line without session fields reads as None.
                    session_id=str(raw_sid) if raw_sid is not None else None,
                    parent_session_id=str(raw_pid) if raw_pid is not None else None,
                )
            )
        except Exception:
            # Interior malformed line — warn and skip.
            print(
                f"[squads reflog] warning: skipping malformed line {i + 1} in {path}",
                file=sys.stderr,
            )

    return out
