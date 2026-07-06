"""Append-only JSONL operation log (reflog) — writer, line model, and path.

One line per mutating ``sq`` operation, written **after** the index ``os.replace``
commit while still holding the file lock.  Applied-without-logged is the tolerated
failure mode; logged-without-applied is designed out by the strict ordering.

Line shape, including the optional session lineage fields:

.. code-block:: json

    {"v": "0.4", "ts": "2026-06-15T10:00:00Z", "actor": "python-dev",
     "session_id": "sid-abc", "parent_session_id": "sid-xyz",
     "op": "status", "target": "TASK-XXXXXX", "delta": {"status": ["Draft", "InProgress"]}}

Fields
------
- ``v``                  — schema version (``SCHEMA_VERSION`` dotted string), present from line 1.
- ``ts``                 — ISO-8601 UTC timestamp, from ``clock.iso(clock.now())``.
- ``actor``              — acting identity slug (flat string), from
                           :func:`squads._actor.current_actor`.  **Kept as a bare string for
                           back-compat.**
- ``session_id``         — *optional*, omitted when ``None``.  Best-effort, untrusted opaque id
                           for the current session, read from ``SQUADS_SESSION_ID`` env var if
                           present.  squads does **not** mint, inject, or verify this value.
- ``parent_session_id``  — *optional*, omitted when ``None``.  Best-effort, untrusted id for the
                           immediate parent session, from ``SQUADS_PARENT_SESSION_ID``.  The full
                           ancestor chain is reconstructable by walking ``parent_session_id`` edges;
                           only the immediate parent is stored.
- ``op``                 — operation name from the closed vocabulary:
                           ``create`` / ``status`` / ``update`` / ``body`` / ``comment`` /
                           ``subentity`` / ``ref`` / ``link`` / ``remove`` / ``repair`` /
                           ``migrate`` / ``renumber``.
- ``target``             — the affected item ID (formatted, e.g. ``"TASK-XXXXXX"``).
- ``delta``              — compact before→after summary; shape depends on ``op``.

**Session lineage guarantee: best-effort, untrusted, observability-only.**
squads is a passive tool, never in the spawn path.  It reads optional env vars
from its own invocation and records them.  A forged, copied, or absent session
id is indistinguishable from a real one.

Append semantics
----------------
One ``O_APPEND`` ``write`` of a single newline-terminated JSON line.  A single
``write`` under ``O_APPEND`` is atomic on POSIX for our line sizes.  No fsync —
the reflog is advisory; fsyncing the index is sufficient.

Reader tolerance
----------------
A trailing partial/unparseable line is skipped silently; interior bad lines are
warn-skipped.  A missing file is an empty log — never an error.
**Legacy slug-only lines** (no ``session_id``/``parent_session_id`` fields) parse
with both fields as ``None`` — no forced rewrite.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from squads._models._schema import SCHEMA_VERSION


@dataclass
class ReflogLine:
    """One parsed reflog entry.

    ``session_id`` and ``parent_session_id`` are ``None`` for legacy lines
    (schema < 0.4) that carry no session fields.  Both absence and ``None`` map
    to the same in-memory value — no rewrite is needed.
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
    """Append one compact JSON line to the reflog file (IO runs on a worker thread).

    ``session_id`` and ``parent_session_id`` are omitted from the written record
    when ``None`` to keep lines small; the reader defaults both to ``None`` on
    absence so legacy lines parse cleanly.

    The swallow of ``(OSError, TypeError, ValueError)`` is kept **inside** the
    threaded closure so no exception ever crosses the loop boundary
    (reflog never-raise contract).
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
            with path.open("a", encoding="utf-8") as fh:
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
                    # Legacy lines (schema < 0.4) have no session fields → None.
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
