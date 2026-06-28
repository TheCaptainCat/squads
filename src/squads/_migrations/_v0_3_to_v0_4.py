"""Schema 0.3 → 0.4 runner: additive session lineage fields (ADR-000158).

This migration is a **no-op runner** — it returns 0 touched files.

What changed (additive, back-compatible):

- ``_actor.py`` gains an optional session pair seeded once from
  ``SQUADS_SESSION_ID`` / ``SQUADS_PARENT_SESSION_ID`` environment variables at
  the CLI root callback.  Session fields are **not** settable by ``--as`` /
  ``--author`` or any later CLI flag.

- Every reflog line now carries optional top-level sibling fields
  ``session_id`` and ``parent_session_id`` (omitted when ``None``).  The
  ``actor`` field stays a flat slug string for back-compat (FEAT-000013
  stability).  Legacy slug-only lines parse with both fields as ``None``.

- Item frontmatter gains two optional fields, ``created_session`` and
  ``modified_session``, each holding the ``SQUADS_SESSION_ID`` string at
  creation / last mutation time.  Absent means legacy (no session env was set).
  ``sq repair`` of legacy items works unchanged — no rewrite is forced.

**No existing file needs to be modified** — all new fields are optional and
default to ``None`` / absent.  ``sq repair`` re-reads files and rebuilds the
index; the new fields simply won't be present on older items, which is the
correct "absent == legacy" state.

Guarantee (from ADR-000158, mandatory in any surface that presents these
fields):
  squads is a passive tool, never in the spawn path.  It reads optional env
  vars from its own invocation and records them.  The recorded session pair is
  **best-effort, untrusted, observability-only** — not tamper-evident, not
  signed, never a basis for authorisation.  A forged, copied, or absent session
  id is indistinguishable from a real one.
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
    """No-op — all 0.4 fields are additive and require no file rewrite.

    Old item files and reflog lines remain valid; ``sq repair`` rebuilds the
    index from the unmodified frontmatter.  Returns 0 (no files changed).
    """
    _ = paths  # unused — kept for the ``Migration.run`` signature
    return 0
