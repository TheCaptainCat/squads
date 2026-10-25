---
id: ADR-604
sequence_id: 604
type: decision
title: Status role is the single source of truth for list colour and default visibility
status: Accepted
author: architect
refs:
- FEAT-570
- ADR-541
- ADR-474
- ADR-323
- ADR-696
- ADR-320
created_at: '2026-07-22T14:03:28Z'
updated_at: '2026-10-25T21:35:36Z'
---
<!-- sq:body -->
## Context

`squads` renders a status in three surfaces (the CLI list and tree, the TUI, the VS Code tree), and
each surface decides two things from it: what **colour or emphasis** to draw it in, and whether to
**show it by default** (versus only under `--all`). Overlapping inputs for those decisions (a
per-status `terminal` flag, an `is_open` flag on item rows, a badge emoji, a few role markers) let
each client re-blend them its own way.

A status role, the semantic marker engine rules key on, already proves the pattern. This decision
makes `role` the single status axis and a role a first-class **object** that carries the
behaviour, so the overlapping flags have no reason to exist and adopters can define their own
roles.

## Decision

**`role` is the sole explicit status axis, and a role is a first-class object, not a string.** A
status references one role by name; the role object carries the behaviour. There is no per-status
`terminal` field and no `is_open` field: both are derived from the referenced role. The badge glyph
stays its own independent attribute (§3).

### 1. The role catalog

`[roles.<name>]`, sibling to `[statuses.…]`, declares the role catalog (`RoleSpec`,
`WorkflowSpec.roles`). This decision gives a role three properties:

- `settled: bool` — a resting or end state;
- `hidden: bool` — hidden from the default (non-`--all`) view;
- `color: <intent>` — a semantic colour intent, not a concrete colour.

Later decisions add behaviour flags to the same object: `live` (ADR-696 §2a: whether a status
materialises a roster entry into backend config), `blocked` (ADR-864, as amended under ADR-696 §3:
the role's statuses mean the item waits on something else) and `deferred` (ADR-1102: the work is
carried by another item).

```toml
[roles.in_force]
settled = true
hidden  = false
color   = "info"

[statuses.Accepted]
role = "in_force"
```

**Roles are open; colour intents are a closed palette.** An adopter may define roles with their
own properties. `color` must be one of `positive` / `danger` / `warning` / `muted` / `neutral` /
`info`, validated at load; an unknown intent fails closed. Each client maps the intent to its own
theme (CLI `rich` style, TUI Textual attribute, VS Code `ThemeColor`), with a **neutral fallback**
for any intent it does not recognise.

`role` is optional on a status: an absent role resolves to the bundled `pending` role (neutral,
shown), so a custom status is fail-safe-visible until its author assigns one. A role a status
names must be declared in the catalog, checked at load.

### 2. The bundled roles and status assignments

| role | statuses | settled | hidden | color |
|---|---|---|---|---|
| `pending` | Draft, Ready, Proposed, Requested, Todo | false | false | `neutral` |
| `active` | InProgress, InReview, ChangesRequested, Fixed, Active | false | false | `positive` |
| `attention` | Open | false | false | `danger` |
| `blocked` | Blocked | false | false | `danger` |
| `in_force` | Accepted, Published | true | false | `info` |
| `done` | Done, Verified, Approved, Noted | true | true | `positive` |
| `deferred` | Deferred | true | true | `info` |
| `retired` | Cancelled, Rejected, Deprecated, WontFix, Archived | true | true | `muted` |
| `superseded` | Superseded | true | true | `muted` |

- `active` is "live and current": work in flight plus the live roster and contract `Active` state.
  `in_force` is the positive settled record state that stays visible (an Accepted ADR, a Published
  guide).
- `done` versus `in_force` is the split that matters: both settled and positive, but completed
  work drops off the board (`hidden`) while an in-force record stays. Category need not be
  consulted; the role encodes the intended presence.
- `attention` and `blocked` both read red: `attention` is the needs-action red (an `Open` bug or
  finding), `blocked` the stuck red. `warning` is unused by the bundled roles and reserved for
  adopters.
- `Rejected` is `retired`: settled, hidden, muted.
- `superseded` stays distinct from `retired` (same display) because the supersession validator
  keys on it.

### 3. Colour and badge are independent

- **Colour** comes from the role's `color` intent, mapped to a concrete colour per client; no
  concrete colour lives in the spec, since one colour cannot serve three theme systems.
- **Badge** stays its own explicit per-status field (`StatusSpec.badge`), never derived from the
  role.

### 4. Derived, never stored

- terminality = `role.settled`;
- open-ness (`WorkflowSpec.is_open`) = `not role.settled`;
- default visibility (`hidden_by_default`) = `role.hidden`, with no category branch.

The sets of settled or hidden roles are computed from the catalog, never a hardcoded list. The
"a lifecycle must reach a terminal status" lint is "must reach a status whose role is settled".
Two properties (`settled`, `hidden`) express everything an independent `terminal` flag could, for
example `in_force` (settled, shown) versus `done` (settled, hidden).

### 5. Discoverable via `--json`, never client-hardcoded

- **`sq workflow roles --json`**: one row per role, `{role, settled, hidden, color}` plus the flags
  later decisions add (`live`, `blocked`, `deferred`).
- **`sq workflow statuses --json`**: `{status, role, badge}`; no `terminal`.
- Item rows carry no `is_open`.

A client joins an item's `status → role → properties`; the policy lives once, in the role objects.

## Consequences

- One self-describing status axis: consumers key everything off the role.
- Roles are adopter-extensible while colour stays a closed palette, so every client renders any
  role safely. Vocabulary (roles, and which role a status takes) is in the spec; behaviour (intent →
  concrete colour) is in each client's code.
- Default-list behaviour follows `role.hidden` for every category: Accepted and Published stay
  shown; Superseded, Deprecated and Rejected hide.
- The row colour is consistent across all three surfaces; the badge glyph is unaffected.
- This is a spec-format and `--json` change only: `is_open`, `terminal` and roles never appear in
  item frontmatter or the index, so there is no schema bump and no data migration.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T14:32:03Z] `architect` Robert Architect:
  - [amendment — 2026-07-22] Folded in two op-pierre calls after his ADR-604 read (status left Proposed for his accept). (1) Added an 8th role 'attention' (red, shown) and moved 'Open' into it — Open keeps its red; attention (fresh needs-action) and blocked (actively-stuck) are two distinct roles that both render red today, a surface may differentiate them later without a vocab change. (2) Reversed the section-2 badge recommendation: StatusSpec.badge STAYS an explicit per-status field — not removed, not derived from role. Role drives row/text colour + visibility only; the glyph stays the status's own independent badge. Dropped the badge-removal/deprecation-shim step accordingly. Everything else unchanged: role→visibility one rule, is_open workload-only, --json item shape unchanged, no schema bump, Rejected→retired.
- [2026-07-22T14:54:58Z] `architect` Robert Architect:
  - [amendment — 2026-07-22] op-pierre escalated: role is now the SOLE explicit status axis — BOTH terminal and is_open are dropped, not just demoted (supersedes the earlier is_open-workload-only line). Folded in: (1) StatusSpec.terminal field removed; terminal-ness ⟺ role ∈ SETTLED_ROLES {in_force,done,retired,superseded}; live ⟺ role ∈ LIVE_ROLES {pending,active,attention,blocked}; hidden ⟺ role ∈ HIDDEN_ROLES {done,retired,superseded} (in_force is settled-but-shown). (2) is_open dropped entirely — field, --json, concept; the reach-a-terminal lint becomes reach-a-settled-role, terminal_set()/TERMINAL recompute from role membership. (3) --json drops is_open from item rows AND terminal from the status catalog (+ adds derived shown_by_default); VS Code + TUI migrate to role, riding FEAT-570 US2/US3. (4) No expressiveness loss — 'resting end that still shows' = in_force. (5) Verified is_open/terminal never touch item frontmatter or .squads.json → NO SCHEMA_VERSION bump / no data migration; spec-format + --json only. Added a full consumer/contract audit section (core/services/CLI/templates/tests/VS Code/TUI) enumerating every is_open/terminal/TERMINAL/terminal_set site and its role re-expression. Unchanged: 8-role vocab incl attention/Open, role→colour+visibility, badge explicit (not derived), Rejected→retired. Status left Proposed.
- [2026-07-22T15:18:32Z] `architect` Robert Architect:
  - [amendment — 2026-07-22] op-pierre converged on the role-as-OBJECT model (supersedes both the single-role-code-sets and multi-tag options); manager accepts after reading. Folded in: (1) role is a first-class object via a new [roles.<name>] spec catalog (sibling to [statuses]) — RoleSpec{settled, hidden, color}; a status references one role by name and inherits its behaviour. (2) Roles are OPEN (adopter-definable, --json-discovered); color is a CLOSED semantic-intent palette {positive,danger,warning,muted,neutral,info}, Plane-1 validated, each client maps intent→its own theme with a neutral fallback. (3) Discoverable via a new 'sq workflow roles --json' catalog {role,settled,hidden,color} + role on the status catalog; clients fetch+consume, re-derive nothing (same as category on the types catalog) — the separately-floated shown_by_default field is dropped in favour of role.hidden. (4) terminal & is_open stay dropped, now derived from the role object: terminal=role.settled, is_open=not role.settled, hidden_by_default=role.hidden; the LIVE/SETTLED/HIDDEN framing becomes a consequence of role definitions, not hardcoded sets. (5) Unchanged: 8 default roles (attention/Open=danger-red, in_force, done, retired incl Rejected, superseded, pending, active, blocked), badge explicit per-status (not derived), no SCHEMA_VERSION change (spec+--json only), client migration rides FEAT-570 US2/US3. Revised the role table into role-object definitions and refreshed the consumer/contract audit for the object shape. Status left Proposed.
- [2026-07-22T15:20:18Z] `op-pierre` Pierre Chat:
  - Accepted (converged through the design discussion; manager accepted after reading the final body). The status role becomes a first-class OBJECT carrying {settled, hidden, color-intent}; a status references one role and inherits its behavior. role is the sole status axis — terminal and is_open are dropped and derived (terminal=role.settled, is_open=not settled, hidden_by_default=role.hidden). Roles are open/adopter-definable and --json-discoverable (sq workflow roles --json); color is a closed semantic-intent palette each client maps to its theme. badge stays explicit per-status. No SCHEMA_VERSION change. Supersedes FEAT-570 US1's ad-hoc RETIRED_STATUS_ROLES approach — that work gets reworked onto role.hidden.
- [2026-08-03T08:46:23Z] `architect` Robert Architect:
  - Lowest-severity item in the audit and it gets a note rather than a narrowing: the roles catalog row carries a fifth key, `live`, added additively by ADR-696 section 2a and declared at that end. No clause here was reversed. Everything else verified in force — eight bundled roles, the closed colour-intent palette validated at load, `terminal` and `is_open` gone, every surface keying on `role.color`.
  - Marked the enumeration at the point it appears rather than in all three places, and recorded the same lesson the type catalog gave: additive-superset makes the addition legitimate, and the enumeration at the frozen end is what has to move with it. Otherwise the freeze cannot be audited against the tree — five keys live against three decisions saying four. Added `related` edge to ADR-696.
- [2026-10-25T21:35:36Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the decision (role is the sole status axis, a role is an object) is unchanged. The bundled catalog has nine roles, not eight: added deferred (ADR-1102) and Noted under done. The role object and roles --json row carry live (ADR-696), blocked (ADR-864 as amended) and deferred (ADR-1102) beside settled/hidden/color; folded the 2026-08-03 note. Removed the pre-implementation consumer/contract audit (§6) and the FEAT-570 rollout notes.
<!-- sq:discussion:end -->
