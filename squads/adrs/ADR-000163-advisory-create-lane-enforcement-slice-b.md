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
updated_at: '2026-10-25T21:36:51Z'
---
<!-- sq:body -->
## Context

When an agent role authors an item type outside its lane (e.g. a `python-dev` runs
`sq create feature`), squads surfaces a visible **advisory** warning, records it for forensics, and
**proceeds anyway** (FEAT-122 Slice B). This decision fixes that enforcement model.

Two prior decisions bound it and must not be contradicted:

- **ADR-155** places real *capability* enforcement (withholding the spawn tool) at the Claude Code
  backend, bound to the agent **type** at launch — not as an sq-runtime check. That slice is
  structural and trustworthy.
- **ADR-158** makes the recorded actor (slug + optional session/parent) **best-effort, untrusted,
  observability-only** — squads is a passive CLI, never in the spawn path; it cannot mint, inject,
  or verify identity. Its §7 is explicit: *any* lane enforcement keyed on the recorded actor is
  **inherently advisory** — it catches the honest accident, never stops a deliberate forger.

Create flows converge on one chokepoint, `ServiceCore.create` in `src/squads/_services/_base.py`. It
resolves `author`, opens the index transaction, runs the author/parent/assignee checks, allocates
the id, writes the file, and logs the `create` op to the reflog. The acting slug is available there
as `actor.current_actor()` and the declared author as the `author` argument. The service returns a
`CreateResult(item, path)` (`src/squads/_services/_results.py`) and the CLI (`_cli/_create.py`)
prints it. The layering invariant holds: **`_services` must not print** — warnings ride back in the
result; the CLI renders them, escaped via `_cli/_common.py::e()`.

The lane is **not** hand-maintained: the playbook (`_specs/playbook.toml`, ADR-226) is the canonical
role↔item-type document, and the lane is read from it.

## Decision

### 1. Scope — creates only (Option A)

Lane checks fire on **`sq create`** and its create-equivalents — everything that routes through
`ServiceCore.create`. **Mutations of existing items are not laned**: no status transition, body
edit, metadata update, or sub-entity mutation triggers a lane check. Under an advisory posture the
value of mutation restrictions is marginal against the friction they add to the normal loop
(tech-lead moving a feature to InProgress, QA closing a bug, manager reassigning mid-sprint); the
reflog already records who did what.

**Option B (laned status transitions) is a documented future upgrade.** Should real incidents show
the need, a later decision may add transition-lane checks (only the lifecycle-owning role advances
an item) on the same advisory warn-and-proceed mechanism. Option C (all mutations laned) is
rejected — too much friction for an advisory system.

### 2. Lane source of truth — declared in the playbook, never duplicated

The create-lane is read from the playbook itself: each role guide declares **`authors: bool`**. A
role is **in-lane to create** the type whose section its guide hangs under exactly when that guide
sets `authors = true`, and that declaration is the sole source of the lane. It is read from the
**active, merged** playbook, so a guide added or edited through `.overrides/playbook.toml` moves the
lane with it, and a role's lane is filtered to the types the active workflow spec still declares.

- **Why declared rather than inferred.** Several roles *interact* with a type without being its
  in-lane **author** (`tech-lead` reads and triages bugs and reviews): the tech-lead who breaks a
  feature down into tasks should not warn on `sq create task`; the tech-lead who reads a bug should
  still warn on `sq create bug`. A guide that only reads, triages or verifies declares nothing and
  carries no lane. Scanning a guide's `do` prose for `sq create <type>` cannot produce the lane set
  below — `tech-writer`'s guide on `guide` carries no create verb at all, and `reviewer`'s
  `sq create review` is written in the **task** section — so a scan would drop lanes silently and
  make prose load-bearing as data. A separate lane map beside the playbook would be a second
  artifact held in agreement by a test, and as a literal table it could only describe the bundled
  playbook. The declared flag keeps the fact *in* the playbook: one artifact, nothing to sync.
- **Capability guides.** A guide addressed to `*<capability>` (e.g. `*dev`) applies to every role
  holding that capability (ADR-984). The developer guides declare no `authors`, so the developer
  create-lane is **empty by declaration** rather than by a special case (see 2a).
- **Multi-type roles fall out for free.** In the bundled playbook `architect` is in-lane for
  `decision` and `guide`; `tech-lead` for `task`; `reviewer` for `review`;
  `qa` for `bug`; `product-owner` for `feature`, `epic`, `contract` and `milestone`; `tech-writer`
  for `guide`.
- **Exemptions are applied before lookup** (see point 5), so they never produce a warning
  regardless of the lane.

**The key, declared against the document it extends.** `authors` is part of the closed key space of
the playbook override document, whose grammar, merge, stamp and validation belong to ADR-696; the
guide model forbids extras, so its field set *is* that key space. `authors` is boolean, defaults to
`false`, and is additive. An adopter may declare it on any guide in an override, and a guide that
omits it behaves as a non-author.

#### 2a. Developer-authored bugs are allowed, with an advisory warning

The playbook gives developers no in-lane create, while the developer guide says "file a newly-found
defect as a bug" and the `qa` guide owns `sq create bug`. A developer running `sq create bug` is
**allowed and proceeds, emitting the standard advisory warning** (expected in-lane author: `qa`).
The `--author qa` slug is not required:

- It is consistent with the whole posture: warn-and-proceed, never block. A developer who finds a
  real defect mid-task can file it on the spot.
- The warning still creates the forensic record that qa's lane was crossed, so triage can
  re-attribute if desired.
- There is no developer-specific carve-out in the lane logic: the developer create-lane stays empty,
  and the developer-bug case is one instance of the general out-of-lane-but-allowed rule.

### 3. Where enforcement sits + the end-to-end data path

Advisory **warn-and-proceed**, computed in the **service layer**, returned in the create result,
rendered (escaped) by the CLI, and recorded in the reflog. No hard block and no override flag —
nothing is ever blocked, so there is nothing to override.

1. **Compute (service).** In `ServiceCore.create`, after `author` is resolved, the lane check runs
   on the **declared `author`** — the slug that will own the item and what `--author` sets:
   - exempt authors (point 5) → no warning;
   - else if the type is in the author's create-lane (`allowed_create_types`) → no warning;
   - else a warning naming the author, the expected in-lane role(s) and the item type. The expected
     owner is the inverse lookup (`in_lane_owner`): which roster role(s) are in-lane to create that
     type.
2. **Record (reflog).** The warning is included in the `create` op's delta as a `lane_warning`
   entry carrying the author, the expected roles, the type and `advisory: true`, so a reader knows
   it is not an error. The reflog delta is additive and free-form, so this needs no schema bump.
3. **Return (result).** `CreateResult.lane_warning: str | None` carries the rendered sentence when a
   warning was produced. The service **does not print**.
4. **Render (CLI).** After the created line, the CLI prints the warning **escaped via `e()`**. Exit
   code stays **0** — the item was created. In `--json` mode the warning is a field of the emitted
   object rather than a side-channel line, so machine consumers see it too.

**Warning content** names the authoring role, the expected in-lane role, and the item type, in
advisory language, e.g.:

> `advisory: 'python-dev' is not the in-lane author for 'feature' items (expected: 'product-owner'). Lane checks are best-effort and advisory — proceeding.`

### 4. Identity basis + honesty

The check keys off the **self-declared `--as`/`--author` slug**. The session pair from ADR-158 is
**context only** — it may be carried into the reflog for forensics but is **never** the basis of the
lane decision, because it is equally untrusted.

Everywhere the feature surfaces (CLI text, `sq role show`, docs), the lane check is described as
**advisory, best-effort, untrusted**. It catches the honest accident; it never stops a forger — a
wrong or forged `--as` slug bypasses it trivially. **No enforcement-grade, tamper-evident, security,
or forge-proof claim may appear** in any CLI string or doc, and the warning text itself carries
"advisory" / "best-effort" language.

### 5. Exemptions

Determined **before** the lane lookup, by `is_lane_exempt(slug, default_slug)` in
`_interactions/_role_guidance.py`:

- **The squad's default role** — fully exempt (the orchestrator authors any type for coordination).
  The default is the slug the squad designates, read from the live roster and falling back to the
  role catalog's own designation — never a literal slug — so `sq role <slug> set-default` moves the
  exemption. In the bundled roster that slug is `manager`.
- **Operators (`op-*`)** — fully exempt. Humans coordinate freely; lane checks apply to agent role
  slugs only.
- **No tech-lead carve-out.** A tech-lead creating a `task` is silent because `task` is in its
  declared lane; a tech-lead authoring a `feature` warns (that is the product-owner's lane).

### 6. Surfacing / visibility

**`sq role <slug> show` displays the active create-lane** alongside ADR-155's `can spawn` row: a
`creates:` row listing the role's lane (e.g. `creates: feature, epic`), or
`creates: — (out-of-lane creates warn)` for a role with an empty lane such as a developer. The
`--json` output carries it as a `create_lane` array next to `can_spawn`. The lane is read from the
playbook, not stored on the role, so `sq role show` computes it on the fly — no persisted field.

## Consequences

- **Positive.** One chokepoint (`ServiceCore.create`), one source (the playbook's `authors`
  declarations), layering preserved (service returns, CLI prints). Declaring `authors` on a guide —
  bundled or override — extends a lane with no code change. The forensic trail is complete via the
  reflog delta. No migration: the reflog delta and the `CreateResult` field are additive. The honest
  accident (a developer creating a feature, a developer filing a bug) is visible in real time and in
  the reflog.
- **Negative / limits (documented, not hidden).** **Advisory only.** Keyed on the self-declared
  slug, which is untrusted (ADR-158): a forged `--as` slug bypasses the check silently, and the
  developer-bug case proceeds by design. Mutations are entirely unlaned (Option A) — a role can
  transition or edit any item with no warning. These are accepted trade-offs of an advisory posture,
  not gaps to be "fixed" by over-claiming.
- **Future upgrade path preserved.** Option B (laned status transitions) reuses this exact
  warn-and-proceed plumbing on the mutation chokepoints, as a deliberate later decision.
- **Tests never assert a block, a non-zero exit, or a security guarantee** for this feature.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-06-22T12:35:54Z] `op-pierre` Pierre Chat:
  - Approved at Option A: advisory create-lane enforcement, creates-only, warn-and-proceed (exit 0). Mutations stay unrestricted. Build it.
- [2026-08-03T08:49:54Z] `architect` Robert Architect:
  - Verified in force by execution, then amended for citations. Section 6 is the one genuine code/decision divergence in the audit and my ruling is that the DECISION is right and the code is wrong.
  - Reproduced it: `sq role python-dev show` prints no `creates:` row. The lane machinery is fine — `--json` returns `create_lane: []`, the correct empty lane. The human card never gets there: `resolve_role` (`_roles/_resolver.py:98-122`) raises for any slug outside `PREDEFINED`, a `<tech>-dev` slug is one, and `_cli/_role.py:281-291` falls back to three rows off the items own fields. So `model`, `can spawn`, `mission` and `responsibilities` are missing from that card too — and `can spawn` is the very surfacing precedent section 6 was written to mirror.
  - Therefore the remedy is not in the `creates:` row and not in this feature. It belongs in role resolution: a `<tech>-dev` slug is a known role shape and `dev_role()` exists to synthesise exactly it, so `resolve_role` should resolve it instead of raising — after which every row section 6 specifies appears with no CLI change. Fixing it at the CLI fallback branch would paper over four missing rows with one. @manager this wants a bug for the QA engineer to author; I am not authoring one from the architect seat.
  - Citations corrected: `_interactions.py` is the package this decision asked for, and section 5s helper is public `is_lane_exempt`. Recorded one thing carefully rather than as a defect: section 2s headline ("a pure derivation of `PLAYBOOK` at lookup time, no hard-coded string list") is not what shipped — `CREATE_LANES` did, which is the fallback section 2 itself permitted and satisfies the invariant it actually stated. Not debt, but a conformance reader checking the headline instead of the invariant will report a violation that is not one.
- [2026-08-15T14:19:35Z] `architect` Robert Architect:
  - **Ruling (2026-08-06) on the §2 departure: the developer is right, and by a stronger argument than the one offered.** He did not depart from this decision — he delivered §2's headline, which neither mechanism §2 named could. "Derived from the playbook, never duplicated" was correct; the prose scan duplicated (prose doing double duty as data) and the co-located map duplicated (a second artifact held in agreement by a test). A declared flag on the guide is the only one of the three that puts the fact *in* the playbook, so the invariant is met by construction instead of by a guard.
  - The scan is not merely brittle — it is **falsified by §2 against its own document**, and this was true the day §2 was written. §2's multi-type bullet asserts `tech-writer` is in-lane for `guide`; the bundled `tech-writer` guide under `[types.guide.roles]` has `do = ["edit for clarity, structure, and currency"]` and no create verb anywhere. No scan of `do` prose produces that lane, whether scoped per-section or run across the whole document. I checked both readings before ruling. The `reviewer` case (its `sq create review` written under `[[types.task.roles]]`, not the review section) is a real second miss but only defeats the per-section reading, so it is the weaker of the two — worth stating in that order, because the tech-writer case is the one that admits no repair short of writing prose to satisfy a parser.
  - Note what the scan would have done with that gap: **silently dropped a lane no prose supports.** The declared flag instead makes `tech-writer`'s guide lane visible as an assertion, which is information — someone can now look at it and decide whether it is right. A derivation that quietly disagrees with the product table is worse than a declaration that visibly asserts it.
  - **The `authors` key rides here rather than in its own decision**, on three conditions, all now met. Its entire meaning is this decision's subject, so hosting it elsewhere would separate the key from the only text that explains it. But it *is* an addition to the closed key space of ADR-696's playbook override document (the guide model forbids extras, so its field set is that key space), so: §2 now declares the key and names the document it extends, states its shape and permanence (boolean, default `false`, additive), and `related` refs run both ways to ADR-696. The general rule, which is the reusable part: **the decision that owns a key's meaning hosts it; the decision that owns the key space gets a declared extension and a reciprocal ref.** A separate ADR for one additive boolean would have bought the second half and paid for it by orphaning the first.
  - **§5 needed the same correction and did not get flagged.** As written it hardcoded the literal `manager` twice — "Check: `author == \"manager\"`" and the helper signature. Reading the squad's designated default role instead is right, for the identical reason as §2 (a bundled literal standing in for a declaration), but leaving §5 unamended would have reproduced exactly the defect being fixed one section over: an ADR naming a mechanism we did not build. Corrected in place with §2. Both corrections leave bundled behaviour byte-identical.
  - Recorded as a clause-level correction in place — §2's mechanism, §5's exemption basis, a dated entry under **Amendment note** — with `related` to ADR-696 and no `supersedes` edge. The 2026-08-03 entry reporting that the shipped map "reads backwards against the headline" is closed by this correction rather than by re-reading the headline. **No revert.**
- [2026-10-25T21:36:51Z] `architect` Robert Architect:
  - 2026-10-25 audit: rewritten; decision unchanged. Lanes are declared by `authors = true` in the merged playbook. Developer guides are `*<capability>` (ADR-984). Helpers live in `_interactions/_role_guidance.py`. The verb is `set-default`. The §6 gap is closed: `sq role python-dev show` prints `creates:`. Removed the amendment sediment and the tech-lead brief.
<!-- sq:discussion:end -->
