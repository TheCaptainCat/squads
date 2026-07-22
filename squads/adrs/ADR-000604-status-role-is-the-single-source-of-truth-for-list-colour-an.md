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
created_at: '2026-07-22T14:03:28Z'
updated_at: '2026-07-22T15:20:19Z'
---
<!-- sq:body -->
## Context

`squads` renders a work-item's status in three surfaces — the CLI list/tree, the TUI, and the
VS Code extension tree — and each surface makes two decisions from a status: what **colour/
emphasis** to draw it in, and whether to **show it by default** (versus only under `--all`). Today
those decisions are driven by overlapping inputs — the per-status `badge` emoji, a `terminal` bool,
`is_open` (`not terminal`, in the `--json` item contract), and a handful of `role` markers — doing
three jobs (lifecycle end-state, workload open/closed, display dim/hide) between them, with each
client re-blending them its own way.

`StatusSpec.role` already exists as the "semantic role marker for engine rules that key on a
specific status" (`active`/`superseded`/`retired`), and the records-hide-by-`retired` behaviour
proves the pattern. This decision promotes `role` to the single status axis — and makes a role a
first-class **object** that carries the behaviour, so the two overlapping flags can be retired and
adopters can define their own roles.

## Decision

**`role` is the SOLE explicit status axis, and a role is a first-class OBJECT — not a string.** A
status references one role by name; that role object carries the behaviour (`settled`, `hidden`,
`color`). The per-status `terminal` field and the `is_open` field/concept are **both dropped**,
derived instead from the referenced role's properties. The badge glyph stays its own independent
explicit attribute (§3).

### 1. A role is an object — the role catalog

A new spec construct `[roles.<name>]`, sibling to `[statuses.…]`, declares the role catalog. Each
role carries:

- `settled: bool` — is this a resting/end state (the old `terminal`)?
- `hidden: bool` — hidden from the default (non-`--all`) view?
- `color: <intent>` — a semantic colour intent (not a concrete colour).

A status names one role; its settled/hidden/color come from that role object:

```toml
[roles.in_force]
settled = true
hidden  = false
color   = "info"

[statuses.Accepted]
role  = "in_force"
badge = "…"          # badge stays explicit and independent (§3)
```

**Roles are OPEN; colour intents are a CLOSED palette.** An adopter may define custom roles with
their own `settled`/`hidden`/`color` (open vocabulary, discovered via `--json`). `color` must be
one of a **closed semantic-intent vocabulary** — `positive` / `danger` / `warning` / `muted` /
`neutral` / `info` — validated at load (Plane 1); an unknown intent fails closed. Each client maps
the intent to its own theme (CLI `rich` ANSI, TUI Textual attribute, VS Code `ThemeColor`), with a
**neutral fallback** for any intent it does not recognise.

`role` stays optional on a status; an absent role resolves to the bundled `pending` role (neutral /
live / shown), so a custom status is fail-safe-visible until its author assigns one.

### 2. The default role catalog + status assignments

Eight bundled roles, one row per role (its object properties + the statuses that reference it):

| role | statuses | settled | hidden | color-intent |
|---|---|---|---|---|
| `pending` | Draft, Ready, Proposed, Requested, Todo | false | false | `neutral` |
| `active` | InProgress, InReview, ChangesRequested, Fixed, Active | false | false | `positive` |
| `attention` | Open | false | false | `danger` |
| `blocked` | Blocked | false | false | `danger` |
| `in_force` | Accepted, Published | true | false | `info` |
| `done` | Done, Verified, Approved | true | true | `positive` |
| `retired` | Cancelled, Rejected, Deprecated, WontFix, Archived | true | true | `muted` |
| `superseded` | Superseded | true | true | `muted` |

On the assignments:

- `active` is "live and current" — non-terminal work-in-flight plus the live roster/contract
  `Active` state. `in_force` is the positive **settled** record state that must stay visible (an
  Accepted ADR, a Published guide): `settled=true, hidden=false` — a resting end that still shows.
- `done` vs `in_force` is the split that matters: both settled and positive, but completed **work**
  drops off the board (`hidden=true`) while an in-force **record** stays (`hidden=false`). Category
  need no longer be consulted — the role object encodes the intended presence.
- `attention` and `blocked` are distinct roles that both resolve to the `danger` (red) intent:
  `attention` is the fresh needs-action/triage red (a bug that is `Open`), `blocked` the
  actively-stuck red. Distinct roles keep the semantic split (a surface may later map them to
  different themes) while both read red today. `warning` is unused by the defaults — reserved in the
  palette for adopters.
- `Rejected` is in `retired` (settled, hidden, muted) — a deliberate change (today a Rejected record
  carries no role and is shown).
- `superseded` stays distinct from `retired` (same properties) because it carries the
  incoming-`supersedes`-edge expectation the validator model keys on.

### 3. Colour and badge: two independent concerns

- **Colour** comes from the role's `color` intent, mapped to a concrete colour **per client** in
  each surface's own code (no concrete colour in the spec — one colour can't serve three theme
  systems). Single-sourced semantic axis, per-client rendering, neutral fallback.
- **Badge** stays its own explicit per-status field. `StatusSpec.badge` is NOT removed and NOT
  derived from role — the glyph and the colour are independent, coexisting concerns; a status sets
  whatever glyph it likes regardless of its role. No `badge` deprecation, no shim.

### 4. `terminal` and `is_open` dropped — derived from the role object

Both are removed as explicit fields/concepts and re-expressed as reads of the referenced role:

- **terminal-ness** = `role.settled`.
- **open-ness** (`is_open`) = `not role.settled`.
- **default visibility** (`hidden_by_default`) = `role.hidden`.

The earlier "`LIVE_ROLES` / `SETTLED_ROLES` / `HIDDEN_ROLES` code-sets" framing is superseded: those
sets are now a **consequence of the role definitions** (the set of settled roles is just
`{r | roles[r].settled}`), computed from the catalog, never a hardcoded list. The
"a lifecycle must reach a terminal status" lint becomes "must reach a status whose role is
`settled`". `terminal_set()` / the golden-lock `TERMINAL` frozenset are computed from role
membership.

**No expressiveness loss.** The one thing an independent `terminal` flag could express that a single
role-set could not — "a settled end that still shows" vs "a settled end that hides" — is carried by
two role properties (`settled` + `hidden`), e.g. `in_force` (`settled=true, hidden=false`) vs `done`
(`settled=true, hidden=true`). So dropping the flag costs nothing.

### 5. Discoverable via `--json`, never client-hardcoded

The role catalog and each status→role reference are exposed on the machine surface, the same way
`category` rides the types catalog and badge codes ride the collections catalog — clients fetch and
consume, re-deriving no policy:

- **`sq workflow roles --json`** (new): one row per role — `{role, settled, hidden, color}`.
- **`sq workflow statuses --json`**: drops `terminal`; keeps `role` (the reference) and `badge`.

A client joins an item's `status → role → {settled, hidden, color}`; the policy (which roles are
settled/hidden, what colour intent each is) lives once, in the role objects. The separate
`shown_by_default` field floated earlier is unnecessary — `role.hidden` in the roles catalog is the
single source.

### 6. Consumer / contract audit (role-object shape)

**Core (`_workflow`):**
- New `RoleSpec` model (`settled: bool`, `hidden: bool = false`, `color: str`) + `WorkflowSpec.roles:
  dict[str, RoleSpec]`, loaded from `[roles.<name>]`.
- `StatusSpec.terminal` field → **removed**; `StatusSpec.role` is the reference (kept, now
  catalog-checked).
- `WorkflowSpec.is_open(s)` → `not roles[statuses[s].role].settled`.
- `WorkflowSpec.terminal_set()` → `{s | roles[statuses[s].role].settled}`.
- `WorkflowSpec.hidden_by_default(type, s)` → `roles[statuses[s].role].hidden` (category branch
  dropped).
- `_check_reachable_terminal` lint → "reach a status whose role is `settled`".
- `_validate` gains Plane-1 checks: every `status.role` names a declared role; every `role.color` is
  in the closed intent palette. The old "terminal status not in status set" belt-check is removed.
- `_workflow/__init__.TERMINAL` frozenset (golden-lock export) → recomputed via role-derived
  `terminal_set()`.

**Services:**
- `_services/_roster.py` open/closed bucket, `_services/_refs.py` blocker traversal +
  `RefContext.is_open` (5 sites), `_services/_collab.py` open-item guard → all read
  `not role.settled` (via the `is_open`/`is_live` helper).
- `_services/_base.py` default-list visibility → unchanged call site (`hidden_by_default`
  re-derives).

**CLI:**
- `_cli/_main.py` `sq tree` / `sq list` `--json` emit of `"is_open"` (2) → **dropped**.
- `_cli/_main.py` `sq mine` open filter + `"is_open"` emit → filter reads `not role.settled`; field
  **dropped** from payload.
- `_cli/_main.py` `sq workload` open/closed counts (roster) → `role.settled`.
- `_cli/_main.py` `sq list` visible filter + hidden count → unchanged (`hidden_by_default`).
- `_cli/_workflow_cmd.py` status catalog `"terminal"` → **dropped**; add the **`sq workflow roles
  --json`** catalog; `role` + `badge` stay on the status catalog. Row colour now keyed on
  `role.color`.
- `_rendering/templates/workflow.md.j2` cheatsheet `.terminal` → a `role.settled` check via a spec
  helper exposed to the template.

**Tests / goldens (implementation task):**
- `test_accepted_and_published_are_terminal`, `test_status_machine_transitions`,
  `test_workflow_spec_artifact` → re-express against the role-derived settled set.
- `test_no_unallowlisted_module_level_mutable_state` → `TERMINAL` stays allowlisted (derived CODE
  constant).
- `tests/goldens/workflow_statuses.json` → regenerate (drop `terminal`; `role` populated); add a
  new `workflow_roles.json` golden.

**VS Code extension (rides FEAT-570 US2/US3 records-view work):**
- `types.ts` `is_open` (node + item) and `terminal` (status-catalog entry) → **removed**; add a
  roles-catalog type `{role, settled, hidden, color}`.
- `sqAdapter.ts` runtime guards for `is_open` (2) and `entry.terminal` → **removed**; add a roles
  catalog fetch + guard.
- `domain/treeMapping.ts` / `metaView.ts` / `listView.ts` `closed: !item.is_open` (3) → `closed`
  from the item's `role.settled` (joined via the roles catalog); dim/hide keyed on `role.hidden`.
- Colour: map `role.color` intent → `vscode.ThemeColor` with a neutral fallback; the
  `emphasisForNode` precedence stays, fed from role.

**TUI:**
- `_tui/_reader.py` uses only `status_badge` (glyph) — nothing to remove; the TUI gains role-`color`-
  keyed row colour (intent → Textual attribute, neutral fallback) as new behaviour.

## Consequences

- A role is now the single, self-describing status axis: `settled`/`hidden`/`color` live on the role
  object, statuses reference it, and `terminal`/`is_open` are gone. Reviewers and consumers key
  everything off the role.
- Roles are adopter-extensible (open), while colour stays a closed semantic-intent palette so every
  client can render any role safely (neutral fallback). This matches the project boundary: vocabulary
  (roles, and which role a status takes) in the spec; behaviour (intent → concrete colour) in each
  client's code.
- `hidden_by_default` loses its category branch (`= role.hidden`) — records-hide-by-retired-role was
  the first instance; this generalises it. Current default-list behaviour is preserved for
  work/roster and for records (Accepted / Published stay shown; Superseded / Deprecated hide), with
  one deliberate change: `Rejected` now hides.
- The row/text colour is fully defined and consistent across all three surfaces (all key on
  `role.color`); the badge glyph is unaffected.
- `--json` contract change (client-facing): item rows drop `is_open`; the status catalog drops
  `terminal`; a new `sq workflow roles --json` catalog carries `{role, settled, hidden, color}`.
  Clients read `role` + the roles catalog and derive live-vs-settled / hidden / colour themselves.
  The VS Code extension and TUI migrate to role; this rides the FEAT-570 US2/US3 records-view work.
- **No frontmatter / `SCHEMA_VERSION` change.** Verified: `is_open` and `terminal` never appear in
  item frontmatter or `.squads.json` (they are spec-derived / `--json`-only), and `role` / the new
  `[roles.…]` catalog are workflow-spec vocabulary. This is a spec-format + `--json`-contract change
  only — no schema bump, no `sq migrate` data migration, per the adopter back-compat policy. The
  bundled spec is regenerated (the `[roles.…]` catalog is added, `terminal` lines removed, each
  status gains its `role`); `badge` is untouched, so no read-compat shim is needed.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T14:32:03Z] Robert Architect:
  - [amendment — 2026-07-22] Folded in two op-pierre calls after his ADR-604 read (status left Proposed for his accept). (1) Added an 8th role 'attention' (red, shown) and moved 'Open' into it — Open keeps its red; attention (fresh needs-action) and blocked (actively-stuck) are two distinct roles that both render red today, a surface may differentiate them later without a vocab change. (2) Reversed the section-2 badge recommendation: StatusSpec.badge STAYS an explicit per-status field — not removed, not derived from role. Role drives row/text colour + visibility only; the glyph stays the status's own independent badge. Dropped the badge-removal/deprecation-shim step accordingly. Everything else unchanged: role→visibility one rule, is_open workload-only, --json item shape unchanged, no schema bump, Rejected→retired.
- [2026-07-22T14:54:58Z] Robert Architect:
  - [amendment — 2026-07-22] op-pierre escalated: role is now the SOLE explicit status axis — BOTH terminal and is_open are dropped, not just demoted (supersedes the earlier is_open-workload-only line). Folded in: (1) StatusSpec.terminal field removed; terminal-ness ⟺ role ∈ SETTLED_ROLES {in_force,done,retired,superseded}; live ⟺ role ∈ LIVE_ROLES {pending,active,attention,blocked}; hidden ⟺ role ∈ HIDDEN_ROLES {done,retired,superseded} (in_force is settled-but-shown). (2) is_open dropped entirely — field, --json, concept; the reach-a-terminal lint becomes reach-a-settled-role, terminal_set()/TERMINAL recompute from role membership. (3) --json drops is_open from item rows AND terminal from the status catalog (+ adds derived shown_by_default); VS Code + TUI migrate to role, riding FEAT-570 US2/US3. (4) No expressiveness loss — 'resting end that still shows' = in_force. (5) Verified is_open/terminal never touch item frontmatter or .squads.json → NO SCHEMA_VERSION bump / no data migration; spec-format + --json only. Added a full consumer/contract audit section (core/services/CLI/templates/tests/VS Code/TUI) enumerating every is_open/terminal/TERMINAL/terminal_set site and its role re-expression. Unchanged: 8-role vocab incl attention/Open, role→colour+visibility, badge explicit (not derived), Rejected→retired. Status left Proposed.
- [2026-07-22T15:18:32Z] Robert Architect:
  - [amendment — 2026-07-22] op-pierre converged on the role-as-OBJECT model (supersedes both the single-role-code-sets and multi-tag options); manager accepts after reading. Folded in: (1) role is a first-class object via a new [roles.<name>] spec catalog (sibling to [statuses]) — RoleSpec{settled, hidden, color}; a status references one role by name and inherits its behaviour. (2) Roles are OPEN (adopter-definable, --json-discovered); color is a CLOSED semantic-intent palette {positive,danger,warning,muted,neutral,info}, Plane-1 validated, each client maps intent→its own theme with a neutral fallback. (3) Discoverable via a new 'sq workflow roles --json' catalog {role,settled,hidden,color} + role on the status catalog; clients fetch+consume, re-derive nothing (same as category on the types catalog) — the separately-floated shown_by_default field is dropped in favour of role.hidden. (4) terminal & is_open stay dropped, now derived from the role object: terminal=role.settled, is_open=not role.settled, hidden_by_default=role.hidden; the LIVE/SETTLED/HIDDEN framing becomes a consequence of role definitions, not hardcoded sets. (5) Unchanged: 8 default roles (attention/Open=danger-red, in_force, done, retired incl Rejected, superseded, pending, active, blocked), badge explicit per-status (not derived), no SCHEMA_VERSION change (spec+--json only), client migration rides FEAT-570 US2/US3. Revised the role table into role-object definitions and refreshed the consumer/contract audit for the object shape. Status left Proposed.
- [2026-07-22T15:20:18Z] Pierre Chat:
  - Accepted (converged through the design discussion; manager accepted after reading the final body). The status role becomes a first-class OBJECT carrying {settled, hidden, color-intent}; a status references one role and inherits its behavior. role is the sole status axis — terminal and is_open are dropped and derived (terminal=role.settled, is_open=not settled, hidden_by_default=role.hidden). Roles are open/adopter-definable and --json-discoverable (sq workflow roles --json); color is a closed semantic-intent palette each client maps to its theme. badge stays explicit per-status. No SCHEMA_VERSION change. Supersedes FEAT-570 US1's ad-hoc RETIRED_STATUS_ROLES approach — that work gets reworked onto role.hidden.
<!-- sq:discussion:end -->
