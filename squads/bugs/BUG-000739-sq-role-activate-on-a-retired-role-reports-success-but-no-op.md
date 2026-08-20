---
id: BUG-739
sequence_id: 739
type: bug
title: sq role activate on a retired role reports success but no-ops
status: Verified
author: qa
priority: medium
severity: medium
refs:
- REV-733
created_at: '2026-08-03T15:40:02Z'
updated_at: '2026-08-15T19:55:21Z'
---
<!-- sq:body -->
## Symptom

`sq role activate <slug>` on a role whose roster status is retired (e.g.
`Archived`) prints the same success line it prints for a real activation, and
leaves the role's status untouched.

## Reproduction (driven, throwaway squad under scratchpad, not this repo's data)

```
sq init --backend claude_code --default-names
sq role tech-writer status Archived
sq list -t role -a --json   # confirms: tech-writer -> Archived
sq role activate tech-writer
```

Observed: `activated Theo Writer (ROLE-8)`, exit 0.
Expected: either the role ends up live, or the command refuses/says nothing
changed — not the unqualified success wording.
Actual status after the command (driven, `sq list -t role -a --json`):
still `Archived`. `sq check` before and after both report `no issues`, i.e.
nothing else is watching for this.

Re-driven against a **project-override (non-bundled) role** scaffolded via
`sq override scaffold --new <slug>`, not just a bundled one — same result:
create → activate → retire → activate again still prints `activated …` and
the status stays `Archived`. So the defect isn't bundled-role-specific.

## Mechanism (read, `src/squads/_services/_roster.py::activate_role` +
`_services/_base.py::roster_item`)

`roster_item()` matches an existing entry by slug alone, with no status
filter. `activate_role()` treats any hit as "already handled" and returns it
untouched:

```
existing = await self.roster_item(ROSTER_ROLE, slug)
if existing is not None:
    return existing
```

The CLI (`_cli/_role.py::activate_role`) then prints `activated …` off
whatever `Item` comes back, unconditionally — it never checks the returned
item's status against what "activate" is supposed to guarantee.

## Scope: narrower than "any roster verb" (driven + read)

This is isolated to `sq role activate`. The sibling create verbs do **not**
share it — driven against the same retired-then-recreate shape:

- `sq dev add --tech <t>` on a slug whose dev-role entry is retired: errors
  `a developer with slug '<slug>' already exists` (does not silently no-op).
- `sq skill add <name>` on an existing (even Archived) skill slug: same —
  errors `a skill with slug '<slug>' already exists`.
- `add_operator` (read, `_services/_roster.py`) raises the same way on any
  existing slug regardless of status.

So `activate_role`'s "return the existing entry untouched" is not the
project's general idempotent-create pattern — every other roster create verb
raises loudly on an existing slug instead of returning silently. `activate_role`
is the one outlier, and it's specifically the status-blind existence check
that turns "idempotent create" (fine when the existing entry is already live)
into a false success report (when it isn't).

Also driven, for contrast, the two shapes that are **not** buggy:
- Activating an already-**live** role (`sq role activate manager` while
  `manager` is `Active`) prints `activated …` and that's true — the
  postcondition already holds.
- Activating a slug with **no** roster entry at all (fresh
  `sq override scaffold` role, never activated) genuinely creates it live.

The false-success shape is specifically: roster entry exists AND its status
is not in the type's live set.

## Why it matters (inferred from the mechanism + read of
`_interactions/__init__.py::orphaned_playbook_guide_message`)

`sq check`/`sq sync` warn when a playbook guide names a role that isn't
live. That warning used to point at `sq role activate <slug>` for a retired
role too. A recent commit (`8473abf`, already on this branch) changed the
wording so a *retired* role's warning now names
`` sq role <slug> status <live-initial> `` instead, precisely because
`activate` doesn't perform the transition — read in the function's own
docstring, which documents this exact no-op as the reason for the split
wording. That commit routes the generated warning around this bug; it is
not a fix for `activate` itself, and anyone who reaches for `sq role
activate` directly (habit, docs, muscle memory, or an older warning cached
in a terminal scrollback) still hits the false success and an unexplained
recurring `sq check` warning.

## Severity justification

Not data loss or corruption — the role's status file is fine, nothing is
written incorrectly, and the real remedy (`sq role <slug> status <live>`) is
one command away once noticed. But it's a command reporting a false
success on a normal, reversible roster operation, with no other signal
(`sq check` is silent) to catch the mismatch — comparable to this repo's
other "misleading report, not data-loss" bugs rated medium (e.g. BUG-11,
`sq check` flagging operator authors/assignees as unregistered).

## Design question: is `activate` a create verb, or a "make it live" verb?

I think it should guarantee the role ends up live, refusing rather than
silently returning when it can't. Two things point that way:

- The verb's own name says "activate" — a user reading `activated Theo
  Writer` has no reason to also check the role's status afterward.
- It's the only roster create verb that returns an existing entry instead
  of erroring (see Scope above). Matching its siblings (`dev add`,
  `skill add`, `add_operator`) means erroring on a non-live existing entry
  with the same remedy hint the landed check-message fix already uses
  (`` sq role <slug> status <live-initial> ``), rather than teaching
  `activate` to also perform arbitrary status transitions. That keeps
  "create" and "transition" as separate verbs project-wide instead of
  making `activate` a special case that blurs the two.

I'd reject the other candidate (`activate` silently performing the
transition) for the same reason: it would make role activation the only
roster surface where a create verb can also revive a retired entry,
inconsistent with the sibling verbs and with the create/transition split
the rest of the CLI holds.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-06T20:28:15Z] Catherine Manager:
  - Corroborating evidence from the tech-writer, driving the same command family while correcting the 0.13.0 notes: there are two non-interchangeable revive commands -- sq role activate <slug> for a slug with NO roster entry, and sq role <slug> status Active for a retired one -- and running the wrong one prints success and changes nothing. That is this bug, reached from a second direction by a different agent on different work. The changelog now says the message picks the right command rather than naming activate; that routes around the defect and does not close it.
- [2026-08-15T14:37:44Z] Elias Python:
  - Fixed as ruled. activate_role now returns an existing entry only when its status is in the roster role type live set; a non-live existing entry raises SquadsError naming the entry, its actual status, and the remedy sq role <slug> status <live-initial> (live_initial(ROSTER_ROLE), not a hardcoded Active). Driven: retired -> exit 1 with that message and the status unchanged; already-live -> unchanged idempotent success; no entry at all -> still created live; following the named remedy then re-activating works.
  - Scope check before implementing: init() activates into an empty roster and adopt() already filters by slug against every existing role item whatever its status, so neither boot path can reach the new refusal.
  - Corrected the now-false claim in orphaned_playbook_guide_message docstring, which documented activate as returning a retired entry untouched. The split wording it justifies is unchanged and now has a stronger reason: naming activate for a retired role would name a command that errors.
  - Tests: tests/service/test_activating_a_retired_role_is_refused.py (6, including one pinning activate against add_dev/add_skill/add_operator on a retired slug so a future "make it idempotent" change has to face all four) and a CLI smoke in tests/cli/test_destructive_body_and_roster_verbs_refuse_cli.py. Falsified by restoring the status-blind return: 4 red, reverted by exact reverse substitution, green again.
  - Also updated tests/integration/test_playbook_guide_dropped_for_a_non_live_role_is_reported.py, whose driven assertion recorded the defect as behaviour ("activate_role is a no-op here"); it now drives the refusal.
- [2026-08-15T19:55:21Z] Catherine Manager:
  - Verified by driving, after my first probe misled me. A --roles core squad has no tech-writer, so my silenced status Archived failed and activate then correctly CREATED the role -- which looked like the defect surviving. Re-driven with the setup visible: retire exits 0 (ROLE-5 to Archived), then sq role activate tech-writer exits 1 with "activate creates a role, it does not revive one" and names sq role tech-writer status Active. Suspect the probe first; I did not, at first.
<!-- sq:discussion:end -->
