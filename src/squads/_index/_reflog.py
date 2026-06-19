"""Append-only JSONL operation log (reflog) — writer, line model, and path.

One line per mutating ``sq`` operation, written **after** the index ``os.replace``
commit while still holding the file lock.  Applied-without-logged is the tolerated
failure mode; logged-without-applied is designed out by the strict ordering.

Line shape (ADR-000117 §4):

.. code-block:: json

    {"v": "0.3", "ts": "2026-06-15T10:00:00Z", "actor": "python-dev",
     "op": "status", "target": "TASK-000112", "delta": {"status": ["Draft", "InProgress"]}}

Fields
------
- ``v``      — schema version (``SCHEMA_VERSION`` dotted string), present from line 1.
- ``ts``     — ISO-8601 UTC timestamp, from ``clock.iso(clock.now())``.
- ``actor``  — acting identity slug, from :func:`squads._actor.current_actor`.
- ``op``     — operation name from the closed vocabulary:
               ``create`` / ``status`` / ``update`` / ``body`` / ``comment`` /
               ``subentity`` / ``ref`` / ``link`` / ``remove`` / ``repair`` /
               ``migrate``.
- ``target`` — the affected item ID (formatted, e.g. ``"TASK-000112"``).
- ``delta``  — compact before→after summary; shape depends on ``op``.

Append semantics
----------------
One ``O_APPEND`` ``write`` of a single newline-terminated JSON line.  A single
``write`` under ``O_APPEND`` is atomic on POSIX for our line sizes.  No fsync —
the reflog is advisory; fsyncing the index is sufficient (ADR-000117 §1).

Reader tolerance (TASK-000113)
-------------------------------
A trailing partial/unparseable line is skipped silently; interior bad lines are
warn-skipped.  A missing file is an empty log — never an error.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from squads._models._schema import SCHEMA_VERSION


@dataclass
class ReflogLine:
    """One parsed reflog entry."""

    v: str
    ts: str
    actor: str
    op: str
    target: str
    delta: dict[str, Any]


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
) -> None:
    """Append one compact JSON line to the reflog file (IO runs on a worker thread).

    The swallow of ``(OSError, TypeError, ValueError)`` is kept **inside** the
    threaded closure so no exception ever crosses the loop boundary
    (ADR-000153 Decision 2 — reflog never-raise contract).
    """
    from squads import _aio

    record: dict[str, Any] = {
        "v": SCHEMA_VERSION,
        "ts": ts,
        "actor": actor,
        "op": op,
        "target": target,
        "delta": delta,
    }

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
        # Trailing partial line (no terminating "\n") — skip silently (ADR-000117 §2).
        lines = lines[:-1]

    out: list[ReflogLine] = []
    for i, raw_line in enumerate(lines):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            data = json.loads(raw_line)
            out.append(
                ReflogLine(
                    v=str(data.get("v", "")),
                    ts=str(data.get("ts", "")),
                    actor=str(data.get("actor", "")),
                    op=str(data.get("op", "")),
                    target=str(data.get("target", "")),
                    delta=data.get("delta", {}),
                )
            )
        except Exception:
            # Interior malformed line — warn and skip (ADR-000117 §2).
            print(
                f"[squads reflog] warning: skipping malformed line {i + 1} in {path}",
                file=sys.stderr,
            )

    return out
