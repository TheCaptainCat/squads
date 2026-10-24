---
id: ADR-1102
sequence_id: 1102
type: decision
title: Findings gain Noted and Deferred; a Deferred finding names its carrier
status: Accepted
author: architect
refs:
- REV-1099:addresses
description: Open gains terminal Noted (done role) and Deferred (new deferred role);
  Deferred stores a deferred_to item pointer that sq check verifies
created_at: '2026-10-24T09:45:21Z'
updated_at: '2026-10-24T22:04:01Z'
---
<!-- sq:body -->
## Context

The bundled `finding` lifecycle is `Open → {Fixed, WontFix}`, `Fixed → {Verified, Open}`, `WontFix → {Open}`, `Verified` terminal. Two ordinary outcomes have no state (REV-1099 F7):

- an `info` finding that records a confirmed-good point, with nothing to fix, can only stay `Open` or be forced closed;
- a finding whose work moves to another item can only be `WontFix` with a note, which misstates the decision.

Both leave `Open` findings that are not debt, or terminal states that say the wrong thing. The ruling on F7 (op-pierre, 2026-10-24): add `Noted` for an info finding and `Deferred` with a pointer to the item that carries the work, so `sq check` can verify it.

What the engine has today, and what constrains the design:

- A sub-entity carries no refs. Its state is the typed slots of `SubEntity` (`status`, `assignee`, `severity`, `story`) plus `extra` for declared badge fields, stored in the parent's `subentities:` frontmatter list. Refs exist only on items, as forward edges (ADR-73).
- Status behaviour comes from the status role (`settled`, `hidden`, `color`, `live`, `blocked`), never from a status name. `blocked_has_blocker` is the precedent for "a status role that requires an edge": it keys on the `blocked` flag, not on the word `Blocked`.
- An override replaces a transition list whole, per source key (arrays are leaves in the deep merge). If the bundled lifecycle gave the new states outgoing edges (`Noted = ["Open"]`), a project whose override already redeclares `Open = ["Fixed", "WontFix"]` would keep those source keys without any edge into them, and the loader refuses the spec ("state 'Noted' unreachable from initial 'Open'"), stopping every command after the upgrade. This was confirmed by building the bundled spec with the two states added under that override. The same spec with the new states as targets only loads cleanly.
- A sibling rule (REV-1099 F10) adds a `sq check` warning for an Approved review that holds open findings.

## Decision

**Lifecycle.** The bundled `finding` lifecycle becomes:

```
Open     → { Fixed, WontFix, Noted, Deferred }
Fixed    → { Verified, Open }
Verified → { }
WontFix  → { Open }
```

`Noted` and `Deferred` are terminal and are declared only as targets of `Open`, with no table key of their own. Reopening either one takes `--force`. They are appended after `WontFix`, so the lifecycle's happy path (`Open → Fixed → Verified`, the first edge of each state) does not change.

**Statuses and badges.**

| Status | Role | Badge |
|---|---|---|
| `Noted` | `done` | 🔵 |
| `Deferred` | `deferred` (new) | 🟣 |

`Noted` is an outcome the review accepts as complete, so it takes the existing `done` role, as `Verified` does.

**A new status role, `deferred`.** The role catalog gains a boolean flag `deferred` (default `false`, TOML boolean only, like `blocked`) and a bundled role `deferred` with `settled = true`, `hidden = true`, `color = "info"`, `deferred = true`. The flag means that the work of an entity in this status is carried by another item, which the entity names. Every behaviour below keys on the flag, never on the word `Deferred`, so a project can name its own status (for example `Postponed`) and give it a role with the flag.

The loader refuses a spec in which an item lifecycle reaches a status whose role sets `deferred`. Items already have refs for this. This rule can be relaxed later, while a flag that silently does nothing on items could not be tightened later.

**The pointer.** `SubEntity` gains one typed slot, `deferred_to`: the formatted ID of the carrying item, written to the sub-entity's frontmatter entry only when set. It is a forward edge stored on the source, consistent with ADR-73, and is not a general ref list.

- Set it with `sq <type> <n> <kind> <k> update --status Deferred --deferred-to <ID>`. `--deferred-to` takes an ID or a number, resolves it like a ref, and refuses an item that does not exist.
- Moving into a deferred-flagged status without a pointer, given in the same command or already stored, is refused. `--force` waives only an illegal edge, never the missing pointer.
- `--deferred-to` on a sub-entity that is not in a deferred-flagged status, or on a kind whose lifecycle reaches no such status, is refused. Run on an already-deferred sub-entity without `--status`, it moves the pointer to another item.
- Leaving the deferred status clears the pointer. The discussion keeps the history.
- The sub-entity's display line shows "Deferred to `<ID>` — `<title>`" (the badge line of `show --full` and `--raw`, and a "deferred to:" line on `<kind> <k> show`), and a sub-entity's `--json` row carries `deferred_to` (`null` when absent).
- Retype, type rename and `sq renumber` remap `deferred_to` wherever they remap `parent` and `refs`. Removing the carrying item severs the pointer, as it severs incoming refs.

**The check.** A new validator, `subentity_deferral_resolved`, at warn level, is added to the `work` category bundle and to the sub-entity validator set. It reports:

- a sub-entity in a deferred-flagged status with no pointer, or with a pointer that does not resolve to an indexed item;
- a deferred sub-entity whose carrying item rests in a status with the `retired` role, the role that marks work stopped without being delivered (bundled `Cancelled`, and `WontFix` on a bug). It keys on the role, never on the name `Cancelled`, the same way the `done` role is read elsewhere. A carrier in `Superseded` (the `superseded` role) is not reported, since its work continues in the item that supersedes it;
- a pointer stored on a sub-entity that is not in a deferred-flagged status (a hand edit).

**Roll-ups and approval.** Both new states are settled, so they count as not open wherever openness is read. That covers the default sub-entity listings, the F10 rule (which must key on the settled role, not on the name `Open`) and anything else that asks "is this finding outstanding". Review approval is not gated, and this decision adds no gate.

**Overrides.** The change is additive. A project whose override redeclares the `Open` list keeps its own machine unchanged and does not get the two new states. It adopts them by adding `"Noted"` and `"Deferred"` to that list. A project's own status with a `deferred`-flagged role gets the pointer, the refusal and the check on the same terms.

**No migration.** No stored value changes meaning and no existing file needs rewriting. `SCHEMA_VERSION` is not bumped.

## Consequences

- Info findings close as `Noted` instead of piling up as false `Open` debt, and handed-off findings say where the work went, which `sq check` verifies.
- Reopening a `Noted` or `Deferred` finding takes `--force`. This is the price of not breaking projects that override the finding lifecycle, and it is off the ordinary path.
- The role catalog surface grows by one flag. `sq workflow roles --json` rows gain `deferred`, and sub-entity rows gain `deferred_to`, both additive.
- An older squads release ignores `deferred_to` when it reads a review, drops it the next time it writes that review, and reports `Noted`/`Deferred` as undeclared statuses. There is no schema bump to stop it, so the release's CHANGELOG entry states that a team upgrades together for this reason.
- The bundled reviewer guidance gains one line on `Noted` for info findings and `Deferred` with `--deferred-to` for work handed to another item.
- `docs/stability.md` needs a refresh: the sub-entity state paragraph (the pointer), the `sq workflow roles --json` row (`deferred`) and the finding's lifecycle wherever it is shown.

## Options rejected

- **Reopen edges on the new states** (`Noted`/`Deferred → Open`): a spec with an existing `Open` override fails to load after the upgrade.
- **A kind-level `deferral = "<status>"` key**, like `completion`: its load-time check would refuse the same overridden specs, and it binds behaviour to a status name.
- **Refs on sub-entities**: a whole new edge surface (`ref add`, backrefs, views, remapping) built for one pointer.
- **An `addresses` ref from the carrier to the review**: it is review-wide, so it cannot say which finding moved.
- **`Open → Verified` for info findings**: `Verified` means a fix was checked, and nothing was fixed.
- **Keeping `WontFix` plus a comment**: it is the misstatement this decision removes.
- **A schema bump**: it would make every adopter run a migration for an additive change.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T09:45:43Z] `architect` Robert Architect:
  - Drafted for REV-1099 F7. Points for @op-pierre to rule on: (1) target-only states, so reopening Noted/Deferred takes `--force`, versus adding reopen edges, which breaks a squad that already overrides the finding `Open` list; (2) whether `sq check` should also warn when a Deferred finding's carrier is settled but not delivered (Cancelled); (3) no schema bump, which leaves an older squads release free to drop `deferred_to` on write. docs/stability.md needs a refresh by the tech writer once this is accepted.
- [2026-10-24T09:52:05Z] `op-pierre` Pierre Chat:
  - 1. Target-only states are accepted: reopening Noted or Deferred takes --force.
  - 2. Yes: sq check also warns when a Deferred finding points at a Cancelled carrier.
  - 3. No schema bump. The CHANGELOG states that a team upgrades together, since an older release drops deferred_to when it rewrites a review.
- [2026-10-24T09:52:50Z] `architect` Robert Architect:
  - Folded the op-pierre rulings into the body: target-only states kept; subentity_deferral_resolved also warns on a carrier whose status has the retired role (bundled Cancelled, WontFix), keyed on the role, not on a status name; Superseded carriers are not reported; no schema bump, and the CHANGELOG must say a team upgrades together.
- [2026-10-24T09:57:04Z] `op-pierre` Pierre Chat:
  - Accepted.
- [2026-10-24T21:59:25Z] `manager` Catherine Manager:
  - @op-pierre for the morning: the tech writer measured that released 0.16.0 does not degrade on a Noted or Deferred finding, it fails every command that loads the board (`sq list`, `sq <type> <n> show` on unrelated items, `sq repair`) with "sub-entity F1 has status 'Noted', which the active spec no longer declares". So "no schema bump, teams upgrade together" means a teammate on 0.16 is locked out with an error that does not say "upgrade sq". Options: (a) keep it, as the CHANGELOG now warns; (b) bump the schema with a no-op migration, so 0.16 hits the schema gate and prints "upgrade the squads package". Recommendation: (b), the gate exists for exactly this.
    Consequence for this repo: board ops run on the released 0.16.0 tool, so no finding here may be set to Noted or Deferred until that tool is upgraded. TASK-1104 ST3 (the review cleanup) waits on this.
- [2026-10-24T22:04:01Z] `architect` Robert Architect:
  - 2026-10-25: amended the pointer clause for REV-1129 F4. No `:head` region is written any more; the "Deferred to <ID> — <title>" line renders in the CLI display (the badge line of `show --full`/`--raw`, and "deferred to:" on `<kind> <k> show`). The older-release consequence is unchanged and awaits the op-pierre ruling.
<!-- sq:discussion:end -->
