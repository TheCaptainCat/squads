---
id: TASK-855
sequence_id: 855
type: task
title: Correct false and build-narrating prose in shipped docstrings
status: Ready
author: tech-lead
priority: medium
refs:
- REV-854:addresses
- MILE-836:targets
description: Docstrings and comments that narrate how the code was built, or assert
  something falsifiable that is no longer true — rewritten in the present tense, prose
  only, no behaviour change
subentities:
- local_id: ST1
  title: Rewrite the agents_md backend prose in the present tense
  status: Todo
- local_id: ST2
  title: Restate the RoleView and validators reasoning as rules
  status: Todo
- local_id: ST3
  title: State adopt's seeding invariant instead of a former gap
  status: Todo
- local_id: ST4
  title: Name what the five flagged test modules cover
  status: Todo
- local_id: ST5
  title: Correct the runner roster projection's false equivalence
  status: Todo
- local_id: ST6
  title: Replace the carry-set rationale's non-existent command
  status: Todo
- local_id: ST7
  title: Restate the dev-role skew exemption's reason in the present tense
  status: Todo
created_at: '2026-09-01T11:22:08Z'
updated_at: '2026-09-01T11:28:06Z'
---
<!-- sq:body -->
## Scope

Prose only. Docstrings, module headers and comments across the source and test tree that either
**narrate how the code was built** rather than describing what it does, or **assert something
falsifiable that is no longer true**. No behaviour changes, no renames, no test logic changes, no
new tests.

Two inputs converge on one surface. A hygiene sweep over the most recent commit range cleaned that
range and flagged nine files whose narration **predates** it and so went untouched. Separately, a
review found two docstrings whose stated premise is false: one describes a projection as matching
a service method that has since diverged from it, and one cites a CLI command that does not exist.
Both classes are the same defect — durable prose the reader cannot trust — and both are corrected
in one pass, by one developer, behind one gate run.

## The standard

**Delivered prose describes the thing, not the pass that produced it.** No "used to be", "a prior
version", "this release", "previously", "before this widening", "the finding this closes", no
phase/round/wave/increment language, no reference to another agent's work or to a ticket.

**Rewrites, not deletions.** Almost every flagged passage is carrying real reasoning — why a field
is declared on the view rather than recovered from rendered text, why a check is warn and not
error, why a cleanup is opportunistic. That reasoning is the valuable part and it survives; what
goes is the framing that dates it. State the constraint in the present tense, as a property of the
code, and the reader gets the same protection without needing to know what the code used to do.

The test: could a reader who has never seen this repository's history act correctly on this
sentence? If the sentence only makes sense to someone who watched the change land, rewrite it.

**No item IDs anywhere.** Not in a docstring, not in a comment, not in a test name. The ticket
pointer belongs on the item, not in the source.

**A `# fmt: skip`, a `noqa`, an allowlist entry and a guard's own justification are load-bearing
and stay** — including the reasons they exist. Those are constraints on future edits, not history.

## Acceptance

- Every passage named in the subtasks below is rewritten in the present tense, describing current
  behaviour and the constraint it protects, with no build narration and no reference to a prior
  state of the code.
- Every load-bearing reason survives the rewrite. For each rewritten passage, the reason it
  existed is still findable in the new text — a passage whose only content was narration is the
  one case that may shrink to nothing, and that case must be named in the handoff.
- The two false claims are corrected against the tree as it is now, each verified before the
  rewrite is written rather than after.
- No behaviour change: `git diff` touches only docstrings, comments and module headers.
- No sq item ID appears in any touched file.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean, and `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 855 add-subtask "<title>"`; track with `sq task 855 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Rewrite the agents_md backend prose in the present tense

<!-- sq:subtask:ST1:body -->
`src/squads/_backends/_agents_md/_backend.py` — three passages, all narrating a staging-file
removal rather than describing the backend.

**Module docstring.** Half of it is the history of a prior version that staged one file per
role/skill under `.agents_md/roles/` and `.agents_md/skills/`, and the announcement that those
files are gone. What the reader actually needs, in the present tense:

- `write_managed` compiles the whole file — roster, workflow cheatsheet, per-role
  mission/responsibilities — entirely from the `RoleView`s/`OperatorView`s it is passed;
- `generate_role_entry`/`generate_skill_entry` write nothing; they exist to satisfy the
  `AgentBackend` ABC's per-entry method contract, which this backend has no per-entry file to
  back;
- both, and `remove_artifacts`, opportunistically delete a leftover `.agents_md/` file for the
  role or skill they are handed, so a squad carrying leftovers from an older layout empties out
  over its next `sq sync`;
- only a leftover whose owning role or skill was removed outright survives, because nothing in the
  roster sweep visits it — `candidate_orphans` reports that one on the next `sq adopt`.

That is the whole contract, and none of it needs a "prior version".

**`write_managed`'s docstring**, second paragraph. "They used to be: `RoleView` carried no
`mission`, so this method recovered it by matching the literal `**Mission:**` prefix…" The
reasoning is genuinely load-bearing — it is the argument for why these fields are declared on the
view instead of scraped back out of generated markdown — but its home is `RoleView`, where the
declaration is (see the sibling subtask). Here, state the invariant: every role field rendered
into AGENTS.md comes from the `RoleView` the service passes in, never from generated text this
backend produced a step earlier.

**`generate_role_entry`'s docstring.** "the materialise half of this release's staging-file
removal" dates the sentence. The property is that materialising and withdrawing a roster entry
delete a leftover file the same way, so a live role's leftover disappears exactly as fast as a
retired one's — say that, and keep the note that `item`/`ctx.resolved_skills_for` are unused
because nothing here renders a role's skills.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Restate the RoleView and validators reasoning as rules

<!-- sq:subtask:ST2:body -->
The twin passage, in the two files that carry the other half of the same reasoning.

**`src/squads/_backends/_base.py` — `RoleView`'s docstring.** `mission` and `responsibilities`
are justified by recounting that without them the AGENTS.md backend recovered the mission by
string-matching a `**Mission:**` line out of markdown it had generated itself, that relabelling
the line silently emptied every mission, and that `responsibilities` "had never once rendered".

This is the passage most worth rewriting rather than cutting: the rule it protects is real and it
constrains future edits. State it as a rule. A view field is the declaration; generated text is
output, never an input. A backend that recovers a declaration by parsing its own rendered markdown
makes a template's formatting the carrier of that declaration, so relabelling a line silently
empties a field with nothing reporting it — which is why every role field a backend renders is
carried here explicitly. Present tense, no incident.

**`src/squads/_services/_validators.py` — four passages.**

- Module header: "the hardcoded `_check_*` methods that used to compute this are retired from
  `_maintenance.py`". The claim worth keeping is that this engine is the **sole** source of
  `sq check`'s per-item/squad-global issues and of the create/update fail-closed gate. Say that
  without the retirement note.
- `_backend_reconciled`'s docstring: "It used to be computed here, unconfirmed, until making it
  roster- (and therefore index-) derived turned it cross-source." The durable content is that a
  per-entry roster pointer is a cross-source claim and therefore needs the confirm round, while
  this rule reads only config and disk and therefore does not. That distinction is the reason;
  where the code used to live is not.
- The per-entry pointer rule's "not for the reason once written here… before this widening…"
  paragraph. The honest reason survives whole — a per-entry pointer going untracked while the
  top-level files stay tracked was invisible to `sq check` altogether, and warn is what keeps that
  shape's exit code unchanged rather than adding a new error — but it can be stated without
  "before this widening" and without correcting a sentence no longer present.
- `backend_entry_drift`'s docstring already reads correctly on the guard question; check it for
  the same framing while the file is open, and leave it alone if it is clean.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — State adopt's seeding invariant instead of a former gap

<!-- sq:subtask:ST3:body -->
`src/squads/_services/_service.py`, in `adopt`'s seeding step: the comment reads "Mirrors
`init()`'s seeding step — adopt is the other path that can create a squad's config, and **was
previously the worse of the two gaps**: it seeded no skill items at all (neither bundled nor
custom), leaving every generated skill body untracked until the first `sq sync`."

The reason to keep is the invariant: `adopt` is the other path that can create a squad's config,
so it must seed both bundled and custom skill items exactly as `init` does — otherwise a generated
skill body is untracked until the first `sq sync`. That is a constraint on anyone editing either
path. The comparative ranking of two historical gaps is not.

While in this file, check the surrounding `adopt`/`init` comments for the same shape and correct
any other passage that describes a former gap rather than the rule that closes it.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Name what the five flagged test modules cover

<!-- sq:subtask:ST4:body -->
Five test modules whose docstrings and comments describe the work that produced them rather than
the behaviour they pin. A test's docstring is read by whoever it fails in front of, months later,
with none of that context.

- **`tests/service/test_frontmatter_skew_guard.py`** — the heaviest. "Reproduces the finding this
  task closes end to end", "The second, broader trigger named in the finding", "the first one used
  to be the opposite". Each should name the *shape* it covers: a faulted index commit during a
  mutation; a role catalog gaining a field so the merge reaches a key the index has not seen. The
  fact that a property used to be the opposite is exactly the sentence that will confuse the next
  reader, who has no way to tell which is current.
- **`tests/integration/test_new_slug_validation_narrows_to_the_undecidable_dev_shape.py`** — "The
  half of the finding that the stored-fact-first fix actually closes". Name the half by what it
  is: the slug shapes that become decidable once the stored fact is read first.
- **`tests/service/test_operator_named_roles_survive_sync.py`** — the module docstring frames
  itself against another test file and against "exactly the shape that shipped with this defect",
  and enumerates "two structural causes [that] had to be fixed together". The two causes are worth
  keeping as a statement of what must hold — the caller supplies a merge base for a non-dev role,
  and the resolver honours the base it is given — but as invariants this file pins, not as a
  repair story. The comment at the sharpest case ("The sharpest regression: …") and the
  `# regression:` note near the end want the same treatment: say what the case is.
- **`tests/unit/test_validators_assignment_surface.py`** — the docstring is otherwise clean but
  routes the reader to "the routing-task parity tests in `tests/service/`". "Routing-task" names a
  work item, not a behaviour. Name the tests by what they cover.
- **`tests/integration/test_workflow_override_service_integration.py`** — lightest of the five;
  the flagged passages are near the badge-family and index-untouched comments. Read them in place
  and correct only what narrates; leave what describes.

Do not rename any test function or module in this subtask — a rename is a separate concern and
would obscure the prose diff. Where a name itself narrates, note it in the handoff instead.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Correct the runner roster projection's false equivalence

<!-- sq:subtask:ST5:body -->
`src/squads/_migrations/_v0_11_to_v0_14.py` — `_live_roster`'s comment describes the projection as
"the same projection `Service.roster` applies, reproduced locally". That was true when written and
is now false: `Service.roster` resolves each role through the catalog, and this local copy still
reads the `extra` mirror.

The divergence is real and has a visible consequence. This projection is handed to the backend's
`write_managed` — the same method `sync` calls with the resolved list — so on a squad carrying a
project role override the mirror has not caught up with, the managed region `sq migrate up` writes
and the one the very next `sq sync` writes differ. Driven: the runner's projection yields the
bundled title while `sq sync` yields the override.

**Prose only. The projection is not to be taught to resolve.** Its locality is deliberate —
`_services` imports the migration registry, so calling `Service` from a runner is a real import
cycle — and a runner is frozen against the corpus vocabulary of the version it transforms, which
still carries the mirror. The correct outcome is a comment a reader can trust, not a code change.

Rewrite it to say: this reads the stored `extra` mirror deliberately, because a runner is frozen
against the corpus it transforms and that corpus still carries the mirror; it is therefore **not**
the resolved projection `Service.roster` produces, and on a squad carrying an override the mirror
has not caught up with, the region this writes differs from the one `sq sync` writes; the
`MANUAL`'s instruction to run `sq sync` next is what closes that window.

Verify the divergence yourself on a scratch squad before writing the sentence — the point of the
subtask is a comment that is true, so it has to be checked, not copied.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Replace the carry-set rationale's non-existent command

<!-- sq:subtask:ST6:body -->
`src/squads/_roles/_resolver.py` — two docstrings cite a CLI command that does not exist, in the
one place a reader is most likely to go and run it.

At `role_base_from_item`: "`EXTRA_FIELDS["role"]` … also accepts
`title`/`mission`/`responsibilities`/`model`/`color` through `sq role <slug> update --set
<key>=<value>` — a real, shipped write path". At `dev_base_from_item`, the same claim in the
shorter form "reachable through the generic `sq <type> update --set` escape hatch too".

**Verified against the tree:** the role addressing group's verbs are `show`, `regen`, `rm`,
`set-default` and `status`. There is no `update`, and `sq role manager update --set color=magenta`
exits with `No such command 'update'`. The generic `update --set` surface is real for work-item
types — `sq milestone <n> update --set target_date=…` is in the bundled playbook — but it does not
reach a role through the CLI.

This matters more than a typo because the sentence is load-bearing: it is the distinction the
whole "dedicated verb, not the generic allowlist" rule is drawn against. A reader checking the
reasoning runs the command, gets `No such command`, and has to reconstruct which write path is
meant before they can judge whether the rule is right.

The **rule is unaffected** and must not be weakened: a generic `set_extra` write really is
converged by `_refresh_catalog_extra` on the next sync and really should not be carried in the
merge base; only `full_name` and `is_default` have dedicated verbs that make the stored value the
operator's lasting answer.

Fix the citation only. Name the write path that actually exists — the service seam that accepts
`set_extra`, and whichever CLI surface genuinely reaches it for a role item. **Establish that
surface by driving it before naming it**; do not substitute one unverified command for another.
If nothing on the CLI reaches a role's `extra` today, say that plainly: the generic surface exists
below the CLI, so the rule guards against a write path a caller can reach programmatically even
though no role verb exposes it.

Worth stating in the same breath, because a reader of this docstring will hit it: a `set_extra`
write on a role field lands in `extra`, reports success, and reaches no generated artifact,
because every generated surface now resolves through the catalog. That is a consequence of the
rule, not a defect — but it is silent, so it belongs wherever the generic `--set` escape hatch is
described.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Restate the dev-role skew exemption's reason in the present tense

<!-- sq:subtask:ST7:body -->
A tenth file, found while triaging the skew-guard finding and not on the original flagged list:
`src/squads/_itemfile.py`, `_exempt_extra_keys`'s docstring.

Its dev-role bullet opens: "A dev role (`extra.is_dev` truthy) gets none of it. **It once got a
narrower exemption of its own** — `extra.skills` alone, since the resolved-skills cache resynced
every role's `extra` this way, dev roles included — **but that cache and its writer are gone, and
nothing replaced them.**"

Everything after that framing is load-bearing and stays: `_refresh_catalog_extra` resolves a dev
role against a base built from the item's own stored identity, writes markdown first and mirrors
into the index inside the same transaction, so it introduces no permanent index lag and needs no
exemption on that account. Every field on a dev role is therefore an ordinary,
transaction-guarded field and must be compared like any other — and widening the exemption would
reopen the loss class it guards: interrupt a dev role's `--set model=haiku`, edit it through any
other seam, and the stale index-loaded value silently overwrites the committed one.

State it as the rule, in the present tense. A retired cache is not why a dev role gets no
exemption; the absence of any out-of-transaction writer for its fields is.

**One ordering caveat, and it is why this subtask is last.** This same docstring's *substance* is
under an open architect question — whether the exemption is still justified at all once the role
mirror is stripped, and whether `is_default` should be excluded from it. If that ruling lands
first and rewrites this paragraph, this subtask is a no-op: say so in the handoff rather than
re-narrating the paragraph the ruling just replaced. If this subtask lands first, the rewrite is
prose only and changes no key set.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
