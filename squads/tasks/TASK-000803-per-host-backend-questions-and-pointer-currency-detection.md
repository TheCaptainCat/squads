---
id: TASK-803
sequence_id: 803
type: task
title: Per-host backend questions and pointer currency detection
status: Done
parent: FEAT-792
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-781:implements
- TASK-802:depends-on
- BUG-784
description: Declare ADR-781's five per-host questions on the AgentBackend ABC and
  add the currency half of pointer detection to sq check and sq sync
subentities:
- local_id: ST1
  title: Declare the five per-host questions without growing the abstract seven
  status: Done
  story: US3
- local_id: ST2
  title: Both bundled backends answer all five questions explicitly
  status: Done
  story: US3
- local_id: ST3
  title: sq check compares a fresh render against disk, at two severities
  status: Done
  story: US4
- local_id: ST4
  title: sq sync reports what it regenerated for a currency fix
  status: Done
  story: US4
created_at: '2026-08-25T14:42:10Z'
updated_at: '2026-08-26T12:04:48Z'
---
<!-- sq:body -->
## Scope

Implements ADR-781 sections 2c and 2d for FEAT-792 stories US3 and US4: the five questions the
`AgentBackend` ABC asks each backend in its own host's terms, and the currency half of pointer
detection in `sq check` plus the `sq sync` report that follows a currency fix.

Grouped as one dev pass because they are one mechanism from two ends. Question 5 — "what would a
pure render of this entry look like, without writing it" — is not documentation: it is the hook
the currency comparison consumes. Splitting the questions from the check would have one dev
declare a seam and another discover it does not fit, in the same three files.

## Presence already shipped — scope this to currency only

BUG-784 is **Verified** and its fix landed in commit `383d5e8`. Confirmed against `HEAD`:

- `AgentBackend.managed_entry_paths` exists with a concrete default at
  `_backends/_base.py:229`, overridden by `_claude_code/_backend.py:424`.
- `sq check` reports an absent per-entry pointer at warn through
  `_services/_validators.py::backend_entry_candidates` plus the
  `backend_entry_missing` confirm predicate, scoped to the live roster via
  `live_roster_slugs` and `is_live_roster_entry`.
- `sq sync` already names each per-entry pointer it had to regenerate
  (`_services/_maintenance.py:572`).

**Re-implementing any of that is wasted work.** Currency is a second finding over the widening
presence already made; it reuses `managed_entry_paths` as its path set rather than declaring a
second one.

**One gap worth naming and not filling here.** ADR-781 section 2c also asks the unprompted
root-callback notice to see the filesystem, and `_cli/_common.py::version_notice` still keys
solely on `.squads.toml`'s recorded `squads_version` (read). That is presence work, which
FEAT-792 places out of scope. Leave it; it is raised on the feature for the architect.

## The declared path set must stay roster-scoped

ADR-781 section 2c makes this a hard constraint rather than a refinement: retirement
*deliberately* removes a pointer, and `sq check` is clean on both sides of a retire/reactivate
cycle today. The currency comparison must take its path set from `managed_entry_paths` fed by
`live_roster_slugs` — the same `is_live_roster_entry` predicate `_project_roster_item` uses to
materialise or withdraw — and never from a fixed or historical slug list. Anything else turns
every retirement into a false positive on the retired side.

Follow presence's shape for the race, too: a currency finding is cross-source (it reads the
index and the disk), so it belongs in `check`'s existing confirm round alongside
`backend_entry_missing`, not reported straight off the scan.

## The never-read-back guard does not forbid this

A developer will hit `tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py`
and needs the reasoning in front of them rather than having to reconstruct it.

That guard forbids a **backend recovering a declaration from its own output**. The failure it
was written for is real and recorded in its own docstring: `agents_md`'s `write_managed`
recovered each role's mission by matching the literal `**Mission:**` prefix of a line it had
rendered one step earlier, so relabelling a template emptied every mission with `sq check`
clean. It is scoped by directory to a backend's own staging-output constant.

A drift check reads output as the **subject under test**. Every declaration still comes from the
role or skill item; the fresh render is the *expectation*, not the source. The direction of
authority — item to output, never output to item — is exactly what the guard protects, and it is
preserved. Two things follow and must hold in the implementation:

- the comparison lives in the **checker**, not inside a backend. A backend renders on request
  (question 5) and never reads a file back to decide anything.
- the checker compares against the path the backend itself declares, so it never reaches into a
  host's directory on its own (invariant 6).

If the guard trips, that is a signal the render hook was put on the wrong side of the seam — do
not add an allowlist entry to quiet it.

## The ABC must not grow past its documented seven

`docs/stability.md:470` and `docs/backends.md:27` both promise `AgentBackend` has exactly seven
abstract methods and that the set does not grow, and
`tests/unit/test_agent_backend_abc_stays_at_seven_documented_methods.py` pins the promise
against the class. That test also records the precedent: `managed_entry_paths` was briefly an
eighth abstractmethod, which broke a third-party backend written from the documented seven, and
the fix was a concrete default that opts a backend *out* rather than requiring it to opt in.

So the five questions arrive the same way — as documented contract plus, where a question needs
a code seam, a **non-abstract** method with a working default. A backend written against the
seven must still instantiate, and a backend that declares nothing must simply not participate in
currency reporting, exactly as one that declares no `managed_entry_paths` is never warned about
a missing pointer.

## The five questions, and the two answers owed

Phrase each so an author who has read only their own host's documentation can answer it, with no
reading of squads internals required. ADR-781 section 2d states them; take its wording as the
starting point:

1. Can an agent running under this host execute a command at all?
2. Which of the values squads projects does this host's configuration have a place for? An
   undeclared one is **reported once at write time and dropped, never silently**, on
   `model_drop_warning`'s precedent (`_backends/_claude_code/_frontmatter.py:24-48`) — and never
   validated a second time against a host-local vocabulary at storage time.
3. Which of those must be present for this host to find and dispatch an entry at all?
4. Which of those constrain what the session may do, rather than configure how it runs?
5. What would you write for this entry, without writing it?

Both bundled backends answer all five explicitly, and their answers differ for a stated reason
rather than by accident:

- **`_claude_code`** answers question 1 **yes**. Its irreducible set is `name` and
  `description`; its question-4 answer is `disallowedTools`.
- **`_agents_md`** answers question 1 **"not knowably"** — its target hosts' command-execution
  capability is declared by whoever builds a backend, not by us. That answer is why it keeps its
  compiled roster prose (full name, slug, title, mission, responsibilities): a host with no
  fetch available has nothing to substitute with. Record it as that answer, not as an
  unexplained asymmetry.

Question 3's *notion* is universal; its membership is per host. Do not lift Claude Code's
`name`/`description` into a shared assertion — ADR-781 calls it the least representative example
available.

## Severities follow section 2a's own distinction

Not a new judgement. A drifted or missing value that **restricts** the session is an **error**:
a pointer still granting a leaf the spawn tool the squad revoked is a live regression against
ADR-155's threat model, and is not repairable from inside the session it governs. Today that is
`disallowedTools`, reached through each backend's question-4 answer rather than by hard-coding
the field name.

Everything else is a **warn**: `sq sync` fixes it and nothing unsafe happens meanwhile. A
correct, already-current pointer produces no finding at all.

## Sequencing against the template rewrite

The sibling task rewrites the pointer templates. The fresh render this check compares against
must be the post-rewrite shape, or the check is written against a shape that is about to change
and would flag every pointer in the corpus the moment it does. Both tasks also edit
`_backends/_claude_code/_backend.py`. Recorded as a `depends-on` ref rather than only as prose.

## Acceptance

- `AgentBackend.__abstractmethods__` is still exactly the documented seven;
  `tests/unit/test_agent_backend_abc_stays_at_seven_documented_methods.py` passes unchanged, and
  a backend implementing only those seven still instantiates.
- The five questions are declared on the ABC in host-neutral terms, and both bundled backends
  answer all five explicitly. A future backend can answer them from its host's documentation
  without reopening ADR-781.
- A value squads projects that a backend cannot express is reported once at write time and
  dropped — never silently dropped, and never re-validated at storage time.
- `sq check` renders a fresh copy of each declared live per-entry artifact and compares it
  against disk. Editing a live role's `disallowedTools` without running `sq sync` is an error;
  editing its resolved skills without syncing is a warn; a current pointer produces no finding.
- The comparison's path set comes from `managed_entry_paths` fed by `live_roster_slugs`. A
  retire followed by a reactivate produces no finding at any point in the cycle — drive it, do
  not reason about it.
- A currency finding goes through `check`'s existing confirm round, like `backend_entry_missing`.
- `sq sync` states what it regenerated for a currency fix, in the same shape BUG-784 established
  for a presence fix, so an operator learns both that there was a fault and that a commit is owed.
- Presence findings are byte-identical to what shipped in `383d5e8`: currency is added alongside
  them, never a second presence mechanism, and no presence test needed editing.
- `tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py` passes with no new
  allowlist entry.
- `docs/backends.md` and `docs/stability.md` describe the five questions and still promise seven
  abstract methods without contradicting themselves.
- `uv run --all-extras pytest`, `uv run --all-extras pyright`, `uv run --all-extras ruff check .`
  and `uv run --all-extras ruff format --check .` are clean, and `uv run sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 803 add-subtask "<title>"`; track with `sq task 803 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Declare the five per-host questions without growing the abstract seven | US3 |
| ST2 | Done |  | Both bundled backends answer all five questions explicitly | US3 |
| ST3 | Done |  | sq check compares a fresh render against disk, at two severities | US4 |
| ST4 | Done |  | sq sync reports what it regenerated for a currency fix | US4 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Declare the five per-host questions without growing the abstract seven

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US3 — Five per-host questions on the AgentBackend ABC
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Declare ADR-781 section 2d's five questions on `AgentBackend`, each phrased so an author who has
read only their own host's documentation can answer it, with no reading of squads internals
required:

1. Can an agent running under this host execute a command at all?
2. Which of the values squads projects does this host's configuration have a place for?
3. Which of those must be present for this host to find and dispatch an entry at all?
4. Which of those constrain what the session may do, rather than configure how it runs?
5. What would you write for this entry, without writing it?

Question 5 is not documentation — it is the render-without-writing seam the currency comparison
consumes, and it is compared against the path the backend itself declares, so the checker never
reaches into a host's directory on its own (invariant 6).

Question 2 carries `model_drop_warning`'s precedent (`_claude_code/_frontmatter.py:24-48`)
generalised from one field to all of them: a value this host cannot express is **reported once at
write time and dropped — never silently**, and never validated a second time against a host-local
vocabulary at storage time. Questions 1, 2 and 4 together give the property worth naming: a
backend may be unable to honour a constraint squads declares, and that is reportable rather than
forbidden — a warning that this host cannot express the boundary, not a refusal to support it.

**The abstract set must stay at seven.** `docs/stability.md:470` and `docs/backends.md:27` both
promise exactly seven abstract methods that do not grow, and
`tests/unit/test_agent_backend_abc_stays_at_seven_documented_methods.py` pins the promise. That
test records the precedent too: `managed_entry_paths` was briefly an eighth abstractmethod and
broke a third-party backend written from the documented seven; the fix was a concrete default
that opts a backend out rather than requiring it to opt in. Any code seam these questions need
arrives the same way — non-abstract, with a working default.

Question 3's *notion* is universal, its membership is per host. Do not lift `name`/`description`
into a shared assertion: ADR-781 calls Claude Code the least representative example available.

Done when a backend implementing only the documented seven still instantiates, the two
documentation files describe the five questions without contradicting the seven-method promise,
and that unit test passes unedited.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Both bundled backends answer all five questions explicitly

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US3 — Five per-host questions on the AgentBackend ABC
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Both bundled backends answer all five questions explicitly, and their answers differ for a stated
reason rather than by accident.

**`_claude_code` answers question 1 "yes".** Its agents run `sq`, which is the premise the whole
pointer rewrite is built on. Its expressible set is the frontmatter it renders today; its
irreducible set — derived from Claude Code's own discovery contract, not asserted universally —
is `name` and `description`; its question-4 answer is `disallowedTools`, Claude Code's spelling
of ADR-155's attenuation.

**`_agents_md` answers question 1 "not knowably".** That is the answer, not a gap. It compiles a
single `AGENTS.md` for tools whose command-execution capability is declared by whoever builds a
backend, not by us. Record it that way: not knowing a host's capabilities is the normal condition
for every backend an adopter brings, so the question is *declared* by the author who has the
host's documentation instead of assumed by us, who never will.

That answer is what justifies the asymmetry ADR-781 chose to state rather than smooth over:
`AGENTS.md` keeps its compiled roster prose — full name, slug, title, mission, responsibilities —
because clause 2 asks whether a runtime fetch can substitute, and a host that cannot run a command
has no fetch available. Same rule, different answer. Write it as the answer to question 1, not as
an exemption, so a future backend that answers "yes" inherits the containment rule in full and
does not inherit `AGENTS.md`'s outcome.

The cost of the negative answer is named rather than hidden: that prose is materialised state, it
drifts, and both presence and currency cover it because both compiled documents are already
declared paths.

Done when each backend's five answers are readable at its own definition, and a reader can tell
why the two differ without reading ADR-781.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — sq check compares a fresh render against disk, at two severities

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US4 — Currency detection for per-entry pointers
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
`sq check` renders a fresh copy of each declared live per-entry artifact (question 5) and compares
it against what is on disk, reporting drift **by comparison, never by a stamp**. ADR-85's
`override-base` stamp exists because an override is user-owned and cannot be re-derived; a pointer
is tool-owned and re-renderable, so comparison is available and answers the question that matters
("is this wrong") instead of the one a stamp answers ("how old is this"). A stamp here would also
flag a correct pointer for predating a release that changed nothing about it.

**Path set.** Reuse `managed_entry_paths` fed by `live_roster_slugs` — the same
`is_live_roster_entry` predicate `_project_roster_item` uses to materialise or withdraw. Never a
fixed or historical slug list: retirement deliberately removes a pointer and `sq check` is clean
on both sides of a retire/reactivate cycle today, and anything else turns every such cycle into a
false positive on the retired side. Drive a full retire-then-reactivate cycle and confirm no
finding appears at any point in it.

**Race.** A currency finding reads the index and the disk, so it is cross-source exactly as
presence is. Route it through `check`'s existing confirm round beside `backend_entry_missing`
rather than reporting straight off the scan.

**Severities, from ADR-781 section 2a's own distinction rather than a new judgement.** A drifted
or missing value that *restricts* the session is an **error** — a pointer still granting a leaf
the spawn tool the squad revoked is a live regression against ADR-155's threat model and is not
repairable from inside the session it governs. Reach that field through the backend's question-4
answer, not by hard-coding `disallowedTools`. Everything else is a **warn**: `sq sync` fixes it
and nothing unsafe happens meanwhile. A correct, already-current pointer produces no finding.

**The never-read-back guard is not breached, and the reasoning belongs in the code.**
`tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py` forbids a *backend*
recovering a *declaration* from its own output — the recorded failure is `agents_md`'s
`write_managed` matching a `**Mission:**` prefix on a line it had just rendered, so relabelling a
template emptied every mission with `sq check` clean. A drift check reads output as the **subject
under test**: every declaration still comes from the role or skill item, and the render is the
expectation, not the source. Keep the comparison in the checker, never inside a backend. If the
guard trips, the render hook is on the wrong side of the seam — do not add an allowlist entry to
quiet it.

Done when editing a live role's `disallowedTools` without syncing is an error, editing its
resolved skills without syncing is a warn, a current pointer is silent, and every presence
assertion shipped in `383d5e8` still passes unedited.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — sq sync reports what it regenerated for a currency fix

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US4 — Currency detection for per-entry pointers
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
`sq sync` states what it regenerated for a currency fix, in the same shape BUG-784 already
established for a presence fix (`_services/_maintenance.py:572`, which names each per-entry
pointer that was missing and has now been regenerated).

The reason is the same one that made the presence report necessary. Generated pointers are
committed in every mode (ADR-781 section 2b), so a silent fix is the wrong silence twice: the
operator learns neither that there was a fault nor that a commit is now owed. `sync` already
returns notices to its caller, so this is a report rather than a mechanism.

Currency's message must be distinguishable from presence's — "was missing" and "had drifted" are
different facts about a repository, and an operator reading the output should be able to tell
which one they are looking at.

Use the same live-roster-derived set on both sides of the write that presence uses, so a
retirement or reactivation racing the sync can never produce a false line either way.

Done when running `sq sync` after a hand-edited pointer names that pointer as regenerated, the
presence lines are byte-identical to what shipped in `383d5e8`, and
`tests/service/test_sync_reports_regenerated_per_entry_pointers.py` still passes.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-26T12:00:08Z] Elias Python:
  - Five questions declared on AgentBackend (docstring + two non-abstract seams): Q1 execute-commands, Q2 expressible-set (model_drop_warning precedent), Q3 irreducible-set, Q4 restriction_fragment(role) -> str|None, Q5 render_role_entry/render_skill_entry(ctx,item,...) -> str|None. Still exactly seven abstractmethods; seven-method test passes unedited.
  - claude_code answers all five at its class docstring: yes / whole frontmatter surface / name+description / disallowedTools via restriction_fragment / render_*_entry sharing the same render helpers generate_*_entry writes from. agents_md answers all five at its class docstring: not knowably / identity+prose only / not applicable (no per-entry file) / None (no boundary expressed) / None (nothing to render) -- explicit inherited defaults, not silent gaps.
  - Currency: sq check does a full render-and-compare per live entry at SCAN time (against the already-loaded index, never a second store.load) and only a genuine mismatch becomes a confirm-round candidate -- mirrors how frontmatter value-skew already works, so a clean board pays one read per live entry and nothing else (pinned by test_check_confirms_cross_source_claims.py, which I had to fix an early design against: my first pass built candidates off mere file-existence and doubled the index load on every check).
  - Never-read-back guard: the comparison lives entirely in _services/_validators.py + _maintenance.py, never inside a backend; a backend only renders on request via render_role_entry/render_skill_entry. Path always comes from managed_entry_paths scoped to one slug (backend_entry_path helper), so the checker never invents a path. tests/meta/test_a_backend_never_reads_back_its_own_generated_output.py passes with no allowlist change.
  - Severities: restriction_fragment(role) returns "disallowedTools: Agent" iff not can_spawn, else None. A drift is error only when that fragment is expected AND absent from disk (capability escalation); every other drift is warn. Driven live on a scratch squad: removed disallowedTools from a leaf role pointer -> error; hand-edited a skill description -> warn; sq sync fixed both and reported "had drifted" (distinct from presence's "was missing"); sq check clean after.
  - Retire/reactivate driven live end-to-end on the same scratch squad: sq check stays clean at every step (active, archived, reactivated) -- no false finding on the retired side.
- [2026-08-26T12:00:18Z] Elias Python:
  - Currency detection is real: it changed the observable output of sq sync for any pointer that was stale relative to CURRENT squad state, not only hand-edited ones. Fixed 10 pre-existing tests across 4 files (test_roles_catalog_document_reaches_an_activated_role.py, test_frontmatter_skew_guard.py, test_role_projects_resolved_name_and_mission_onto_item_fields.py x7, test_a_role_override_title_reaches_every_generated_roster.py) that asserted "sync produced no report" for scenarios (activate role, then place/apply an override before the first sync) that are genuinely a pointer written stale then first regenerated -- now correctly reported as "had drifted", exactly the class of case this decision exists to surface.
  - Two pre-existing latent defects this surfaced and left unfixed (out of this task's scope, both proven live via a repro script, not just read): (1) an unrelated item.update() on a role whose index is lagging on a catalog-mirrored key (title/agreements) projects the backend pointer from that STALE in-memory item, briefly writing a blank role title into the pointer until the next sync notices; (2) sync's own skip-and-rollback path on a frontmatter/index skew leaves the item at the rolled-back (stale) values rather than the disk-truthful ones before projecting, so the same sync pass that reports the skew can also regress the pointer to a stale identity for one cycle. Both are pre-existing gaps in _refresh_catalog_extra's skip path, invisible before because nothing ever compared pointer CONTENT. Recommend a bug for the architect/tech-lead to size.
- [2026-08-26T12:00:24Z] Elias Python:
  - @architect open question carried, not settled here per this task's instruction: sq role <slug> show still prints mission/responsibilities twice (computed card + stored body) -- ADR-781 names this its own consequence to settle, and TASK-802 made sq role show an agent's primary definition read, which is what turns the duplication from cosmetic into something an agent can act on wrongly. The two named options (drop the overlapping card rows, or render the body from the resolved definition on every show) are unchanged from the decision. Needs a ruling, does not block this task.
- [2026-08-26T12:02:05Z] Elias Python:
  - Gates clean: pyright (0 errors), ruff check ., ruff format --check . -- all --all-extras, whole repo. tests/meta: 258 passed. tests/service+cli+unit+integration: 3842 passed, 2 skipped (up from 3834/3824 baseline -- +8 new: my test_backend_entry_currency_detection.py). Did not run the full suite (tests/tui, --run-slow) per instruction -- that is the main loop's gate.
  - Files touched: src/squads/_backends/_base.py (five questions + restriction_fragment/render_role_entry/render_skill_entry), _claude_code/_backend.py (answers + shared render helpers + _resolve_model pairing fix), _agents_md/_backend.py (answers, no code change -- inherited defaults), _services/_validators.py (backend_entry_path/backend_entry_drift), _services/_maintenance.py (_scan_backend_entry_drift/_confirm_backend_entry_drift_candidates/_entry_content_snapshot/_entry_drift_report), docs/backends.md + docs/stability.md. New test: tests/service/test_backend_entry_currency_detection.py. 10 pre-existing tests updated across 4 files (see prior comment) for the new, correct sync report.
  - sq check clean on this repo throughout. Moving to InReview.
<!-- sq:discussion:end -->
