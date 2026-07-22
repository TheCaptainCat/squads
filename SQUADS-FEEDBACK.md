# squads — field report from the first real migration (Nabudoc)

**Author:** Claude (Catherine Manager session), driving the conversion for the operator.
**Date:** 2026-07-21
**squads version:** 0.11.1 (`sq --version`)
**Context:** Nabudoc is the first real project migrated onto squads besides squads itself. This is
a dogfooding report: what worked, and every friction point / ambiguity / doc drift hit while
converting a home-made role-based agent system into a squad.

---

## 1. What was migrated (so you know the surface this exercised)

A mature, densely cross-referenced corpus, all authored by hand in the old system:

| Old artifact | → squads type | Volume |
|---|---|---|
| `specs/features/FEAT-00X` (+ user stories) | `feature` (+ `add-story`) | 6 features, 26 stories |
| `dev/tasks/TASKS-FEAT-00X` (+ `.N` subtasks) | `task` (+ `add-subtask --story`) | 34 tasks, 121 subtasks |
| `specs/architecture.md` (`AD-001…038`) | `decision` (`ADR-22…59`) | 38 ADRs |
| `dev/reviews/REVIEW-*` | `review` (+ `add-finding`) | 7 reviews, ~50 findings |
| `dev/bugs/BUG-*` | `bug` | 3 |
| `specs/guides/*` | `guide` | 2 |
| dev handoff discussion threads | dated `comment`s | 186 comments |
| 9 home-made roles | bundled roster + `sq dev add` | 8 roles (UX/UI dropped) |

History was preserved with `--at` (origin dates on creation, real closure dates, real dates on
every handoff comment). Final `sq check`: **✓ no issues, exit 0**. The whole migration ran as
~460 `sq` invocations from a Python driver.

**Net verdict:** squads modeled this domain faithfully — the epic→feature→task hierarchy,
story/subtask sub-entities, decision/review/guide types, refs, and dated discussion all mapped
cleanly. Nothing about the data model was a blocker. The friction below is about *migration
ergonomics*, *docs accuracy*, and a few *design surprises* — not about whether squads can hold the
work. It can.

---

## 2. High-impact gaps (cost drivers for any migration)

### 2.1 Global IDs break dense cross-references — no alias / preferred-ID import
**Severity: high (the dominant hidden cost).**

The old corpus used *feature-scoped* IDs referenced inline everywhere: tasks cite `AD-032`,
`TASK-006-002`, `US-006-003`; reviews cite features; ADRs cite each other. squads mints *global*
IDs in **adoption order** (`ADR-22…59`, `TASK-60…`), so:

- Every inline reference in prose is now stale (`AD-032` no longer resolves to anything).
- The only recovery path is a lookup table the migrator has to build and thread through every
  phase (I persisted `adr_map`, `story_map`, `feat_map`, `rev_map`, `task_map` in scratchpad).
- I rebuilt the **structural** links as real refs (122 ADR `implements`, 4 review `addresses`,
  parents, story mappings), but **inline prose IDs stay as legacy text** — I left a
  `_Migrated from … (AD-031)_` breadcrumb in each body so a human/agent can still trace them.

**Impact:** this is the single biggest reason the migration needed a bespoke parser+driver rather
than a few commands.

**Suggested fixes (any one helps):**
- An import mode that lets you **assign the ID/number** on create (`sq create … --id ADR-31`), so a
  migration can preserve the original numbering and every inline reference keeps resolving.
- Or a **stable external-alias field** on items (`--alias AD-031`) that `sq search`/`sq show` resolve,
  so old identifiers remain first-class.
- Or a documented **ref-rewrite helper** that takes an old→new map and rewrites inline IDs in bodies.

### 2.2 History replay is one-timestamp-per-invocation — no bulk import
**Severity: high.**

`--at` is excellent and did exactly what's advertised, but it's **one timestamp per command**.
Faithfully replaying revision-history rows + dated discussion handoffs across ~50 items meant ~460
separate `sq` calls. There's no batch/manifest format, so every migration must write its own
subprocess driver, and per-call process overhead makes it slow.

**Suggested fix:** a **bulk event-import format** — e.g. `sq import events.jsonl` where each line is
`{at, op: "create|status|comment|ref|body|add-story|…", …}`. This turns "write a parser *and* a
driver" into "emit a file", and collapses hundreds of process spawns into one.

---

## 3. Docs ↔ CLI drift (all verified against 0.11.1)

These cost real time because the docs are otherwise good enough to trust verbatim.

| # | Docs say | Actual CLI | Where |
|---|---|---|---|
| 3.1 | `sq role list`, `sq role list --available` | **No `list` verb.** `list` is parsed as a role address → error. Active/available roster is `sq role catalog` (but catalog has no active/inactive marker). | `docs roles`, `docs recipes`, `docs agents` |
| 3.2 | `sq operator list` | **No operator list verb at all** — only `add`/`show`/`rm`. No way to enumerate operators from the CLI. | `docs roles`, `docs agents` |
| 3.3 | `sq … story add FEAT-7 "…"`, `subtask add TASK-8 "…"` | Verbs are `add-story` / `add-subtask` on the addressed item (`sq feature 7 add-story "…"`). | `docs adoption`, `docs tutorial` |
| 3.4 | `override-base:0.4.2` example strings | Installed version is 0.11.1; examples read as stale. | `docs overrides` |

**Suggested fix:** a docs test that shells the exact commands in the docs against the current CLI
(even just the verb names) would catch 3.1–3.3 mechanically.

---

## 4. Design rough edges / surprises

### 4.1 No design/UX role in the bundle, and `dev` assumes a coding stack
**Severity: medium.**

The old team had a **UX/UI Dev** (design quality, a11y, UX consistency — not a code implementer).
It maps to neither a bundled role nor cleanly to `sq dev add`, because `dev add` requires
`--tech <coding-stack>`. The only clean path was a custom `.overrides/roles/ux-ui-dev.toml`.
(The operator chose to drop it, but it forced a decision that shouldn't be necessary.)

**Suggested fix:** ship a `designer`/`ux` bundled role, or let `dev` represent non-code specialties
(e.g. `sq dev add --tech ux --kind design`).

### 4.2 `adopt`/`init` into a project that already has `CLAUDE.md` + `.claude/agents` is unspecified
**Severity: medium.**

This project already had a hand-written `CLAUDE.md` (no managed markers) and hand-made
`.claude/agents/*.md`. Running `init`:
- **Appended** the managed `<!-- squads:start -->…<!-- squads:end -->` block *below* the existing
  hand-written operating model (leaving contradictory instructions co-resident until I reconciled by hand).
- **Overwrote** pointers whose slug happened to match (`architect.md`, `qa.md`, …) but **left orphaned**
  the non-matching home-made ones (`lead.md`, `project-manager.md`, `ux-ui-dev.md`, `.index.md`),
  which I had to delete manually.

`adopt` is documented as "non-destructive," but the interaction with a **pre-existing non-squads**
CLAUDE.md/`.claude` isn't covered.

**Suggested fix:** a documented "adopting into a project that already has CLAUDE.md/.claude" runbook,
and ideally an `init`/`adopt` warning that lists pre-existing agent pointers it did **not** generate
(candidate orphans).

### 4.3 Closed items disappear from default views — including `Accepted` decisions
**Severity: low–medium (surprising, not wrong).**

After migrating a mostly-completed history, `sq tree` and `sq list` look **nearly empty**: features
are `Done`, ADRs are `Accepted`, bugs `Verified` — all hidden unless `--all`. For features/bugs
that's reasonable. For **decisions it's surprising**: an `Accepted` ADR is *live reference*, not
"finished work", yet the entire decision log is hidden by default.

**Suggested fix:** treat `Accepted` as non-hiding for decisions (they're the standing record), or
add a hint in empty `sq list`/`sq tree` output ("N closed items hidden — use `--all`").

### 4.4 `add-finding` / `add-story` / `add-subtask` leave an unwritten-body stub that `sq check` warns on
**Severity: low.**

Creating a sub-entity with only a title (`add-finding "…"`) leaves a placeholder body, and
`sq check` then warns `F6 body is unwritten (still the placeholder stub)`. So the "quick" creation
path produces a lint warning until you *also* set a body. For a review with N findings that's N
extra body-set calls just to get a clean check.

**Suggested fix:** either let a non-empty title satisfy the check, or make `add-finding` accept the
body as the primary positional so the one-shot form is clean by default.

### 4.5 Sub-entity title length advisory fires easily on migrated data
**Severity: low.**

Using each source subtask's one-line description as the subtask **title** tripped the >120-char
advisory 33 times. Reasonable guidance, but on import the "description" *is* the natural title.
Minor; I truncated titles and kept full text in the body.

### 4.6 Per-invocation overhead
**Severity: low (subsumed by 2.2).**

Every `sq` call is a fresh process (Python import + index load). Fine interactively; painful at
460 calls. A batch/import mode (2.2) or a persistent `sq` session/daemon would remove it.

---

## 5. What was genuinely good (keep it)

- **`--at` is the right primitive** for history — global, ISO-8601, applied per invocation, survives
  `repair`/`check`. Made a faithful timeline possible at all.
- **`--json` on `create`/`add-*`/`list`/`findings`** returns clean structured output incl. the new
  `id`/`local_id` — reliable ID capture without scraping human text. This is what made scripting sane.
- **The data model fit a real, messy corpus** with zero contortion: epic→feature→task, story &
  subtask sub-entities with `--story` mapping, the 8 ref kinds (esp. `implements`/`addresses`/`fixes`),
  dated attributed comments, review findings with their own lifecycle.
- **`sq check` is trustworthy** — it caught the unwritten-finding-body stubs and the long titles, and
  went green once fixed. Exit codes are clean for CI.
- **Sequential story/subtask local IDs** (`US1…`, `ST1…`) matched the old `US-00X-001…` ordering, so
  `--story US2` mapping "just worked".
- **`sq workflow` / `sq docs` offline** are excellent for ramping — I learned the whole model from
  them before touching anything (the drift in §3 aside).

---

## 6. Priority order if you only fix a few things

1. **Alias / preferred-ID on import (§2.1)** — unblocks faithful migrations without reference rot.
2. **Bulk event import (§2.2)** — turns migrations from "write a driver" into "emit a file".
3. **Fix docs drift §3.1–3.3** — cheap, high trust-per-fix.
4. **`init`/`adopt` orphan-warning + "already has CLAUDE.md/.claude" runbook (§4.2)**.
5. **Decisions visible by default (§4.3)** and **clean one-shot `add-finding` (§4.4)**.

---

## 7. Additional findings from the review-rework pass

A second pass reworked the 7 migrated reviews (move each finding's detail into its finding *body*,
slim the review body to a scope overview, and migrate the `Issue #N` resolution threads to dated
review comments). It surfaced three more gaps.

### 7.1 Sub-entities cannot be deleted
**Severity: medium.**

`finding` / `story` / `subtask` support `show` / `update` / `body` / `comment` — but there is **no
`remove`**. A mis-created or spurious sub-entity is permanent; the only recourse is to re-title it or
repurpose its body. Hit concretely: the first migration pass created a spurious finding on the
FEAT-006 review (an over-broad parse), and there was no way to delete it — only overwrite it with a
"consolidated into other findings" note. Parent items *do* have `remove`; sub-entities should too
(guarded/`--yes`), so migrations and mistakes are correctable.

### 7.2 `add-finding` / `add-story` / `add-subtask` are two-step for full metadata
**Severity: low.**

These accept a title + body (`--file`/`-m`) + `--assignee`/`--story`, but **not** `--severity` or
`--status` inline. Setting a finding's severity or a non-initial status requires a follow-up
`update … --status … --force`. Combined with §4.4 (the created sub-entity's body is an unwritten
stub that `sq check` warns on until set), the "quick" one-shot form essentially always needs a
second (often third) call to be clean. Letting `add-*` take `--severity`/`--status` (and treating a
provided body as non-stub) would make the common path one call.

### 7.3 No read-back verb for an item's discussion/comments
**Severity: low (discoverability).**

`sq <type> <n> comment` appends a comment, but there is no `comments` / `discussion` subcommand to
list them back. To verify the 112 migrated review comments I had to `show --json` and read the
`discussion[]` array (or eyeball `show --comments`). A dedicated `sq <type> <n> comments` (with
`--json`) would round out the CRUD surface and aid scripting/verification.

---

*Reproduction environment: Linux (WSL2), `sq` 0.11.1 installed at `~/.local/bin/sq`. The full
migration driver (Python, ~6 phase scripts using `sq --json`) can be shared if useful.*
