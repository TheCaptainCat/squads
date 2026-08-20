---
id: ADR-163
sequence_id: 163
type: decision
title: Advisory create-lane enforcement (Slice B)
status: Accepted
author: architect
priority: medium
refs:
- FEAT-122:implements
- ADR-155
- ADR-158
- FEAT-125
- ADR-696
created_at: '2026-06-22T12:14:44Z'
updated_at: '2026-08-15T14:19:35Z'
---
<!-- sq:body -->
## Context

Slice B asks: when an agent role authors an item type outside its lane (e.g. a `python-dev`
runs `sq create feature`), surface a visible **advisory** warning, recorded for forensics, and
**proceed anyway**. This ADR fixes the enforcement model so the tech-lead can break it down
without re-litigating the open questions.

Two prior decisions bound this design and must not be contradicted:

- **ADR-155** established that real *capability* enforcement (e.g. withholding the spawn
  tool) lives at the Claude Code backend, bound to the agent **type** at launch — not as an
  sq-runtime check. That slice (Slice A) is structural and trustworthy.
- **ADR-158** established that the recorded actor (slug + optional session/parent) is
  **best-effort, untrusted, observability-only** — squads is a passive CLI, never in the spawn
  path; it cannot mint, inject, or verify identity. Its §7 is explicit: *any* lane enforcement
  keyed on the recorded actor is **inherently advisory** — it catches the honest accident, never
  stops a deliberate forger.

Create flows converge on one chokepoint: `ServiceCore.create` in
`src/squads/_services/_base.py`. It already resolves `author`, opens the index transaction, runs
`_check_author`/`_check_parent`/`_check_assignee`, allocates the id, writes the file, and logs the
`create` op to the reflog via `self.store._log("create", item.id, {...})`. The acting slug is
available there as `actor.current_actor()` and the declared author as the `author` argument. The
service returns a `CreateResult(item, path)` (`src/squads/_services/_results.py`); the CLI
(`_cli/_create.py`) prints `created <id> → <path>`. The layering invariant holds: **`_services`
must not print** — warnings ride back in the result; the CLI renders them, escaped via
`_cli/_common.py::e()`.

The lane mapping is **not** to be hand-maintained: `src/squads/_interactions.py::PLAYBOOK` is the
canonical role↔item-type playbook. Each `ItemPlaybook` lists `RoleGuide`s; a role's `do=` bullets
say whether that role *authors* (`sq create <type>`) the item. We derive the create-lane from this
existing structure — adding a new playbook entry extends the lane automatically (AC-B5).

## Decision

### 1. Scope — creates only (adopt Nina's Option A)

Lane checks fire on **`sq create`** and its create-equivalents (the generic `create_*` commands and
`create guide` — all route through `ServiceCore.create`). **Mutations of existing items are NOT
laned in this cut**: no status transition, body edit, metadata update, or sub-entity mutation
triggers any lane check (AC-B6). Rationale (Nina's, adopted): under an advisory posture the value
of mutation restrictions is marginal against the friction they add to the normal loop (tech-lead
moving a feature to InProgress, QA closing a bug, manager reassigning mid-sprint); the reflog
already records who did what.

**Option B (laned status transitions) is recorded as a documented future upgrade, not now.** Should
real incidents show the need, a later slice may add transition-lane checks (only the lifecycle-owning
role advances an item) on the same advisory warn-and-proceed mechanism. This is recorded explicitly
so Option A is not re-litigated ad-hoc. Option C (all mutations laned) is rejected — too much
friction for an advisory system.

### 2. Lane source of truth — derived from the playbook, never duplicated

The create-lane is a **pure derivation of `_interactions.py::PLAYBOOK`**, computed at lookup time —
no second source of truth, no hard-coded string list (AC-B5).

Computation — `allowed_create_types(slug) -> set[ItemType]`:

- Each role guide in the playbook declares **`authors: bool`**. A role is **in-lane to create** the
  type whose section its guide hangs under exactly when that guide sets `authors = true`, and that
  declaration is the sole source of the lane. It is read from the **active, merged** playbook, so a
  guide added or edited through `.overrides/playbook.toml` moves the lane with it (AC-B5). The lane
  is declared rather than inferred because several roles *interact* with a type (`tech-lead`
  reads/triages bugs and reviews) without being its in-lane **author**: the tech-lead who breaks
  down a feature into tasks should not warn on `sq create task`; the tech-lead who reads a bug
  should still warn on `sq create bug`. A guide that only reads, triages or verifies declares
  nothing and carries no lane.
- **`*dev` sentinel.** A guide whose `slug == DEV` (`_interactions.DEV == "*dev"`) applies to any
  `<tech>-dev` slug (`is_dev_slug`). The DEV guides declare no `authors`, so the dev create-lane is
  **empty by declaration** rather than by a special case (see point 2a for the dev-bug rule).
- **Multi-type roles fall out for free.** `architect` is in-lane for both `decision` and `guide`
  (two declarations); `tech-lead` for `task` (and co-authors `guide`); `reviewer` for `review`;
  `qa` for `bug`; `product-owner` for `feature` and `epic`; `tech-writer` for `guide`.
  This matches Nina's §1 table exactly.
- **Manager + operator exemptions are applied before lookup** (see point 5), so they never produce
  a warning regardless of the derived lane.

**Why a declared flag and not the two mechanisms this section originally named.** A scan of a
guide's `do` prose for `sq create <type>` cannot reproduce the lane set stated three bullets above.
`tech-writer` is in-lane for `guide`, and its bundled guide carries no create verb at all, so no
scan of `do` bullets — scoped to a section or run across the whole document — yields that lane;
`reviewer`'s `sq create review` is additionally written in the **task** section rather than the
review one, which a per-section scan also misses. A scan drops lanes silently, and it makes prose
load-bearing as data, which is the naming-convention-standing-in-for-a-declaration shape this
codebase removes on sight. A declarative map co-located with the playbook is a second artifact kept
in agreement with the first by a test — duplication with a guard on it rather than the absence of
duplication — and being a literal table it can only ever describe the bundled playbook, so a role
declared as an author through an override got the create command in its generated skill and an
advisory saying it was not the author.

The declared flag is the only one of the three that satisfies this section's headline literally: the
fact lives *in* the playbook, so there is one artifact and nothing to keep in sync. The invariant
stands exactly as first stated — one source, test-locked to the playbook — and is now met by
construction rather than by a test holding two things together.

**The key, declared against the document it extends.** `authors` is an addition to the closed key
space of the playbook override document (`.overrides/playbook.toml`), whose grammar, merge, stamp
and validation belong to ADR-696; the guide model forbids extras, so its field set *is* that key
space. Named here per the rule that a decision adding a key to a frozen surface says so and names
the surface: `authors`, boolean, defaulting `false`, additive — renaming nothing, removing nothing,
retyping nothing. An adopter may declare it on any guide in an override, and a guide that omits it
behaves exactly as before.

#### 2a. Open question resolved — dev-authored bugs are ALLOWED with an advisory warning

Nina flagged the gap: the playbook gives devs no in-lane create, and the DEV guide says "file a
newly-found defect as a bug" while the qa guide owns `sq create bug --author qa`.

**Decision: a `<tech>-dev` running `sq create bug` is allowed and proceeds, emitting the standard
advisory warning** (expected in-lane author: `qa`). We do **not** require the `--author qa` slug.
Rationale:

- It is consistent with the whole posture: warn-and-proceed, never block. A dev who finds a real
  defect mid-task should be able to file it on the spot; forcing a slug swap adds friction for the
  exact cooperative case the playbook encourages ("file a newly-found defect as a bug").
- The warning still creates the forensic record (AC-B2) that qa's lane was crossed, so triage can
  re-attribute if desired.
- It avoids a special-case carve-out in the lane logic: the dev create-lane stays empty, and the
  dev-bug case is simply *one instance* of the general out-of-lane-but-allowed rule. No bespoke
  code path.

So there is **no** dev-specific exemption; `sq create bug --author <tech>-dev` warns like any other
out-of-lane create and succeeds.

### 3. Where enforcement sits + the end-to-end data path

Advisory **warn-and-proceed**, computed in the **service layer**, returned in the create result,
rendered (escaped) by the CLI, and recorded in the reflog. No hard block, no override flag in v1 —
it proceeds by design (a `--no-lane-check` flag is unnecessary because nothing is ever blocked).

**Path, end to end:**

1. **Compute (service).** In `ServiceCore.create`, after `author` is resolved and inside the
   existing flow, compute the acting slug = `actor.current_actor()` and evaluate
   `lane_warning(acting_slug, author, item_type)`:
   - Exempt actors (point 5) → no warning.
   - Else if `item_type in allowed_create_types(author)` → no warning. (We lane on the **declared
     `author`**, which is the slug that will own the item and is what `--author` sets; in the normal
     case `current_actor()` and `author` coincide because `_cli/_create.py` calls
     `actor.set_actor(author)`. Laning on `author` keeps the check meaningful even when they differ
     and matches AC-B1's "the acting role … the expected in-lane role".)
   - Else produce a warning value: `(acting_role=author, expected_roles=in_lane_owner(item_type),
     item_type)`.
   The owner-of-a-type lookup is the inverse of the same derivation: which role(s) are in-lane to
   create `item_type` (e.g. `feature → product-owner`, `bug → qa`).
2. **Record (reflog).** When a warning is produced, include it in the `create` op's delta so it
   lands in the reflog alongside the operation (AC-B2): extend the existing
   `self.store._log("create", item.id, {...})` delta with an advisory-lane tag, e.g.
   `"lane_warning": {"actor": author, "expected": [<owner-slug>], "type": item_type.value}`. The
   reflog delta is documented as additive/free-form (`ReflogEntry.delta`), so this is purely
   additive and needs no schema bump. Tag it clearly as an *advisory lane check* so a reader knows
   it is not an error.
3. **Return (result).** Add an **optional** field to `CreateResult` in `_services/_results.py`,
   e.g. `lane_warning: str | None = None` (a pre-rendered human-readable sentence, or a small
   dataclass the CLI formats — implementer's choice; a formatted string keeps the CLI dumb). The
   service sets it when a warning was produced, else `None`. The service **does not print**
   (layering invariant preserved).
4. **Render (CLI).** In `_cli/_create.py`, after the existing `created <id> → <path>` line, when
   `res.lane_warning` is set, print it on stderr/console **escaped via `e()`** (the warning names a
   role slug, no markup risk, but `e()` is the convention for dynamic content). Exit code stays
   **0** — the item was created (AC-B1). In `--json` mode, surface the warning as a field in the
   emitted JSON rather than as a side-channel line, so machine consumers see it too.

**Warning content** (AC-B1): names the acting/authoring role, the expected in-lane owner role, and
the item type, in advisory language. Example wording:

> `advisory: 'python-dev' is not the in-lane author for 'feature' items (expected: 'product-owner'). Lane checks are best-effort and advisory — proceeding.`

### 4. Identity basis + honesty

The check keys off the **self-declared `--as`/`--author` slug** surfaced by
`actor.current_actor()` / the `author` argument. The session pair from FEAT-125
(`actor.current_session()`) is **context only** — it may be carried into the reflog delta for
forensics but is **never** the basis of the lane decision, because (ADR-158) it is equally
untrusted.

State plainly, everywhere the feature surfaces (CLI text, `sq role show`, docs): the lane check is
**advisory, best-effort, untrusted**. It catches the honest accident; it never stops a forger — a
wrong/forged `--as` slug bypasses it trivially. **No enforcement-grade, tamper-evident, security, or
forge-proof claim may appear** in any CLI string or doc (AC-B4). The warning text itself must carry
"advisory" / "best-effort" language (see point 3 wording).

### 5. Exemptions

Determined **before** the lane lookup, by slug shape:

- **The squad's default role** — fully exempt from all lane checks (orchestrator; authors any type
  for coordination). Check: the author equals the slug the squad designates as its **default role**,
  read from the live roster and falling back to the role catalog's own designation. Not the literal
  `manager`: the exemption belongs to the designation, so `sq role <slug> default` moves it. In the
  bundled roster that slug is `manager`, so bundled behaviour is unchanged.
- **Operators (`op-*`)** — fully exempt. Humans coordinate freely; lane checks apply to agent role
  slugs only. Check: `author.startswith("op-")`. (Consistent with how operators are modelled as
  `OPERATOR` items with `op-` slugs; the same prefix the greeting/operator flows use.)
- **Tech-lead (`tech-lead`)** — exempt for `task` creation **because `task` is in its derived
  lane**, not via a special case. A tech-lead authoring a `feature` would still warn (that is the
  product-owner's lane), which is the correct behaviour per Nina's §4. So no extra tech-lead carve-
  out is needed for creates; the derived lane already gives the right answer. (If a future Option B
  mutation slice lands, tech-lead would get the mutation-lane exemptions Nina's §4 describes — out
  of scope here.)

A single `is_lane_exempt(slug, default_slug) -> bool` helper (`slug == default_slug or
slug.startswith("op-")`), co-located with the lane derivation in `_interactions.py`, keeps the rule
in one place.

### 6. Surfacing / visibility

**Yes — surface the active create-lane in `sq role <slug> show`**, alongside Slice A's `can spawn`
(AC-B7). `_cli/_role.py` already renders a `can spawn: yes/no` row from `RoleDef.can_spawn`; add a
companion row, e.g. `creates: feature, epic` (the derived `allowed_create_types(slug)`, or
`creates: — (out-of-lane creates warn)` for roles with an empty lane such as devs/devops). Include
it in the `--json` output too (a `create_lane` array next to `can_spawn`).
*Not yet true for a `<tech>-dev` slug — the row is missing from the human card, and the cause is not
in this feature. See the amendment note.* This makes the lane
legible without reading code and mirrors the Slice A surfacing precedent. Because the lane is
derived (not stored on `RoleDef`), `sq role show` computes it on the fly from the playbook — no new
persisted field, consistent with "one source of truth."

## Consequences

- **Positive.** One chokepoint (`ServiceCore.create`), one derivation source (`_interactions.py`),
  layering preserved (service returns, CLI prints). Adding a playbook author entry extends a lane
  automatically (AC-B5). Forensic trail complete via the reflog delta (AC-B2). No migration: the
  reflog delta and `CreateResult` field are additive; no schema bump. The honest accident (a dev
  creating a feature, a dev filing a bug) is now *visible* in real time and in the reflog.
- **Negative / limits (must be documented, not hidden).** **Advisory only.** Keyed on the
  self-declared slug, which is untrusted (ADR-158): a forged `--as` slug bypasses the check
  silently, and the dev-bug case proceeds by design. Mutations are entirely unlaned in this cut
  (Option A) — a role can transition/edit any item with no warning. These are accepted trade-offs
  of an advisory posture, not gaps to be "fixed" by over-claiming.
- **Derivation brittleness risk.** Deriving the lane by scanning playbook `do=` prose for
  `sq create <type>` couples the check to command wording. Mitigation (mandatory for the tech-lead):
  a unit test pins each role's derived lane to Nina's §1 table, so any playbook edit that silently
  shifts a lane fails CI. If prose-scanning is judged too fragile, the declarative-map-in-the-same-
  module fallback (point 2) is permitted — still one source, test-locked.
- **Future upgrade path preserved.** Option B (laned status transitions) reuses this exact
  warn-and-proceed plumbing on the mutation chokepoints; recorded here so it is a deliberate later
  decision, not a surprise.

## For the tech-lead (before breakdown)

- The whole slice is **advisory plumbing**, no new enforcement primitive — do not let any test or
  doc assert a block, a non-zero exit, or a security guarantee.
- Three small additive seams: (a) `allowed_create_types` / `in_lane_owner` / `_is_lane_exempt` in
  `_interactions.py` with a table-pinning test; (b) a `lane_warning` field on `CreateResult` set
  inside `ServiceCore.create` + the reflog delta tag; (c) the CLI render in `_cli/_create.py`
  (escaped, exit 0, JSON-aware) and the `creates:` row in `_cli/_role.py`.
- Lane on the **declared `author`**, exempt **before** lookup, key off `current_actor()` /
  `author` only — `current_session()` is forensic context, never the decision basis.
- Map subtasks to US1 of FEAT-122; AC-B1..AC-B7 are the acceptance gates.

## Amendment note

**2026-08-03 — three citations refreshed, and §6 is not delivered for developer slugs.** The decision
itself is verified in force by execution: an out-of-lane create prints §3's advisory copy verbatim and
exits 0, an in-lane create is silent, the reflog carries the `lane_warning` delta with `advisory: true`,
`sq role product-owner show` renders the `creates:` row, `--json` carries `create_lane`, and a status
transition warns not at all — confirming §1's creates-only scope.

Citations:

- `_interactions.py` is the `_interactions/` package this decision itself asked for; `PLAYBOOK` and the
  helpers live in its `__init__`.
- §5's helper is public `is_lane_exempt`, not `_is_lane_exempt`. Corrected above.
- §2's headline — "a pure derivation of `PLAYBOOK`, computed at lookup time, no hard-coded string list"
  — is **not** what shipped. What shipped is the fallback this decision's own §2 permitted: a
  `CREATE_LANES` mapping co-located with the playbook and test-locked, which satisfies the invariant §2
  actually stated ("one source, test-locked"). So this is not debt — but the headline reads backwards
  against the code, and a reader checking conformance against the headline rather than the invariant
  will report a violation that is not one. The lane set is also keyed by `str` now rather than
  `ItemType` (ADR-322), and `allowed_create_types` gained a `spec` parameter so a role's lane is
  filtered to the types the adopter still declares.

**§6 is a genuine gap, and the decision is right rather than the code.** `sq role python-dev show`
prints no `creates:` row at all. The lane machinery is fine — `--json` returns `create_lane: []`, which
is the correct empty lane — but the human card never gets there: `resolve_role` raises for any slug
outside the bundled catalog, and a `<tech>-dev` slug is one, so the card falls back to three rows from
the item's own fields. The `creates:` row is only the most visible casualty; `model`, `can spawn`,
`mission` and `responsibilities` are missing from the same card, and `can spawn` is Slice A's surfacing
precedent that this section was written to mirror.

So the remedy does not belong in the `creates:` row or in this feature. It belongs in role resolution:
a `<tech>-dev` slug is a *known* role shape — `dev_role()` exists to synthesise exactly it — and
`resolve_role` should resolve it rather than raising, after which every row this section specifies
appears with no CLI change at all. Fixing it at the CLI's fallback branch instead would paper over four
missing rows with one.

**2026-08-06 — §2's mechanism and §5's exemption basis corrected in place; the headline is
unchanged.** Both mechanisms §2 originally offered are withdrawn, and the entry above reporting that
the shipped map "reads backwards against the headline" is closed by the correction rather than by
re-reading the headline.

- **The prose scan was not brittle; it could not produce this section's own stated result.** §2's
  multi-type bullet asserts `tech-writer` is in-lane for `guide`, and the bundled `tech-writer`
  guide on `guide` carries no create verb in any bullet — so no scan of `do` prose yields that lane,
  under either a per-section or a whole-document reading. `reviewer`'s `sq create review` living in
  the **task** section is a second miss, and the one that also breaks the per-section reading. This
  was a contradiction inside §2 from the day it was written, not a discovery about the code.
- **The declarative map satisfied the invariant's letter and lost its point.** "One source,
  test-locked" was met by two artifacts and a test binding them; and a literal table could only
  describe the bundled playbook, so an override-declared authoring role received a generated skill
  containing the create command together with an advisory that it was not the author, and a renamed
  or adopter-declared type left the lane machinery with nothing to say at all. That is the defect
  this correction closes.
- **What replaces both:** a declared `authors` flag on the playbook's own role guides, read from the
  merged document. The headline — derived from the playbook, never duplicated — is unchanged and is
  now true by construction. The key is declared against ADR-696's override document in §2; `related`
  refs both ways.
- **§5 no longer names `manager`.** The exemption attaches to the squad's designated default role,
  read from the live roster with the catalog designation as fallback, so `sq role <slug> default`
  moves it. Same class of correction as §2's: a bundled literal standing in for a declaration.
  Bundled behaviour is byte-identical in both cases.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-22T12:35:54Z] Pierre Chat:
  - Approved at Option A: advisory create-lane enforcement, creates-only, warn-and-proceed (exit 0). Mutations stay unrestricted. Build it.
- [2026-08-03T08:49:54Z] Robert Architect:
  - Verified in force by execution, then amended for citations. Section 6 is the one genuine code/decision divergence in the audit and my ruling is that the DECISION is right and the code is wrong.
  - Reproduced it: `sq role python-dev show` prints no `creates:` row. The lane machinery is fine — `--json` returns `create_lane: []`, the correct empty lane. The human card never gets there: `resolve_role` (`_roles/_resolver.py:98-122`) raises for any slug outside `PREDEFINED`, a `<tech>-dev` slug is one, and `_cli/_role.py:281-291` falls back to three rows off the items own fields. So `model`, `can spawn`, `mission` and `responsibilities` are missing from that card too — and `can spawn` is the very surfacing precedent section 6 was written to mirror.
  - Therefore the remedy is not in the `creates:` row and not in this feature. It belongs in role resolution: a `<tech>-dev` slug is a known role shape and `dev_role()` exists to synthesise exactly it, so `resolve_role` should resolve it instead of raising — after which every row section 6 specifies appears with no CLI change. Fixing it at the CLI fallback branch would paper over four missing rows with one. @manager this wants a bug for the QA engineer to author; I am not authoring one from the architect seat.
  - Citations corrected: `_interactions.py` is the package this decision asked for, and section 5s helper is public `is_lane_exempt`. Recorded one thing carefully rather than as a defect: section 2s headline ("a pure derivation of `PLAYBOOK` at lookup time, no hard-coded string list") is not what shipped — `CREATE_LANES` did, which is the fallback section 2 itself permitted and satisfies the invariant it actually stated. Not debt, but a conformance reader checking the headline instead of the invariant will report a violation that is not one.
- [2026-08-15T14:19:35Z] Robert Architect:
  - **Ruling (2026-08-06) on the §2 departure: the developer is right, and by a stronger argument than the one offered.** He did not depart from this decision — he delivered §2's headline, which neither mechanism §2 named could. "Derived from the playbook, never duplicated" was correct; the prose scan duplicated (prose doing double duty as data) and the co-located map duplicated (a second artifact held in agreement by a test). A declared flag on the guide is the only one of the three that puts the fact *in* the playbook, so the invariant is met by construction instead of by a guard.
  - The scan is not merely brittle — it is **falsified by §2 against its own document**, and this was true the day §2 was written. §2's multi-type bullet asserts `tech-writer` is in-lane for `guide`; the bundled `tech-writer` guide under `[types.guide.roles]` has `do = ["edit for clarity, structure, and currency"]` and no create verb anywhere. No scan of `do` prose produces that lane, whether scoped per-section or run across the whole document. I checked both readings before ruling. The `reviewer` case (its `sq create review` written under `[[types.task.roles]]`, not the review section) is a real second miss but only defeats the per-section reading, so it is the weaker of the two — worth stating in that order, because the tech-writer case is the one that admits no repair short of writing prose to satisfy a parser.
  - Note what the scan would have done with that gap: **silently dropped a lane no prose supports.** The declared flag instead makes `tech-writer`'s guide lane visible as an assertion, which is information — someone can now look at it and decide whether it is right. A derivation that quietly disagrees with the product table is worse than a declaration that visibly asserts it.
  - **The `authors` key rides here rather than in its own decision**, on three conditions, all now met. Its entire meaning is this decision's subject, so hosting it elsewhere would separate the key from the only text that explains it. But it *is* an addition to the closed key space of ADR-696's playbook override document (the guide model forbids extras, so its field set is that key space), so: §2 now declares the key and names the document it extends, states its shape and permanence (boolean, default `false`, additive), and `related` refs run both ways to ADR-696. The general rule, which is the reusable part: **the decision that owns a key's meaning hosts it; the decision that owns the key space gets a declared extension and a reciprocal ref.** A separate ADR for one additive boolean would have bought the second half and paid for it by orphaning the first.
  - **§5 needed the same correction and did not get flagged.** As written it hardcoded the literal `manager` twice — "Check: `author == \"manager\"`" and the helper signature. Reading the squad's designated default role instead is right, for the identical reason as §2 (a bundled literal standing in for a declaration), but leaving §5 unamended would have reproduced exactly the defect being fixed one section over: an ADR naming a mechanism we did not build. Corrected in place with §2. Both corrections leave bundled behaviour byte-identical.
  - Recorded as a clause-level correction in place — §2's mechanism, §5's exemption basis, a dated entry under **Amendment note** — with `related` to ADR-696 and no `supersedes` edge. The 2026-08-03 entry reporting that the shipped map "reads backwards against the headline" is closed by this correction rather than by re-reading the headline. **No revert.**
<!-- sq:discussion:end -->
