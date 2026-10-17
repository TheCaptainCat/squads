---
id: REV-1034
sequence_id: 1034
type: review
title: 'Docs audit: adoption, agents, roles, recipes'
status: Approved
author: reviewer
description: 'Adopter-docs audit of docs/adoption.md, agents.md, backends.md, roles.md,
  recipes.md and clients/vscode/README.md against the release/0.16 dev build: every
  concrete claim driven in scratch squads or read in the code.'
subentities:
- local_id: F1
  title: create examples omit the required --author option (adoption.md, agents.md)
  status: Fixed
  severity: high
- local_id: F2
  title: 'roles.md: developers also manage sq-contract'
  status: Fixed
  severity: medium
- local_id: F3
  title: 'backends.md: registering a backend describes a mechanism that no longer
    exists'
  status: Fixed
  severity: medium
- local_id: F4
  title: 'adoption.md: example item filename is not zero-padded like the real one'
  status: Fixed
  severity: medium
- local_id: F5
  title: 'vscode README: layer map and the user listing omit the board and memory
    panels'
  status: Fixed
  severity: medium
- local_id: F6
  title: Pointers also preload sq-memory; manager/devops carry more than squads
  status: Fixed
  severity: low
- local_id: F7
  title: 'backends.md: three non-abstract methods, not two; managed_entry_paths never
    introduced'
  status: Fixed
  severity: low
- local_id: F8
  title: 'roles.md: rm without --purge leaves the file and sq check then errors'
  status: Fixed
  severity: low
- local_id: F9
  title: 'roles.md: ''metadata stored on extra (keys in ExtraKey)'' is internal and
    mostly stale'
  status: Fixed
  severity: low
- local_id: F10
  title: 'recipes.md: ''Prefix with uv run from a source checkout'' is repo-process
    content'
  status: Fixed
  severity: low
- local_id: F11
  title: 'vscode README: canary fixture/surface list is stale'
  status: Fixed
  severity: low
- local_id: F12
  title: 'vscode README: TypeScript is not pinned to 6.0.x in package.json'
  status: Fixed
  severity: low
- local_id: F13
  title: 'adoption.md: sq repair does not empty a role''s stored body'
  status: Fixed
  severity: medium
- local_id: F14
  title: 'adoption.md: generated skill bodies are rewritten by sq repair'
  status: Fixed
  severity: medium
- local_id: F15
  title: agents.md tells agents to read ROLE-*.md files instead of running sq role
    show
  status: Fixed
  severity: medium
created_at: '2026-10-16T08:49:38Z'
updated_at: '2026-10-16T11:26:15Z'
---
<!-- sq:body -->
## Scope

Adopter-facing documentation audit for docs/adoption.md, docs/agents.md, docs/backends.md, docs/roles.md, docs/recipes.md and clients/vscode/README.md, against the release/0.16 dev build.

## Method

Every concrete claim was driven or read, not trusted: `sq init`/`sq adopt`/`sq sync` run in scratch squads (fresh project, pre-existing CLAUDE.md with orphan `.claude/` files, `agents_md` and dual-backend inits), the generated pointers/skills/managed sections diffed against the text, the role catalog compared with `roles.toml` and the generated pointers, every recipe in recipes.md run end to end (feature, tasks, bug, review, decision, contract, milestone, guide, developer onboarding, inbox/mine/workload/search/blocked, `--at`, `renumber`), `sq repair`'s rewrite exercised on a role body, a skill body and mirrored `extra` keys, and the backend ABC/registry read in `_backends/`. The VS Code README was checked against `package.json`, `package-lock.json`, `src/`, `test/` and the CI workflow.

## Result

Fifteen findings: one high (every `create` needs `--author`, three examples omit it), seven medium (stale `sq repair` claims about role and skill bodies, agents.md pointing agents at ROLE files, developers also managing `sq-contract`, a backend-registration mechanism that no longer exists, unpadded example filenames, a VS Code layer map and listing missing the board/memory panels), seven low. Everything else driven in these six files holds today, including the retirement refusals and their wording, `--unlink`, `set-default`, the orphan and pre-existing-CLAUDE.md warnings, the `sq check` presence/currency findings and `sq sync`'s was-missing/had-drifted report, the inbox regions and `sq mine` sub-entity matching, and the milestone roll-up.

## Observed outside the docs' scope

Two tool behaviours surfaced while driving, for QA rather than the writer: `sq init --backend agents_md` on a fresh directory warns that AGENTS.md "had pre-existing hand-written content" although no AGENTS.md existed; and `sq skill <addr> rm` / `sq operator <addr> rm` without `--purge` leave the item file on disk, so the next `sq check` exits 3 with "on disk but not in index".
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1034 add-finding "…" --severity medium`; track with `sq review 1034 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — create examples omit the required --author option (adoption.md, agents.md)

<!-- sq:finding:F1:body -->
**Where:** docs/adoption.md:13 (`sq --at 2024-01-15 create task "Fix login"`), docs/adoption.md:98 (`sq --at 2024-01-15 create feature "User authentication" --parent EPIC-1`), docs/agents.md:128 (`sq create task "Validate token" --parent FEAT-<n>`).

**Doc says:** `create` works with just a title (plus `--parent`).

**True today:** `--author` is a required option on every `sq create <type>`. Driven: `sq create task "T1"` and `sq create epic "No author"` both exit 2 with `Missing option '--author'`; `sq create task --help` lists `--author  Authoring agent (role slug); must be registered. [required]`. The generated AGENTS.md/CLAUDE.md sections and docs/recipes.md all pass `--author`.

**Impact:** the first command an adopter copies from the adoption guide fails; the agents manual's canonical "Create" step fails too.

**Suggested correction:** add `--author <slug>` to the three examples (e.g. `--author tech-lead`, `--author product-owner`) and say once, near the top of adoption.md, that `create` always needs an author (which `--as`/`--author op-<slug>` can also satisfy for a human).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-16T09:02:49Z] Theo Writer:
  - Fixed in docs/adoption.md (both create examples carry --author; one sentence after the first block says every create needs it) and docs/agents.md (Create step).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — roles.md: developers also manage sq-contract

<!-- sq:finding:F2:body -->
**Where:** docs/roles.md:52 (`Every developer manages sq-task, sq-bug, and sq-review.`).

**True today:** a developer pointer preloads `sq-task`, `sq-bug`, `sq-contract`, `sq-review`. Driven: `sq dev add --tech dotnet` in a scratch squad; `.claude/agents/dotnet-dev.md` skills list is `squads, greeting, sq-memory, sq-task, sq-bug, sq-contract, sq-review` (same for `node-js-dev` and `python-dev`).

**Suggested correction:** list `sq-contract` too, or phrase it as "the item skills the playbook gives `*dev` (today `sq-task`, `sq-bug`, `sq-contract`, `sq-review`)".
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-16T09:02:52Z] Theo Writer:
  - Fixed in docs/roles.md (Stack-specific developers): sq-contract added, driven with sq dev add.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — backends.md: registering a backend describes a mechanism that no longer exists

<!-- sq:finding:F3:body -->
**Where:** docs/backends.md:352-354 (`Today _registry.get_backend imports the built-in _claude_code package for its registration side-effect; add an import for your package the same way`).

**True today:** `src/squads/_backends/_registry.py` holds a `_BUILTIN_BACKEND_MODULES` tuple (`squads._backends._claude_code`, `squads._backends._agents_md`) that `_load_builtins()` imports once; `get_backend` only calls `_load_builtins()`. Read in the source. A new built-in is appended to that tuple, not added as an import in `get_backend`. The page also never says plainly that two backends ship today (`claude_code` and `agents_md`, both selectable with `--backend`; driven: `sq init --backend agents_md` writes AGENTS.md, `--backend claude_code --backend agents_md` runs both) — the intro still reads as if Claude Code were the only one.

**Suggested correction:** step 2 -> "append `squads._backends._cursor` to `_BUILTIN_BACKEND_MODULES` in `_registry.py`"; add one sentence in the intro naming the two bundled backends.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-16T09:02:55Z] Theo Writer:
  - Fixed in docs/backends.md: intro names the two bundled backends; Registering step 2 appends to _BUILTIN_BACKEND_MODULES.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — adoption.md: example item filename is not zero-padded like the real one

<!-- sq:finding:F4:body -->
**Where:** docs/adoption.md:99 (`# -> created FEAT-7 -> squads/features/FEAT-7-user-authentication.md`), and the same shape at docs/agents.md:129 (`squads/tasks/TASK-<n>-validate-token.md`).

**True today:** files are `PREFIX-NNNNNN-slug.md`. Driven: `sq create epic "Auth" --author product-owner` prints `created EPIC-22 -> .../squads/epics/EPIC-000022-auth.md`. adoption.md:47 states the padded form correctly, so the page contradicts itself; a user hand-converting legacy files into "the squads layout" (adoption.md:47-49) could name them unpadded.

**Suggested correction:** `FEAT-000007-user-authentication.md` and `TASK-00000<n>-validate-token.md` (or just `TASK-NNNNNN-validate-token.md`).
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-16T09:02:59Z] Theo Writer:
  - Fixed in docs/adoption.md (FEAT-000007-...) and docs/agents.md (TASK-NNNNNN-...).
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — vscode README: layer map and the user listing omit the board and memory panels

<!-- sq:finding:F5:body -->
**Where:** clients/vscode/README.md:6-10 (the "in one line" feature summary), :33-42 (domain-layer module list), :20-31 (host-layer table).

**True today:** `src/domain/` also holds `boardView`, `memoryView`, `metaFilter`, `recordsFilter`, `omissions`, `itemDirectory`, `itemIdPattern`, `treeAnchor` (read: `ls src/domain`), and the host layer has `types.ts`. `package.json` contributes `squads.openBoard`, and `itemPreviewManager.ts` documents two extra panels: the team board (`sq board list --json`) and a Roster memory entry (`sq memory <role> show <slug> --json`). Neither panel appears in the README summary, and `MARKETPLACE.md` — which README:6-7 names as "the file to update when a user-visible feature changes" — does not mention the board or memory entries either (grep for board/memory/bulletin/notice finds only the metaphorical "board").

**Suggested correction:** add the board and memory-entry panels to the README summary and the domain list (one line each), and flag MARKETPLACE.md for the same addition.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-16T09:03:02Z] Theo Writer:
  - Fixed in clients/vscode/README.md (summary, host table incl. types.ts, domain list) and clients/vscode/MARKETPLACE.md (Roster memory entries, new team board section).
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Pointers also preload sq-memory; manager/devops carry more than squads

<!-- sq:finding:F6:body -->
**Where:** docs/agents.md:18-20 (`preloads the squads skill, the greeting skill, plus the item-type skills`), docs/roles.md:13 and :18 (`squads skill only`), docs/roles.md:22-23 (`that's why the manager and devops carry only squads`).

**True today:** every pointer preloads `squads`, `greeting`, `sq-memory`, then the item skills. Driven: `sq init` in a scratch squad; `.claude/agents/manager.md` and `devops.md` list `squads, greeting, sq-memory`.

**Suggested correction:** roles.md: "every role gets `squads`, `greeting` and `sq-memory`; a role that manages no item type gets nothing more (manager, devops)"; agents.md: add `sq-memory` to the list.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-16T09:03:05Z] Theo Writer:
  - Fixed in docs/agents.md (pointer skills) and docs/roles.md (roster table, the paragraph under it, Managing skills).
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — backends.md: three non-abstract methods, not two; managed_entry_paths never introduced

<!-- sq:finding:F7:body -->
**Where:** docs/backends.md:234-244 (`Two more methods are non-abstract`), :277-278 (uses `managed_entry_paths` without defining it).

**True today:** `AgentBackend` has seven abstract methods and three non-abstract ones with defaults: `managed_entry_paths` (per-entry pointer paths, default `[]`), `restriction_fragment`, `render_role_entry`/`render_skill_entry`. Read: `src/squads/_backends/_base.py:263-341`. The "seven methods, does not grow" promise is intact.

**Suggested correction:** "Three more methods are non-abstract…" and add a bullet for `managed_entry_paths` (the per-entry counterpart of `managed_paths`, read at warn by `sq check` and by `sq sync`'s was-missing/had-drifted report).
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-16T09:03:07Z] Theo Writer:
  - Fixed in docs/backends.md: three non-abstract methods, managed_entry_paths bullet added.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — roles.md: rm without --purge leaves the file and sq check then errors

<!-- sq:finding:F8:body -->
**Where:** docs/roles.md:72, :123, :140 (`rm [--purge]` with no explanation of either form).

**True today (driven):** `sq skill deploy-runbook rm` and `sq operator OP-000025 rm` print `removed …`, but the item file stays on disk and the next `sq check` reports `error SKILL-24: on disk but not in index (run sq repair)` / `error OP-25: …` (exit 3); `sq repair` would re-index them. Nothing on the page tells the reader that `--purge` deletes the file or that a plain `rm` leaves the squad in a state `sq check` rejects.

**Suggested correction:** one sentence: "`rm` drops the entry from the roster and its generated pointer; pass `--purge` to delete the item file too, otherwise `sq check` reports the orphaned file." (The behaviour itself may deserve a bug: a verb that leaves the squad failing `sq check` by default.)
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-16T09:03:10Z] Theo Writer:
  - Fixed in docs/roles.md: one paragraph after the operator commands explains rm vs --purge for roles, skills and operators (driven).
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — roles.md: 'metadata stored on extra (keys in ExtraKey)' is internal and mostly stale

<!-- sq:finding:F9:body -->
**Where:** docs/roles.md:253 (`Role/dev metadata is stored on the role item's extra (keys in ExtraKey).`).

**True today:** a role item's `extra` carries only `slug` (plus `model`, `is_dev`, `tech` for a developer); the rest of the definition is rendered from the catalog and overrides. Driven: `sq init` + `sq dev add` scratch files. `ExtraKey` is a private Python enum of this codebase, not something an adopter can use.

**Suggested correction:** drop the sentence, or say "a role item stores only its slug (and a developer's model/tech); everything else is resolved from the catalog and your overrides".
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-16T09:03:13Z] Theo Writer:
  - Fixed in docs/roles.md (last paragraph): sentence replaced with what a role item stores; dropped the private module and function names in the same paragraph.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — recipes.md: 'Prefix with uv run from a source checkout' is repo-process content

<!-- sq:finding:F10:body -->
**Where:** docs/recipes.md:257.

**Issue:** adopters install `sq` (`uv tool install squads`, adoption.md:24); running from a source checkout is this repository's development workflow. Every recipe otherwise reads as adopter-facing.

**Suggested correction:** delete the sentence (contributor docs are the home for it).
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-16T09:03:17Z] Theo Writer:
  - Fixed in docs/recipes.md intro: sentence removed.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — vscode README: canary fixture/surface list is stale

<!-- sq:finding:F11:body -->
**Where:** clients/vscode/README.md:95-98 (`checks that the committed fixtures (test/fixtures/tree.json, graph.json, list.json, show-raw.txt) still match … sq tree --json, sq graph --json, sq list --json, and sq show <id> --raw`).

**True today:** `test/fixtures/` holds 14 fixtures (also `show-json.json`, `search.json`, `type-catalog.json`, `statuses-catalog.json`, `collections-catalog.json`, `subentity-kinds-catalog.json`, `roles-catalog.json`, `workflow-raw.txt`, …) and `test/canary/skewCanary.test.ts` also exercises `sq show --json` and `sq workflow types --json` (read: its header comment and `describe` blocks).

**Suggested correction:** describe the canary by intent ("every `sq --json`/`--raw` surface the client reads, one committed fixture each") instead of enumerating four files.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-16T09:03:20Z] Theo Writer:
  - Fixed in clients/vscode/README.md: canary described by the surfaces it guards, not four fixture names.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — vscode README: TypeScript is not pinned to 6.0.x in package.json

<!-- sq:finding:F12:body -->
**Where:** clients/vscode/README.md:62-63 (`TypeScript stays on 6.0.x. The type-aware lint layer peer-caps below 6.1`).

**True today:** `package.json` declares `"typescript": "^6.0.3"`, which admits any 6.x; what holds 6.0.3 is the lockfile plus `typescript-eslint@8.64.0`'s peer range `>=4.8.4 <6.1.0` (read: package.json, package-lock.json). An `npm update`/`npm install typescript@latest` would move past the peer cap with only a peer warning.

**Suggested correction:** either pin `"typescript": "~6.0.3"` in package.json so the claim is true, or reword: "TypeScript is held at 6.0.x by the lockfile because typescript-eslint peer-caps below 6.1".
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-16T09:03:23Z] Theo Writer:
  - Fixed in clients/vscode/README.md convention 7: reworded (package.json allows 6.x, the lockfile plus the typescript-eslint peer cap hold 6.0.x).
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — adoption.md: sq repair does not empty a role's stored body

<!-- sq:finding:F13:body -->
**Where:** docs/adoption.md:195-198 (`a **role's** stored body — emptied, not deleted: the sq:body marker pair stays and only its contents go`).

**True today:** the index rebuild touches a role body only when it is *empty*, and then writes the `the `sq:view:role_definition` tag` placement tag into it; prose in a role body is left alone. Read: `_services/_maintenance.py::_converge_body_tag` returns the text unchanged unless the region is empty or already just the tag, and `_retired_region_tags` strips only the summary region and `*:head` regions. Driven: in a scratch squad I replaced the manager's body with `hand-written role prose`, ran `sq repair` -> `stripped retired regions from 2 item files`, and `git diff` shows the prose still in place (only the mirrored `extra` keys were removed).

**Suggested correction:** replace the bullet with what happens: an empty role body is converged onto the role-definition view tag; a role body carrying prose is not rewritten. The pointer to `.overrides/roles/<slug>.toml` can stay as general advice.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-10-16T09:03:26Z] Theo Writer:
  - Fixed in docs/adoption.md (What sq repair writes): emptied-body bullet removed; an empty role body gets its view tag, prose is left alone (driven). Section 1 no longer claims an exception.
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — adoption.md: generated skill bodies are rewritten by sq repair

<!-- sq:finding:F14:body -->
**Where:** docs/adoption.md:206-207 (`**No skill body is touched** — not one you wrote, and not a template-owned one either; on disk the two cannot be told apart, so both are left alone.`).

**True today:** a generated skill whose body region is empty gets its view tag written by the rebuild. Driven: emptied the `squads` skill's body in a scratch squad, ran `sq repair` -> the file is in the `stripped` list and `git diff` shows `+the `sq:view:squads_skill` tag` inside `sq:body`. Read: `_repair_body_tag` classifies both `role` and `skill` items (`views.roster_body_view_name`), so skills are in scope of the convergence. An authored skill body with prose is indeed left alone, and the two *can* be told apart (by slug/view classification), so the "cannot be told apart" rationale is also stale.

**Suggested correction:** "An authored skill's body is never touched. A generated skill (`squads`, `greeting`, `sq-memory`, `sq-<type>`) whose body region is empty is converged onto its view tag, like a role."
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
- [2026-10-16T09:03:29Z] Theo Writer:
  - Fixed in docs/adoption.md (What sq repair writes): empty generated-skill bodies get their view tag; prose and authored skills are untouched (driven).
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — agents.md tells agents to read ROLE-*.md files instead of running sq role show

<!-- sq:finding:F15:body -->
**Where:** docs/agents.md:12-14 (`load their role definition from squads/agents/roles/ROLE-*.md and act as them`).

**True today:** the generated CLAUDE.md section (driven: `sq init` in a scratch squad, "Impersonation on greeting") says `run sq role <slug> show to read the full role definition`, and the role file's body is only a `the `sq:view:role_definition` tag` tag, so opening the file yields nothing. The same page's golden rules (agents.md:163-166) say never to read a `.md` file directly, so the page contradicts itself.

**Suggested correction:** `load their role definition with sq role <slug> show and act as them`.
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
- [2026-10-16T09:03:32Z] Theo Writer:
  - Fixed in docs/agents.md: impersonation now says sq role <slug> show.
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-16T08:52:15Z] Paul Reviewer:
  - Audit complete: 15 findings (1 high, 7 medium, 7 low), bodies carry file:line, the truth, how it was verified and a suggested correction. @tech-writer for the corrections; @qa for the two tool behaviours noted in the body (spurious AGENTS.md warning on fresh init; rm without --purge leaves sq check failing).
- [2026-10-16T09:03:52Z] Theo Writer:
  - All 15 findings fixed in my files. Out of scope: docs/faq.md:92/104 and docs/internals.md:130 repeat the stale role-body and skill-body repair claims (F13/F14); docs/workflow.md:63 cites TASK-3 and fails the ticket-reference meta test.
- [2026-10-16T11:26:15Z] Catherine Manager:
  - Approved: every finding Fixed (re-run by the writer on the dev build) or closed with a home; cross-doc seams checked in REV-1047.
<!-- sq:discussion:end -->
