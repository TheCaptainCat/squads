---
id: TASK-945
sequence_id: 945
type: task
title: 'Extension: consume exit 4 and the omissions report, keep the role'
status: Done
parent: FEAT-690
author: tech-lead
assignee: typescript-dev
refs:
- REV-943:fixes
- TASK-944:depends-on
- ADR-947:implements
subentities:
- local_id: ST1
  title: Show a degraded memory pool as partial, not as a smaller pool
  status: Done
  story: US1
- local_id: ST2
  title: Map exit 4 in the adapter and keep the board rendering
  status: Done
  story: US2
- local_id: ST3
  title: Keep the role in the memory panel title after a successful fetch
  status: Done
  story: US1
- local_id: ST4
  title: Prove the memory entry summary is escaped as the body already is
  status: Done
  story: US1
created_at: '2026-09-14T13:53:51Z'
updated_at: '2026-09-15T12:30:58Z'
---
<!-- sq:body -->
The TypeScript half of the fixes raised by the batch review of this feature's two delivered
halves: the extension's two degraded-read divergences — where it is strictly worse than `sq ui`
at exactly the signal this feature exists to produce — plus the memory panel title and the
bracket-safety coverage gap on the entry summary.

The degraded-read shape is settled by ADR-947 and is not open here: exit code `4` for a
usable-but-short result, one compact JSON line on stderr under `--json` naming what was omitted,
and payload shapes untouched. What does not exist yet is the CLI *implementation*, which lands on
TASK-944 — so the dependency stands and this task goes second.

## F2 — a degraded memory pool is silently under-reported

The identity's entry count is the primary hygiene signal this feature exists to produce, and in
the extension it is silently wrong whenever a pool holds a file `sq` could not read. Nothing on
screen distinguishes that from a genuinely smaller notebook — and a role whose count reads low
is precisely the thing a reader is meant to act on, so an under-reported count manufactures the
exact signal the feature is built to detect. `sq ui` appends a "listing partial" line; the
extension has no partial state on `MemoryFetchResult` at all.

## F3 — one unreadable notice blanks the whole board

`runSqRaw` checks the exit code before it ever looks at stdout and `classifyNonZeroExit` turns
the board listing's non-zero exit into a runtime error, so `renderBoardHtml` takes its failure
branch and every notice that *was* read is discarded. `sq ui` renders the readable notices plus
a partial-listing line. Same data, opposite outcome, on the client that could still show you the
team's notices — and a board that goes blank is a worse failure than one that is short, because
the point of a broadcast notice is that someone reads it before starting work.

Both fixes are the same one row in the adapter's general exit-code mapping. The adapter must gain
no per-command exit-code knowledge: it pins none today, and the reason the contract was settled
CLI-side is so it never has to start.

## F4 — the memory panel title drops the role once the fetch succeeds

`clients/vscode/src/itemPreviewManager.ts::renderMemoryEntry` opens the panel titled
`memoryEntryPanelTitle(roleSlug, entrySlug)` and then, on success, replaces the whole title with
the bare entry slug. The panel is a single reused slot by design, so a reader drilling from one
identity's notebook into another's sees the same tab retitled, with nothing naming whose
notebook is open — and the entries a reader is hunting here are, by construction, ones whose
slugs and summaries look alike across roles.

## F7 (TypeScript half) — the entry summary is unproven

`renderMemoryEntryHtml` is tested for HTML escaping of the entry **body** but not of the
**summary**, which travels the same `renderMarkdownToHtml` path and is equally free-form.

## How to work it

- Work in `clients/vscode`; run its vitest suite, not the Python one.
- Read ADR-947 for the contract and TASK-944's handback for what actually shipped. If the CLI has
  not landed, the title and summary-escaping subtasks are independent and can go first.
- Keep the adapter free of per-command exit-code knowledge. Exit `4` is a row in the frozen table,
  the same standing as `2` and `3`; it is not a fact about `board list`.
- An older `sq` predating exit `4` exits `1` and falls through to today's behaviour. That is the
  intended fallback — do not add a version probe.
- **Falsify every behaviour you add**: break the implementation, watch the new test go red,
  restore it, watch it go green.
- No ticket ids in source or test filenames — name tests by the behaviour they pin.
- Leave `sq check` clean before handing back.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 945 add-subtask "<title>"`; track with `sq task 945 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Show a degraded memory pool as partial, not as a smaller pool

<!-- sq:subtask:ST1:body -->
`getMemoryList` does not inspect stderr on a zero exit — its own doc comment says so — so
`MemoryFetchResult` carries no partial state and `memoryGlanceText` renders a shortened count as
if it were the whole pool. `sq ui` renders "N memory files could not be read — listing partial"
under the same data.

The signal is settled by ADR-947 and is not board- or memory-specific: **exit code `4` means the
payload on stdout is valid and in its documented shape, and entries are missing**, and under
`--json` one compact line on stderr holds `{"omitted":[{"code","source","message"}]}`. The memory
listing's payload is a bare JSON array, unchanged in the degraded case as in the clean one — there
is no new field on it to read, and expecting one is how this subtask goes wrong.

Two consequences for the adapter, and both belong in `classifyNonZeroExit` rather than here:

- `4` is a new row in the general exit-code mapping, beside `2` and `3`. The result is a
  *success carrying omissions*, not a `runtime-error` — see ST2, which lands that row.
- The omissions line is found by the rule ADR-947 states: **the one line of stderr that parses as
  a JSON object is the report.** Stderr has prose co-tenants under `--json`, so do not assume the
  whole stream is JSON and do not take the first or last line blindly.

An older `sq` that predates the code exits `1` and falls through to today's behaviour. That is the
intended fallback and needs no version check.

Done when:

- `MemoryFetchResult` can represent a partial listing, populated from the general adapter outcome
  rather than from memory-specific parsing.
- The glance text says so — a reader tells a degraded pool from a genuinely smaller notebook at a
  glance, without expanding it.
- The entries that *were* read still render; a partial listing is never treated as a failed fetch.
- A fetch that failed outright still reads as an error, distinctly from a partial one.
- Vitest coverage over all three states (whole, partial, failed), falsified per state, with the
  partial case driven from a real exit code and a real stderr line rather than a hand-built result
  object.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Map exit 4 in the adapter and keep the board rendering

<!-- sq:subtask:ST2:body -->
One unreadable notice file hides the entire board in VS Code. `runSqRaw` checks the exit code
before it ever looks at stdout, and `classifyNonZeroExit` (`src/sqAdapter.ts`) turns any non-zero
that is not `2` or `3` into a `runtime-error`, so `renderBoardHtml` takes its failure branch and
discards every notice that was read. `sq ui` shows the readable notices plus a partial-listing
line.

**The fix is one row in the general mapping, not a board special case.** ADR-947 adds exit `4` to
the frozen exit-code table: stdout carries a valid payload in its documented shape and entries are
missing. `classifyNonZeroExit` gains a `4` branch returning a *success with omissions* outcome,
and every caller of the adapter inherits it — the board, the memory listing, and any listing the
CLI adds later. The adapter gains no per-command exit-code knowledge, which is the constraint it
deliberately satisfies today and the whole reason the contract was settled CLI-side.

Where the omissions come from: under `--json`, one compact line on stderr holds
`{"omitted":[{"code","source","message"}]}`. Find it by ADR-947's own consumer rule — **the one
line of stderr that parses as a JSON object is the report** — because stderr has prose co-tenants
under `--json`, notably the `sq sync` version notice. Treat an unrecognised `code` as "part of the
result is missing" rather than branching on its value; the set is open by design. `source` is a
display token and must not be parsed.

Done when:

- `classifyNonZeroExit` maps `4` to a distinct outcome kind that carries the parsed omissions, and
  `runSqRaw`'s callers reach stdout on that path instead of short-circuiting.
- A board listing that could not be read in full renders the notices that *were* read, plus a
  visible statement that the listing is partial.
- A genuine failure — nothing parseable on stdout, or a `1`/`2`/`3` — still renders the failure
  branch with the stderr text; the outcomes stay distinguishable.
- A malformed or absent omissions line on an exit `4` still renders the payload, degrading to "the
  listing is partial" with no detail rather than to an error.
- Vitest coverage for each outcome, falsified, including the stderr line arriving beside a prose
  co-tenant.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Keep the role in the memory panel title after a successful fetch

<!-- sq:subtask:ST3:body -->
`clients/vscode/src/itemPreviewManager.ts::renderMemoryEntry` opens the panel titled
`memoryEntryPanelTitle(roleSlug, entrySlug)` and then, on a successful fetch, overwrites the
title with the bare entry slug. The panel is a single reused slot by design, so after drilling
from one identity's notebook into another's, the tab is retitled and nothing on screen names
whose notebook is open.

Done when:

- The settled successful title carries the role and the entry together, via
  `memoryEntryPanelTitle`.
- The in-flight and failure titles are untouched — that fallback is already the right string.
- `renderMemoryEntryHtml`'s heading names the role as well as the entry slug.
- Vitest coverage pins the post-success title, falsified before it counts.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Prove the memory entry summary is escaped as the body already is

<!-- sq:subtask:ST4:body -->
`renderMemoryEntryHtml` is covered for HTML escaping of the entry **body**, but not of the
**summary** — which travels the same `renderMarkdownToHtml` path and is just as free-form. One
code path, already proven for one input; the assertion is a one-liner and closes the shape.

Done when:

- A summary carrying HTML-significant characters renders escaped, asserted directly rather than
  inferred from the body case.
- Falsified: bypass the escape, watch it go red, restore it.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T08:07:27Z] Olivia Lead:
  - ST1/ST2 rescoped for the accepted ADR-947 rather than the shape TASK-944 was going to invent. Exit 4 is a new row in the adapter's general exit-code mapping (classifyNonZeroExit), the same standing as 2 and 3 — both fixes land there, so the adapter still gains no per-command exit-code knowledge. The omissions detail comes from the one line of stderr that parses as a JSON object; payloads stay bare arrays, so there is no new field on the listing to read. ST2 renamed to say where the edit goes.
  - Added: a malformed or absent omissions line on an exit 4 must still render the payload, degrading to 'partial, no detail' rather than to an error; and an older sq exits 1 and falls through to today's behaviour, so no version probe.
  - implements ADR-947 added; depends-on TASK-944 stands, CLI first. Left Draft. @manager
- [2026-09-15T12:29:46Z] Ada Typescript:
  - All four subtasks Done. clients/vscode only; src/squads and tests/ untouched.
  - F2/ST1: MemoryFetchResult's loaded variant gained an optional omissions field, populated from the general adapter outcome (not memory-specific parsing). memoryGlanceText/memoryTooltipLine append a (partial) marker + omissions summary; memoryChildren still renders the entries that were read. A pool is partial iff omissions !== undefined (present-but-empty means the report itself was malformed/absent, degrading to 'partial, no detail' rather than clean).
  - F3/ST2: classifyNonZeroExit gained one row for exit 4 -> a success outcome carrying data (stdout) + omissions (parsed via the 'one stderr line that parses as a JSON object' rule), instead of falling into runtime-error. runSqJson/runSqJsonObject thread omissions through unchanged. Every caller (getTree/getList/getMemoryList/getBoardList/etc.) inherits this from one place; the adapter still pins no per-command exit-code knowledge. renderBoardHtml renders the readable notices plus a visible 'listing partial' line instead of the old failure branch that discarded them.
  - F4/ST3: extracted resolveMemoryEntryPanelTitle (pure, unit-tested) — success keeps roleSlug: entrySlug via memoryEntryPanelTitle instead of dropping to the bare slug. renderMemoryEntryHtml's heading now also takes roleSlug.
  - F7/ST4: added a summary-escaping assertion mirroring the existing body one; behavior was already correct (renderMarkdownToHtml escapes both), this closes the coverage gap.
  - Robustness: malformed/absent omissions line on exit 4 -> omissions: [] (still partial, no detail, never an error) — verified with (a) well-formed line, (b) malformed ('omitted' not an array, and an array of wrongly-shaped entries), (c) absent line and stderr with only the sq-sync version-notice prose. No version probe added; an older sq exiting 1 falls through to runtime-error unchanged (tested).
  - Shared a summarizeOmissions helper (new src/domain/omissions.ts) between board and memory views so the two never compose divergent wording — mirrors sq ui's 'N ... could not be read — listing partial' phrasing.
  - Falsified all 6 behaviours individually (exit-4 mapping, malformed-report degrade, memory glance/tooltip partial marker, memoryChildren-still-renders-on-partial, renderBoardHtml partial rendering, resolveMemoryEntryPanelTitle, F7 summary escaping): broke each, watched vitest go red, restored, watched it go green.
  - Gates (npm run check = typecheck+lint+format:check) and npm test: all clean, 688/688 passing. TypeScript stayed pinned at ^6.0.3, type-aware lint untouched. sq check clean.
  - Not touching TASK-945's own status per your note — over to you to verify. @manager
<!-- sq:discussion:end -->
