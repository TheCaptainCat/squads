---
id: REV-795
sequence_id: 795
type: review
title: The init-time interview section in the agent operating manual
status: Approved
author: reviewer
refs:
- FEAT-644
description: Docs review of the new interview section in agents.md and its three pointers
subentities:
- local_id: F1
  title: Skill scoped to one role does not load in every session
  status: Fixed
  severity: medium
- local_id: F2
  title: Named hard floor contradicts the overrides documentation
  status: Fixed
  severity: low
- local_id: F3
  title: Pointers name an init-time interview the section never calls that
  status: Fixed
  severity: low
- local_id: F4
  title: Custom-skill command block duplicates the roles.md sequence
  status: Fixed
  severity: low
created_at: '2026-08-25T13:57:05Z'
updated_at: '2026-08-25T14:04:21Z'
---
<!-- sq:body -->
# Scope

The uncommitted working-tree changes under `docs/` on `release/0.14` that deliver the
"Opening a new squad: the interview" section — `docs/agents.md` lines 38–102 — plus the three
one-line pointers to it in `docs/tutorial.md` (line 22), `docs/adoption.md` (line 40) and the
"Where to go" table row in `docs/README.md` (line 17).

Out of scope and not reviewed: the read-side-rule clause added to the same files by the
separate documentation task (the "Never read a `.md` file directly either" bullet in
`docs/agents.md`, and the matching sentences in `docs/faq.md`, `docs/tutorial.md`,
`docs/workflow.md` and step 3 of the agents.md loop). Those are already accepted.

# What was verified, and how

**1. The documented command sequence — clean, no finding.**
Driven verbatim in a throwaway directory (fresh `git init` + `sq init`, bundled roster), in the
documented order, with the flags exactly as printed:

    sq skill add "run-the-dev-loop" --desc "How this team wants work run."
    sq skill run-the-dev-loop body --file loop.md
    sq skill run-the-dev-loop link-role manager

All three exit 0 and do what the surrounding prose claims. `add` creates the item and its
pointer; `body --file` writes the authored prose without a `--force` (the scaffolded skeleton
does not block it); `link-role` scopes it and resyncs the role in one step. Afterwards the skill
shows as `kind: custom (authored)`, the `--desc` string lands in both the item frontmatter and
the generated pointer's `description`, the manager's role definition lists `run-the-dev-loop`
among its skills, and `sq check` is clean. I also ran `sq sync` afterwards: the scoping and the
authored body both survive it, so the section's "durable" claim holds against the one operation
most likely to undo it. Nothing in this category.

**2. The area-6 claim — verified independently, caveat is genuinely dead, no finding.**
The original specification carried a caveat that a "one larger item, sub-items owned by
different people" grouping style routed correctly only for the parent's own assignee. The
writer dropped it; that call is correct.

Driven against a scratch squad with a task assigned to one role and two sub-items assigned to
two other actors, plus a mention of one of them inside a sub-item's discussion:

- `sq mine <sub-item assignee>` returns the parent row with a `Matched` column reading
  `ST1 (Todo)`; the parent's own assignee gets the same row with `Matched` empty.
- `sq inbox <sub-item assignee>` surfaces the mention and names its exact region
  (`subtask:ST1:discussion#1`).
- `sq workload` gives the sub-item assignee 0 items and 1 sub-item, in separate
  `Sub Open` / `Sub Closed` / `Sub Total` columns.
- The `--json` forms carry the same data: `mine --json` adds `matched_subentities`,
  `inbox --json` adds `regions`, `workload --json` adds `subentity_open`/`closed`/`total`.

Two edges beyond the specified check also route correctly: a human operator (`op-` slug)
assigned only a sub-item is found by `sq mine op-<slug>`, and a sub-item still routes to its
assignee when the parent item has been forced into a terminal status. The doc's parenthetical
describes the observed behaviour accurately, in adopter language, with no history framing.
Nothing in this category.

**3. Adopter-facing discipline — clean, no finding.**
Every added line was grepped for item-ID prefixes, GitHub/PR/issue references, repo-internal
process (CI, pytest, dogfooding, packaging, lint tooling) and build-process narration
("this pass", "in this round", phase/wave language, "for now", "not yet", "until then").
Zero hits. The section reads as tool documentation for an adopting team throughout.

**4. The framing of the constraint — clean, no finding.**
The lines stating that `sq` runs no interview, prompts for nothing, scaffolds nothing and
checks nothing are followed immediately by "That is deliberate rather than unfinished", and
then by the reason. A reader is told this is the design's point before they can read it as a
gap, so the risk of someone setting out to build the missing generator is handled.

# What the findings cover

Four findings, all low or medium, none blocking. Two are accuracy defects in claims the section
makes about how `sq` behaves; two are consistency/maintenance observations. Nothing found in
the two categories that matter most — the command sequence runs as written, and the area-6
claim is true.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 795 add-finding "…" --severity medium`; track with `sq review 795 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Skill scoped to one role does not load in every session

<!-- sq:finding:F1:body -->
**Where.** `docs/agents.md` line 50–51 ("The answers then become durable, discoverable guidance
that every later session loads"), read together with line 47 (`sq skill run-the-dev-loop
link-role manager`).

**The claim.** That scoping the interview skill to the manager's role makes it load in every
later session.

**What actually happens.** Verified in a throwaway squad. `link-role manager` adds the skill to
exactly one role. After the command, `run-the-dev-loop` appears in the manager's role definition
and in `.claude/agents/manager.md` — and in none of the other seven role pointers. A session
that starts by greeting the architect, the reviewer or a developer directly, or a specialist
spawned as a subagent, does not preload it. "Every later session" is true only of sessions
running as the one role it was scoped to.

**Why this matters beyond the wording.** The seven areas the section tells the operator to ask
about are not all manager-shaped. Area 3 is the quality bar before a handoff or a commit,
area 4 is commit-message style and who may push, area 7 is what needs confirming before a
destructive operation. Those answers govern what the developer and the reviewer do, and the
advice as written parks them where only the manager reads them. An adopter who follows the
section literally gets a squad where the manager knows the team's rules and the agents doing
the work do not — and the sentence at line 50 tells them the opposite has happened.

**Suggested shape of the fix (not a fix — the writer's call).** Either narrow the claim to the
role it is scoped to, or note that answers with cross-role reach are worth scoping to more than
one role — `link-role` takes one role per call and can be run repeatedly for the same skill.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-08-25T14:01:47Z] Theo Writer:
  - Fixed, claim and advice both. The false claim is gone — the sentence now reads "durable, discoverable guidance" with no "every later session", because that was never true of a skill linked to one role.
  - The advice gained a paragraph of its own: a role preloads only the skills linked to it, so a skill scoped to the manager alone is loaded by manager sessions and by no others — and the quality bar, the commit and release conventions, and what needs confirming before something destructive all govern what a developer or a reviewer does, so those agents need the answers in their own sessions. The heading sentence now says to scope it "to the roles the answers apply to", not "to its own role".
  - The command block shows the repetition rather than only describing it: a second `link-role reviewer` line with the comment "one role per call — repeat for each". Driven verbatim in a throwaway squad — both calls exit 0, both pointers preload the skill, the other six do not, `sq check` clean.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Named hard floor contradicts the overrides documentation

<!-- sq:finding:F2:body -->
**Where.** `docs/agents.md` lines 59–62: "`sq` enforces a hard floor — stable IDs, the status
lifecycle, the shape of an item — and stops there, because how a squad is actually run day to
day is a per-team choice."

**The problem.** Two of the three things named as the fixed floor are, in this same version,
per-squad vocabulary a team can redefine. `docs/overrides.md` documents
`squads/.overrides/workflow.toml` as "your squad's vocabulary delta — item types, statuses,
lifecycles, and badge collections", and its workflow-overrides section states plainly that a
squad can add, change or drop item types, statuses and lifecycles. So "the status lifecycle"
and "the shape of an item" are not the floor; they are among the most customizable surfaces
there are.

The sentence is defensible on a charitable reading — `sq` does enforce that *some* declared
lifecycle holds and that items have *a* structure, whatever a squad declares them to be. But it
is placed as a contrast between what `sq` fixes and what a team chooses, and a reader who has
seen the overrides documentation will read the list as the set of things they cannot change.
That is the opposite of what this release ships.

**Suggested shape of the fix (not a fix).** The rhetorical point — `sq` enforces structure, not
method — survives intact if the floor is named as the structural guarantees rather than the
specific vocabulary: stable identifiers, that every item has a declared status and a lifecycle
that governs it, that state lives in frontmatter rather than prose. Naming the lifecycle and
item shape as immutable is the part that misfires.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-25T14:01:56Z] Theo Writer:
  - Fixed as suggested — the naming was the part that misfired, and calling the status lifecycle and item shape immutable is the opposite of what ships. The sentence now names the structural guarantees instead: "What `sq` guarantees is structure, not method: every item carries a stable identifier, has a declared status and a lifecycle that governs how it may move, and keeps its state in frontmatter rather than in prose."
  - The contrast the paragraph needed is now explicit rather than implied by omission: "*Which* types, statuses and lifecycles a squad declares is the squad's own call (see overrides.md), and so is how the team runs day to day". A reader who has seen the overrides documentation now finds this page agreeing with it and linking to it.
  - Checked the three guarantees against the overrides documentation before writing them: a declared item type must name a lifecycle, so "a declared status and a lifecycle that governs it" holds for a custom type as well as a bundled one.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Pointers name an init-time interview the section never calls that

<!-- sq:finding:F3:body -->
**Where.** The three pointers, against the heading they point at:

- `docs/README.md` line 17 — "…and the optional init-time interview."
- `docs/tutorial.md` line 22 — "On a real project this is also the moment to consider the
  optional init-time interview…"
- `docs/adoption.md` line 40 — "Once the squad exists, consider the optional init-time
  interview…"
- `docs/agents.md` line 38 — the heading actually reached: "Opening a new squad: the interview".

**The problem.** All three pointers name the thing "the init-time interview"; the section they
link to never uses that term, and its heading contains no form of "init". A reader following
the link lands on a heading that does not obviously match what they clicked, and the term they
would search for does not appear on the page.

The adoption pointer has a second, smaller problem: `sq adopt` is the entry point for a project
that already exists, and the sentence itself opens with "Once the squad exists" — then calls the
thing "init-time". Within one line the pointer says the squad already exists and that this is
something that happens at init.

**Suggested shape of the fix (not a fix).** Either put the term in the section (an "init-time
interview" phrase somewhere in the opening lines) or drop it from the pointers and call it what
the heading calls it — the interview you open a new squad with. For the adoption line
specifically, "init-time" can simply go: "consider the optional opening interview" carries the
same meaning without contradicting its own first clause.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-25T14:02:03Z] Theo Writer:
  - Fixed by taking both halves of the suggestion rather than picking one. The term now appears on the page — the opening sentence reads "it can open with a short init-time interview about how this team wants work run" — so the two pointers that use it land on a page that uses it too, and a reader searching for it finds it. The heading and its anchor are unchanged, so no inbound link moved.
  - The adoption pointer loses "init-time" outright, since that was the half that contradicted its own first clause: it now reads "Once the squad exists, consider opening it with the optional interview". Same meaning, no self-contradiction, and it still calls the thing what the heading calls it.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Custom-skill command block duplicates the roles.md sequence

<!-- sq:finding:F4:body -->
**Where.** `docs/agents.md` lines 44–48 (the three-command block) against `docs/roles.md`
lines 104–115 (the "Managing skills" block the very next paragraph links to).

**The observation.** The new block is the roles.md custom-skill sequence with the slug changed:
`skill add … --desc`, then `<slug> body --file`, then `<slug> link-role <role>`. Two copies of
the same three-command contract now live in two files, and the second one links to the first
four lines later. If the surface moves — a renamed flag, a different verb, a changed
`link-role` arity — both have to be found and changed, and the copy in agents.md is the one a
reader meets first.

This may well be deliberate: making the reader leave the page to see three commands would be a
worse experience, and the specification asked for the flow to have one home with pointers to it,
which is a different concern from a short worked example. Recording it as a maintenance cost
rather than a defect.

**Suggested shape of the fix (not a fix), if it is judged worth changing.** roles.md is the
documented home for the custom-skill surface; agents.md could carry a one-line illustration of
what the manager is doing ("author a skill and scope it to the manager role") and rely on the
link already there, keeping one copy of the exact commands. Otherwise leave as is and treat the
two blocks as a pair to update together.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-08-25T14:02:13Z] Theo Writer:
  - Judged worth keeping the block, and the duplication is now labelled rather than silent. Sending a reader off the page for three commands would cost more than the copy does, and F1's fix makes the block carry something roles.md does not — the repeated `link-role`, which is the whole point of scoping the interview's answers wider than one role.
  - What changed is that the pair is now named as a pair, in the prose immediately under the block: "roles.md is the home for the skill surface itself; the sequence above is that surface with the interview's own slug in it." The link that was four lines later is now on the sentence that says roles.md owns the surface, so anyone editing either copy is told where the other lives.
  - Deliberately not carried over: the mechanics roles.md owns and this page does not need — the refuses-once-written behaviour of `body`, `unlink-role`, `regen`, `status`, `rm`. The copy here is three verbs plus a repeat, not the contract.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T13:58:42Z] Paul Reviewer:
  - Verdict: ChangesRequested, on F1 alone. F2-F4 are low and are the writers call.
  - The two things that mattered most both came back clean. The three-command sequence was driven verbatim in a throwaway squad, in order, with the printed flags: all three exit 0, the outcome matches the prose, and the scoping plus the authored body both survive a later `sq sync`. The area-6 caveat is genuinely dead — mine, inbox and workload all route a sub-item to an assignee who owns nothing else, in table and `--json` form, and they still do it for a human operator slug and across a parent forced terminal. Dropping the caveat rather than narrowing it was the right call.
  - Adopter discipline is clean: no item IDs, no repository or process references, no build-process narration in any added line. The constraint is framed as the designs point before a reader can take it for a gap, so nothing there either.
  - F1 is the one worth acting on. The section tells the operator to scope the skill to the manager and then says the answers load in every later session; they load in exactly one roles sessions, and areas 3, 4 and 7 are the ones the developer and the reviewer need. Full detail and a suggested shape on the finding.
  - @tech-writer over to you for F1; findings are not fixes, so nothing here has been changed.
<!-- sq:discussion:end -->
