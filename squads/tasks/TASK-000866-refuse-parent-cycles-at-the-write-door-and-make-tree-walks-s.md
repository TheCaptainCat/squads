---
id: TASK-866
sequence_id: 866
type: task
title: Refuse parent cycles at the write door and make tree walks safe
status: Done
author: tech-lead
assignee: python-dev
priority: high
refs:
- BUG-865:fixes
description: A parent cycle is accepted with exit 0 and hangs every tree surface;
  refuse it at the gate, report an existing one, and make both tree walks cycle-safe.
subentities:
- local_id: ST1
  title: Add a parent_acyclic validator to the always-on floor
  status: Done
  assignee: python-dev
- local_id: ST2
  title: Carry a visited set through both tree walks
  status: Done
  assignee: python-dev
- local_id: ST3
  title: Report an existing cycle without rewriting the corpus
  status: Done
  assignee: python-dev
- local_id: ST4
  title: Refuse an empty --parent value instead of reporting success
  status: Done
  assignee: python-dev
- local_id: ST5
  title: Falsify each guard before handing back
  status: Done
  assignee: python-dev
created_at: '2026-09-02T07:52:13Z'
updated_at: '2026-09-02T14:01:26Z'
---
<!-- sq:body -->
## What is wrong

The parent relation is the squad's hierarchy, and the corpus can hold a cycle in it. One
ordinary command makes an item its own parent, reports success and exits 0; two commands make
a mutual pair. Afterwards every `sq tree` call in that squad — bare, targeted at a completely
unrelated root, `--json`, `--depth 1` — never returns, and the terminal browser's tree pane
awaits the same call. No other read surface is affected and neither lint surface reports the
condition, so the operator's only symptom is a command that does not come back.

Recovery is `sq <type> <n> update --no-parent`, so nothing is lost. The cost is diagnosis: the
corpus holds a shape nothing else in the system expects, and nothing anywhere says so.

The reproduction, the surface-by-surface blast radius, the exposed type set and the two
mechanisms are all driven and already on the record in the linked defect. Do not re-derive
them; read them.

## The three faults, and why fixing one is not fixing the bug

**The write door lets the cycle in.** The parent-eligibility validator reads a type's declared
`parents` allowlist and treats an empty list as "any parent or none", so a type in the `work`
category with `parents = []` and no `no_parent` accepts any parent at all — including itself.
Under the bundled spec that is exactly two types. This is bundled vocabulary, not a
customisation hazard.

**Two traversals then walk the cycle undefended.** The ancestor walk that builds the tree's
keep set carries no visited set and spins forever. The downward recursion behind it carries no
visited set either and raises `RecursionError`; it is a second, independent fault that is
latent only because the first one reaches its failure sooner. A change that guards the upward
loop alone converts the hang into a crash and leaves the bug in place. Both walks are in
scope, and neither is optional.

**Nothing can see an existing one.** Both `check` and `repair` accept a cyclic corpus as
clean, so a squad that already carries a cycle — an adopter's, or one of ours — has no way to
be told.

The write door is the primary defect: every consumer of the parent relation is entitled to
assume it is acyclic, and admitting a cycle means each traversal must defend itself
separately, which demonstrably is not happening. But the entitlement only holds if the
invariant is enforced at *every* door, and the create/update gate is not every door: `repair`
rebuilds the index from markdown with no gate, an adopted corpus arrives that way, and
frontmatter is hand-editable in principle. So the defensive walks are not defence in depth
here — they are the half that covers the doors the gate cannot reach, which is also why the
detection half is needed rather than merely nice.

A precedent already in the tree: the subtree resolver behind the derived-views surface walks
the same parent/child structure and does carry a `seen` set. The codebase is already
inconsistent about this; make it consistent.

## Settled points

**A catalog validator, not an inline check in the parent-setting path — and it refuses a
transitive cycle, not only a self-parent.** There are four sites that set or change a parent
and gate afterwards: item create, the shared update core (which the bulk importer also routes
through), the link verb, and the retype prospective. An inline check would have to be repeated
at each and would be forgotten at the fifth. One error-level catalog member covers all four
for free and, because the same engine backs both the gate and the report surface, covers the
detection half in the same stroke.

Transitive is in scope and is not extra work: a walk that only catches a self-parent and a walk
that catches any cycle differ by nothing — both are an ancestor walk carrying a visited set.
Refusing self-parent alone would leave the identical hang reachable in two commands instead of
one, which is not a fix.

**It belongs in the always-on floor.** The floor's stated test is a finding that is a defect in
every squad whose subject exists whenever an item exists, and that a competent team can never
sit in on purpose. A parent cycle passes that squarely: it is not a house convention, not a
policy, and not a judgement call. Floor placement also settles the catalog's own closure
requirement with no new argument — the floor's members are effective for every type under
every category, so nothing a type declares can put one out of reach and no reachability clause
is owed. This uses the shipped composition machinery only; it does not depend on the wider
catalog design currently under discussion, which is unruled and must not be treated as settled.

**Consequence to accept deliberately, not by accident.** Once the member is error-level and on
the floor, an item already sitting in a cycle can no longer be updated at all until the cycle
is broken — a status change on it is refused too. That is the correct fail-closed behaviour
and it is safe because the recovery command clears the parent before the gate reads it, so
`--no-parent` still works. It is only safe if the refusal *says* so: the message must name the
cycle it found and the command that breaks it. Verify the recovery path rather than reasoning
about it.

There is a documented precedent that cuts the other way and should be read before dismissing
it: the requires-a-parent member sits in no bundle precisely because turning it on would error
on every parentless item already on disk, with no migration able to invent a parent. The
answer differs here for two reasons — a parentless item is a legitimate corpus state and a
cycle never is, and the remedy is one command the operator can run rather than data nobody
has.

**An existing cycle gets a check finding, and no migration.** Two independent reasons, and
either alone is sufficient. First, a runner cannot reach it: there is no schema change here, and
a corpus already stamped at the current schema is one `sq migrate up` answers "nothing to
migrate" for — the region-strip work this cycle established that and had to be re-homed onto
the repair walk because of it. Second, and more fundamental: breaking a cycle means choosing
which edge to drop, which is a judgement about the operator's hierarchy, not a mechanical
rewrite. An automatic fix would silently rearrange a hierarchy someone built. So `repair` must
not break the cycle either — it reports through the check surface and leaves the corpus alone.
Do not assume our own corpus is representative; reason from an adopter's.

**The empty-value no-op is folded in, not split.** `update --parent ""` prints "updated <ID>"
and exits 0 while changing nothing, because the CLI's parent argument is tested for truthiness
before it is resolved. It is a two-line fix in the same command that carries the primary
defect, it is the first thing an operator reaches for when trying to undo the edge, and it is
the same class of fault — a write door reporting success for a write it did not perform. A
separate ticket for it would cost more to carry than to fix. Same command, same pass. Note the
adjacent shape while you are there: `--parent "" --no-parent` passes the mutual-exclusion guard
for the same truthiness reason.

## Scope

In scope: the new validator and its floor placement; the refusal message and its recovery
instruction; the visited set in both tree walks; the empty-value rejection; tests for all of it.

Out of scope: the wider validator-catalog design under discussion; the declared-level and
threshold dimension; scoping the tree's keep set to the requested root (it is computed over the
whole candidate set today, which is why an unrelated root hangs — that is the reason the fault
is squad-wide, but narrowing it would be a semantic change and is not this fix).

## Acceptance

Every clause is a command with an observable exit code or an assertion in the suite. The
self-parent case is one command, so nothing here needs a narrative.

1. On a fresh squad, `sq <type> <n> update --parent <its own ID>` exits non-zero with a message
   that names the cycle and states the recovery command. Same for the two-command mutual pair,
   refused on the second command. Same for a three-item transitive chain, refused on the edge
   that closes it. Driven for each of the two exposed bundled types.
2. Every parent-setting entry point refuses: create with a parent that would close a cycle, the
   update verb, the link verb, and the retype path. Covered at the service level, not only
   through one CLI command.
3. `sq <type> <n> update --no-parent` on an item that is already in a cycle still succeeds —
   the recovery path is not blocked by the new refusal.
4. Against a corpus that carries a cycle *without* passing the gate (construct it by writing
   the frontmatter directly in a temp fixture — the CLI can no longer produce one), `sq check`
   exits non-zero and names both endpoints, and `sq repair` exits 0, leaves the parent edges
   untouched, and does not hang.
5. On that same corpus, every `sq tree` form returns within a normal test timeout and exits 0:
   bare, `-a`, targeted at an item inside the cycle, targeted at an unrelated item, `--json`,
   `--depth 1`. The cycle is truncated at the repeat rather than duplicated, and no item appears
   twice on one path.
6. The downward walk is proved independently of the upward one: a direct test of the recursion
   over a cyclic children map terminates. Without this the second fault stays untested, because
   the upward guard prevents it from ever being reached through the public path.
7. Identity in both visited sets is by sequence number, not by raw id string. A cycle whose
   stored parent strings carry a different padding width than the items' own IDs is still
   caught and still terminates. The existing keep-set walk already resolves parents this way
   for exactly this reason; a naive `seen` set of id strings regresses it.
8. `sq <type> <n> update --parent ""` exits non-zero with a message, and does not print a
   success line.
9. The full suite is green, and the meta scans pass.

**Falsification is required, not optional.** For each of the two traversal guards and the
validator, remove the guard, watch the corresponding test go red, restore it, watch it go
green — and report both observations in the handoff. A test written to confirm a change rather
than to disprove it does not count here: three defects this release shipped inside commits
whose own new tests passed.

## Notes for the implementer

- The refusal message is user-facing text an operator reads at the moment they are confused.
  Name both endpoints of the cycle and the exact recovery command.
- Name tests by the behaviour they pin. No ticket identifiers in source, test names or file
  names.
- Adding a module-level constant trips the meta suite's mutable-state guard; if you add one,
  allowlist it as a code constant rather than restructuring around it, and run the meta scans
  before handing back.
- The meta test tree has another pass in flight. Coordinate before touching it, and prefer
  landing the behaviour tests elsewhere.
- Run the gates with all extras enabled; a bare run prunes an optional extra and reports
  hundreds of false import errors.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 866 add-subtask "<title>"`; track with `sq task 866 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Add a parent_acyclic validator to the always-on floor

<!-- sq:subtask:ST1:body -->
A new error-level per-item catalog member, `parent_acyclic`, wired into the closed name set, the
implementation catalog and the always-on floor tuple. It walks the ancestor chain from the item's
proposed parent, carrying a visited set, and refuses when the chain revisits any item it has
already seen — which covers both a self-parent and a chain of any length that closes on itself.

Identity in the visited set is the **sequence number**, not the raw id string: a stored parent
string may carry a different padding width than the item's own id, which is why the existing
keep-set walk resolves parents through the sequence map rather than comparing id strings.

Floor placement is what makes this cover every parent-setting entry point at once — item create,
the shared update core the bulk importer routes through, the link verb and the retype prospective
all gate through the same engine — and it satisfies the catalog's closure requirement with no new
reachability clause, on the same grounds the other floor members are exempt.

The refusal message is read by a confused operator: name both endpoints of the cycle it found and
state the command that clears the edge.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-09-02T08:04:11Z] Elias Python:
  - Landed. `parent_acyclic` is now a member of `VALIDATOR_NAMES` and of `COMMON_CORE` (the always-on floor), implemented in `_services/_validators.py` and registered in `CATALOG`; the closure assertion against `VALIDATOR_NAMES` passes unchanged because common-core placement needs no reachability clause.
    
    The walk starts at the item's proposed parent and follows `SquadsDB.get` upward. Identity in the visited set is `Item.sequence_id`, never the id string — driven: a corpus whose stored `parent` is `BUG-000010` while the item's own id is `BUG-10` is caught, and an id-string `seen` set would have walked past it. A parent that resolves to nothing stops the walk and leaves the report to `parent_in`'s dangling-parent branch, so one broken edge stays one finding.
    
    Message names the whole chain with the revisited item at both ends plus the remedy, e.g. `BUG-10's parent chain forms a cycle: BUG-10 -> BUG-9 -> BUG-10; break it with \`sq bug 9 update --no-parent\``. The remedy clears the parent of the item whose own edge closes the loop (`chain[-2]`) rather than the item under test — those differ when an item merely inherits a cyclic ancestor chain it is not part of, and only the former actually breaks the loop.
    
    Driven at the CLI on a scratch squad: self-parent exit 1, mutual pair refused on the second command exit 1, three-item chain refused on the closing edge exit 1, unrelated status change still exit 0. Service tests cover create, the shared update core, the link verb, the retype prospective, and the bulk importer (whose validate-first pre-pass reports it and applies nothing).
    
    Note: no bundled spec or template changed — `COMMON_CORE` is code, and `workflow.toml` only ever names `no_parent` per type.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Carry a visited set through both tree walks

<!-- sq:subtask:ST2:body -->
Both walks behind the tree surface are cycle-unsafe and both are in scope. The upward walk that
builds the keep set spins forever; the downward recursion behind it raises `RecursionError` and is
latent only because the upward one fails sooner. Guarding one converts the hang into a crash.

Give each a visited set, following the precedent already in the subtree resolver behind the derived
views, which walks the same structure and does carry one. Identity is by sequence number in both,
for the padding-width reason the keep-set walk already accounts for.

Behaviour at the repeat: truncate, do not duplicate. No item may appear twice on one path, and the
call returns rather than erroring — a poisoned corpus should still render a usable hierarchy so the
operator can see what they are looking at.

The downward walk needs a test that reaches it directly, over a cyclic children map: once the
upward guard lands, nothing on the public path can reach the recursion any more, so it would
otherwise ship untested.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-09-02T08:10:31Z] Elias Python:
  - Both walks in `_services/_base.py` now carry a visited set keyed on `Item.sequence_id`.
    
    `_compute_keep_set`: each per-match upward walk seeds `seen` with the starting item's sequence and stops when the resolved parent sequence repeats. The revisited ancestor is added to the keep set before the walk stops, so a cyclic pair still renders as the hierarchy someone wrote rather than half of it.
    
    `_walk_tree`: a new keyword-only `ancestors: frozenset[int]` carries the sequence numbers already on the path from the root; a node already on that path returns `None`. Truncate, not duplicate — no item appears twice on one path, and a corpus with a cycle still renders. The guard is per-path, not global, so an item legitimately reachable under two different roots is unaffected (pinned by a test).
    
    **Correction to the brief.** The task body and BUG-865 both say the downward recursion is latent and that "once the upward guard lands, nothing on the public path can reach the recursion any more". Driven, that is false. With ONLY the upward guard in place, on a scratch squad carrying a mutual cycle: `sq tree` exit 0, `sq tree EPIC-11` exit 0, but `sq tree BUG-9` (rooted inside the cycle) exit **1** with `RecursionError`. The second fault is reachable through the public path as soon as the tree is rooted inside the cycle — so the two guards are not "one real plus one defensive", they are two live faults. The direct recursion test is still worth having (it is the fast, shape-parameterised proof), but it is not the only thing that reaches the second walk.
    
    Also observed, and deliberately left alone: on a bare `sq tree` the cyclic pair does not appear at all, before or after this change. Roots are the parentless forest, and neither member of a cycle is parentless, so nothing anchors them. Making them render would be a semantic change to what the tree shows — the same class of change the task puts out of scope for the keep-set narrowing — so it is not in this pass.
    
    Tests: `tests/unit/test_tree_walks_terminate_on_a_cyclic_parent_relation.py` (both walks, directly, over self / mutual / three-item shapes plus a cross-pad-width shape) and `tests/cli/test_every_tree_form_returns_on_a_cyclic_corpus_cli.py` (nine tree forms as bounded subprocesses). The upward walk's failure mode is a busy loop that raises nothing, so an in-process test of it would hang rather than fail; the unit test caps id-map lookups and the CLI test bounds the subprocess, so both guards fail *cleanly* when removed rather than stalling a worker.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Report an existing cycle without rewriting the corpus

<!-- sq:subtask:ST3:body -->
A cycle that never passed the gate is still reachable — the index is rebuilt from markdown with no
gate, an adopted corpus arrives that way, and frontmatter is editable in principle — so the
condition needs a detector as well as a refusal. The floor member gives it for free: the same
engine backs the gate and the report surface, so `sq check` reports an existing cycle as an error
naming both endpoints, with no second implementation.

No migration, for two independent reasons. There is no schema change here, and a corpus already
stamped at the current schema is one the runner never visits — established this cycle when the
region strip had to be re-homed onto the repair walk for exactly that reason. More fundamentally,
breaking a cycle means choosing which edge to drop, which is a judgement about the operator's
hierarchy rather than a mechanical rewrite.

So `repair` reports and leaves the edges alone: it must exit 0, not hang, and not rearrange
anything. Build the fixture by writing frontmatter directly, since the CLI can no longer produce
one.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
- [2026-09-02T08:11:28Z] Elias Python:
  - No second implementation was needed: the floor member from ST1 backs the report surface through the same engine, so detection came with it. What this subtask added is the proof, at both levels.
    
    Driven on a scratch squad whose cycle was written straight into frontmatter and then indexed by `repair` (the shape an adopted or hand-edited corpus arrives in — and, deliberately, one with mismatched pad widths: `BUG-9`'s stored parent was `BUG-000010`):
    
    - `sq repair` exit 0, "rebuilt index: 10 items", did not hang, and both edges survived the rebuild byte for byte.
    - `sq check` exit **3**, one error per endpoint, each naming the whole chain and the remedy.
    - After `sq bug 9 update --no-parent`: `sq check` exit 0.
    
    No migration added, per the two settled reasons. Nothing here changes the schema, and `repair` is left reporting rather than repairing because choosing which edge to drop is a judgement about the operator's hierarchy.
    
    Tests: `tests/cli/test_check_and_repair_on_a_cyclic_corpus_cli.py` (check exit 3 + the `--json` shape as error-level + repair exit 0 with both edges intact) and, at service level, the report/recovery block of `tests/service/test_a_parent_cycle_is_refused_at_every_write_door.py`.
    
    One detail worth recording: a parent that resolves to nothing stops the ancestor walk and is left to `parent_in`'s dangling-parent branch, so a single broken edge is still reported once rather than as both a dangling parent and a cycle. Pinned by a test.
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Refuse an empty --parent value instead of reporting success

<!-- sq:subtask:ST4:body -->
`update --parent ""` prints a success line and exits 0 while changing nothing, because the CLI
tests the parent argument for truthiness before resolving it, so an empty string falls through to
the no-change path. Reject it with a message and a non-zero exit instead.

Folded in here rather than split: it is the same write door reporting success for a write it did
not perform, and it is the first thing an operator reaches for when trying to undo a bad parent
edge, so an operator hitting the primary defect hits this one immediately after.

The adjacent shape has the same cause and is worth closing in the same pass: an empty `--parent`
combined with the clearing flag slips past the mutual-exclusion guard for the same truthiness
reason.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
- [2026-09-02T08:13:31Z] Elias Python:
  - Fixed in `_cli/_items.py`'s `update`: the mutual-exclusion guard and the resolution below both now test `parent is not None` rather than truthiness, and an empty or whitespace-only value is refused outright.
    
    Driven, before: `sq feature 10 update --parent ""` printed `updated FEAT-10` and exited 0 with the parent untouched; `--parent "" --no-parent` also exited 0.
    
    Driven, after:
    - `--parent ""` → `error: --parent needs an item ID; use --no-parent to clear the parent`, exit 1, no success line.
    - `--parent "   "` → same refusal, exit 1.
    - `--parent "" --no-parent` → `error: use either --parent or --no-parent, not both`, exit 1 (caught by the mutual-exclusion guard, as the task asked).
    - `--no-parent`, `--parent EPIC-9` and `--parent 9` all still exit 0 and write what they say.
    
    Two things I found while there, one folded in and one deliberately not:
    
    **Folded in.** The `--priority`/`--no-priority` pair on the very next line had the identical truthiness shape: `--priority "" --no-priority` slipped past the guard and took the clear path. One word, same guard, no valid invocation changes. (`--priority ""` alone was already refused by the service's own field check, so only the paired form was reachable.)
    
    **Not folded in — reporting instead.** `sq create <type> "…" --parent ""` has the same cause and is still silent: it exits 0 and creates a parentless item. The write is legitimate in itself, so it is not the "success line for a write that did not happen" shape this subtask names, but it is the same truthiness bug on the same option in `_cli/_create.py` (three sites: lines 103, 357, 445). Left alone because the brief scoped this subtask to `_cli/_items.py`; flagging it rather than deciding it.
    
    Tests: `tests/cli/test_an_empty_parent_value_is_refused_not_reported_as_updated.py`.
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Falsify each guard before handing back

<!-- sq:subtask:ST5:body -->
For each of the three guards — the validator, the upward walk, the downward walk — remove it, watch
the test that pins it go red, restore it, watch it go green. Report both observations in the
handoff, per guard.

This is required rather than advisory. Three defects this release shipped inside commits whose own
new test suites passed, because the tests were written to confirm the change rather than to
disprove it. A test that has never been observed failing has not been shown to test anything.

Cover the shape families, not one instance per branch: self-parent and mutual pair and a longer
transitive chain, both exposed types, every parent-setting entry point, and every tree form
including the targeted-unrelated-root and depth-bounded ones that a naive fix would appear to pass.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
- [2026-09-02T08:25:00Z] Elias Python:
  - Each of the three guards was removed, the suite re-run, the guard restored, and the suite re-run again. Both observations per guard, verbatim.
    
    **1. The validator.** Neutered the body of `_parent_acyclic` (an early `return []`, so the wiring, the closure assertion and the catalog all stay intact and only the behaviour is gone).
    - removed → `14 failed, 5 passed` across `test_a_parent_cycle_is_refused_at_every_write_door.py` and `test_check_and_repair_on_a_cyclic_corpus_cli.py` — every entry point, every shape, both the gate and the report surface.
    - restored → `19 passed`.
    
    Also tried removing `parent_acyclic` from `COMMON_CORE` instead: that fires the catalog's own closure assertion at import (`every validator must be guarded by a consistency clause, common-core, or named unguarded`) and gives a collection error rather than behavioural reds — a real signal about the closure guard, but not a falsification, which is why the body was neutered instead.
    
    **2. The upward walk (`_compute_keep_set`).** Dropped the visited-set lines.
    - removed → `5 failed, 6 passed` in `test_tree_walks_terminate_on_a_cyclic_parent_relation.py`, in 0.18s; and `2 failed in 180.43s` in `test_every_tree_form_returns_on_a_cyclic_corpus_cli.py`, through `subprocess.TimeoutExpired`.
    - restored → `11 passed` / `2 passed`.
    
    The unit reds are fast because the fixture's `id_map` caps how many times it may be read. Without that cap the unguarded walk is a busy loop that raises nothing and never returns, so removing the guard would have suspended the worker rather than failed it — and a test that can only hang has not been shown to test anything. The subprocess timeout does the same job at the corpus level.
    
    **3. The downward walk (`_walk_tree`).** Dropped the `ancestors` membership test.
    - removed → `5 failed, 6 passed` (unit, `RecursionError`) and `2 failed` (the tree-form CLI module: one form exits 1 instead of 0, one renders nothing).
    - restored → `11 passed` / `2 passed`.
    
    **4. The empty `--parent` fix**, falsified the same way — reverted the four edits in `_cli/_items.py`:
    - removed → `3 failed, 2 passed`.
    - restored → `5 passed`.
    
    One of that module's five tests (`test_a_whitespace_only_parent_is_refused_the_same_way`) did **not** go red on its own, because a whitespace value is truthy and the id parser refused it further down anyway. It is a behaviour pin, not a falsification, so it now asserts the specific message the guard produces rather than just a non-zero exit — which does distinguish the two paths.
    
    Shape families rather than one instance per branch: self-parent, mutual pair and a three-item chain are each parameterised across both walks and driven through the gate; both exposed bundled types get their own self-parent case; all four parent-setting entry points plus the importer are covered at service level; and nine tree forms — including the targeted-unrelated-root and both depth-bounded ones a naive fix would appear to pass — run as bounded subprocesses.
    
    Full suite, run once with all extras: **`4418 passed, 7 skipped in 85.22s (0:01:25)`**, zero `FAILED` lines (baseline 4381 passed / 7 skipped; the 37 added are exactly the new tests). `pyright` 0 errors, `ruff check` clean, `ruff format --check` clean, `sq check` exit 0.
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-02T07:53:47Z] Olivia Lead:
  - Authored off op-pierre's ruling that this defect lands in 0.14. One task, five subtasks — the
    surface is coherent and the owner role is the same throughout, so no sibling tasks.
    
    @qa your primary-defect call stands and I have adopted it, with one sharpening written into the
    body: the write door is primary, but the gate is not *every* door. `repair` rebuilds the index from
    markdown without gating, an adopted corpus arrives that way, and frontmatter is editable in
    principle. So the two defensive walks are not defence-in-depth here — they cover the doors the gate
    cannot reach, which is also what makes the detection half necessary rather than merely nice. Your
    second-fault finding is carried explicitly: guarding the upward loop alone converts the hang into a
    crash, and the downward recursion gets a test that reaches it directly, because once the upward
    guard lands nothing on the public path can reach it any more.
    
    Three points settled, all in the body:
    
    - The fix is one error-level catalog member on the always-on floor, not an inline check in the
      parent-setting path. Four sites set a parent and gate afterwards (create, the shared update core
      the importer routes through, link, retype); an inline check would be repeated at each and
      forgotten at the fifth. Floor placement also gives the check surface for free.
    - Transitive cycles are in scope, not only self-parent. A walk that catches one and a walk that
      catches any differ by nothing — both are an ancestor walk with a visited set. Catching only
      self-parent leaves the identical hang reachable in two commands.
    - An existing cycle gets a check finding and no migration, for two independent reasons: no schema
      change means a runner never visits a corpus already stamped current (the region strip proved that
      this cycle and had to be re-homed onto the repair walk), and breaking a cycle means choosing which
      edge to drop, which is a judgement about someone's hierarchy, not a mechanical rewrite. `repair`
      reports and leaves the edges alone.
    
    The empty `--parent ""` no-op is folded in rather than split — same write door, same class of
    fault, two lines. The adjacent shape (empty value plus the clearing flag slipping past the
    mutual-exclusion guard) has the same cause and closes in the same pass.
    
    @architect noted your catalog record proposes this member. I have used the same name, but the task
    stands on the shipped composition machinery alone and does not depend on your wider catalog design
    being ruled. Nothing here forecloses it.
- [2026-09-02T08:25:33Z] Elias Python:
  - Built and handed back. Per-subtask detail is on ST1-ST5's own discussions; two things there that contradict the brief: the downward walk is NOT unreachable through the public path once the upward guard lands (ST2), and sq create --parent "" still has the truthiness bug I left out of scope (ST4). Full suite 4418 passed, 7 skipped, 0 failed; pyright/ruff/sq check clean. Nothing committed. @tech-lead @reviewer
- [2026-09-02T08:44:45Z] Catherine Manager:
  - Reopened InReview->InProgress. Acceptance is not met: the settled consequence recorded on this task says an item inside a cycle cannot be updated at all, a status change included. QA drove the shortcut verb and it exits 0 and writes the transition — sq <type> <n> status <S> goes through set_status, a separate service path that never reaches ValidatorEngine.gate, while update --status on the same item exits 1.
  - Not amending the clause to match what shipped. The verb's own help calls it a shortcut for update --status; either it enforces the same gate or the task's prose stops claiming it does, and the first is the honest one.
  - Also folding in the retype refusal message, which prints a chain reading as unclosed (REV-10 -> BUG-9 -> BUG-10). Correct on sequence identity since the prospective item keeps its number, but the operator sees two endpoints against a message required to name both.
- [2026-09-02T09:23:56Z] Elias Python:
  - - Reopened clause closed: the `status` verb now reaches the same gate. The gate call moved onto the shared transition core (`_set_status_model` in `_services/_items.py`), where `_update_model` already has one, so `set_status`, `set_roster_status` and the bulk importer's status events (pre-pass and apply) all refuse what `update --status` refuses. I did not narrow the acceptance.
    
    - Driven before, on a frontmatter-built cross-width cycle: `sq bug 9 status InProgress` exit **0**, transition written, while `sq bug 9 update --status InProgress` exit 1. After: exit 1, `BUG-9's parent chain forms a cycle: BUG-9 -> BUG-10 -> BUG-9; break it with sq bug 10 update --no-parent`, status unchanged. `--force` does not carry past it (it overrides the lifecycle edge, never the catalog). An item outside the loop still transitions, exit 0.
    
    - **Recovery is intact.** `update --no-parent` never runs through the transition core, so the way out is untouched: cyclic corpus -> `sq check` exit 3 -> `status` refused exit 1 -> `sq bug 10 update --no-parent` exit 0 -> `sq check` exit 0 -> `sq bug 9 status InProgress` exit 0 -> `sq tree -a` exit 0. Re-driven end to end after the change on the same cross-width shape QA used. No release blocker.
    
    - **The full list of doors still around the gate**, driven at the CLI against an item inside a cycle rather than read off the source. Refused (exit 1): `status`, `update` on every axis, `retype`. Accepted (exit 0): `body`, `comment`, `ref add`, `ref rm`, every sub-entity verb (`add-subtask`/`add-story`/`add-finding`, `<kind> <k> update`, `<kind> <k> body`, `<kind> <k> comment`, `<kind> <k> rm`), `rm`/`rm --purge`, `set-default`, and the corpus-wide maintenance walks (`repair`, `renumber`, `sync`, `migrate`, the seeders, `rename_type`/`rename_status`/`repad`). `Service.link` gates and `Service.unlink` does not, but neither has a CLI surface.
    
    - My read of that list, for a ruling rather than asserted as one: the status verb was the only genuine instance of the reported fault, because it is the only ungated door that is documented as an alias of a gated one. The others split into three kinds — prose appends (`body`, `comment`) whose refusal would block the discussion in which recovery is coordinated; parent-clearing and destructive doors (`unlink`, `rm`) which are the way out of a cycle, not a way into one; and the maintenance walks, which the task settles explicitly as report-only. The sub-entity doors are the one group I would not wave through on those grounds: they write the parent item's frontmatter and bypass two error-level members (`subentity_status_valid`, `subtask_story_mapping`) as well as `parent_acyclic`, so they are a real gate gap — but it is a wider one than this clause, since it is about sub-entity writes never being gated at all rather than about a cycle. Flagging it rather than deciding it. No ungated door can create or preserve a parent cycle: all four parent-setting doors gate.
    
    - **Retype refusal message.** It read `REV-10's parent chain forms a cycle: REV-10 -> BUG-9 -> BUG-10` — correct on sequence identity, two endpoints to an operator. The chain now names the closing endpoint as the head with the stored spelling alongside when the head carries a prospective id: `REV-10's parent chain forms a cycle: REV-10 -> BUG-9 -> REV-10 (stored as BUG-10); break it with sq bug 9 update --no-parent`. The aside appears only in that case; every other refusal is byte-identical to before (pinned by a test). Remedy line untouched.
    
    - Falsified, both guards. Status gate removed -> `4 failed, 2 passed` in the new CLI module; restored -> `6 passed`. Retype aside neutered (`restyled = False`) -> the reclassification test red, the ordinary-refusal and check/repair modules still green (so the aside is not load-bearing anywhere it should not be); restored -> all green.
    
    - Tests: `tests/cli/test_the_status_shortcut_refuses_what_update_status_refuses_cli.py` (6, including the roster status verb — the roster category's status axis is unreachable through `update` at all, so it is the case that proves the gate had to go on the transition core and not on the update seam) and 6 added to `tests/service/test_a_parent_cycle_is_refused_at_every_write_door.py`. Nothing existing weakened.
    
    - Gates: full suite once with all extras, **`4435 passed, 7 skipped in 66.40s`**, zero FAILED lines (baseline 4423/7; +12 = exactly the new tests). pyright 0 errors, `ruff check` clean, `ruff format --check` clean, `sq check` exit 0. No bundled template or spec touched. Nothing committed.
    
    - One consequence to record rather than bury: a roster entry whose frontmatter was hand-edited into a self-parent can no longer change status either, and the roster surface has no `update --no-parent` — recovery there is `rm` or fixing the frontmatter back. Roster items cannot acquire a parent through any command, so this is only reachable by hand-editing, and `sq check` already errored on that corpus before this change.
    
    @manager @qa ready for re-verification.
- [2026-09-02T09:26:40Z] Catherine Manager:
  - Ruling on the clause's literal reading, which the dev raised rather than quietly narrowing: his reading is the right one. 'Cannot be updated' names the metadata-update axis — the update verb and its shortcut — not every write. Blocking body and comment would block the discussion an operator uses to coordinate recovery, which would make the fail-closed design worse, not safer. The clause stands as written and is now met.
  - His roster-path consequence is accepted: a roster entry hand-edited into a self-parent can no longer change status, and the roster surface has no --no-parent. Only reachable by hand-editing, and sq check already errored on that corpus beforehand. Not exempting the roster path to avoid it.
- [2026-09-02T09:47:57Z] Mara Tester:
  - The sub-entity gate gap Elias flagged rather than decided is now BUG-873 (linked `related` to BUG-865). Verified at the CLI, not transcribed: the structural claim holds, `subentity_status_valid` is reachable through `<kind> <k> update --status … --force` at exit 0 with `sq check` exit 3 after, but `subtask_story_mapping` is held shut by bespoke guards on every door and cannot be violated through the shipped CLI. Nothing here reopens this task. @tech-lead
<!-- sq:discussion:end -->
