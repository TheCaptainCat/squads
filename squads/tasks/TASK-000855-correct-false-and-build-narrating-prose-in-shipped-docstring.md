---
id: TASK-855
sequence_id: 855
type: task
title: Correct false and build-narrating prose in shipped docstrings
status: InReview
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
  status: Done
- local_id: ST2
  title: Restate the RoleView and validators reasoning as rules
  status: Done
- local_id: ST3
  title: State adopt's seeding invariant instead of a former gap
  status: Done
- local_id: ST4
  title: Name what the five flagged test modules cover
  status: Done
- local_id: ST5
  title: Correct the runner roster projection's false equivalence
  status: Done
- local_id: ST6
  title: Replace the carry-set rationale's non-existent command
  status: Done
- local_id: ST7
  title: Restate the dev-role skew exemption's reason in the present tense
  status: Done
created_at: '2026-09-01T11:22:08Z'
updated_at: '2026-09-01T13:21:02Z'
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
- [2026-09-01T12:57:42Z] Theo Writer:
  - Rewrote all three flagged passages in _backends/_agents_md/_backend.py, plus two neighbours carrying the same framing. All narration, no false claims found here.
  - Module docstring: dropped the "a prior version staged one file per role/skill" history and the "those staging files are gone" announcement; states the four present-tense properties instead (write_managed compiles from the views it is passed; the two generate_* methods write nothing and exist for the ABC contract; those two and remove_artifacts opportunistically delete a leftover .agents_md/ file for the entry they are handed; only a leftover whose owning role or skill was removed outright survives, and candidate_orphans reports it). Verified candidate_orphans is reached from init and adopt only (_services/_service.py) — not from sync — so "the next time sq adopt runs" stands.
  - write_managed: the "they used to be" paragraph is gone from here; the invariant it was arguing for stays — every role field rendered comes from the RoleView, never from text this backend produced a step earlier — and points at RoleView for the rule itself, which is where ST2 puts it.
  - generate_role_entry: "the materialise half of this release's staging-file removal" replaced by the property (materialise and withdraw clean up the same way, so a live role's leftover disappears as fast as a retired one's); kept the note that item/ctx.resolved_skills_for are unused.
  - Also corrected while open, same framing: remove_artifacts and candidate_orphans said "staging file from a pre-upgrade version of this backend" (history as identifier — now just names the file), and the managed_entry_paths comment said "does not name a staging file ... any more".
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
- [2026-09-01T13:01:31Z] Theo Writer:
  - Done: _backends/_base.py RoleView + four passages in _services/_validators.py. Two of the four turned out to be FALSE, not just narrating — details below.
  - NARRATION. RoleView docstring: the incident (mission recovered by string-matching **Mission:** out of self-generated markdown, relabelling emptied it, responsibilities never rendered) is replaced by the rule it protects — a view field is the declaration, generated text is output and never an input; a backend recovering a declaration by parsing its own rendered markdown makes a template's formatting the carrier of that declaration, so relabelling a line empties the field silently. "Anything a backend renders is therefore declared here rather than read back off the page."
  - NARRATION. _backend_reconciled: dropped "It used to be computed here, unconfirmed, until making it roster- (and therefore index-) derived turned it cross-source." Kept the distinction as the reason: a per-entry pointer is roster- and therefore index-derived, which makes it cross-source and needs the confirm round; a rule reading only config and disk does not.
  - NARRATION. backend_entry_candidates warn paragraph: dropped "not for the reason once written here", "before this widening" and "adding a new error to a patch release". The whole honest reason survives — gitignoring the directory already fails on _backend_reconciled's top-level error entry, so warn is not protecting a supported choice; the shape this rule reaches is the narrower one (a per-entry pointer gone while the top-level files are present) and warn surfaces it without changing the exit code. Verified the exit contract at _cli/_main.py: "0 = clean (or warnings only), 3 = one or more error-level issues found."
  - FALSE. Module header claimed the engine reads state "exactly what _maintenance.py's _check_* methods hold today via self.store/self.paths/self.spec" and that those methods "are retired from _maintenance.py". `grep -c "def _check_" src/squads/_services/_maintenance.py` returns 0 — there are no such methods, so the first half asserts a present-tense parallel to code that does not exist. Rewrote to describe what the two context objects carry. Also dropped the "per the accepted category/validator decision and the architect's module-boundary pins on the category-axis feature" provenance line (a reference to another agent's work). Re-verified the surviving factual claims against the tree: COMMON_CORE and CATEGORY_BUNDLES are in _workflow/_models.py, "records" carries no_parent, and items.epic (category "work") declares validators = ["no_parent"] in workflow.toml — so I state both routes explicitly rather than the old compressed phrasing.
  - FALSE. _opens_with_status_banner pointed at "``_maintenance._opens_with_status_banner`` for the full false-positive rationale". No such symbol exists anywhere in src/. The rationale it pointed at is already stated in the pattern comment two lines above (leading-line anchoring), so the docstring now states it in place. The pattern comment itself said "Mirrors _maintenance.py's detector (the routing task retires that copy once _check_status_banners is decomposed away)" — a ticket reference plus a mirror that is not there; replaced with the verified fact that this is the only status-banner detector in the tree and _no_status_banner its sole consumer (checked: the two regexes are used only by this helper, the helper only by _no_status_banner).
  - Also cleaned in passing, same framing: ValidatorContext's raw_text paragraph ("replaces Phase A's placeholder on_disk_bodies shape ... exactly as the _check_* methods it replaces do" — phase language plus the same dead symbol), and SquadGlobalContext's "mirroring what _check_backends holds via self._ctx/self._backends() today".
  - backend_entry_drift: read in full as instructed. It is clean — "question 4"/"question 5" are the ABC's own numbered questions (established vocabulary, also used in AgentsMdBackend's class docstring), and the closing sentence about the mirror describes present behaviour. Left untouched.
  - NOT FIXED, reported instead: _validators.py carries 15 provenance markers of the form `← ``_check_items``` / `← ``_check_backends``` etc. opening a validator docstring. None of those names exists anywhere in the tree (grep across .py/.md/.j2 hits only these markers), so a reader following one finds nothing. Same defect class as the two false citations above, but removing the whole family is a call about whether we keep a provenance map at all, and the subtask author read this file and named four other passages — so I have left them and am flagging them rather than deciding unilaterally. Same for _services/_maintenance.py:1614, whose comment says "(mirrors _check_reconciliation)"; the live equivalent is _validators._index_reconciled.
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
- [2026-09-01T13:02:44Z] Theo Writer:
  - Done: two comments in _services/_service.py, both narration, no false claims.
  - adopt's seeding step: dropped "and was previously the worse of the two gaps". The invariant survives whole — adopt is the other path that can create a squad's config, so it has to seed both halves, bundled and custom, exactly as init does; without them a generated skill file sits on disk with no SKILL item indexing it, and stays that way until the first sq sync seeds it.
  - Wording check against the tree as it stands: the old comment said "leaving every generated skill body untracked". Since system skill definitions stopped being stored, a system skill's file carries an EMPTY sq:body region, so "skill body" is the wrong noun for what goes unindexed — it is the skill FILE and its missing SKILL item. Reworded accordingly. Confirmed "until the first sq sync" is still true: _maintenance.py calls seed_bundled_skills/seed_custom_skills on every sync.
  - Swept the rest of the file as instructed. One more of the same shape at open_service's no-override fast path: "so this stays byte-identical to today" — a comparison to a prior version. Now states the property: a squad with neither override still lands on the bundled playbook singleton here. Two other "today"/"no longer" hits are about the SQUAD's data or a genuine present-state fact (no dedicated playbook lint surface; an item whose status the spec no longer declares), not build narration — left alone.
  - NOT FIXED, adjacent file, reported: _services/_maintenance.py around the sync-time seeding call opens "Seeding only the custom half here — which is what this did — left a hole exactly the width of ...". Same shape as the passage this subtask names, but it is in _maintenance.py and outside the "while in this file" instruction, so I have flagged rather than rewritten it.
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
- [2026-09-01T13:06:19Z] Theo Writer:
  - Done: all five modules. One FALSE claim and one stale count found along the way — the rest was narration. 68 tests in the five modules pass; no test function or module renamed, as instructed.
  - test_frontmatter_skew_guard.py (the heaviest). "Reproduces the finding this task closes end to end" -> names the shape: a faulted index commit during a mutation on a field outside {status, parent}. "The second, broader trigger named in the finding" -> the shape: a role catalog gaining a field, so the merge reaches a key the index has not seen. "Two properties, and the first one used to be the opposite" -> both properties stated flat, present tense, with no claim about which one changed. Also: "restoring what this test was once narrowed to a single non-default leg to sidestep a regression" -> now says what each parametrized leg pins and why the default leg cannot stand in for the other; "disk ahead by construction here rather than by a writer that no longer exists (the resolved-skills cache ... is gone along with link-role's write of it)" -> the divergence is written directly, since no live writer produces it; "rather than the old behaviour, which let the mutation through" -> states the loss class instead ("the stale index-loaded value silently overwrites the committed one").
  - FALSE, same file. The dev-role test asserted "a dev role's own catalog fields are not exempt (only `extra.skills` is)". Checked _itemfile._exempt_extra_keys: a dev role returns frozenset() — NOTHING is exempt, extra.skills included. The parenthetical is the only surviving reference to a narrower dev exemption that the code does not have; cut it, kept the surrounding claim, which is correct.
  - FALSE, same file. The false-refusal banner said "all five are expected to pass on the FIRST run" and pointed at "the paired sabotage test below, which proves it is not [inert]". There are six false-refusal test functions under that banner (seven cases, one is parametrized over two legs), and the tests that prove the guard is not inert are ABOVE it, not below — there is no test named or shaped as a sabotage below. Rewrote without the count and with the correct direction: the divergences collapse in the round trip through Item.from_frontmatter(...).to_frontmatter_dict() before the guard compares the two sides, and the real-skew cases at the top of the file are what show it is not inert.
  - Left alone in that file, on purpose: the PERMITTED_EXTRA_SKEW banner and the legacy-severity / legacy-ref-kinds / padded-id docstrings all describe SQUAD DATA shapes an older release left on disk. That is a live adopter condition, not build narration.
  - test_new_slug_validation_...py: "After the stored-fact-first fix ... that is no longer true" and "narrowing the original finding down to" -> the module docstring now states where the line falls (a slug with a roster entry is decided by the stored fact, not by its suffix) and names the lenient shape as the one no stored fact CAN decide. The test docstring's "The half of the finding that the stored-fact-first fix actually closes" -> "The slug shape the stored fact decides". Verified both cross-referenced test files exist under the paths named.
  - test_operator_named_roles_survive_sync.py: dropped "exactly the shape that shipped with this defect" (the sibling file is now introduced by what it covers, not by the defect) and "Two structural causes had to be fixed together" -> two invariants stated positively (the caller supplies a merge base for a non-dev role; resolve_role_with_base honours the base it is given, PREDEFINED included). I did NOT carry over the closing claim that reverting either site turned every --name test red and restoring one alone was not enough — that is a falsification experiment I cannot verify without breaking the code, so per the standard I cut it rather than softening it. What replaces it is derivable: every test exercises both at once, so a red test points at either site. "The sharpest regression:" -> "The tightest case:"; the "# regression:" note now says what the case is (a "had drifted" report here is currency detection doing its job).
  - test_validators_assignment_surface.py: "the routing-task parity tests in tests/service/" named a work item and a directory. Now names the two files by what they cover — tests/service/test_validator_catalog_lift.py for each named validator's own behaviour, tests/service/test_records_epic_no_parent_enforcement.py for a type's own additions extending its effective set (that file's subject is literally epic's own no_parent addition).
  - test_workflow_override_service_integration.py: as expected, only one passage narrated — "is the whole finding" in the crossed-case banner. Now says it is the case neither pole above reaches. The badge-family and index-untouched comments describe behaviour and are untouched.
  - NOT FIXED, reported: tests/service/test_validator_catalog_lift.py's module docstring says "Parity between each lifted CATALOG entry and the hardcoded _check_* method it replaces" and "The engine itself is still inert (empty bundles)". Both are false now — no _check_* method exists in _maintenance.py, and COMMON_CORE plus CATEGORY_BUNDLES are populated (verified in _workflow/_models.py). Outside this subtask's five modules, so flagged rather than rewritten.
  - No test function or module was renamed. One module name does narrate: tests/integration/test_new_slug_validation_narrows_to_the_undecidable_dev_shape.py — "narrows to" describes a change to the validation rather than the behaviour pinned. A behaviour-named alternative would be something like the suffix space being decided by the stored fact except where no roster entry exists. Noting it here as instructed, not renaming.
- [2026-09-01T13:20:15Z] Theo Writer:
  - Post-gate note, shared here because ST4 is where the doc-claim work landed alongside the test prose: the ADDITIONAL SCOPE doc corrections are done too. See the ST5/ST6 comments for the driven verifications, and the parent handoff for the per-file split.
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
- [2026-09-01T13:07:48Z] Theo Writer:
  - Done: _migrations/_v0_11_to_v0_14.py, _live_roster's docstring. Prose only — the projection is untouched.
  - DRIVEN, not read. Scratch squad, sq init with roles_spec=architect, then a .overrides/roles/architect.toml setting title = "chief architect" placed WITHOUT a sync, so the item's extra mirror still holds the bundled title. Then both projections against the same index: Service.roster -> [("architect", "chief architect")]; _live_roster -> [("architect", "architect")]. The divergence the subtask describes is real and reproduces on the first try. Scratch squad removed afterwards.
  - One correction to the subtask's framing, and the new docstring says so: only the ROLE half diverges. Compared field for field — _live_roster's operator projection and Service.operators are identical (both read extra SLUG/FULL_NAME with the same fallbacks), and its skill_paths and Service._skill_paths are identical too. So "the same projection Service.roster/Service.operators/Service._skill_paths apply" was two-thirds true; claiming the whole thing diverged would have been as wrong as the sentence it replaces.
  - The consequence is stated and traced, not assumed: _regenerate_surface passes this projection straight to backend.write_managed, and _maintenance.py's sync loop calls the same write_managed with await self.roster() — so the managed region sq migrate up writes differs from the one the next sq sync writes, on a squad carrying an override the mirror has not caught up with. MANUAL already says "Run `sq sync` next", verified in the module, and the docstring now names that as what closes the window.
  - The locality rationale survives, restated as a rule rather than an aside: _services imports the migration registry to run this module, so calling Service from a runner is a real import cycle; and a runner is frozen against the corpus vocabulary of the version it transforms, which still carries the mirror. That second half is the reason the projection must NOT be taught to resolve, so it now leads the paragraph instead of trailing it.
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
- [2026-09-01T13:10:13Z] Theo Writer:
  - Done: _roles/_resolver.py, both docstrings. The rule is untouched and uncarried fields are still uncarried — only the citation changed.
  - DRIVEN before writing, twice. (1) `uv run sq role manager update --set color=magenta` -> exit 2, "No such command 'update'". The role addressing group offers show/regen/rm/status/set-default (sq role --help). (2) Established what DOES reach it: _cli/_items.py's `update --set` is the only CLI command that builds a set_extra dict, and _cli/__init__.py only builds those item apps for spec.non_roster_types(). So nothing on the CLI reaches a role's extra — the subtask's fallback instruction applies, and the docstring now says so plainly: the seam is Service.update's set_extra argument, reachable programmatically, with no role verb exposing it.
  - DRIVEN, the silent consequence the subtask asked to state. Scratch squad: svc.update(role.id, set_extra={"title": "grand architect"}) succeeds; item.extra["title"] == "grand architect"; the role's .claude/agents/architect.md pointer does NOT contain it; CLAUDE.md does NOT contain it; after svc.sync() extra["title"] is back to "architect". That is now in the docstring as a named consequence of the rule, not a defect.
  - Wording care on the "every surface" claim: I did not write an enumeration of surfaces. The docstring names the MECHANISM — every surface that renders a role resolves through the catalog against the base this function builds, which carries full_name and is_default and nothing else — then gives the pointer and the managed regions as the two I drove. An exhaustive list here would rot the next time a surface is added.
  - The rule itself is verbatim in substance: _refresh_catalog_extra converges a generic write on the next sync rather than preserving it, so carrying those fields in the base would break the reconciliation for whichever was written last; only full_name and is_default have dedicated verbs that make the stored value lasting, and only those two are carried. Also verified EXTRA_FIELDS["role"] really does declare title/mission/responsibilities/model/color (plus is_default and tech) in _models/_metadata.py — the field list in the sentence is correct as written.
  - dev_base_from_item: "reachable through the generic `sq <type> update --set` escape hatch too" replaced by the seam name, cross-referencing role_base_from_item rather than repeating the CLI analysis in two places.
  - One more in the same file, same class, corrected while open: role_base_from_item's squad_dir paragraph said the None default is "exactly today's behaviour" so "a caller that has not been updated to pass it keeps its current answer" — a sentence about a migration in progress. It now states the property: None resolves against the bundled catalog alone, the honest answer for a caller with no squad directory to offer.
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
- [2026-09-01T13:13:59Z] Theo Writer:
  - Done, prose only — no key set changed, `_exempt_extra_keys` returns exactly what it returned before.
  - The ordering caveat did NOT trigger: the architect ruling has not landed. The dev pseudo-role question is on the board as a POST-0.14 candidate, explicitly parked until the release is out, so this paragraph is the one in force and I rewrote it rather than skipping.
  - Dropped: "It once got a narrower exemption of its own — extra.skills alone, since the resolved-skills cache resynced every role's extra this way — but that cache and its writer are gone, and nothing replaced them." Replaced by the reason itself: a dev role gets none of the exemption because no writer persists a dev role's extra outside a transaction, so there is no permanent lag for an exemption to tolerate. Everything after that framing is intact — _refresh_catalog_extra resolving a dev role against a base built from the item's own stored identity, writing markdown first and mirroring inside the same transaction, every field therefore ordinary and transaction-guarded, and the loss class widening would reopen.
  - One correction inside the surviving text. It said "interrupt a dev role's `--set model=haiku`" — a CLI command that does not exist. Drove it while on ST6: the role addressing group has no `update` verb, and `sq dev` offers only `add` and `list`, so there is no --set for a dev role either. Now names the seam: "interrupt a set_extra write of a dev role's model". Same loss, real write path.
  - Also tightened the closing verb from "would silently overwrite" to "silently overwrites" — the sentence is describing what happens if the exemption is widened, not what used to happen.
  - NOT FIXED, same docstring, flagged because ST7 warns this paragraph is under an open question: the second bullet still carries "Keying off the type rather than an extra key (``extra.mission``, previously)". "previously" narrates, but the contrast is load-bearing to the sentence and it sits in the half the architect ruling may rewrite, so I left it rather than churning prose that may be replaced.
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-01T13:20:55Z] Theo Writer:
  - ADDITIONAL SCOPE (operator-supplied after this task was written, no subtask to hold it): the adopter-facing doc claims that went false when system skill definitions stopped being stored. Each verified against a fresh scratch squad before rewriting.
  - GROUND TRUTH, driven on a fresh sq init: a system skill file (squads/agents/skills/SKILL-000012-sq-task.md) contains frontmatter and an sq:body region with nothing between its open and close markers. Its .claude pointer contains no @-path at all — it names `sq skill sq-task show`. A CUSTOM skill (sq skill add, then body -m) DOES store its text in that region. A ROLE file still stores its full definition in its body, and the role pointer likewise names `sq role architect show` rather than an @-path.
  - Fixed, all FALSE: docs/internals.md:58 (skills folder described as holding "squads.md / sq-<type>.md (managed skill bodies)" — wrong filenames and wrong content); docs/internals.md:286-290 (the @-arrow diagram, pointing at a file that holds no body, via an @-import that is not used); docs/internals.md:47-48 (the same two POINTER arrows in the earlier tree); docs/backends.md:130 ("managed skill bodies live in squads/agents/skills/<name>.md"); docs/stability.md:516 (write_managed listed as writing "skill definitions" — it writes the pointer and the body file's SHAPE).
  - Two more sites the brief did not name, same claim, same vintage — fixed rather than left, because leaving the identical falsehood in two other adopter-facing files defeats the correction: docs/README.md:66-67 (the same @-arrow diagram, annotated "(real body)"), and README.md:155 + 164-165 ("pointers to the real definitions under squads/agents/" and the two POINTER path arrows).
  - Two more false claims found in the SAME internals.md passage while rewriting it, both fixed: the role pointer's body was quoted as saying "load your full definition at @squads/agents/roles/ROLE-...md" (it says `sq role <slug> show`), and the managed-skill bullet claimed the body file carries a "managed — regenerated by `sq sync`" header (the file carries frontmatter and an empty region — no such header).
  - Did NOT overcorrect: every rewritten passage names the authored/custom skill as the case where a body really is stored and read back, so the pointer-not-copies guidance still has its durable example.
  - NOT FIXED, found while there, reported: docs/internals.md:281 names the ABC methods as generate_role_pointer/generate_skill_pointer. The ABC declares generate_role_entry/generate_skill_entry — docs/stability.md's own table four screens later spells them correctly, so the two adopter docs disagree. Different vintage from the skill-body change and outside the scope I was given, so flagged rather than changed.
<!-- sq:discussion:end -->
