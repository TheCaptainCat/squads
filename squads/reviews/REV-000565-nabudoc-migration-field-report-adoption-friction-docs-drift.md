---
id: REV-565
sequence_id: 565
type: review
title: 'Nabudoc migration field report: adoption friction, docs drift, design gaps'
status: Requested
author: reviewer
refs:
- FEAT-543
- EPIC-538
- FEAT-533
subentities:
- local_id: F1
  title: Global IDs break dense cross-refs; no alias / preferred-ID on import
  status: WontFix
  severity: high
- local_id: F2
  title: History replay is one-timestamp-per-invocation; no bulk event import
  status: Open
  severity: high
- local_id: F3
  title: 'Docs drift: sq role list / --available do not exist (it is role catalog)'
  status: Open
  severity: medium
- local_id: F4
  title: 'Docs drift + CLI gap: no verb to enumerate operators'
  status: Open
  severity: medium
- local_id: F5
  title: 'Docs drift: story add / subtask add — actual verbs are add-story / add-subtask'
  status: Open
  severity: medium
- local_id: F6
  title: 'Docs: stale override-base version examples'
  status: Open
  severity: low
- local_id: F7
  title: No bundled designer/UX role; dev add requires a coding --tech
  status: Open
  severity: medium
- local_id: F8
  title: init/adopt into a pre-existing non-squads CLAUDE.md/.claude is unspecified
  status: Open
  severity: medium
- local_id: F9
  title: Closed items (incl. Accepted decisions) hidden from default list/tree
  status: Open
  severity: medium
- local_id: F10
  title: add-* leaves an unwritten-body stub that sq check warns on
  status: Open
  severity: low
- local_id: F11
  title: Sub-entity title-length advisory fires easily on migrated data
  status: WontFix
  severity: low
- local_id: F12
  title: Per-invocation process overhead
  status: WontFix
  severity: low
- local_id: F13
  title: Sub-entities cannot be deleted (no remove for finding/story/subtask)
  status: Open
  severity: medium
- local_id: F14
  title: add-* cannot take --severity/--status inline (two-step for full metadata)
  status: Open
  severity: low
- local_id: F15
  title: No read-back verb for an item's discussion/comments
  status: Open
  severity: low
created_at: '2026-07-22T07:54:46Z'
updated_at: '2026-07-22T08:24:28Z'
---
<!-- sq:body -->
## Scope

Field report from the **first real external adoption** of squads (the "Nabudoc" project,
squads **0.11.1**): a Claude session converted a home-made role/workflow corpus into a squad and
logged every friction point, docs drift, and design surprise. This is adopter feedback about
**squads the product**, not a code-diff review of a specific change.

The migration exercised a dense, mature corpus — ~460 `sq` invocations from a Python driver
covering **6 features / 26 stories / 34 tasks / 121 subtasks / 38 ADRs / 7 reviews (~50 findings) /
3 bugs / 2 guides / 186 dated comments**, with full history replayed via `--at`. Final migration
`sq check` was clean (exit 0).

**Headline positive:** the data model held with **zero contortion**. The epic→feature→task
hierarchy, story/subtask sub-entities with `--story` mapping, the decision/review/guide types, the
8 ref kinds, and dated attributed discussion all mapped a real messy corpus cleanly. Nothing about
the data model was a blocker.

The findings below are **adoption-ergonomics, docs-accuracy, and design-gap** inputs — NOT
data-model defects. They are triage material for the operator; each becomes a fix-task or feature
only if we decide to act on it.

## What was genuinely good (keep it — on the record as positives)

- **`--at` is the right primitive for history** — global, ISO-8601, applied per invocation,
  survives `repair`/`check`. Made a faithful timeline possible at all.
- **`--json` on `create`/`add-*`/`list`/`findings`** returns clean structured output including the
  new `id`/`local_id` — reliable ID capture without scraping human text. This is what made
  scripting the migration sane.
- **The data model fit a real, messy corpus with zero contortion** (see headline above).
- **`sq check` is trustworthy** — it caught the unwritten-finding-body stubs and the long titles,
  and went green once fixed. Exit codes are clean for CI.
- **Sequential story/subtask local IDs** (`US1…`, `ST1…`) matched the old ordering, so `--story US2`
  mapping "just worked".
- **`sq workflow` / `sq docs` offline** are excellent for ramping — the whole model was learnable
  from them before touching anything (the drift below aside).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 565 add-finding "…" --severity medium`; track with `sq review 565 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟠 high | WontFix |  | Global IDs break dense cross-refs; no alias / preferred-ID on import |
| F2 | 🟠 high | Open |  | History replay is one-timestamp-per-invocation; no bulk event import |
| F3 | 🟡 medium | Open |  | Docs drift: sq role list / --available do not exist (it is role catalog) |
| F4 | 🟡 medium | Open |  | Docs drift + CLI gap: no verb to enumerate operators |
| F5 | 🟡 medium | Open |  | Docs drift: story add / subtask add — actual verbs are add-story / add-subtask |
| F6 | 🟢 low | Open |  | Docs: stale override-base version examples |
| F7 | 🟡 medium | Open |  | No bundled designer/UX role; dev add requires a coding --tech |
| F8 | 🟡 medium | Open |  | init/adopt into a pre-existing non-squads CLAUDE.md/.claude is unspecified |
| F9 | 🟡 medium | Open |  | Closed items (incl. Accepted decisions) hidden from default list/tree |
| F10 | 🟢 low | Open |  | add-* leaves an unwritten-body stub that sq check warns on |
| F11 | 🟢 low | WontFix |  | Sub-entity title-length advisory fires easily on migrated data |
| F12 | 🟢 low | WontFix |  | Per-invocation process overhead |
| F13 | 🟡 medium | Open |  | Sub-entities cannot be deleted (no remove for finding/story/subtask) |
| F14 | 🟢 low | Open |  | add-* cannot take --severity/--status inline (two-step for full metadata) |
| F15 | 🟢 low | Open |  | No read-back verb for an item's discussion/comments |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Global IDs break dense cross-refs; no alias / preferred-ID on import

<!-- sq:finding:F1:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟠 High
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Report §2.1 — the dominant hidden cost of the migration.

The old corpus used **feature-scoped** IDs referenced inline everywhere (tasks cite `AD-032`,
`TASK-006-002`, `US-006-003`; reviews cite features; ADRs cite each other). squads mints
**global** IDs in adoption order (`ADR-22…59`, `TASK-60…`), so:

- Every inline reference in prose is now stale (`AD-032` no longer resolves).
- The only recovery is a lookup table the migrator builds and threads through every phase
  (`adr_map`, `story_map`, `feat_map`, `rev_map`, `task_map` were persisted in scratchpad).
- Structural links were rebuilt as real refs (122 ADR `implements`, 4 review `addresses`, parents,
  story mappings), but **inline prose IDs stay as legacy text** — a `_Migrated from … (AD-031)_`
  breadcrumb was left in each body so a human/agent can still trace them.

**Impact:** the single biggest reason the migration needed a bespoke parser + driver rather than a
few commands.

**Suggested fixes (any one helps):**
- An import mode that lets you **assign the ID/number** on create (`sq create … --id ADR-31`) so
  original numbering is preserved and every inline reference keeps resolving.
- Or a **stable external-alias field** on items (`--alias AD-031`) that `sq search`/`sq show`
  resolve, so old identifiers stay first-class.
- Or a documented **ref-rewrite helper** that takes an old→new map and rewrites inline IDs in bodies.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — History replay is one-timestamp-per-invocation; no bulk event import

<!-- sq:finding:F2:head -->
**Status:** 🔴 Open
**Severity:** 🟠 High
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
Report §2.2.

`--at` is excellent and did exactly what's advertised, but it's **one timestamp per command**.
Faithfully replaying revision-history rows + dated discussion handoffs across ~50 items meant ~460
separate `sq` calls. There's no batch/manifest format, so every migration must write its own
subprocess driver, and per-call process overhead makes it slow.

**Suggested fix:** a **bulk event-import format** — e.g. `sq import events.jsonl` where each line is
`{at, op: "create|status|comment|ref|body|add-story|…", …}`. This turns "write a parser *and* a
driver" into "emit a file", and collapses hundreds of process spawns into one.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Docs drift: sq role list / --available do not exist (it is role catalog)

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Report §3.1 — docs drift, verified against 0.11.1.

**Docs say:** `sq role list`, `sq role list --available`.
**Actual CLI:** there is no `list` verb — `list` is parsed as a role *address* and errors. The
active/available roster is `sq role catalog` (but catalog has no active/inactive marker).
**Where:** `docs roles`, `docs recipes`, `docs agents`.

**Suggested fix:** a docs test that shells the exact commands in the docs against the current CLI
(even just the verb names) would catch this mechanically.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Docs drift + CLI gap: no verb to enumerate operators

<!-- sq:finding:F4:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Report §3.2 — docs drift AND a real CLI gap, verified against 0.11.1.

**Docs say:** `sq operator list`.
**Actual CLI:** no operator list verb at all — only `add` / `show` / `rm`. There is **no way to
enumerate operators from the CLI**.
**Where:** `docs roles`, `docs agents`.

So this is both a docs fix and a genuine missing command. Adding `sq operator list` (with `--json`)
would close the gap and make the docs true.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Docs drift: story add / subtask add — actual verbs are add-story / add-subtask

<!-- sq:finding:F5:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F5:head:end -->

<!-- sq:finding:F5:body -->
Report §3.3 — docs drift, verified against 0.11.1.

**Docs say:** `sq … story add FEAT-7 "…"`, `subtask add TASK-8 "…"`.
**Actual CLI:** the verbs are `add-story` / `add-subtask` on the addressed item
(`sq feature 7 add-story "…"`).
**Where:** `docs adoption`, `docs tutorial`.

**Suggested fix:** covered by the docs-command test proposed for the §3.1 drift.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Docs: stale override-base version examples

<!-- sq:finding:F6:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F6:head:end -->

<!-- sq:finding:F6:body -->
Report §3.4 — docs, verified against 0.11.1.

The `docs overrides` page uses `override-base:0.4.2` example strings. The installed version is
0.11.1, so the examples read as stale.

**Suggested fix:** refresh the version examples (or make them version-agnostic) so they don't
signal an old release.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — No bundled designer/UX role; dev add requires a coding --tech

<!-- sq:finding:F7:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F7:head:end -->

<!-- sq:finding:F7:body -->
Report §4.1.

The old team had a **UX/UI Dev** (design quality, a11y, UX consistency — not a code implementer).
It maps to neither a bundled role nor cleanly to `sq dev add`, because `dev add` requires
`--tech <coding-stack>`. The only clean path was a custom `.overrides/roles/ux-ui-dev.toml`. The
operator chose to drop it, but it forced a decision that shouldn't be necessary.

**Suggested fix:** ship a `designer`/`ux` bundled role, or let `dev` represent non-code specialties
(e.g. `sq dev add --tech ux --kind design`).

**Note (triage):** partially addressed since 0.11.1 by FEAT-543 (custom non-dev role scaffolding
via `.overrides/roles`) and is squarely within EPIC-538 (spec-driven customization). Remaining gap
vs. the report: a *bundled* designer/UX role out of the box, and/or `dev add` accepting a non-code
specialty without a hand-written override.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — init/adopt into a pre-existing non-squads CLAUDE.md/.claude is unspecified

<!-- sq:finding:F8:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F8:head:end -->

<!-- sq:finding:F8:body -->
Report §4.2.

The project already had a hand-written `CLAUDE.md` (no managed markers) and hand-made
`.claude/agents/*.md`. Running `init`:
- **Appended** the managed `<!-- squads:start -->…<!-- squads:end -->` block *below* the existing
  hand-written operating model, leaving contradictory instructions co-resident until reconciled by
  hand.
- **Overwrote** pointers whose slug happened to match (`architect.md`, `qa.md`, …) but **left
  orphaned** the non-matching home-made ones (`lead.md`, `project-manager.md`, `ux-ui-dev.md`,
  `.index.md`), which had to be deleted manually.

`adopt` is documented as "non-destructive," but the interaction with a **pre-existing non-squads**
CLAUDE.md/`.claude` isn't covered.

**Suggested fix:** a documented "adopting into a project that already has CLAUDE.md/.claude"
runbook, and ideally an `init`/`adopt` warning that lists pre-existing agent pointers it did **not**
generate (candidate orphans).
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Closed items (incl. Accepted decisions) hidden from default list/tree

<!-- sq:finding:F9:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F9:head:end -->

<!-- sq:finding:F9:body -->
Report §4.3 — surprising, not wrong.

After migrating a mostly-completed history, `sq tree` and `sq list` look **nearly empty**: features
are `Done`, ADRs are `Accepted`, bugs `Verified` — all hidden unless `--all`. For features/bugs
that's reasonable. For **decisions it's surprising**: an `Accepted` ADR is *live reference*, not
"finished work", yet the entire decision log is hidden by default.

**Suggested fix:** treat `Accepted` as non-hiding for decisions (they're the standing record), or
add a hint in empty `sq list`/`sq tree` output ("N closed items hidden — use `--all`").
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — add-* leaves an unwritten-body stub that sq check warns on

<!-- sq:finding:F10:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F10:head:end -->

<!-- sq:finding:F10:body -->
Report §4.4.

Creating a sub-entity with only a title (`add-finding "…"`) leaves a placeholder body, and
`sq check` then warns `F6 body is unwritten (still the placeholder stub)`. So the "quick" creation
path produces a lint warning until you *also* set a body. For a review with N findings that's N
extra body-set calls just to get a clean check.

**Suggested fix:** either let a non-empty title satisfy the check, or make `add-finding` accept the
body as the primary positional so the one-shot form is clean by default.

Related: §7.2 (F14) — the metadata two-step compounds this.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Sub-entity title-length advisory fires easily on migrated data

<!-- sq:finding:F11:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F11:head:end -->

<!-- sq:finding:F11:body -->
Report §4.5.

Using each source subtask's one-line description as the subtask **title** tripped the >120-char
advisory 33 times. Reasonable guidance, but on import the "description" *is* the natural title.
Minor; the migrator truncated titles and kept full text in the body.

**Suggested fix (if any):** on bulk import, treat an over-long title as a hint to auto-split
title/body rather than a per-item advisory, or relax the advisory for imported items.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — Per-invocation process overhead

<!-- sq:finding:F12:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F12:head:end -->

<!-- sq:finding:F12:body -->
Report §4.6 — subsumed by §2.2 (F2).

Every `sq` call is a fresh process (Python import + index load). Fine interactively; painful at
460 calls. A batch/import mode (§2.2 / F2) or a persistent `sq` session/daemon would remove it.

**Note (triage):** the statelessness precondition for a long-lived/daemon `sq` process is being
built by FEAT-533 (one process, many squads, per-request context). This finding is the
migration-perf motivation for that direction; the actual fix is the bulk-import format in F2.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Sub-entities cannot be deleted (no remove for finding/story/subtask)

<!-- sq:finding:F13:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F13:head:end -->

<!-- sq:finding:F13:body -->
Report §7.1 (surfaced in the review-rework pass).

`finding` / `story` / `subtask` support `show` / `update` / `body` / `comment` — but there is **no
`remove`**. A mis-created or spurious sub-entity is permanent; the only recourse is to re-title it
or repurpose its body. Hit concretely: the first migration pass created a spurious finding on the
FEAT-006 review (an over-broad parse), and there was no way to delete it — only overwrite it with a
"consolidated into other findings" note.

Parent items *do* have `remove`; sub-entities should too (guarded / `--yes`), so migrations and
mistakes are correctable.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — add-* cannot take --severity/--status inline (two-step for full metadata)

<!-- sq:finding:F14:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F14:head:end -->

<!-- sq:finding:F14:body -->
Report §7.2 (surfaced in the review-rework pass).

`add-finding` / `add-story` / `add-subtask` accept a title + body (`--file`/`-m`) +
`--assignee`/`--story`, but **not** `--status` inline. Setting a non-initial status requires a
follow-up `update … --status … --force`. Combined with §4.4 (F10) — the created sub-entity's body
is an unwritten stub that `sq check` warns on until set — the "quick" one-shot form essentially
always needs a second (often third) call to be clean.

**Suggested fix:** let `add-*` take `--status` (and treat a provided body as non-stub) so the
common path is one call.

**Reviewer note (current tree):** since the 0.11.1 report, `add-finding` now *does* accept
`--severity` inline (used to author this very review). So the severity half of §7.2 is already
partly closed; the remaining gap is `--status` inline + the body-stub interaction with `sq check`.
Verify parity across `add-story`/`add-subtask` before scoping a fix.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — No read-back verb for an item's discussion/comments

<!-- sq:finding:F15:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F15:head:end -->

<!-- sq:finding:F15:body -->
Report §7.3 (surfaced in the review-rework pass) — discoverability.

`sq <type> <n> comment` appends a comment, but there is no `comments` / `discussion` subcommand to
list them back. To verify the 112 migrated review comments the migrator had to `show --json` and
read the `discussion[]` array (or eyeball `show --comments`).

**Suggested fix:** a dedicated `sq <type> <n> comments` (with `--json`) would round out the CRUD
surface and aid scripting/verification.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-22T08:24:25Z] Pierre Chat:
  - Triage of all 15 findings (fix / won't-fix + how):
    - F1 WON'T FIX — prefer a generic *link* feature (design later) over alias/preferred-ID import.
    - F2 DEFER — draft an 'sq import' bulk-event-import command as a feature, for later.
    - F3 FIX — add a real 'sq role list' verb (active/inactive marker) + fix docs.
    - F4 FIX — add 'sq operator list' verb (+ --json) + fix docs.
    - F5 FIX — correct add-story/add-subtask verb docs + a docs command-test (also covers F3).
    - F6 FIX — refresh stale override-base version examples + guard against version drift.
    - F7 RESOLVED via FEAT-543 — no bundled designer role; document the custom-role (.overrides/roles) path for non-code roles.
    - F8 FIX — init/adopt orphan-warning (list non-generated pointers) + 'adopting into an existing CLAUDE.md/.claude' runbook.
    - F9 FIX — category-aware visibility: records stay visible while final, hide when cancelled/superseded; + empty-view hint; + a category filter on all filterable surfaces (rides EPIC-538 category axis).
    - F10 FIX — add-finding/story/subtask take a body via stdin/file/inline; placeholder only when absent.
    - F11 WON'T FIX — keep the >120-char title advisory (truncate title, full text in body).
    - F12 FOLD — no separate item; covered by F2 (bulk import) + FEAT-533 (daemon).
    - F13 FIX — add a guarded 'remove' (--yes) for finding/story/subtask.
    - F14 FIX — make the add-* command builder dynamically generate the spec's badge/field --flags (generic, not hardcoded --severity/--status).
    - F15 FIX — add a dedicated 'sq <type> <n> comments' read-back verb (+ --json).
<!-- sq:discussion:end -->
