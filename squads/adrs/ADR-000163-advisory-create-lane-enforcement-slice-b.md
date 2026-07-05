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
created_at: '2026-06-22T12:14:44Z'
updated_at: '2026-06-22T12:35:54Z'
---
<!-- sq:body -->
## Status

Proposed — design for FEAT-122 Slice B (US1). Goes to the operator (Pierre) for approval
before any build. Parent context EPIC-121. Builds directly on Nina's lane-rules spec
(FEAT-122 body §1–§5, AC-B1..AC-B7) and adopts it; consistent with ADR-155
(capability attenuation) and ADR-158 (best-effort, untrusted lineage). Identity primitive
(FEAT-125) is Done — `current_actor()` and `current_session()` are available.

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

- For each `(item_type, ItemPlaybook)` in `PLAYBOOK`, the role is **in-lane to create** that type
  when it has a `RoleGuide` whose `do=` describes authoring it. The robust, low-coupling rule:
  a role is an in-lane author of `item_type` when its `RoleGuide.do` contains the create verb for
  that type — concretely, a bullet matching `sq create <item_type.value>` (the playbook already
  writes these literally, e.g. `sq create feature "…" --author product-owner`,
  `sq create task … --parent`, `sq create decision`, `sq create bug`, `add-finding`→`reviewer`
  opens a `review` via `sq create review`, `sq create guide`). The derivation keys off this verb
  rather than mere presence in the playbook, because several roles *interact* with a type
  (`tech-lead` reads/triages bugs and reviews) without being its in-lane **author**. The tech-lead
  who breaks down a feature into tasks should not warn on `sq create task`; the tech-lead who
  reads a bug should still warn on `sq create bug`.
- **`*dev` sentinel.** A `RoleGuide` whose `slug == DEV` (`_interactions.DEV == "*dev"`) applies to
  any `<tech>-dev` slug (`is_dev_slug`). The DEV guides in the playbook tell devs to *fix inside a
  task* and *file a defect as a bug* — they contain **no** `sq create <type>` author verb for a
  top-level item. So the derived dev create-lane is **empty** (see point 2a for the dev-bug rule).
- **Multi-type roles fall out for free.** `architect` is in-lane for both `decision` and `guide`
  (two `do=` author bullets); `tech-lead` for `task` (and co-authors `guide`); `reviewer` for
  `review`; `qa` for `bug`; `product-owner` for `feature` and `epic`; `tech-writer` for `guide`.
  This matches Nina's §1 table exactly.
- **Manager + operator exemptions are applied before lookup** (see point 5), so they never produce
  a warning regardless of the derived lane.

Resolving the derivation against the playbook prose is acceptable because the playbook commands are
authored to a fixed `sq create <type>` shape; the tech-lead breaking this down should add a small,
well-tested helper (`allowed_create_types`) next to `PLAYBOOK` in `_interactions.py`, with a unit
test pinning each role's lane to Nina's §1 table so a future playbook edit that changes a lane is
caught. (If the prose-scan proves brittle in implementation, the equivalent is a thin declarative
`CREATE_LANES: dict[slug-or-DEV, set[ItemType]]` *co-located in `_interactions.py` and asserted in a
test to agree with the playbook* — still one module, still the playbook as the audited source. The
tech-lead chooses the mechanism; the invariant is: one source, in `_interactions.py`, test-locked to
the playbook.)

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

- **Manager (`manager`)** — fully exempt from all lane checks (orchestrator; authors any type for
  coordination). Check: `author == "manager"`.
- **Operators (`op-*`)** — fully exempt. Humans coordinate freely; lane checks apply to agent role
  slugs only. Check: `author.startswith("op-")`. (Consistent with how operators are modelled as
  `OPERATOR` items with `op-` slugs; the same prefix the greeting/operator flows use.)
- **Tech-lead (`tech-lead`)** — exempt for `task` creation **because `task` is in its derived
  lane**, not via a special case. A tech-lead authoring a `feature` would still warn (that is the
  product-owner's lane), which is the correct behaviour per Nina's §4. So no extra tech-lead carve-
  out is needed for creates; the derived lane already gives the right answer. (If a future Option B
  mutation slice lands, tech-lead would get the mutation-lane exemptions Nina's §4 describes — out
  of scope here.)

A single `_is_lane_exempt(slug) -> bool` helper (`slug == "manager" or slug.startswith("op-")`),
co-located with the lane derivation in `_interactions.py`, keeps the rule in one place.

### 6. Surfacing / visibility

**Yes — surface the active create-lane in `sq role <slug> show`**, alongside Slice A's `can spawn`
(AC-B7). `_cli/_role.py` already renders a `can spawn: yes/no` row from `RoleDef.can_spawn`; add a
companion row, e.g. `creates: feature, epic` (the derived `allowed_create_types(slug)`, or
`creates: — (out-of-lane creates warn)` for roles with an empty lane such as devs/devops). Include
it in the `--json` output too (a `create_lane` array next to `can_spawn`). This makes the lane
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
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-22T12:35:54Z] Pierre Chat:
  - Approved at Option A: advisory create-lane enforcement, creates-only, warn-and-proceed (exit 0). Mutations stay unrestricted. Build it.
<!-- sq:discussion:end -->
