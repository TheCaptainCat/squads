---
id: REV-1032
sequence_id: 1032
type: review
title: 'Docs audit: README, tutorial, FAQ'
status: Approved
author: reviewer
description: Claim-by-claim audit of README.md, docs/README.md, docs/tutorial.md and
  docs/faq.md against the 0.16 dev build
subentities:
- local_id: F1
  title: 'Tutorial: every sq create lacks the required --author, so step 1 fails with
    exit 2'
  status: Fixed
  severity: high
- local_id: F2
  title: 'Tutorial step 4: --as developer is refused as an unknown slug, not downgraded
    as the note claims'
  status: Fixed
  severity: medium
- local_id: F3
  title: Tutorial promises a clean sq check but leaves two unwritten-body warnings
  status: Fixed
  severity: medium
- local_id: F4
  title: 'README omits the contract and milestone types: count, prefixes, lifecycles,
    layout, aliases, create'
  status: Fixed
  severity: medium
- local_id: F5
  title: 'README: sq renumber shown without the required --from option; contradicts
    the FAQ'
  status: Fixed
  severity: medium
- local_id: F6
  title: 'README: claude_code pointers do not @-include the definition; contradicts
    Concepts'
  status: Fixed
  severity: medium
- local_id: F7
  title: 'README: agents_md backend no longer writes a .agents_md/ staging folder'
  status: Fixed
  severity: medium
- local_id: F8
  title: 'README: per-role preloaded skill lists are stale (manager, product owner,
    developer)'
  status: Fixed
  severity: medium
- local_id: F9
  title: 'README layout: .squads.toml does not hold the default role'
  status: Fixed
  severity: low
- local_id: F10
  title: 'README: sq workflow subcommand list omits views and view'
  status: Fixed
  severity: low
- local_id: F11
  title: 'README: sq graph --format omits mermaid-md'
  status: Fixed
  severity: low
- local_id: F12
  title: 'README: generic sq create flag list does not apply to guides'
  status: Fixed
  severity: low
- local_id: F13
  title: 'docs/README: migration.md index entry describes transformers and LLM runbooks
    that are not in the doc'
  status: Fixed
  severity: low
- local_id: F14
  title: 'Tutorial: sample output path and ''IDs spent on roles'' understate what
    init allocates'
  status: Fixed
  severity: low
- local_id: F15
  title: 'Tutorial: bare sq tree lists the 20 roster items before the hierarchy'
  status: Fixed
  severity: low
- local_id: F16
  title: 'FAQ gap: no entry for Missing option --author or unknown slug errors'
  status: Fixed
  severity: low
created_at: '2026-10-16T08:44:34Z'
updated_at: '2026-10-16T11:26:14Z'
---
<!-- sq:body -->
## Scope

Adopter-facing docs audit, one of five shares: README.md, docs/README.md, docs/tutorial.md, docs/faq.md. Every concrete claim (commands, flags, messages, layouts, lifecycles) was checked against the release/0.16 dev build by driving it in a scratch squad (sq init --roles all, then the tutorial end to end) or by reading the source where a claim could not be driven. Each finding states which.

## Method

The tutorial was followed as a newcomer would; every README command-reference line was compared with the live --help output; every quoted error message in the FAQ was reproduced. Findings carry file:line, what the doc says, what is true, how it was verified, and a suggested correction.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1032 add-finding "…" --severity medium`; track with `sq review 1032 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Tutorial: every sq create lacks the required --author, so step 1 fails with exit 2

<!-- sq:finding:F1:body -->
**Where:** docs/tutorial.md:28, 76, 96, 116, 124, 126 (every `sq create` in the walkthrough).

**Doc says:** `sq create epic "Authentication platform"` (and likewise for the feature, task, bug, decision and guide) with no `--author`.

**True today:** `--author` is a required option on every `sq create <type>`. The very first tutorial command exits 2 with `Missing option '--author'`, and so does every later create. A newcomer following the tutorial is stopped at step 1 with nothing created. README.md:65-66 and `sq workflow` both state that every item is authored by a role, so the tutorial contradicts its own sibling docs.

**Verified:** driven in a scratch squad (`sq -C <scratch> init --roles all`, then the tutorial commands verbatim).

**Fix:** add `--author <slug>` to each create, matching the role the section heading names: `--author product-owner` (epic, feature), `--author tech-lead` (task), `--author qa` (bug), `--author architect` (decision, guide). One sentence in section 1 explaining that every item is authored by a role would also prevent the FAQ gap (separate finding).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T09:02:15Z] `tech-writer` Theo Writer:
  - Fixed in docs/tutorial.md: every create carries --author (product-owner, tech-lead, qa, architect), plus a sentence in step 1 that every item is authored by a registered role.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Tutorial step 4: --as developer is refused as an unknown slug, not downgraded as the note claims

<!-- sq:finding:F2:body -->
**Where:** docs/tutorial.md:105 and the parenthetical at 110-111.

**Doc says:** `sq task 11 comment --as developer -m "Hashing done" …`, then "(`--as developer` only resolves to a full name if you've activated a dev role; otherwise use a real slug like `architect`, or `operator`.)"

**True today:** `--as developer` is refused outright: `error: unknown slug 'developer'; valid slugs: architect, devops, manager, product-owner, qa, reviewer, tech-lead, tech-writer` (exit 1). It does not "resolve to a bare slug"; the comment is not written. `--as operator` is still accepted (renders as "Operator (operator)"), and `--as architect` works. With `sq dev add --tech python` the slug is `python-dev`, never `developer`.

**Verified:** driven.

**Fix:** use a real slug in the command (e.g. `--as tech-lead`) and reword the parenthetical: `--as` must be a registered slug (a role, `op-<slug>` for a human, or a `<tech>-dev` after `sq dev add`); an unknown slug is refused.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T09:02:18Z] `tech-writer` Theo Writer:
  - Fixed in docs/tutorial.md step 4: the comment uses --as tech-lead; the note says --as takes a registered slug (role, <tech>-dev after sq dev add, op-<slug>) and an unknown one is refused.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Tutorial promises a clean sq check but leaves two unwritten-body warnings

<!-- sq:finding:F3:body -->
**Where:** docs/tutorial.md:3-5 ("… and a clean `sq check`") and 134 (`sq check … → ✓ no issues`).

**Doc says:** following the tutorial ends with a clean `sq check` printing `✓ no issues`.

**True today:** following the steps as written (with `--author` added so they run), `sq check` prints two warnings and exits 0: `warn FEAT-<n>: US2 body is unwritten (still the placeholder stub)` and `warn TASK-<n>: ST2 body is unwritten (still the placeholder stub)`. Step 2 sets only story 1's body and step 3 gives only subtask 1 a `-m`. The `✓ no issues` string does exist (printed on a fully clean squad), but the tutorial never reaches it.

**Verified:** driven.

**Fix:** either set US2's body in step 2 and pass `-m` on the second `add-subtask` in step 3, or show the two warnings as the expected output and explain that an unwritten sub-entity body is what `sq check` flags.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T09:02:21Z] `tech-writer` Theo Writer:
  - Fixed in docs/tutorial.md: story 2 gets a body in step 2 and the second add-subtask passes -m; the tutorial run end to end on a fresh squad ends with sq check printing the clean result.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — README omits the contract and milestone types: count, prefixes, lifecycles, layout, aliases, create

<!-- sq:finding:F4:body -->
**Where:** README.md:131-137 (type count and categories), 147 (prefix list), 179-186 (lifecycle table), 170 (on-disk layout), 292 (alias list), 296 (`sq create` type list); docs/README.md:70 (layout).

**Doc says:** "Ten types ship by default"; records are `decision`, `guide`; built-in prefixes are `EPIC FEAT TASK BUG ADR REV GUIDE ROLE SKILL OP`; the lifecycle table lists six rows; the layout shows `epics/ features/ tasks/ bugs/ adrs/ reviews/ guides/ operators/`; aliases are `e f t b d r g` plus `feat`/`dec`/`rev`; `sq create epic|feature|task|bug|decision|review|guide`.

**True today:** twelve types ship. `contract` (prefix `PRD`, folder `contracts/`, lifecycle `Draft → Active → Superseded (+ Deprecated)`, aliases `c`/`prd`) and `milestone` (prefix `MILE`, folder `milestones/`, lifecycle `Draft → InProgress → Done (+ Cancelled)`, aliases `m`/`mile`) are both in the records category, both creatable with `sq create contract|milestone`, both get an `sq-contract`/`sq-milestone` skill, and both folders are created by `sq init`. docs/README.md:16 already mentions milestones and contracts, so the two READMEs disagree.

**Verified:** driven (`sq workflow types|lifecycles`, root `--help`, `sq create --help`, `ls squads/` after init).

**Fix:** say twelve types; add `contract` and `milestone` to the records bullet, `PRD MILE` to the prefix list, two rows to the lifecycle table, `contracts/ milestones/` to both layouts (plus `board/` and `agents/memory/`, which appear on first `sq board post` / `sq memory add`), `c m` and `prd`/`mile` to the alias sentence, and `contract|milestone` to the create line.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T09:02:24Z] `tech-writer` Theo Writer:
  - Fixed in README.md (twelve types, records bullet, PRD/MILE prefixes, two lifecycle rows, contracts/ milestones/ in layout with board/ and memory/ noted as appearing on first use, c/m/prd/mile aliases, create line) and docs/README.md layout.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — README: sq renumber shown without the required --from option; contradicts the FAQ

<!-- sq:finding:F5:body -->
**Where:** README.md:341.

**Doc says:** `sq renumber --onto N | --by N — shift this branch's IDs clear of another branch's range before a merge`.

**True today:** `--from INTEGER` is required (`sq renumber --help` marks it `*`); the command as documented is refused with a usage error. docs/faq.md:132 has the correct form, `sq renumber --from <N> --onto 287`, so the README contradicts the FAQ.

**Verified:** `sq renumber --help` read from the dev build; FAQ form cross-checked.

**Fix:** `sq renumber --from N (--onto M | --by K)` with a clause that `--from` is the lowest local sequence number to shift.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T09:02:27Z] `tech-writer` Theo Writer:
  - Fixed in README.md Maintenance: sq renumber --from N (--onto M | --by K), with --from explained.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — README: claude_code pointers do not @-include the definition; contradicts Concepts

<!-- sq:finding:F6:body -->
**Where:** README.md:390-392 (Backends › claude_code).

**Doc says:** "Each role and skill gets its own pointer file that @-includes the real definition from `squads/agents/`."

**True today:** the pointer files contain no `@` include. `.claude/agents/<slug>.md` carries the frontmatter the host selects on (name, description, model, color, disallowedTools, skills) and tells the agent to run `sq role <slug> show`; `.claude/skills/<skill>/SKILL.md` likewise names `sq skill <skill> show`. README.md:157 ("each names the `sq` command that produces the full definition") and docs/README.md:66-67 describe this correctly, so the README contradicts itself.

**Verified:** read the generated pointer files in the scratch squad.

**Fix:** "Each role and skill gets its own pointer file that names the `sq` command producing its full definition (`sq role <slug> show`, `sq skill <name> show`)."
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T09:02:30Z] `tech-writer` Theo Writer:
  - Fixed in README.md Backends > claude_code: pointers name the sq command producing the definition.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — README: agents_md backend no longer writes a .agents_md/ staging folder

<!-- sq:finding:F7:body -->
**Where:** README.md:412-413 (Backends › agents_md).

**Doc says:** "Internal staging files live in `.agents_md/` (one per role/skill); commit `AGENTS.md` but `.agents_md/` can be gitignored."

**True today:** `sq init --backend agents_md` creates `AGENTS.md`, `.squads.toml`, `.gitignore` and `squads/` — no `.agents_md/` directory. In the source the backend only *deletes* a leftover `.agents_md/` from older versions (`_backends/_agents_md/_backend.py`, "opportunistically delete a leftover `.agents_md/` file"). Telling adopters to gitignore a folder that is never written is stale advice.

**Verified:** driven (`ls -a` after init) and read in the source.

**Fix:** drop the sentence, or replace it with: "No staging files are written; commit `AGENTS.md`."

Aside for the dev team, not a doc defect: on a brand-new empty directory the same init prints `warning: AGENTS.md had pre-existing hand-written content with no squads markers; the managed section was inserted at the top`, which is false on a fresh init.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T09:02:33Z] `tech-writer` Theo Writer:
  - Fixed in README.md Backends > agents_md: the .agents_md/ sentence is replaced with "No staging files are written" and what to commit.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — README: per-role preloaded skill lists are stale (manager, product owner, developer)

<!-- sq:finding:F8:body -->
**Where:** README.md:84-89.

**Doc says:** "the product owner gets `sq-feature`/`sq-epic`, a developer gets `sq-task`/`sq-bug`/`sq-review`, and the manager (who triages rather than owning a type) gets just `squads`."

**True today (generated pointers after `sq init --roles all` + `sq dev add --tech python`):** every role preloads `squads`, `greeting` and `sq-memory`; the manager gets exactly those three, not "just `squads`"; the product owner additionally gets `sq-epic`, `sq-feature`, `sq-contract`, `sq-milestone`; the developer gets `sq-task`, `sq-bug`, `sq-contract`, `sq-review`.

**Verified:** read `.claude/agents/manager.md`, `product-owner.md`, `python-dev.md` in the scratch squad.

**Fix:** describe the rule rather than a fixed list ("every role preloads `squads`, `greeting` and `sq-memory`, plus one `sq-<type>` skill per item type the playbook gives it a part in"), and if examples stay, make them current.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-16T09:02:36Z] `tech-writer` Theo Writer:
  - Fixed in README.md Working with agents: states the rule (squads, greeting, sq-memory plus one sq-<type> per playbook part) with current product-owner/developer/manager examples, re-read from generated pointers.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — README layout: .squads.toml does not hold the default role

<!-- sq:finding:F9:body -->
**Where:** README.md:163 (on-disk layout comment on `.squads.toml`).

**Doc says:** `.squads.toml  # config (squad dir, active backends, version, default role)`.

**True today:** the file written by `sq init` holds `schema_version`, `squad_dir`, `active_backends`, `squads_version` — no default-role key. The default-role designation lives on the role item itself (`is_default` in the role's frontmatter `extra`, moved by `sq role <slug> set-default`).

**Verified:** `cat .squads.toml` in the scratch squad; `grep` of `_models/_config.py` and `_models/_extras.py`.

**Fix:** `# config (squad dir, active backends, schema + package version)`.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-16T09:02:39Z] `tech-writer` Theo Writer:
  - Fixed in README.md on-disk layout: .squads.toml holds squad dir, active backends, schema + package version.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — README: sq workflow subcommand list omits views and view

<!-- sq:finding:F10:body -->
**Where:** README.md:282.

**Doc says:** `sq workflow [show|types|subentity-kinds|lifecycles|collections|statuses|roles|ref-kinds|lint]`.

**True today:** `sq workflow --help` also lists `views` (every declared derived view) and `view` (resolve one view against an item). docs/README.md:16 advertises derived views, so the README's command reference omits the only commands that expose them.

**Verified:** `sq workflow --help` read from the dev build.

**Fix:** add `views|view` to the bracket list and a clause: "or resolve a declared derived view (`views`, `view`)".
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-16T09:02:42Z] `tech-writer` Theo Writer:
  - Fixed in README.md command reference: views|view added to sq workflow with a clause.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — README: sq graph --format omits mermaid-md

<!-- sq:finding:F11:body -->
**Where:** README.md:324.

**Doc says:** `sq graph <ID> … [--format dot|mermaid]`.

**True today:** `--format` also accepts `mermaid-md` (the Mermaid body wrapped in a ```mermaid fence, for pasting into a doc or PR); `sq workflow` even recommends it. Also `--depth` defaults to 2.

**Verified:** `sq graph --help` read from the dev build.

**Fix:** `[--format dot|mermaid|mermaid-md]`.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-16T09:02:46Z] `tech-writer` Theo Writer:
  - Fixed in README.md command reference: sq graph --format dot|mermaid|mermaid-md.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — README: generic sq create flag list does not apply to guides

<!-- sq:finding:F12:body -->
**Where:** README.md:296.

**Doc says:** one flag list for all types: `sq create epic|feature|task|bug|decision|review|guide TITLE --author <slug> [--parent ID] [--desc] [--label] [--ref ID] [--assignee] [--priority CODE] [-m|--file] [--json]`.

**True today:** `sq create guide` has a different option set: no `--label`, `--ref` or `--priority`; it takes `--tech` and `--tag` (repeatable) instead. The guide-specific line at README.md:334 mentions `--tech`/`--tag` but not that the generic flags are absent, so a reader combining the two lines writes a command that is refused.

**Verified:** `sq create guide --help` vs `sq create task --help`.

**Fix:** footnote the create line: "guides take `--tech`/`--tag` in place of `--label`/`--ref`/`--priority`".
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-16T09:02:49Z] `tech-writer` Theo Writer:
  - Fixed in README.md command reference: create line notes guides take --tech/--tag in place of --label/--ref/--priority.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — docs/README: migration.md index entry describes transformers and LLM runbooks that are not in the doc

<!-- sq:finding:F13:body -->
**Where:** docs/README.md:23.

**Doc says:** migration.md covers "`sq sync`/`repair`, frontmatter & marker transformers, and LLM runbooks for non-deterministic changes".

**True today:** migration.md is organised around `sq migrate up|help|chlog`, the schema runners, the three tiers of on-disk state, what counts as a breaking change, and the per-release upgrade sections (0.16: the schema step, `-C` replaces `--dir`). The words "transformer" and "LLM runbook" do not appear in it (one mention of "runbooks" for `chlog` manual steps). The index entry describes a document that no longer exists in that shape. (The migration doc itself is being edited for comment-header slugs; this finding is about the index line only.)

**Verified:** read docs/migration.md headings and grepped for the terms.

**Fix:** "Upgrading a squad to a new squads version: `sq migrate up`, the changelog (`help`/`chlog`), and the per-release manual steps."
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-16T09:02:52Z] `tech-writer` Theo Writer:
  - Fixed in docs/README.md index: migration.md entry now describes sq migrate up, help/chlog, breaking changes and per-release manual steps.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Tutorial: sample output path and 'IDs spent on roles' understate what init allocates

<!-- sq:finding:F14:body -->
**Where:** docs/tutorial.md:29 and 32.

**Doc says:** `# → created EPIC-9 → squads/epics/EPIC-000009-authentication-platform.md` and "(Your numbers differ — the global counter already spent IDs on the bundled roles.)"

**True today:** with `sq init --roles all` the counter has spent 20 ids before the first item — 8 roles and 12 generated skills — so the epic is EPIC-21, and the create line prints the absolute path, not a squad-relative one. Only the roles are credited, which leaves a reader wondering where the other dozen ids went.

**Verified:** driven (`sq list --all --category roster` after init; create output).

**Fix:** "the global counter already spent IDs on the bundled roles and their generated skills"; show the path as `…/squads/epics/EPIC-000021-authentication-platform.md` or say the path printed is absolute.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-16T09:02:55Z] `tech-writer` Theo Writer:
  - Fixed in docs/tutorial.md: IDs are the real ones from a fresh sq init --roles all (EPIC-21 onward), credited to roles and their generated skills, and the printed path shown as absolute.
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — Tutorial: bare sq tree lists the 20 roster items before the hierarchy

<!-- sq:finding:F15:body -->
**Where:** docs/tutorial.md:132 (`sq tree  # the epic → feature → task hierarchy`).

**Doc says / implies:** `sq tree` shows the epic → feature → task hierarchy.

**True today:** a bare `sq tree` on the tutorial squad first lists all 20 roster items (ROLE-1 … SKILL-20) as roots, then the three work items and the bug, ADR and guide. The hierarchy the sentence promises is at the bottom of a 26-line forest. Not false, but a newcomer looking for "the hierarchy" sees a roster dump first.

**Verified:** driven.

**Fix:** `sq tree EPIC-<n>` (rooted) or `sq tree --category work`, with a note that the bare form shows every root including the roster.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-16T09:02:58Z] `tech-writer` Theo Writer:
  - Fixed in docs/tutorial.md step 7: sq tree EPIC-21, with a note that the bare form lists every root including the roster.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — FAQ gap: no entry for Missing option --author or unknown slug errors

<!-- sq:finding:F16:body -->
**Where:** docs/faq.md (gap; no entry).

**Doc says:** nothing about the two most likely first errors a newcomer hits.

**True today:** `Missing option '--author'` (exit 2) on any `sq create` without `--author`, and `error: unknown slug 'developer'; valid slugs: …` (exit 1) on `--as`/`--author` with a slug that is not registered. The tutorial as written triggers both (see the two tutorial findings), and the FAQ is the doc the README points to for "common errors".

**Verified:** driven.

**Fix:** add two short entries: "Missing option '--author'" (every item is authored by a registered role; `sq role list` shows the slugs) and "unknown slug '…'" (`--as`/`--author`/`--assignee` take a role slug, `op-<slug>` for a human, or a `<tech>-dev` added with `sq dev add`).
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
- [2026-10-16T09:03:01Z] `tech-writer` Theo Writer:
  - Fixed in docs/faq.md: two new entries, "Missing option --author" and "unknown slug", both reproduced on the dev build.
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T08:48:42Z] `reviewer` Paul Reviewer:
  - Audit complete: 16 findings (1 high, 7 medium, 8 low). The high one stops a newcomer at the first tutorial command. Three product asides surfaced while driving and are not doc defects: the add-story/add-subtask hint prints a nonexistent command form (sq story body FEAT-n USn); the task-parent refusal hints sq ref add <task> <id>, also not a real form; a fresh agents_md init warns about pre-existing AGENTS.md content on an empty directory.
  - @tech-writer to correct the four docs; verdict left for the main loop.
- [2026-10-16T09:04:10Z] `tech-writer` Theo Writer:
  - All 16 findings fixed in README.md, docs/README.md, docs/tutorial.md and docs/faq.md; each fact re-driven on the dev build in a scratch squad.
  - Tutorial proven: its bash blocks extracted verbatim and run on a fresh sq init --roles all squad; all 29 commands exit 0 and sq check prints the clean result.
  - tests/meta has one failure outside this share: docs/workflow.md:63 cites TASK-3 (a concurrent edit in another writer's file).
  - @manager ready for verdict.
- [2026-10-16T09:06:35Z] `tech-writer` Theo Writer:
  - Also fixed outside the findings, at the REV-1034 writer's request: docs/faq.md 'Does sq repair change my files?' no longer says repair empties role bodies or touches no skill body. Re-driven: a role/skill body with prose is left alone; an empty role or generated-skill body gets its view tag written back; a second run rewrites nothing.
- [2026-10-16T11:26:13Z] `manager` Catherine Manager:
  - Approved: every finding Fixed (re-run by the writer on the dev build) or closed with a home; cross-doc seams checked in REV-1047.
<!-- sq:discussion:end -->
