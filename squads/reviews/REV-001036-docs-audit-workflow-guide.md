---
id: REV-1036
sequence_id: 1036
type: review
title: 'Docs audit: workflow guide'
status: Approved
author: reviewer
description: 'Claim-by-claim audit of docs/workflow.md against the release/0.16 dev
  build: lifecycles, category rules, quoted output, override refusals, gaps.'
subentities:
- local_id: F1
  title: Review lifecycle omits the ChangesRequested -> Approved edge (lines 203,
    223)
  status: Fixed
  severity: medium
- local_id: F2
  title: Work-item diagram shows Blocked -> InReview, which the machine refuses (line
    195)
  status: Fixed
  severity: medium
- local_id: F3
  title: 'parents is not ignored on a records type: declaring it refuses the spec
    at load (lines 969-970)'
  status: Fixed
  severity: high
- local_id: F4
  title: Records do appear in sq inbox, and retired records are hidden from sq list
    (lines 942-950, 971)
  status: Fixed
  severity: medium
- local_id: F5
  title: 'Quoted sq workflow lint error table is stale: message and fix hint changed
    (lines 1332-1341)'
  status: Fixed
  severity: medium
- local_id: F6
  title: Statuses section says role is mandatory and that it defaults to pending (lines
    838-839, 877-878)
  status: Fixed
  severity: low
- local_id: F7
  title: Example IDs INC-1 / PM-1 ignore the squad-wide counter; a fresh squad starts
    at 21 (lines 969, 1390)
  status: Fixed
  severity: low
- local_id: F8
  title: 'Dropping implements or targets is a hard stop even with no edges: bundled
    rule/view name them (1298-1304)'
  status: Fixed
  severity: medium
- local_id: F9
  title: '''The result'' block shows the custom template''s output, not what sq milestone
    show renders (443-452)'
  status: Fixed
  severity: low
- local_id: F10
  title: A self view's --json carries a spec {schema_version, override, digest} block
    beyond show --json (318-321)
  status: Fixed
  severity: low
- local_id: F11
  title: Team-workflow section never introduces sq blocked, sq mine or sq workload
    (lines 10-73)
  status: Fixed
  severity: low
- local_id: F12
  title: The --author option also accepts a registered operator slug, not only a role
    (line 55)
  status: Fixed
  severity: medium
created_at: '2026-10-16T08:50:45Z'
updated_at: '2026-10-16T11:26:19Z'
---
<!-- sq:body -->
## Scope

`docs/workflow.md` (1,452 lines) as it stands on `release/0.16`, audited claim by claim against the dev build: commands and flags against `sq --help` and each group's help, quoted messages against driven output in scratch squads, statuses/transitions/types/kinds/ref kinds/views/collections against the bundled `src/squads/_specs/workflow.toml` and the `sq workflow … --json` catalogs, `sq check` and `sq workflow lint` messages against their source, and every cross-document link and anchor.

## What held

Type aliases, the catalog join table and row shapes, the settled-status list and role table, the sub-entity verbs and flags, the view verbs and their messages (`view add`/`view disable`, the marker refusal, the retired-key load errors, position and name refusals), the milestone roll-up and `targets` membership, the contract validator (warn text, `@error` exit 3, inert while no target exists, multi-target wording, refusal without a `ref_rules` entry), the reflog line shape and op list, rename-type/rename-status and their one-line-per-item logging, the override refusals for roster keys, prefix changes and stranded items, and every link target.

## Method note

Each finding names the line, what the text says, what is true, whether it was driven or read, and a correction.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1036 add-finding "…" --severity medium`; track with `sq review 1036 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Review lifecycle omits the ChangesRequested -> Approved edge (lines 203, 223)

<!-- sq:finding:F1:body -->
**Where:** `docs/workflow.md:203` (diagram) and `docs/workflow.md:223` (table row `review`).

**Doc says:** `review  Requested ─▶ InReview ─▶ Approved  (InReview ⇄ ChangesRequested ; any ─▶ Rejected)` and `ChangesRequested→{InReview, Rejected}`.

**True:** the bundled `lifecycles.review.transitions` has `ChangesRequested = ["InReview", "Approved", "Rejected"]`. A review can go straight from ChangesRequested to Approved.

**Verified:** read `src/squads/_specs/workflow.toml`; driven in a scratch squad: `sq review 23 status ChangesRequested` then `sq review 23 status Approved` → `REV-23 → Approved`, exit 0. `sq workflow lifecycles --json` lists the `{from: ChangesRequested, to: Approved}` edge.

**Fix:** table row → `ChangesRequested→{InReview, Approved, Rejected}`; diagram → `(InReview ⇄ ChangesRequested ─▶ Approved ; any ─▶ Rejected)` or equivalent.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T09:02:46Z] Theo Writer:
  - Fixed in docs/workflow.md § Status lifecycles: review diagram line and table row now carry ChangesRequested→Approved (driven).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Work-item diagram shows Blocked -> InReview, which the machine refuses (line 195)

<!-- sq:finding:F2:body -->
**Where:** `docs/workflow.md:195` (work-item diagram): `Blocked  ⇄  Ready / InProgress / InReview`.

**Doc says:** Blocked moves both ways with InReview.

**True:** `Blocked = ["Ready", "InProgress", "Cancelled"]` in the bundled `work` lifecycle; InReview→Blocked exists, Blocked→InReview does not. The table at line 218 has it right, so the two disagree within the same section.

**Verified:** read `workflow.toml`; driven: `sq task 24 status Blocked` then `sq task 24 status InReview` → `error: task cannot move Blocked → InReview (use --force to override)`, exit 1.

**Fix:** redraw as `Ready / InProgress / InReview ─▶ Blocked ─▶ Ready / InProgress` (or drop InReview from the ⇄ group).
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T09:02:49Z] Theo Writer:
  - Fixed in docs/workflow.md § Status lifecycles: work diagram redrawn as Ready/InProgress/InReview → Blocked → Ready/InProgress, plus Cancelled → Draft (driven).
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — parents is not ignored on a records type: declaring it refuses the spec at load (lines 969-970)

<!-- sq:finding:F3:body -->
**Where:** `docs/workflow.md:969-970`: "Records never have parents, so the `parents` field is ignored for records-category types."

**Doc says:** declaring `parents` on a `category = "records"` type is harmless.

**True:** it is refused at spec load. The records category bundle turns on `no_parent`, and the loader rejects a records type that still declares `parents`, so every `sq` command hard-stops until the key is removed.

**Verified:** driven with `[items.postmortem] category = "records" / lifecycle = "guide" / parents = ["epic"]`: `sq workflow lint` → `item 'postmortem': category 'records' forbids a parent (its validator set includes 'no_parent'), but the type still declares parents=['epic'] — that constraint can never apply. Drop the parent field(s), or leave 'postmortem' in a category that allows a parent`; `sq list` → "workflow override could not be loaded", exit 1. Read: `_workflow/_models.py:495` (`"records": ("no_parent", "supersedes_incoming")`).

**Fix:** "Records never have parents: a records type must not declare `parents` — the spec is refused at load if it does." Rated high because a reader following the sentence as written locks every command out of the squad until they undo it.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T09:02:52Z] Theo Writer:
  - Fixed in docs/workflow.md § Records-category item types: a records type must not declare parents; the spec is refused at load (driven).
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Records do appear in sq inbox, and retired records are hidden from sq list (lines 942-950, 971)

<!-- sq:finding:F4:body -->
**Where:** `docs/workflow.md:942-950` and `:971`.

**Doc says:** work items "appear in `sq inbox`" while a records type "never appears in `sq inbox`"; records "are shown at all times".

**True:** `sq inbox <role>` lists open (non-settled) items whose discussion @mentions the role, whatever their category. A Proposed decision or a custom records item with an `@qa` comment is listed. And `sq list` hides a retired records item (Superseded/Deprecated/Cancelled) unless `--all`, so "shown at all times" is wrong too.

**Verified:** driven: `sq decision 26 comment --as architect -m "@qa ping"` then `sq inbox qa` → `ADR-26 Use JWT (Proposed) - @qa ping`; same with a custom `postmortem` records item (`PM-22 PM one (Draft)` listed). `sq list --help` states the category-aware hiding rule for records. Settled-item exclusion confirmed separately (an Approved review with an @qa comment is not listed).

**Fix:** drop the inbox claim from the category description (inbox keys on open status + mention, not category), and replace "shown at all times" with the actual rule: visible while settled-but-shown (Accepted, Published), hidden once retired. Line 944's "tracked as effort" also contradicts line 584 ("squads has no estimation vocabulary").
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T09:02:56Z] Theo Writer:
  - Fixed in docs/workflow.md § Records-category item types: inbox claim and "tracked as effort" dropped from the category text; list hiding rule stated (settled-but-shown vs retired, --all) (driven).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Quoted sq workflow lint error table is stale: message and fix hint changed (lines 1332-1341)

<!-- sq:finding:F5:body -->
**Where:** `docs/workflow.md:1332-1341`, the quoted `sq workflow lint` error table.

**Doc says:** error column `Invalid workflow spec: lifecycle 'incident' not found (referenced in items.incident)`, fix hint `Fix the TOML at .overrides/workflow.toml and re-run sq workflow lint.`

**True (today's output):** error `item 'incident': lifecycle 'incident' not declared in lifecycles`, fix hint `Fix the referenced key in .overrides/workflow.toml, or add it back (directly or via selected), and re-run sq workflow lint.`, followed by `1 error(s) — fix the errors above then re-run sq workflow lint.`

**Verified:** driven with an override declaring `[items.incident] lifecycle = "incident"` and no `[lifecycles.incident]`.

**Fix:** replace the quoted table with the current output (or paraphrase it rather than quoting, since this surface is not in the stability contract).
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T09:02:59Z] Theo Writer:
  - Fixed in docs/workflow.md § Authoring and validation: lint error table replaced with current output, including the count line (driven).
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Statuses section says role is mandatory and that it defaults to pending (lines 838-839, 877-878)

<!-- sq:finding:F6:body -->
**Where:** `docs/workflow.md:838-839` ("Each status definition must specify: `role`") vs `:877-878` ("Every status must declare a role; if omitted, it defaults to `pending`").

**Doc says:** both that `role` is mandatory and that it has a default — the second sentence contradicts itself.

**True:** `role` is optional and defaults to `pending`.

**Verified:** driven: an override with `[statuses.Triage]` carrying no `role` loads (`sq workflow lint` → `workflow spec OK — no errors or warnings.`), and `sq workflow statuses --json` shows `{"status": "Triage", "role": "pending", "badge": null}`.

**Fix:** state once, in the Statuses subsection: "`role` — optional; defaults to `pending`. Declare it explicitly for any status that should settle, since `pending` never does."
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T09:03:02Z] Theo Writer:
  - Fixed in docs/workflow.md § Statuses and § Status roles: role stated once as optional, defaulting to pending (driven).
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Example IDs INC-1 / PM-1 ignore the squad-wide counter; a fresh squad starts at 21 (lines 969, 1390)

<!-- sq:finding:F7:body -->
**Where:** `docs/workflow.md:1390` (`sq create incident "Auth outage" --author manager   # → INC-1`) and `:969` ("items like `PM-1`, `PM-2`").

**Doc says:** a new type's first item is number 1.

**True:** the counter is global across all types and the roster occupies it first: in a fresh `sq init` the eight roles and twelve skills take 1-20, so the first custom item is `INC-21`. Elsewhere the guide already uses `<n>` placeholders.

**Verified:** driven in a fresh scratch squad: `sq create incident "Auth outage" --author manager` → `created INC-21`.

**Fix:** write `# → INC-<n>` / "items like `PM-<n>`", or add "the number comes from the squad-wide counter, so it is not 1".
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T09:03:05Z] Theo Writer:
  - Fixed in docs/workflow.md: PM-<n> in § Records-category item types and INC-<n> in § Worked example, both naming the squad-wide counter (driven: INC-21, PM-21).
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Dropping implements or targets is a hard stop even with no edges: bundled rule/view name them (1298-1304)

<!-- sq:finding:F8:body -->
**Where:** `docs/workflow.md:1298-1304` ("A ref kind dropped or renamed while live refs spell it — bounded, not a hard stop … A kind no edge uses may be dropped or renamed freely") and `:1014` ("drop one it doesn't use").

**Doc says:** any unused kind can be dropped.

**True:** the bounded behaviour holds for a kind nothing else in the spec names (verified with `duplicates`: lint refuses, `list`/`check`/`refs`/`graph`/`ref rm` keep running, `ref add --kind duplicates` is refused). But two bundled kinds are named by other bundled declarations and dropping them is a hard stop even with zero edges: `implements` (named by `items.feature.ref_rules`) and `targets` (named by `views.milestone_rollup.source`).

**Verified:** driven: `[selected] ref_kinds` without `implements` → `items.feature ref_rule[0]: kind 'implements' is not one of the declared ref kinds […] — every ref surface would reject it, so a rule for it can never apply`, every command exits 1; without `targets` → `view 'milestone_rollup': source names ref kind 'targets', not declared in [ref_kinds] — 'targets' was dropped from a [selected] list`.

**Fix:** qualify: "A kind no edge uses may be dropped or renamed freely, unless a bundled `ref_rules` entry or a view `source` names it (`implements`, `targets`) — drop or shadow that declaration in the same override."
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-16T09:03:08Z] Theo Writer:
  - Fixed in docs/workflow.md § What the override may and may not change (implements/targets exception) and § Ref kinds (pointer to it) (driven).
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — 'The result' block shows the custom template's output, not what sq milestone show renders (443-452)

<!-- sq:finding:F9:body -->
**Where:** `docs/workflow.md:443-452` ("The result": `sq milestone <n> show` renders … `### feature` / `- **FEAT-<n>** ⚪ Draft — Ship the widget` / `Outstanding: 1`).

**Doc says / implies:** that is what `sq milestone <n> show` renders.

**True:** that is the output of the minimal replacement template written in step 2, not the bundled view. The bundled `milestone_rollup` renders `## Delivered (0)` / `## Outstanding (1)` / `- **TASK-31** (task) InProgress — Validate token — op-alice` / `## Settled without delivering (0)`. A reader skimming to "The result" takes the three-line block for the default rendering.

**Verified:** driven: `sq milestone 24 show` on a milestone with one `targets` member.

**Fix:** say "with the minimal template above in place, `sq milestone <n> show` renders:" and, optionally, show the bundled three-bucket rendering once under § Milestones (line 568-577 describes it in prose only).
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-16T09:03:11Z] Theo Writer:
  - Fixed in docs/workflow.md: § The result now says it shows the step-2 minimal template; § Milestones shows the bundled three-bucket rendering (driven).
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — A self view's --json carries a spec {schema_version, override, digest} block beyond show --json (318-321)

<!-- sq:finding:F10:body -->
**Where:** `docs/workflow.md:318-321`: "`role`/`self` match their own `show --json`".

**Doc says:** a `self` view's `--json` is the item's `show --json`.

**True:** it is `show --json` plus a `spec` block `{schema_version, override, digest}` (the 0.16 addition recorded in CHANGELOG under Added). A client reading the guide does not learn the block exists or that `digest` is the equality-only change detector.

**Verified:** driven: `sq workflow view greeting_skill SKILL-9 --json` keys = `show --json` keys + `spec`; `sq skill greeting show --json` has no `spec`. `role_definition` does match `sq role <slug> show --json` key for key.

**Fix:** "… `self` matches its own `show --json` plus a `spec` block (`schema_version`, `override`, `digest`) — see stability.md".
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-16T09:03:14Z] Theo Writer:
  - Fixed in docs/workflow.md § Derived views: self matches sq show <id> --json plus the spec key, with a pointer to stability.md (driven; note the host is sq show <id>, not sq skill <slug> show).
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Team-workflow section never introduces sq blocked, sq mine or sq workload (lines 10-73)

<!-- sq:finding:F11:body -->
**Where:** `docs/workflow.md` § Team workflow (lines 10-73) and § Ref kinds (1010-1061).

**Gap:** the guide calls itself "the full reference" for the team workflow, yet the dependency semantic is only reached through the ref-kind table: nothing explains that `blocks`/`depends-on` make `sq blocked` list stuck work, and the queue commands a role actually reads — `sq mine <role>` (items assigned to you, directly or via a sub-entity) and `sq workload` — are never mentioned (`sq inbox` is). `sq blocked` appears once, in a clause about the `dependency` role at line 1045. README.md and recipes.md cover them, workflow.md does not.

**Verified:** read; `grep -n 'sq mine\|sq workload' docs/workflow.md` → no hits; `sq --help` lists `blocked`, `mine`, `workload`.

**Fix:** add two lines to "Commands at a glance": `sq task 3 ref add TASK-9 --kind depends-on   # sq blocked lists it while TASK-9 is open` and `sq mine qa` next to `sq inbox qa`, with one sentence that the two queues answer different questions.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-16T09:03:17Z] Theo Writer:
  - Fixed in docs/workflow.md § Commands at a glance: depends-on example, sq mine / sq blocked / sq workload lines, and a sentence on inbox vs mine.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — The --author option also accepts a registered operator slug, not only a role (line 55)

<!-- sq:finding:F12:body -->
**Where:** `docs/workflow.md:55`: "`--author` is required on every create, and must name a registered role".

**Doc says:** only a role slug is accepted.

**True:** a registered operator slug is accepted too (`--author op-alice`), which is also what the surrounding "humans are participants too" block (lines 69-72) implies for `--as` and `--assignee` but never says for `--author`.

**Verified:** driven: `sq operator add "Alice Tester"` → `op-alice`; `sq create task "Op author" --author op-alice` → `created TASK-29`, exit 0. (`sq create <type> --help` carries the same understatement: "Authoring agent (role slug); must be registered".)

**Fix:** "must name a registered role or operator (`op-<slug>`)", and add `sq create … --author op-alice` to the operators block.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-16T09:03:20Z] Theo Writer:
  - Fixed in docs/workflow.md § Commands at a glance: --author accepts a role or operator, plus an op-alice create example (driven). The create --help understatement is code and is not touched.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T08:51:56Z] Paul Reviewer:
  - Audit of docs/workflow.md against the release/0.16 dev build (scratch squads under the session scratchpad, every quoted message and transition driven or read in source). 12 findings: 1 high, 7 medium, 4 low. Recommended verdict: ChangesRequested once a tech-writer pass lands the corrections; @tech-writer for the doc edits, @manager to route.
- [2026-10-16T08:53:05Z] Paul Reviewer:
  - Correction to the count above: 12 findings = 1 high (F3), 6 medium (F1, F2, F4, F5, F8, F12), 5 low (F6, F7, F9, F10, F11).
- [2026-10-16T11:26:18Z] Catherine Manager:
  - Approved: every finding Fixed (re-run by the writer on the dev build) or closed with a home; cross-doc seams checked in REV-1047.
<!-- sq:discussion:end -->
