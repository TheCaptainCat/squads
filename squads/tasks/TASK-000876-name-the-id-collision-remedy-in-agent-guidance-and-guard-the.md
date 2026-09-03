---
id: TASK-876
sequence_id: 876
type: task
title: Name the id-collision remedy in agent guidance and guard the class
status: Done
author: tech-lead
assignee: python-dev
priority: high
refs:
- BUG-872:fixes
description: Two shipped commands are named in no agent-facing surface; add the collision
  condition and its remedy to the carriers, give the repair flag help text, and guard
  that no future command can be invisible.
subentities:
- local_id: ST1
  title: Name the collision condition and both remedy verbs
  status: Done
  assignee: python-dev
- local_id: ST2
  title: Give the repair renumber flag help text
  status: Done
  assignee: python-dev
- local_id: ST3
  title: Guard the class with a documented exemption list
  status: Done
  assignee: python-dev
created_at: '2026-09-02T09:58:56Z'
updated_at: '2026-09-02T14:01:32Z'
---
<!-- sq:body -->
## What is wrong

The `.squads.json` counter is per-tree, so a worktree, a branch, or an isolated scratch
index allocates from its own sequence. When those trees meet, two items carry the same
number. `sq` ships a remedy for exactly this — `sq repair --renumber` after a merge,
`sq renumber` before one — and no surface an agent reads names either.

Measured: of the shipped top-level commands, all but `renumber` and `ui` appear somewhere
in the union of the agent-facing surfaces — the `squads` skill, the nine `sq-<type>`
skills, `sq-memory`, `greeting` and the `CLAUDE.md` managed section. `ui` is defensibly
absent; an agent should not be launching an interactive TUI. `renumber` is not, because
it is the remedy for a condition agents actually cause. It is named in eight human-facing
files and in none of the thirteen agent-facing ones.

It has already cost a hand recovery: two trees allocated the same number, and the agent
recreated the item by hand because it did not know the command existed.

One asymmetry compounds it: `sq repair --help` lists `--renumber` as a bare flag with no
help text at all, so even an agent who reads that help learns nothing about what it does.

## The ruling: fix the instance *and* close the class

Adding `renumber` to a skill fixes this instance and leaves the class untouched — the
next command shipped is equally invisible. A guard closes the class. Both ship here.

The objection to a guard is that it forces a judgement about commands that legitimately
should not appear, and `ui` is the live example. That objection does not survive contact
with this repository, which has already solved that exact problem three separate times: a
lockstep guard over the live command table with a hand-maintained constant, an
allowlist of illustrative types in the documented-commands guard, and the vulture
`ignore_names` list. In each, the exception is one entry carrying a one-line reason, and
the assertion runs in **both** directions so a stale exemption fails too. `ui` is one
such entry. It is not an obstacle; it is the guard working.

The distinction from the earlier guidance bug, which was ruled documentation-only, is
real and worth stating so this ruling is not read as a reversal. There, the condition was
an agent *choosing* to open a file instead of running a command — a property of that
agent's tool use, outside any tracked artifact, unobservable in principle. Here, the
condition is that a name present in one artifact squads generates is absent from another
artifact squads generates. Both are in-process, static, and fully enumerable. That is
the line, and an existing guard already sits on it from the other side: it walks every
command cited in the bundled docs and resolves it against the live command tree. This
work is the missing inverse direction of that same guard — the docs cannot cite a command
that does not exist, and now a command cannot exist uncited by agent guidance.

A guard that only ever fires on a name nobody wrote guidance for is also cheap in the way
that matters: it costs nothing until someone ships a command, and at that moment it asks
the one question nobody remembered to ask.

## Implementation trap, measured — read this before building the guard

The count of 38 commands comes from the rendered `sq --help`. The live Typer table holds
**52**, because item-type aliases are registered as commands. A guard built naively from
`typer.main.get_command(app).commands` will flag all fourteen aliases as missing from
guidance and be useless.

De-alias against the bundled spec — subtract every declared type name and every declared
alias — which is exactly what the existing lockstep guard over the live command table
already does. Reuse that derivation rather than writing a second one; 52 minus the 14
declared aliases is 38, verified.

Two more properties of the corpus the guard must respect:

- The generated `sq-<type>` skill text is **roster-dependent** (a has-dev gate changes
  what renders). Pin the roster the way the existing skill-body goldens do — the eight
  bundled roles plus one dev — or the guard's corpus shifts under it.
- A zero hit is the one search result that never proves the search worked. The original
  measurement returned zero for *every* command, including obvious positives, because a
  byte-wise strip mangled multi-byte box-drawing characters. Validate the matcher against
  known positives before letting any zero stand. Strip ANSI, and note the harness sets
  `FORCE_COLOR`, so a render that looks clean interactively may not be.

## Carriers

The carrier set and the regeneration path are already established by the earlier
guidance fix; reuse them rather than re-deriving. The bundled templates that carry
agent-facing guidance are the `CLAUDE.md` managed section, the `squads` skill body, the
per-item-type skill body, the shared workflow cheatsheet partial, and the role body. The
two `.claude` pointer templates are **not** carriers — a pointer holds only identity, the
slug-bound startup commands, and the command that renders the full definition, and a
maintenance verb is none of those. That was decided, with reasons, on the earlier fix.
Do not re-open it.

Where the new text lands is a judgement, not a broadcast. This is a maintenance remedy
for a merge-time condition, not something every agent needs on every turn. The workflow
cheatsheet and the `squads` skill are the natural homes, next to the neighbouring
maintenance verbs which are all already present. Do not add it to all five just because
five carriers exist.

The text must name the **condition** before the remedy. An agent that meets two items
with the same number does not know that state has a name; a bare command listing next to
`repair` will not connect. One clause on the condition — separate trees allocate from
separate counters, so a merge can produce two items with one number — and then the two
verbs and which is for before a merge and which for after.

## Register

Agent-facing generated text must not name a bundled type, status or role literal — a
meta guard enforces this, and it will fail the build if the new wording hardcodes
vocabulary. Keep the phrasing vocabulary-neutral.

## Coordinator's step, not the implementer's

The agent-facing surfaces render from bundled templates, and the templates and the
bundled workflow spec are covered by the template manifest. A change here needs a
manifest regeneration, and **that step belongs to the coordinator, not to whoever
implements this.** Do not run the manifest generator, and do not run the version-bump
script. Regenerating a manifest against the wrong version corrupts a released version's
recorded hashes, and the ordering call that prevents it is a release-level decision.

Goldens are different and are yours: the managed-section and cheatsheet goldens and the
generated skill-body goldens move with these templates. Regenerate them, never hand-edit
them, then read the diff — a golden refresh touching lines you did not intend to change
means the edit went wider than planned. Say in your handoff that the manifest is
outstanding, so the coordinator does not have to discover it.

## Explicitly deferred, with the reason

Nothing detects a collision either: there is no uniqueness rule over ids or sequence
numbers, and the index rebuild reports a count without saying whether a number arrived
twice. That is a third gap and it is **not** in this task.

The reason it is deferred rather than folded in: a duplicate number cannot exist inside
one index, so the condition is only observable at the moment two trees' markdown lands in
one folder — which makes the corpus-walking rebuild, not the per-item validator catalog,
its natural home. Deciding what the rebuild should then do (refuse, report, or shift the
collision itself) is a design call on the integrity core, and a validator-catalog
decision is currently open that such a member would have to fit into. It needs its own
item and the architect's call. Making the remedy discoverable does not depend on it, and
should not wait for it.

## Acceptance

- The condition and both remedy verbs appear in the agent-facing surfaces, phrased so an
  agent meeting a duplicate number can recognise the state and reach the right verb.
  Verified against the **rendered** surfaces, not the template source.
- `sq repair --renumber` has help text that says what it does and distinguishes it from
  the separate pre-merge verb.
- A guard asserts that every top-level command, after de-aliasing, is named in at least
  one rendered agent-facing surface, with a documented exemption list. It asserts in both
  directions: an unexempted absent command fails, and an exemption for a command that is
  now present fails as stale.
- The exemption list holds `ui`, with a one-line reason.
- **The guard fails before the guidance edit.** Land the guard first, watch it fail
  naming `renumber`, then land the guidance and watch it pass. Report both. Then remove
  `ui` from the exemption list and confirm it fails again — that proves the exemption is
  load-bearing and not decoration.
- The goldens that move with these templates are regenerated, not hand-edited, and the
  diff contains only the intended lines.
- The generated-text vocabulary guard still passes.
- `uv run --all-extras pytest`, `ruff check .`, `ruff format --check .`, `pyright` and
  `sq check` all clean. `--all-extras` on each.
- The manifest regeneration is **not** performed and is flagged in the handoff.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 876 add-subtask "<title>"`; track with `sq task 876 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Name the collision condition and both remedy verbs

<!-- sq:subtask:ST1:body -->
Add the missing guidance to the bundled templates that carry agent-facing text.

Name the **condition** before the remedy. An agent that meets two items with the same
number does not know that state has a name, so a bare verb listed next to the other
maintenance commands will not connect. One clause on the condition — separate trees
allocate from separate counters, so a merge can produce two items carrying one number —
then the two verbs, and which one is for before a merge and which for after.

Placement is a judgement, not a broadcast. This is a merge-time maintenance remedy, not
something every agent needs on every turn. The workflow cheatsheet and the main skill are
the natural homes, alongside the neighbouring maintenance verbs which are all already
present. Do not add it to every carrier just because several exist.

The two pointer templates are not carriers and stay as they are — a pointer holds
identity, the slug-bound startup commands, and the command that renders the full
definition, and a maintenance verb is none of those. That was decided with reasons on the
earlier guidance fix of this same shape; do not re-open it.

Keep the wording vocabulary-neutral: a meta guard forbids generated agent text from
naming a bundled type, status or role literal, and it will fail the build.

Done when: the condition and both verbs appear in the rendered surfaces — verified by
rendering them, not by reading the template source — and the vocabulary guard still
passes.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-09-02T12:15:29Z] Elias Python:
  - Landed in one carrier: `_rendering/templates/workflow_static.md.j2`, a new "Duplicate numbers across trees" section placed immediately after the existing "Sequence gaps are sanctioned" paragraph — the nearest neighbour that already talks about sequence numbers, the counter high-water mark, `sq check` and `sq repair`.
    
    One edit reaches both homes the scope named: `workflow_static.md.j2` is included by `workflow.md.j2`, which is included by `agents/squads_skill.md.j2`. So the clause renders into the `squads` skill body, the AGENTS.md managed section and `sq workflow` alike. `claude/claude_section.md.j2` does *not* include the cheatsheet, so the CLAUDE.md managed section is untouched — which matches the "placement is a judgement, not a broadcast" instruction. The two pointer templates were not opened.
    
    The condition is named before the remedy, as specified: the counter lives in each tree's own index, so a worktree/branch/second clone allocates from its own sequence; two trees hand out the same number and a merge lands both. It then gives the recognition signal (the same sequence number on two items, often under two prefixes) and the two verbs with which side of the merge each is for.
    
    Both invocations were read off the code before being written, not paraphrased from the bug: `sq renumber --from <n> --onto <other-counter>` (`_offset_plan` computes `delta = max(onto, counter) + 1 - from_seq`, so "a range above both counters" is exact) and `sq repair --renumber` (`_renumber_plan` keeps the first record per number and mints fresh ones for the rest; `_apply_remap` rewrites refs, renames files, resyncs — hence "refs, parent links, prose mentions and filenames").
    
    Verified on the rendered surfaces, not the template source: the new section appears in `tests/goldens/workflow_cheatsheet.txt`, `workflow_cheatsheet_raw.txt` and `agents_md_section.txt` after regeneration, and the class guard on ST3 — which renders the twelve skill bodies itself — flips from failing on `renumber` to passing.
    
    Register held: the wording names no bundled type, status or role literal. `tests/meta/test_generated_agent_text_names_no_bundled_vocabulary.py` passes, including its bare-`task` scan over this template.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Give the repair renumber flag help text

<!-- sq:subtask:ST2:body -->
The renumber flag on the repair command is declared with no help text at all, so it
renders as a bare flag. An agent who does reach that help learns nothing about what the
flag does or when to use it.

Give it help text that says what it does and distinguishes it from the separate,
deliberately-run pre-merge verb. That verb's own help already draws the distinction well
and is the right source for the wording; the point here is that the reader who found the
flag first should not have to already know the other command exists.

This is the one part of this task that touches command code rather than templates. Keep
it to the flag's help string. No behaviour change, no new option, no signature change.

Done when: the repair help renders a description for the flag, and it names the
distinction between fixing a collision after a merge and shifting a range before one.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-09-02T12:15:40Z] Elias Python:
  - Confirmed the defect first — `sq repair --help` rendered `--renumber` with an empty description column, because `_cli/_main.py` declared it as `typer.Option(False, "--renumber")` with no `help=`.
    
    Help text now reads:
    
    > Also resolve duplicate sequence numbers before rebuilding: where two trees' merged files both claim a number, keep one item and mint a fresh number for the rest, rewriting every reference to them. This is the after-the-fact fixer; `sq renumber` shifts a range deliberately BEFORE a merge so no collision happens.
    
    It draws the distinction the other verb's own help already draws, from the reader's side: someone who found the flag first is told the other command exists and what separates them (after the collision vs. before the merge), without having to already know it.
    
    Scope held to the flag's help string — no behaviour change, no new option, no signature change. The only other edit to the function is the reformatting `ruff format` requires once the option no longer fits on one line.
    
    Rendered and read back: `sq repair --help` now shows a five-line description for `--renumber`.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Guard the class with a documented exemption list

<!-- sq:subtask:ST3:body -->
The class fix: a guard asserting that every top-level command, after de-aliasing, is
named in at least one rendered agent-facing surface.

Build it in the shape this repository already uses three times over for exactly this
problem — a hand-maintained exemption list, each entry carrying a one-line reason, and an
assertion that runs in **both** directions so that an unexempted absent command fails and
an exemption for a now-present command fails as stale. The existing lockstep guard over
the live command table is the closest model and should be read first.

Two measured traps.

**De-alias, or the guard is useless.** The live command table holds 52 entries; the
rendered help shows 38. The difference is fourteen item-type aliases registered as
commands. Subtract every declared type name and alias from the bundled spec — the
existing lockstep guard already does precisely this derivation, so reuse it rather than
writing a second one. Verified: 52 minus 14 is 38.

**Pin the roster.** The generated per-type skill text is roster-dependent through a
has-dev gate, so an unpinned corpus shifts under the guard. Pin it the way the existing
skill-body goldens do — the bundled roles plus one dev.

And validate the matcher against known positives before trusting any zero. The original
measurement returned zero for every command including obvious positives, because a
byte-wise strip mangled multi-byte box-drawing characters; a zero is the one result that
never proves the search worked. Strip ANSI properly, and note the harness sets a colour
variable that can make a render look clean when it is not.

The exemption list starts with the interactive TUI command, on the grounds that an agent
should not be launching one.

Done when: the guard fails naming the missing verb before the guidance lands and passes
after; removing the TUI entry from the exemption list makes it fail again, proving the
entry is load-bearing rather than decoration; and both directions are asserted.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-09-02T12:16:01Z] Elias Python:
  - Guard: `tests/meta/test_every_cli_command_is_named_in_agent_guidance.py`, five assertions.
    
    **Derivation.** The live Typer table (52 entries) minus every alias the bundled spec declares (14) = 38. That is the same de-aliasing the `RESERVED_CLI_VERBS` lockstep guard performs, with one deliberate difference recorded in the docstring: that guard also subtracts each type's canonical *name*, because its subject is what a declared type may not collide with; this one keeps them, because `sq bug` and `sq role` are commands an agent is as entitled to find named as `sq check`. The derivation is repeated rather than imported — `tests/` has no `__init__.py` at its root and this suite has no `from tests....` precedent.
    
    `test_the_command_inventory_is_de_aliased` proves the subtraction happened instead of leaving it to be inferred: the raw table is strictly larger by exactly the alias count, no declared alias survives, and the canonical names those aliases stand for do.
    
    **Corpus.** The twelve generated skill bodies (`squads`, `greeting`, `sq-memory`, nine `sq-<type>`), rendered in-process from the same templates the service renders at read time — including the real `_item_skill_role_sections`, so there is no mirror to drift — plus this repository's `CLAUDE.md` in full. Roster pinned to the eight bundled roles plus one developer, the fixture the skill-body goldens use, because the per-type text is roster-dependent through the has-dev gate.
    
    **Exemption list.** `_UNGUIDED_BY_DESIGN`, a name -> reason dict so the reason is code rather than a comment. One entry: `ui`, "an interactive full-screen TUI: an agent has no terminal to drive it and must not launch one."
    
    **Asserted in both directions, and each direction falsified by construction rather than asserted:**
    
    - absent-and-unexempted fails — before the ST1 edit the guard failed with exactly `['renumber']`;
    - a stale exemption fails — adding `check` (which the corpus does name) produced "exempts ['check'], but the agent-facing guidance now names them";
    - an exemption naming nothing real fails — adding `nosuchverb` produced "names non-existent command(s)";
    - the `ui` entry is load-bearing, not decoration — removing it made the guard fail with exactly `['ui']`, and it was restored;
    - the class itself is caught, not just this instance — registering a fresh command on the live app object in a scratch probe moved the unnamed set from `[]` to `['quarantine']`.
    
    **Zero-proof discipline.** `test_the_matcher_is_validated_against_known_positives` anchors the matcher on terms that must hit and one that must not, and the corpus fixture asserts no escape sequences survived (the harness sets `FORCE_COLOR`). This caught a real bug in my own first draft: `\b@mention\b` can never match, because `\b` before `@` demands a word character in front of it — the anchor was silently unmatchable and would have been read as a broken corpus. Anchors are now plain words.
    
    **Limit stated rather than overclaimed**, and it is in the docstring: matching is by *name*, case-insensitively and on word boundaries, so a command whose name is also ordinary English (`list`, `show`, `check`, `guide`) is credited by any prose use of that word. The guard proves a name is absent; it never proves the guidance around a present name is any good.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T10:02:48Z] Olivia Lead:
  - Scoped from BUG-872 and dispatchable. The ruling asked for is made and is in the body:
    the guidance edit and the class guard both ship here, and the exemption the guard forces
    a judgement on is one documented entry, in the shape this repository already uses three
    times.
    
    Sequence matters and is written into the acceptance: land the guard first and watch it
    fail naming the missing verb, then land the guidance and watch it pass, then pull the
    exemption entry and watch it fail again. A guard whose exemption list has never been
    shown to be load-bearing is decoration.
    
    Ownership note: this is one owner in one pass rather than a writer and a dev in the same
    tree, because the guard and the guidance have to land together — the guard fails the
    build without the guidance. The wording clause is short; have the writer read it before
    the goldens are regenerated rather than authoring it concurrently.
    
    Two things held back from the implementer on purpose. The template manifest regeneration
    is the coordinator's step, not theirs — regenerating against the wrong version corrupts a
    released version's recorded hashes, and the ordering call is release-level. Goldens are
    theirs and must be regenerated rather than hand-edited. Their handoff should state the
    manifest is outstanding so the coordinator does not have to discover it.
    
    @python-dev ready for dispatch. @tech-writer for a read of the new clause before the
    goldens are refreshed.
- [2026-09-02T12:17:18Z] Elias Python:
  - All three subtasks done. Sequence ran as the acceptance specified: guard first (failed with exactly `['renumber']`), then the guidance (passed), then the exemption pulled (failed with exactly `['ui']`, restored).
    
    **Files.** `src/squads/_rendering/templates/workflow_static.md.j2` (+21, the new "Duplicate numbers across trees" section); `src/squads/_cli/_main.py` (the `--renumber` help string, plus the reformat it forces); `tests/meta/test_every_cli_command_is_named_in_agent_guidance.py` (new, the guard); three regenerated goldens — `workflow_cheatsheet.txt`, `workflow_cheatsheet_raw.txt`, `agents_md_section.txt`, +21 identical lines each, no other line moved.
    
    **Manifest regeneration is OUTSTANDING and is the coordinator's step**, as instructed. A bundled template changed, so `tests/meta/test_override_manifest_and_stamp_freshness.py` fails 5 tests until `scripts/gen_template_manifest.py` (and the content-store seed) are re-run. I did not run either. The causal link is proven rather than assumed: reverting only the template edit takes that module to 35 passed, restoring it takes it back to 5 failed. Everything else is green — full suite `5 failed, 4499 passed, 8 skipped`, which is the 4499 baseline exactly (the 5 manifest tests moved out of the passing set, my 5 new guard tests moved in). `pyright` 0 errors, `ruff check` and `ruff format --check` clean, `sq check` clean.
    
    **One measured correction to the scope, and it matters for how the guard should be read.** The "36 of 38 commands appear, only `renumber` and `ui` missing" figure holds *only* because the measured corpus included this repository's `CLAUDE.md` in full — the hand-written contributor half above the managed markers, not just the section squads generates. Against squads' generated output alone (the twelve skill bodies plus the CLAUDE.md managed section) five further commands are named nowhere: `graph`, `import`, `init`, `migrate`, `override`. They are credited in the guard only by prose this repository happens to have written for its own contributors, which no adopting squad has.
    
    I built the guard on the measured corpus, so the exemption list is the single `ui` entry the ruling called for and nothing was invented. But that means a passing run certifies *this repository's* agent surfaces, not squads' generated surfaces in general — the docstring says so in those words. Whether an agent should be told about a bootstrap or an upgrade verb is a judgement nobody has made, and I did not make it. @tech-lead if that gap is worth its own item, it is yours to scope; I did not create one.
    
    **Nothing else in the brief proved wrong.** The de-alias trap was real and exactly as described (52 live, 14 aliases, 38 after), and a naive guard would indeed have flagged all fourteen. The `--renumber` flag really did render with an empty description. The zero-proof warning earned its keep on my own first draft: my known-positive anchor `@mention` used `\b@`, which can never match, so the anchor was silently unmatchable — precisely the failure mode the warning describes, found because the check was there.
    
    @reviewer for review. Ready apart from the manifest step.
- [2026-09-02T12:30:21Z] Olivia Lead:
  - Ruling on the corpus caveat you flagged, and thank you for writing it into the docstring
    rather than around it — the finding is right, and it is the kind that is only ever found by
    whoever built the thing.
    
    I re-measured before ruling rather than taking the handoff's numbers. Your five hold exactly:
    against the generated output alone (the twelve bodies plus the managed section, 8,041
    characters of it) `graph`, `import`, `init`, `migrate` and `override` are all zero, matcher
    validated on known positives first.
    
    **There is a sixth you missed, and it is the more interesting one.** `adopt` scores two hits
    in the managed section and both are the English verb — "adopt that agent", "not a persona to
    adopt", in the impersonation paragraph. The string `sq adopt` appears in no generated surface
    at all. Your docstring's stated limit is not hypothetical; it is already firing, on the same
    category the ruling is about. `sq sync`'s single hit is real but incidental — the
    "regenerated by `sq sync`" line every managed region carries.
    
    Ruling: four named, one exempt, corpus narrowed. Scoped as TASK-882, Ready, and it is a
    different defect from BUG-872 rather than the same one — that bug is one command being
    undiscoverable with a hand recovery to show for it; this is a gate certifying the wrong
    subject. Linked `related` both ways, not folded in.
    
    Nothing you built is being undone. The exemption list you shipped with one entry was the
    right call on the corpus you measured, and the falsification discipline you ran is the reason
    I can extend the list without re-proving the machinery.
    
    Two things I am not doing, deliberately. I am not tightening the matcher: I probed a stricter
    invocation-form match and it withdraws credit from four more commands whose names double as
    ordinary prose, each its own substantive question, and my probe's own regex was not validated
    against the real invocation forms — legislating off an unproven measurement is how the
    byte-strip trap happened the first time. And I am not reshaping the corpus into something
    derived from a fresh bootstrap, which would close the same gap one level up. Both are
    recorded as deferred on TASK-882 with reasons.
    
    Your manifest flag is noted and stands. TASK-882 lands before that regeneration on purpose,
    so one regeneration covers both template changes instead of two arriving in sequence.
    
    @python-dev TASK-882 is yours and is dispatchable. @reviewer this does not hold up the review
    of this task — nothing here reverses what landed.
<!-- sq:discussion:end -->
