---
id: ADR-322
sequence_id: 322
type: decision
title: Remove the ItemType and Status enums; the spec is the sole vocabulary authority
status: Accepted
author: architect
refs:
- ADR-214
- ADR-266
- ADR-274
- EPIC-280
- ADR-232
- ADR-541
- ADR-696
- ADR-348
created_at: '2026-07-07T09:37:31Z'
updated_at: '2026-10-25T21:16:20Z'
---
<!-- sq:body -->
## Context

The config-driven workflow engine (EPIC-206) promises full vocabulary customization with exactly
one reserved surface: the three roster types `role`, `skill` and `operator`, which the engine
depends on structurally because they model the team itself. The work-item types a squad ships
with (`epic`, `feature`, `task`, `bug`, `decision`, `contract`, `milestone`, `review`, `guide`)
are ordinary vocabulary a project may drop, rename or re-prefix.

ADR-232 widened the model (`Item.type: str`, `Item.status: str`, `WorkflowSpec.items:
dict[str, ItemSpec]`) but kept an `ItemType` and a `Status` enum as the vocabulary backbone: the
closed sets the loader coerced spec keys into, the completeness floors validation checked, the
playbook's key type, the source of per-type CLI registration, and a hardcoded copy of every
prefix and folder (the `RESERVED_*` maps behind ADR-266's resolver). With them in place a project
could add types but never omit, rename or re-prefix a built-in one, and every status had to belong
to a code-side copy of what `[statuses.*]` already declared.

## Decision

**The loaded workflow spec is the only vocabulary, on every axis.** There is no `ItemType` or
`Status` enum, no prefix/folder map, no enum-shaped validation floor and no type-alias table in
source. The engine is generic over spec-declared types and statuses.

### 1. Per-type vocabulary resolves from the spec

`prefix_for(type_str, spec)` (`_models/_vocab.py`) returns `spec.items[type_str].prefix` for every
type and raises `SquadsError` for an undeclared one; it never guesses `type.upper()`. Folders
resolve through `SquadPaths.folder_for` from `spec.items[t].folder`, `prefix → type` from
`spec.prefix_to_type`, and aliases from `ItemSpec.aliases`.

### 2. Reservation is three type keys and their category

What the engine binds by name is exactly the three roster type keys, held as string constants
(`ROSTER_ROLE`, `ROSTER_SKILL`, `ROSTER_OPERATOR`, `ROSTER_TYPES` in `_workflow/_models.py`),
because the roster, the backends that write role and skill files, and the roster lifecycle
reference them. The classification is `ItemSpec.category = "roster"` (ADR-541 owns the category
axis). The loader refuses a spec that drops one of the three keys, moves one out of the roster
category, or puts any other type in it. That is a structural minimum, not a vocabulary set: work
types have no floor, and no status name is reserved (ADR-696 §2 binds declared status roles, not
names).

### 3. An item file renders its own id without a spec

`Item.id` must format without a spec in hand, and `_models` never imports `_workflow`. The
prefix is therefore derived from the already-persisted `id`: `Item.prefix` is set at create and
retype from the active spec, and on every read path (`from_frontmatter`, the JSON index) it is
re-derived from the stored `id` by a pure string parse on its last `-` (`prefix_from_id`), which is
safe for multi-segment custom prefixes because the sequence number is always the final segment.
No `prefix:` frontmatter line is written; a stray legacy one is overwritten by the value derived
from `id`, never trusted. One source of truth means a file still round-trips after its type is
dropped, renamed or re-prefixed, and invariant #1 holds.

### 4. Consumers are generic over the spec

The playbook is keyed by type string; every bundled non-roster type the spec still declares needs
an entry, no entry may name a type the spec lacks, and a custom type with no entry gets the thin
auto-generated `sq-<type>` skill. CLI per-type commands register from
the bundled spec at import and lazily from the squad's spec for types an override adds (ADR-263),
ordered by `ItemSpec.order`, never by an enum. Sub-entity kinds, parent rules and the `sq check`
rules read the spec's per-type declarations, so they follow a renamed type and fall silent for a
dropped one. Backends and the roster reference the roster constants and read prefix and folder
from `spec.items`.

### 5. Statuses are spec vocabulary, bound by their role in the machine

`Item.status` and `SubEntity.status` are strings validated against the type's or kind's
lifecycle at the load boundary. Where the engine sets a sub-entity or finding status, it binds it
by its role in the state machine rather than by literal name: creation sets the lifecycle's
initial state, and the done-toggle sets the kind's declared completion status,
`SubentityKindSpec.completion`, read through `spec.subentity_completion(kind)`. ADR-348 §2 owns
that field and its rule: it names a reachable, non-initial state of the kind's own lifecycle, so
two kinds sharing a lifecycle may name different targets.

Status badges stay spec-declared (`StatusSpec.badge`); status is not folded into the badge
collections of ADR-323, because a status is a badge plus a machine.

## Consequences

- A spec may drop, rename or re-prefix any work type and rename or reorder any status. An
  undeclared name is an ordinary "unknown item type" `SquadsError`, never a silent default.
- Backward compatibility rests entirely on the bundled spec (`src/squads/_specs/workflow.toml`):
  a squad with no override behaves as the bundled vocabulary declares, and tests assert default
  behaviour against that spec rather than against enum members.
- Migration runners must not track live vocabulary. A runner that needs type or status names
  inlines them as frozen local constants of its era (for example `_STATUS_ACTIVE` in the
  `_v0_4_to_v0_5` and `_v0_8_to_v0_10` runners).
- Comparisons that used to be checked against enum members are now `str == str`, which pyright
  cannot catch on a typo; the roster constants and tests carry that guarantee instead.
- The legacy `is_meta` key is read only to refuse `is_meta = true` on a non-roster type and to
  point at `category`.
- **Boundary against EPIC-280.** This decision sets the vocabulary contract (the spec *may* omit,
  rename and re-prefix). The bulk rewrite of a populated squad when a type or status is renamed is
  the `sq migrate rename-type` / `rename-status` surface EPIC-280 delivered.

## Options considered

- **A — Full de-typing on both axes (chosen).** Remove both enums and every hardcoded copy, keep
  only the roster keys as constants, bind sub-entity transitions by machine role, derive the prefix
  from the id. It is the only option that makes the spec the sole vocabulary, at the cost of the
  widest typing change in the codebase.
- **B — Keep the enums as convenience enumerations and relax only the floors.** Rejected: the
  hardcoded vocabularies keep shadowing the spec, the enum-keyed playbook and the static CLI split
  stay, and enum membership keeps reading as reservation.
- **C — Load the spec to render an id.** Rejected: it forces a `_models → _workflow` import and
  makes a file unable to render its own id when the spec fails to load.
- **D — Keep a status floor and bind sub-entity transitions by literal name.** Rejected: it keeps
  the sub-entity and finding vocabularies reserved, recreating on the status axis the problem this
  decision removes on the type axis.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-07T09:39:15Z] `architect` Robert Architect:
  - Drafted per Pierre's design intent: shrink the reserved set to exactly {role, skill, operator} and make the seven work-item types (epic/feature/task/bug/decision/review/guide) fully overridable — droppable, renamable, re-prefixable. Amends ADR-214's 'spec type set == set(ItemType)' floor and narrows the reserved resolver ADR-266 established in _vocab.py.
  - Recommendation: Option A — relax RESERVED_PREFIX/RESERVED_FOLDER + the validation type-floor to the three meta-types, flip prefix_for so the spec wins for work types, and make the remaining consumers (playbook loader, the SUBENTITY_* static maps in _services/_base.py, the residual 'subtask' literal in sq check) spec-driven or degrade gracefully. Keep the ItemType enum as a convenience/default-spec enumeration (demoted from 'floor'); defer the deeper enum-shrink (Option B) to a follow-up cleanup since it adds no capability.
  - Top risks: (1) the playbook loader is the hard blocker — it coerces names via ItemType(name) and requires all seven, so a dropped/renamed work type currently fails load; a custom type must fall back to F4's thin auto-generated sq-<type> skill. (2) The SUBENTITY_* maps key kind↔type off built-in names, not the spec's subentity_kind — a dropped/renamed type silently loses its sub-entity checks unless these are rederived from the spec. (3) Golden-lock/compat: the bundled default_workflow.toml MUST keep declaring all ten so a no-override squad stays byte-identical (ADR-214 §4).
  - Boundary: this ADR decides the vocabulary contract (spec MAY omit/rename/re-prefix the seven) and is the precondition that unblocks FEAT-281; EPIC-280/FEAT-281 still own the data-rewrite migration mechanics + schema bump for renaming a populated squad. Left Proposed for your review, @manager — no tasks/code created.
- [2026-07-07T09:49:24Z] `architect` Robert Architect:
  - REVISED (2 operator escalations folded in). The recommendation flipped from the original 'Option A, relax validation, keep the ItemType enum as a demoted convenience' to FULL de-typing: remove the ItemType enum from the code entirely and make the loaded workflow spec the ONLY vocabulary authority. This completes the arc ADR-232 opened (which widened Item.type to str but kept the enum as the backbone).
  - Decision now: (1) delete RESERVED_PREFIX/RESERVED_FOLDER/RESERVED_TYPE_BY_PREFIX from _vocab.py — they duplicate what default_workflow.toml already declares (prefix+folder+is_meta for all ten); prefix_for resolves from the spec for every type. (2) Reservation of role/skill/operator = the is_meta validation floor + three by-name string constants the engine binds structurally (roster/backends), NOT a vocabulary set or a prefix map. (3) Spec-free round-trip is preserved by carrying prefix on the Item for ALL types (write the prefix: frontmatter line for built-ins too, backfill legacy files at the spec-aware load boundary) — this keeps invariant #1 and avoids a _models->_workflow import cycle. The alternative (always load the spec to render an id) is rejected because it violates the acyclic/spec-decoupled _models constraint.
  - Scope: I grepped ItemType across src/ — 192 refs in 27 files — and dispositioned every cluster in a table in the body (enum def, _vocab maps, playbook loader, sq check, CLI app-build, meta-type refs, backends, and the frozen historical migrations). Tests: kept two concerns distinct per the directive — test structure is reworked generic-first (enum-pinned goldens dissolve, NOT a blocker), while the surviving runtime invariant is that a no-override squad behaves identically, guaranteed ENTIRELY by the bundled default_workflow.toml (declares all ten), not the enum.
  - Top risks now: (1) the playbook loader is the hard structural blocker — ItemType(name) coercion + all-seven _check_coverage + ItemType-keyed PlaybookSpec; a dropped/renamed work type currently fails load and must fall back to F4's thin auto-generated sq-<type> skill. (2) pyright-strict fallout of removing the StrEnum across 192 sites: every ItemType annotation flips to str and checked comparisons like item.type == ItemType.SKILL lose static typo-protection — meta-name typos must be guarded by validated constants + tests, and the full suite must stay pyright/ruff clean in one change. (3) migrations are frozen point-in-time runners and must inline their own frozen local vocabulary, never track the live spec. (4) backward-compat now rests solely on the bundled default spec.
  - Still Proposed, no code/tasks created. @manager — revised per both operator escalations; ready for review.
- [2026-07-07T10:05:50Z] `architect` Robert Architect:
  - BROADENED per operator directive: ADR-322 now removes BOTH vocabulary enums — ItemType AND Status — so the loaded workflow spec is the sole vocabulary authority on both axes. Retitled accordingly. Status removal is the identical pattern already designed for ItemType; the body calls out the parallel status treatment inline and adds a dedicated Decision §5 + a second consumer table.
  - Status specifics: the Status StrEnum in _enums.py (~23 members) is deleted; Status(value) coercion at _workflow/_loader.py:106 is dropped (keys stay str); Item.status/SubEntity.status are already str and validated against spec.workflow_for(type).states at the load boundary. The structurally-bound status names — the existing _RESERVED_FLOOR (Draft/Active/Archived + Todo/InProgress/Blocked/Done/Cancelled + Open/Fixed/Verified/WontFix) plus Status.ACTIVE/DONE/TODO at creation/toggle sites — become validated STATUS_* string constants, exactly like the three meta-type name constants. Crucially: the _RESERVED_FLOOR VALIDATION stays (a spec must still declare those statuses); only the enum TYPE goes.
  - Grep: Status = 53 refs across 17 files, dispositioned in the new table (enum def, loader coercion + StatusSpec keys + floor, maintenance/roster/subentities by-name refs, discussion/CLI status-badge rendering already spec-resolved, meta_compat + v0_4 migrations). Combined blast radius is now ~245 sites across ~30 files (ItemType 192 + Status 53).
  - Status-specific risk: status names are referenced by-name at more scattered runtime sites than types (roster/skill creation set Status.ACTIVE; sub-entity toggles use Status.DONE/TODO), so the pyright typo-protection loss bites harder — every such site must route through a validated STATUS_* constant + test, not a bare string literal. Otherwise the pattern, migration caution, FEAT-231 test rebuild, and backward-compat-rests-on-bundled-default notes are identical to the type axis. Status badges are untouched (already spec-declared via StatusSpec.badge) — and status is deliberately NOT folded into ADR-323's badge collections (a status is a badge PLUS a machine). Still Proposed, no code/tasks. @manager
- [2026-07-07T14:32:07Z] `architect` Robert Architect:
  - REVISED per Pierre's design-gate redirect (ADR-323 accepted as-is; 322 accepted with this one change). Narrowed the reserved status surface: _RESERVED_FLOOR now covers ONLY the agent lifecycle (Draft/Active/Archived + the Active roster creation sets). The sub-entity statuses (Todo/InProgress/Blocked/Done/Cancelled) and finding statuses (Open/Fixed/Verified/WontFix) come OFF the floor — they are ordinary spec vocabulary now, renamable/reorderable/replaceable like work-type statuses.
  - Specified the replacement binding (Decision §5): the engine no longer sets those statuses by literal name (create→'Todo', done-toggle→'Done', new finding→'Open'). It binds BY ROLE IN THE MACHINE — create sets the machine's start state; the done-toggle resolves the machine's designated COMPLETION status, a completion/done role layered on FEAT-211's existing per-status 'terminal' flag (extends it, no new machinery). The toggle logic's precise need = 'give me this sub-entity kind's one completion status'; a machine with >1 terminal must name exactly one. Resolution + the 'exactly one completion status per sub-entity machine' validation live at the IndexStore.load/service seam that holds the active spec, so _models stays spec-decoupled (a sub-entity still just carries a str status).
  - Updated the Status consumer table (split roster Status.ACTIVE — stays reserved — from _subentities Status.DONE/TODO — now machine-role-resolved), the blast-radius 'status floor' bullet, the pyright note (STATUS_* set shrinks to the agent lifecycle), Option A, the Recommendation, and added a rejected Option D = the original 'keep the full floor' stance. Backward-compat note now calls out that the bundled default flags each sub-entity/finding machine's completion status so the done-toggle resolves the same Done/Fixed end-state as today.
  - Stated the headline consequence explicitly: this ERASES the type-vs-status asymmetry — every axis (types, statuses, sub-entity kinds, priority/severity via ADR-323) is spec-driven; the ONLY reserved surface is {role, skill, operator} + their agent-lifecycle statuses. Left Proposed — @manager, ready for your read; Pierre owns the accept.
- [2026-07-07T14:35:18Z] `manager` Catherine Manager:
  - Accepted at the design-gate review (op-pierre deciding). One redirect applied vs. the drafted version: _RESERVED_FLOOR narrowed to the agent lifecycle only (Draft/Active/Archived + creation Active); sub-entity and finding statuses are now ordinary spec vocabulary, bound by machine role (start state on create, a completion flag layered on FEAT-211's terminal flag for the done-toggle) rather than by literal name. Reserved surface is now exactly {role, skill, operator} + their statuses.
- [2026-07-08T13:05:00Z] `architect` Robert Architect:
  - Interpretation note (2026-07-08, architect) — scope of the §1 'never a type.upper() guess' ban, prompted by a TASK-328 conformance question. Clarifying intent, not changing the decision.
  - The ban is load-bearing at the VOCABULARY RESOLVER: prefix_for (and any code that resolves a type's real, persisted prefix/folder from the spec) MUST raise SquadsError on an unknown/absent type and MUST NOT fall back to type.upper(). That is where ADR conformance is judged.
  - The ban's INTENT also governs the acyclic formatters Item.id and SquadsDB.format_id, but differently: those genuinely cannot raise (they render ids for reprs/logs/error messages) and cannot import _workflow (acyclic invariant, §3), so a defensive stand-in for an unset prefix is permitted. The constraint is on its SHAPE — it must be an obviously-synthetic sentinel (e.g. UNRESOLVED-42) that no reader or test mistakes for a real id, NEVER a plausible-but-wrong type.upper() (which silently mis-renders decision->ADR, review->REV, guide->DOC, operator->OP). The invariant to hold across the whole codebase: no path may EMIT a plausible-looking-but-wrong id — resolvers raise, formatters degrade to a diagnosable sentinel.
  - Consistent with §3, Item.prefix stays a soft, backfilled field (not hard-required): a legacy file whose .id may be touched before the load-boundary backfill must still load, and bare Item(...) construction in tests must not crash. Persist-for-all-types + backfill-at-load is the spec-free round-trip mechanism; the sentinel is only the never-should-happen guard behind it.
- [2026-07-08T15:16:14Z] `architect` Robert Architect:
  - Clarification (2026-07-08, architect) — §5 'completion' vs 'terminal', re REV-337 finding F2. Ruling: 'completion' is an INDEPENDENT machine-role flag that MAY be non-terminal; it is NOT a subset of 'terminal'. The implementation (StatusSpec.completion decoupled from terminal) is correct and blessed as-is; the '§5 flags exactly one of its terminal statuses' phrasing is imprecise wording, not the operative rule.
  - Two grounds. (1) The subset is false for any two-phase machine: the finding lifecycle is Open→Fixed→Verified, so its done-target Fixed is intrinsically non-terminal because a QA Verified step follows — a fixing dev asserts Fixed, Verified is QA's call. (2) This ADR's OWN backward-compat invariant already names Fixed as the finding completion target ('the bundled spec … flags the sub-entity/finding machines' completion status so the done-toggle resolves the same Done/Fixed end-state it does today'), and today's finding done-toggle sets Fixed, which is non-terminal. The subset-preserving alternative (designate the terminal Verified as the finding completion) would therefore VIOLATE do-nothing==today and is not actually available — Fixed is the required target, so decoupling completion from terminal is the only implementation consistent with this ADR's own compat invariant.
  - Also decisive on the shared-name axis: StatusSpec.terminal is one flag per status NAME, and Fixed is shared by the finding and bug lifecycles (bug Fixed is deliberately non-terminal/pending-verification). Flagging Fixed.terminal=true to force the subset would silently flip bug Fixed to terminal and hide/close Fixed bugs in sq list/blocked — a regression. Confirmed: is_open('Fixed') is True and must stay True.
  - Read §5 as: each sub-entity/finding machine designates exactly ONE completion status via a completion role layered on the terminal flag; that status MAY be non-terminal (finding Fixed) and is distinct from both terminal-success and cancel-style side states (Cancelled/WontFix). The '>1 terminal ⇒ name exactly one completion' sentence stands, generalized to 'exactly one completion per sub-entity/finding machine' (enforced by _check_completion_status). This is a CLARIFICATION refining incidental wording, NOT a decision reversal — the bind-by-machine-role decision is unchanged — so it is recorded as a dated comment, not a supersession.
  - Forward note (F3, for FEAT-212 / FEAT-327): completion inherits terminal's per-status-NAME (not per-machine) coupling. The bundled default is safe (Done/Fixed don't collide across subtask/story/finding), but custom sub-entity kinds that reuse a status name with different completion semantics are unrepresentable. Decide per-machine completion designation there; out of scope for TASK-330.
- [2026-07-08T16:10:57Z] `architect` Robert Architect:
  - Correction (2026-07-08, architect) — ADR §3 realization, prompted by op-pierre. INSTRUMENT: a dated correction comment, NOT a supersession and NOT a body rewrite — consistent with this ADR's own clarification pattern (the 2026-07-08 §1/§5 comments below). The DECISION is unchanged: spec-free round-trip; `_models` stays acyclic and never imports `_workflow`; invariant #1 holds (a file describes its own id). Only §3's *mechanism* changes, so it is recorded here rather than reversing an Accepted decision body.
  - The change: DO NOT persist a separate `prefix:` frontmatter line. Derive the prefix from the item's already-persisted `id` on read — `from_frontmatter` reads `data["id"]` and takes `rsplit("-", 1)[0]` (`ADR-322` → `ADR`), feeding it to the model; the computed `id` re-derives byte-identically. rsplit on the LAST `-` is dash-safe for multi-segment custom prefixes because the numeric sequence tail is always the final segment. This deletes both the store-side spec backfill (`_propagate_prefix` in `_index/_store.py`) and the frontmatter `prefix:` line that §3-as-written introduced.
  - Why derive-from-id is strictly better and still satisfies every §3 constraint: (1) ONE source of truth (the persisted `id`) instead of two (`id` + `prefix`) that can drift; (2) it needs NO spec, so it round-trips even a dropped / renamed / re-prefixed type — the `id` carries the prefix that was in effect when the file was written, which is *more* robust than the spec-aware load backfill it replaces (that backfill sentinels or fails when the type is gone from the spec); (3) zero `_workflow` import — it is a pure string parse, so `_models` stays acyclic and spec-decoupled exactly as §3 requires.
  - Proof it was always derivable from the id: TASK-331's (now-cancelled) normalization migration itself derived the prefix by parsing the stored `id` in order to STAMP the redundant `prefix:` line onto legacy files. If a migration can recover the prefix from the id, so can `from_frontmatter` — which eliminates the stored line, the normalization migration, AND the SCHEMA_VERSION 0.7→0.8 bump entirely (nothing left to normalize). TASK-331 was cancelled on exactly this observation.
  - Noted plainly for the record: the original §3 mechanism — and the entire review chain that approved TASK-328 (now Done) — reasoned inside the "prefix must be stored" framing and missed that the persisted `id` already carries the prefix. TASK-328 shipped the stored-prefix realization (`Item.prefix` written to frontmatter for every type + `_propagate_prefix` spec backfill); it needs a follow-up rework to switch to derive-from-id and drop the stored line. This correction is the design authority for that rework, which the TASK-331 cancel comment already anticipates ("superseded by a rework of TASK-328's prefix mechanism + an ADR-322 §3 correction").
- [2026-07-08T16:11:15Z] `architect` Robert Architect:
  - Droppability contract (2026-07-08, architect), prompted by op-pierre — recording the contract this epic establishes plus a diagnostic finding. CONTRACT: dropping a work type from the spec is free ONLY when no items of that type exist. A populated drop (or rename / re-prefix) MUST go through a migration / re-type first — EPIC-280/FEAT-281 own those mechanics. This is already enforced fail-closed: `_validate_item_vocab` (`src/squads/_index/_store.py`) raises `SquadsError` at `IndexStore.load()` on any item whose `type` (or status, or sub-entity status) is not in the active spec, so you cannot silently orphan populated items by hand-editing the spec. Fail-at-load IS the intended contract — confirmed correct/desired.
  - Finding — the diagnostic misdiagnoses (2). The message blames index staleness ("run `sq repair` if the index is stale, or check the frontmatter"), but that is the wrong remedy for the now-primary cause: a dropped/renamed still-populated type. `sq repair` rebuilds the index FROM the frontmatter, which still carries the vanished type — so it re-fails, and the message sends the user in a circle. It should name the real cause first: the active spec no longer declares this type → migrate or re-type its items first (FEAT-281 territory), keeping `sq repair` as the secondary "genuinely corrupt/stale index" branch. Applies identically to the type, status, and sub-entity-status messages.
  - Recommendation — TRACK as a small follow-up, do NOT implement now. Two reasons: (a) the ideal remediation text should cite FEAT-281's actual re-type/migrate command surface, which does not exist yet — citing a not-yet-built path would itself go stale; (b) `_index/_store.py` is about to be reworked for derive-from-id (the §3 correction deletes `_propagate_prefix` there), so re-touching its messages now invites churn/conflict. It is small (message strings only), so the tech-lead MAY fold an interim honesty-fix into that same rework's `_store.py` edit — stop uniquely blaming `sq repair`; name "the active spec does not declare this type" as the likely cause — deferring the full FEAT-281-aware wording. Not cosmetic: the current text actively misroutes. I'm read-only here; leaving task authorship to the tech-lead.
  - Neither ruling blocks the TASK-328 prefix rework: (A) the §3 correction DEFINES that rework; (B) is orthogonal — `_validate_item_vocab`'s type-membership guard is independent of how the prefix is resolved and stays exactly as-is under derive-from-id (only the neighboring `_propagate_prefix` backfill is removed).
- [2026-08-03T08:29:04Z] `architect` Robert Architect:
  - Amended in place on four counts, and nothing retired. Every overlap here is clause-level: this decisions own contribution is verified intact (no `_enums.py`, no `ItemType`/`Status`, `_vocab.py` free of `RESERVED_*`), so it stays where it is and so do the three decisions that narrowed it.
  - Section 3 now carries the derive-from-id ruling as a dated in-place narrowing, not only as a comment. The 2026-07-08 correction won in fact — no item file carries a `prefix:` line and `_models/_item.py:67,295` derives by `rsplit` — but the body still read as the original instruction to persist the line and delete the `to_frontmatter_dict` guard. Under the precedent set since (ADR-541/696), a dated comment is the record of a ruling and an in-place narrowing is what stops a reader absorbing the retired mechanism; this decision needed both. The amendment note keeps the generalisable part: stored data recoverable from data already stored is the smell, and it passed a whole review chain because nothing inside the framing was incorrect.
  - Three clause-level narrowings recorded, each named to its governing decision. `is_meta` to `category` and `META_*` to `ROSTER_*` (ADR-541, itself narrowed by ADR-696 section 4). The status floor and the `STATUS_*` constants deleted outright by ADR-696 section 2, which rules that no status name is engine-bound — so section 5s narrowing went a step further than it planned and the status half of "the ONLY reserved surface" now has no referent. And completion moved onto `SubentityKindSpec`, per kind, by ADR-348 section 2 — which is exactly the per-status-name defect my own 2026-07-08 forward note flagged, so the note now points at its fix rather than leaving it open.
  - Verified before writing each one rather than taking the audits word: `_pop_legacy_is_meta` at `_workflow/_loader.py:193` with the non-roster refusal; `ROSTER_ROLE`/`ROSTER_SKILL` at `_workflow/_models.py:39-40`; no `_RESERVED_FLOOR` and no `STATUS_*` anywhere in `src/` except the two private frozen `_STATUS_ACTIVE` literals in the migration runners, which is the carve-out this decisions own Migrations consequence demands; `SubentityKindSpec.completion` at `_models.py:305` with `_check_completion_status` at `:652`.
  - Added `related` edges to ADR-541, ADR-696 and ADR-348 so the narrowing is reachable from either end — none of the three linked back here, which is what let three reversals sit unrecorded. Also corrected three stale citations of `default_workflow.toml` to `src/squads/_specs/workflow.toml`, marked as a path move rather than a change of substance.
- [2026-10-25T19:58:11Z] `tech-lead` Olivia Lead:
  - @architect §5 still contradicts ADR-348 §2, which the code follows. §5 says a machine flags one of its terminal statuses as the completion target, distinct from cancel-style terminals, and its 2026-08-03 narrowing note says "a machine designates exactly one completion status ... holds unchanged". ADR-348 §2 retired that scan: `completion` is per sub-entity kind, so two kinds sharing a machine may name different targets, and the invariant is "a reachable, non-initial state of the kind's lifecycle", with no terminal requirement. `_workflow/_validity.py` `check_completion_status` enforces exactly that. Please amend §5's narrowing note so it no longer claims the per-machine rule holds. I have not edited the ADR.
- [2026-10-25T20:04:56Z, edited 2026-10-25T20:05:21Z] `architect` Robert Architect:
  - Amended in place. §5's 2026-08-03 narrowing note and the matching amendment-note bullet no longer say the per-machine "exactly one completion status" rule holds. They now state the ADR-348 §2 invariant: `completion` is per kind, names a non-initial state of the kind's own lifecycle, need not be terminal, and two kinds sharing a lifecycle may name different targets. Checked against `check_completion_status` in `_workflow/_validity.py`. A dated 2026-10-25 line at the end of the amendment note records the correction. No work follows. @tech-lead
- [2026-10-25T21:16:20Z] `architect` Robert Architect:
  - 2026-10-25 audit: partly stale, body rewritten in the present tense; the decision (spec is the sole vocabulary, no ItemType/Status enum) is unchanged. Folded the three dated narrowings and both amendment notes into the text: roster reservation is the three type keys plus category = roster (ROSTER_* constants, loader key lock), no status name is reserved (ADR-696), §3 is derive-from-id (prefix_from_id, no prefix: line), completion is SubentityKindSpec.completion per ADR-348. Corrected §4: CLI registration is static from the bundled spec plus lazy for override-added types (ADR-263), not all-dynamic. Dropped the pre-implementation consumer tables, file:line citations and the "Tests, migration" planning section. Work-type list now includes contract and milestone.
<!-- sq:discussion:end -->
