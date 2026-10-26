"""Schema 0.3 → 0.4 runner: additive session lineage fields, a no-op that touches no file.
``_actor.py`` gains an optional session pair seeded once from
``SQUADS_SESSION_ID``/``SQUADS_PARENT_SESSION_ID`` at the CLI root callback (not settable by
``--as``, ``--author`` or any later flag). Every reflog line carries optional top-level
``session_id`` and ``parent_session_id`` (omitted when ``None``; ``actor`` stays a flat slug and
slug-only legacy lines parse with both as ``None``). Item frontmatter gains optional
``created_session`` and ``modified_session``, absent meaning legacy; ``sq repair`` of legacy items
needs no rewrite.

Guarantee, mandatory in any surface presenting these fields: squads is a passive tool, never in the
spawn path, reading optional env vars from its own invocation and recording them. The pair is
best-effort, untrusted and observability-only, not tamper-evident or signed and never a basis for
authorisation; a forged, copied or absent id is indistinguishable from a real one.
"""

from squads._paths import SquadPaths

MANUAL = """\
## Schema 0.3 → 0.4 — additive session lineage fields

No manual steps are required for existing squads.  The new fields are entirely
optional and additive; all existing item files and reflog lines remain valid
without any rewrite.

**What the upgrade gives you (once your orchestrator skills propagate the env
vars):**

- Set `SQUADS_SESSION_ID` in the environment before calling `sq` commands to
  have every mutating operation record that session id on the reflog line and on
  the item's frontmatter (`created_session` / `modified_session`).
- Set `SQUADS_PARENT_SESSION_ID` to record the immediate parent session (the
  session that spawned the current one).
- `sq reflog --json` now surfaces `session_id` and `parent_session_id` fields
  on each entry when they were set at write time; absent on legacy lines.

**Important — guarantee framing (read before exposing these fields in a UI or
check):**
  squads is a passive tool, never in the spawn path.  It reads optional env vars
  from its own invocation and records them.  The result is best-effort,
  untrusted, observability-only — not tamper-evident, not signed.  A forged,
  copied, or absent session id is indistinguishable from a real one.  Never use
  these fields as an authorisation input.
"""


def migrate(paths: SquadPaths) -> int:
    """No-op: every 0.4 field is additive, so old item files and reflog lines stay valid and ``sq
    repair`` rebuilds the index from the unmodified frontmatter. Returns 0.
    """
    _ = paths  # unused — kept for the ``Migration.run`` signature
    return 0
