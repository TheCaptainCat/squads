---
summary: Reconcile the whole ticket subtree's statuses before delegating — never promote
  just the leaf
created_at: '2026-07-24T12:31:35Z'
---
Keep the whole ticket subtree's statuses coherent before delegating — never promote just the leaf.

When a coordinator hands work to an agent, the full hierarchy must already reflect reality **before** the spawn, not get patched afterward: when a task starts, its parent feature AND the mapped stories move too (e.g. all → InProgress); when work finishes, they roll to Done top-down together. A parent must never trail its child (e.g. a feature left in Draft while its task is InProgress).

How to hold it:
- At every transition/handoff, reconcile top-down: epic → feature → story → task → subtask.
- Verify coherence with `sq tree <id> --json` (or `show`) BEFORE spawning, and again when the agent returns.
- Record the *why* on the item (a `comment`), not just the status flip — the board is the team's shared memory; the next agent reads it.
- Close review findings as they're fixed (mark Fixed + cite the fix), don't let them pile up as false "Open" debt.

CLI note: items use `sq <type> <n> status <S>`; sub-entities (story/subtask/finding) use `sq <type> <n> <kind> <k> update --status <S>`.