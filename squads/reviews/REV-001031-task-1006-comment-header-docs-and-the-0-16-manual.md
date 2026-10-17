---
id: REV-1031
sequence_id: 1031
type: review
title: 'TASK-1006: comment-header docs and the 0.16 MANUAL'
status: Approved
author: reviewer
assignee: reviewer
refs:
- TASK-1006:addresses
- FEAT-980:addresses
description: Claim-by-claim check of the slug-header docs, CHANGELOG and MANUAL against
  the dev build
subentities:
- local_id: F1
  title: Reserved-slug rule worded wider than the build enforces
  status: Fixed
  severity: medium
- local_id: F2
  title: CHANGELOG keeps the corrected stamped-release remedy
  status: Fixed
  severity: medium
- local_id: F3
  title: MANUAL example omits a per-name line
  status: Fixed
  severity: low
- local_id: F4
  title: Slug origin stated as derived from the name
  status: Fixed
  severity: low
- local_id: F5
  title: Tier 3 bullet uses release-delta wording
  status: Fixed
  severity: low
- local_id: F6
  title: CHANGELOG omits the VS Code preview slug
  status: Fixed
  severity: low
- local_id: F7
  title: Tutorial --as developer claim is false
  status: Fixed
  severity: low
- local_id: F8
  title: Remedy text depends on pending decisions
  status: WontFix
  severity: info
created_at: '2026-10-16T08:33:42Z'
updated_at: '2026-10-16T08:39:06Z'
---
<!-- sq:body -->
Review of the adopter docs for slug-bearing comment headers: `docs/stability.md` (Tier 1 "Comment headers", "A roster slug never changes", Tier 3 "Discussion entries"), `docs/internals.md`, `docs/migration.md` § "Upgrading to 0.16: the schema step", the 0.16.0 CHANGELOG entries, and the reworded `_HEADER_MANUAL` / `_MANUAL_PREAMBLE` in `src/squads/_migrations/_v0_15_to_v0_16.py` (uncommitted, on top of 45ea351e and 8c51ae24).

**Method.** Every claim below was driven with the dev build (`uv run --all-extras sq -C <scratch>`) on squads written by the released 0.15.0 tool, in scratch folders under the session scratchpad. Nothing was run against this repository's squad except board operations with the released tool.

**Claims driven and holding**

- Happy-path run report, quoted verbatim in migration.md: matches. Only header lines change, a header-shaped line in an item body is left alone, no frontmatter changes, `updated_at` unchanged.
- The refused-run block in migration.md (purged `qa`): byte-identical to the real output, exit 1, item files untouched.
- The below-0.15 refusal line (a v0_11 corpus copy with one unresolvable header): matches. Following the page (0.15.0 `sq migrate up`, roster change, dev `sq migrate up`) completes.
- Each remedy, performed with 0.15.0, then the dev migration completes: `sq role activate qa --name "Mara Tester"`, `sq dev add --tech python --name "Elias Python"` (slug comes back as `python-dev`), `sq operator add "Zoë Müller" --slug op-zo`.
- Duplicate-name remedy: in today's frontmatter (0.15.0 and the dev build) the operator's name is `full_name:` under `extra:`, not top-level, and the runner reads `extra.full_name`, so the page and the MANUAL are correct. 0.15.0 `sq check` reports the edit as extra drift; the migration then completes; after it, editing back and `sq repair` leaves `sq check` clean.
- Bad-timestamp and malformed-marker failure texts: match.
- The schema gate: the dev build refuses `role list`, `sync`, `repair` on an unmigrated squad and runs `migrate help`.
- Reserved role slugs refused through `dev add --tech op`, `role activate squads` (from `override scaffold --new squads`) and an import `create`: messages match.
- Importer: `Bad Actor` and `squads` refused with the quoted text, `ghost` and `operator` import, unknown `unset_fields` key refused; an import `update` title on a role keeps the slug and file name.
- The override slug refusal quoted in stability.md: matches.
- The `\r` fix: 0.15.0 reads a `\r`-carried line back as a separate comment under another author; the dev build keeps it (and U+2028) inside the comment.
- Search attribution: 0.15.0 says "comment 5 (Done, x)", the dev build "comment 4 (Robert Architect, …)".
- Tier 3: `author_slug` in `comments --json`, item and sub-entity `show --json`; inbox rows carry no author; search location keeps the display name.
- Human renders show `Name (slug)`, and a retype entry shows `squads` once. A rename keeps old headers' name snapshot; a purged slug taken again reads old headers under the new holder with the old name.
- The operator-without-`op-` report line.

**Read, not driven:** the TUI discussion tab; the name line-break collapse in `format_comment`.

**MANUAL vs migration.md:** they agree on every remedy, the release sentence and the failure kinds. F3 is the one MANUAL-only inaccuracy.

**ADR-979 A1-A6:** nothing from the pending amendment is stated as a rule. F1 is the opposite problem: the role-only rule is worded wider than the build enforces. F8 records what to revisit when the amendment and the ADR-1007 part land.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1031 add-finding "…" --severity medium`; track with `sq review 1031 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Reserved-slug rule worded wider than the build enforces

<!-- sq:finding:F1:body -->
**Where.** `docs/stability.md` Tier 1 "Comment headers", the reserved-slugs bullet; the CHANGELOG Added entry "No role can take the slugs…".

**What the docs say.** Tier 1 (the durable file format) says the two slugs "are reserved for authors that are not roster entries", that "No role may take either slug, nor a slug that starts with `op-`, which is the prefix of operator slugs". A reader takes that as a guarantee about any squad's files: a header with `squads` is a system entry, one with `op-…` is an operator.

**What the build does (driven).**

- A 0.15.0 squad with a role `op-dev` (`sq dev add --tech op --name "Opal Dev"`, then a comment as `op-dev`) migrates with exit 0. The run reports nothing about the role. The header becomes `` `op-dev` Opal Dev ``, `sq role list` still shows `op-dev` live, and `sq check` is clean. The same applies to a role a 0.15.0 project role file created as `squads` or `operator`.
- On the dev build, `sq operator add "Sys Person" --slug squads` succeeds, and `comment --as squads` then writes `` - [ts] `squads` Sys Person: ``: a roster entry writing headers with the system slug. `--slug zed` also succeeds, so `op-` is not "the prefix of operator slugs".

**Why it matters.** The rule is stated as file-format fact in Tier 1, but the only enforcement is at role creation. An adopter or tool reading slugs by the stated rule (prefix means operator, `squads` means sq) misreads an upgraded squad.

**Fix (docs only, nothing from the pending amendment).** Say what is true today. Creating a role with those slugs is refused. A role created by an earlier release keeps its slug, and the migration neither reports nor refuses it. Operator slugs are not checked, and the migration report lists an operator without `op-`. Drop "reserved for authors that are not roster entries" and "the prefix of operator slugs" as guarantees, or qualify them. Apply the same qualification to the CHANGELOG entry. If the engine should report an existing reserved-slug role the way it reports a non-`op-` operator, that goes to @python-dev, not into prose.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T08:38:07Z] Theo Writer:
  - Fixed in docs/stability.md Tier 1 and the CHANGELOG Added entry: the reserved slugs and op- are stated as a role-creation refusal only; a role an earlier release created keeps its slug and the migration neither reports nor refuses it; operator slugs are not checked (driven: 0.15.0 op-dev role migrates clean, dev operator add --slug squads and --slug zed succeed). Nothing from the pending amendment.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — CHANGELOG keeps the corrected stamped-release remedy

<!-- sq:finding:F2:body -->
**Where.** CHANGELOG [0.16.0], Changed, the BREAKING comment-header entry: "it writes nothing, leaves the schema as it was … The fix is made with the release the squad is stamped for".

**What the build does (driven).** A copy of the v0_11 corpus with one unresolvable header: the dev `sq migrate up` exits 1, leaves the stamp at `0.11`, and the files are now in the v0.15 shape. Item files, `CLAUDE.md` and `.claude/` were rewritten by the earlier steps. The refusal itself names "a squads release that reads schema v0.15 (v0.15.0 is one)". 0.15.0 is not the release the squad is stamped for. Following the docs page instead (0.15.0 `sq migrate up`, roster fix, dev `sq migrate up`) completes.

**Why it matters.** This is the sentence the MANUAL review corrected on TASK-1004. migration.md and the MANUAL now say "a release that reads the squad's schema; the refusal names one" and handle the below-0.15 case. The CHANGELOG kept the old wording, so the three sources disagree on the one remedy instruction, and the CHANGELOG version is wrong for exactly the case the others document. "Writes nothing" also holds for the 0.16 step but not for the run on such a squad.

**Fix.** Reuse migration.md's sentence: "the fix is made with a squads release that reads the squad's schema (the refusal names one)", with "this step writes nothing" in place of "it writes nothing", or point to the migration page for the below-0.15 case.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T08:38:09Z] Theo Writer:
  - Fixed: the CHANGELOG entry now says the step writes nothing and the fix uses a squads release that reads the squad schema (the refusal names one), with 0.15.0 migrate up first below 0.15, matching migration.md and the MANUAL.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — MANUAL example omits a per-name line

<!-- sq:finding:F3:body -->
**Where.** `_HEADER_MANUAL` in `src/squads/_migrations/_v0_15_to_v0_16.py`, the example report printed by `sq migrate chlog v0.15.0..v0.16.0`.

**What.** The example lists three failures ('Hugo Ops' no entry, 'Sam Lee' two entries, a bad timestamp), then `3 problem(s) found.`, then only `'Hugo Ops': 1 header(s) in 1 file(s)`. The real report (driven, a run with no-entry, two-entry and bad-timestamp failures) prints one per-name line for every failing name, sorted, and none for a timestamp failure. That example would print a `'Sam Lee': …` line as well.

**Fix.** Add `  'Sam Lee': 1 header(s) in 1 file(s)` after the 'Hugo Ops' line. @python-dev owns the string.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T08:36:18Z] Elias Python:
  - Fixed: the MANUAL example now prints the 'Sam Lee' per-name line after the 'Hugo Ops' one, as the real report does.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Slug origin stated as derived from the name

<!-- sq:finding:F4:body -->
**Where.** `docs/stability.md` "A roster slug never changes", first sentence: the slug is "derived from its name, or given with `sq operator add --slug`".

**What (driven).** That is true only for an operator, where the slug is `op-` plus the first name. A role's slug is its catalog key or project role file name (`sq role activate qa --name "Mara Tester"` gives `qa`, whatever the name). A developer role's slug comes from `--tech` (`sq dev add --tech python --name "Elias Python"` gives `python-dev`). A skill's comes from its catalog entry.

**Fix.** "fixed when the entry is created: a role's from its catalog entry or project role file, a developer role's from `--tech`, an operator's from its first name or `--slug`".
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T08:38:11Z] Theo Writer:
  - Fixed: slug origin per type in stability.md (role: catalog key or project role file whatever --name; developer: --tech; skill: catalog entry or sq skill add name; operator: op- plus first name or --slug). Driven: activate qa --name, dev add --tech python, skill add.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Tier 3 bullet uses release-delta wording

<!-- sq:finding:F5:body -->
**Where.** `docs/stability.md` Tier 3, the new "Discussion entries" bullet: "`search --json` and `inbox --json` are unchanged".

**What.** stability.md is the durable contract, not a release note. "Unchanged" only means something to a reader who knows the previous release, so it fails the stranger test. The rest of the sentence already states the durable fact: a search hit names the author by display name in `location` and `snippet`, and an inbox row names no author (both driven).

**Fix.** Drop "are unchanged:" and keep the factual clause, e.g. "`search --json` and `inbox --json` carry no `author_slug`: a search hit names…". The CHANGELOG is the right place for "unchanged", and it already says it.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T08:38:13Z] Theo Writer:
  - Fixed: Tier 3 bullet now says search --json and inbox --json carry no author_slug, then the factual clause; no release comparison.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — CHANGELOG omits the VS Code preview slug

<!-- sq:finding:F6:body -->
**Where.** CHANGELOG [0.16.0], the BREAKING comment-header entry, the list of human views that "now show the author as `Name (slug)`".

**What.** The list names `comments`, `show --comments`, `show --raw` and the TUI. The VS Code extension's item preview also changed (committed in 8c51ae24, read). Each comment shows the slug after the author, in the editor font, when `author_slug` differs from `author`. The CHANGELOG has covered the extension's preview in earlier releases, so an adopter using it gets no entry for a visible change.

**Fix.** Add the extension's preview to the list (or one sentence for it), with its own rule: the slug is shown next to the name, and left out when the two are equal.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T08:38:15Z] Theo Writer:
  - Fixed: the BREAKING entry adds the VS Code preview: slug after the name, left out when equal or when sq gives no author_slug (read from previewDocument.ts, not driven).
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Tutorial --as developer claim is false

<!-- sq:finding:F7:body -->
**Where.** `docs/tutorial.md` § 4: "(`--as developer` only resolves to a full name if you've activated a dev role; otherwise use a real slug like `architect`, or `operator`.)" This text predates the change.

**What (driven).** `comment --as developer` is refused by both 0.15.0 and the dev build (`error: unknown slug 'developer'; valid slugs: …`), with or without a dev role (a dev role's slug is `<tech>-dev`). The sentence also states the retired claim class this task's sweep targets: that `--as` "resolves to a full name". It was missed because the sweep pattern matched the internals.md wording, not this one.

**Fix.** Use a real slug in the example (`--as python-dev` after `sq dev add --tech python`, or `--as architect`) and drop the parenthetical, or say that `--as` takes a roster slug and the header records it with the author's name.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T08:38:16Z] Theo Writer:
  - Fixed: only the tutorial section 4 parenthetical: --as takes a roster slug (python-dev after sq dev add --tech python, architect, operator), the header records it with the name, and --as developer is refused as unknown (driven on the dev build). No other tutorial change.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Remedy text depends on pending decisions

<!-- sq:finding:F8:body -->
**Where.** migration.md and `_HEADER_MANUAL`: the duplicate-name remedy (`full_name:` under `extra:`, edit back after the migration), the operator matching rule ("by its full name, or by its slug when it has none") and the line "An operator whose slug does not start with `op-` is listed in the run's report; nothing is refused for it".

**What.** All three are true of the build today (driven; the runner reads `extra.full_name` or the slug, `_read_roster`). Each depends on a decision still moving:

- ADR-1007, accepted, says the 0.16 runner flattens `extra` and folds `full_name` into `title`, "taking its value when the two differ". If that lands as a later part of this same step, the remedy breaks. The temporary name typed "for the run" becomes the operator's permanent title, and the "edit it back" key no longer exists.
- ADR-979 A4 (pending) would turn the non-`op-` operator note into a refusal, and A6 (pending) words the match as title first, then any operator's slug, which differs from the shipped rule.

**Ask.** Nothing to change in TASK-1006 now. Whoever adds the ADR-1007 part to "Upgrading to 0.16: the schema step" (TASK-991's writer), and whoever implements A4/A6 if confirmed, re-checks these three passages. The remedy probably needs to say "edit `title:`" for an operator once flattening is in.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-16T08:39:02Z] Catherine Manager:
  - Home: FEAT-1016 (comment there lists the three passages to re-check).
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T08:34:58Z] Paul Reviewer:
  - ChangesRequested: 2 medium, 5 low, 1 info. F1 Tier 1 states the reserved role slugs and the op- prefix as file-format fact, but an upgraded squad can hold a role op-dev and an operator can take squads (both driven). F2 the CHANGELOG keeps the stamped-release remedy that migration.md and the MANUAL corrected. F3 is MANUAL text for @python-dev; the rest are docs for @tech-writer. F8 is a re-check note for the ADR-1007 part and the pending A4/A6.
  - Twenty-plus claims driven on 0.15.0-written scratch squads with the dev build: every quoted refusal, the run report, all remedy commands, the duplicate-name edit (full_name sits under extra: today, so it is correct), importer and role refusals, the CR fix, search attribution, Tier 3 keys. MANUAL and migration.md agree. @manager
- [2026-10-16T08:39:05Z] Catherine Manager:
  - Approved: F1–F7 Fixed (wording driven by the writer on the dev build), F8 WontFix with home FEAT-1016.
<!-- sq:discussion:end -->
