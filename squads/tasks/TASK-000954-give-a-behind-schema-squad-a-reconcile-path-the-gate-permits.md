---
id: TASK-954
sequence_id: 954
type: task
title: Give a behind-schema squad a reconcile path the gate permits
status: Draft
author: tech-lead
priority: high
refs:
- REV-952:fixes
description: require_current_schema exempts only migrate, so every remedy naming sq
  repair is unreachable exactly when it is needed; needs a ruling on what repair may
  do under a stale schema
subentities:
- local_id: ST1
  title: Inventory every remedy that names a gate-refused command
  status: Todo
- local_id: ST2
  title: Narrow what repair may do on a behind-schema squad, then exempt it
  status: Todo
- local_id: ST3
  title: Drive the escape end to end on a behind-schema squad
  status: Todo
created_at: '2026-09-15T08:41:13Z'
updated_at: '2026-09-15T09:00:25Z'
---
<!-- sq:body -->
## Scope

`require_current_schema` (`src/squads/_cli/_common.py`) exempts only `migrate` and `--help`. So a
squad whose on-disk schema is behind the installed package has exactly one command available, and
every remedy the codebase names for the state a failed or interrupted migration leaves —
`sq repair` — is refused precisely when it is needed.

This is a **general** hazard, not one migration's. The 0.14 to 0.15 runner surfaced it because its
abort paths all pointed there, and that runner's own abort paths are being removed under its
feature. What is left standing is the shape itself: any future runner that raises, and any
`migrate up` interrupted between the markdown writes and the index commit, lands a squad in the
markdown-ahead-of-index state the index store's docstring sanctions **because** `sq repair` heals
it losslessly — and `sq repair` cannot be run.

Filed outside the milestone-view feature deliberately: the surface is a gate every command passes
through, its blast radius is every schema version and every migration, and the feature must stay
closable without it.

## The question that has to be answered first

**Exempting `repair` is not obviously safe, and that is the decision this needs.** `sq repair`
does not only rebuild the index. It runs the retired-region strip sweep and the roster body-tag
convergence (`_services/_maintenance.py`), both of which rewrite item bodies using the *installed*
package's vocabulary. Run against a corpus still on the older schema, that is the new vocabulary
touching pre-migration prose — exactly the staleness the gate exists to prevent, and a content
rewrite rather than a reconciliation.

So the shape is not "add `repair` to the exempt tuple". It is: decide what a reconcile is allowed
to do on a behind-schema squad, and expose only that. Plausible narrowings, for the ruling to
choose between rather than for this task to assume:

- Exempt `repair` but refuse its content-rewriting sweeps while the schema is behind, leaving the
  index rebuild — the part that is genuinely version-neutral.
- Exempt `repair` wholesale on the argument that a rebuild answers from the frontmatter and not
  from vocabulary, if that argument survives contact with the sweeps.
- Leave the gate alone and give `migrate up` its own reconcile step, so the recovery is inside the
  one command that is already exempt.

**This does not dispatch to an implementer before that ruling exists.** The work below is scoped
against the narrowing, not against a chosen answer.

## Constraints

- Gates run with `uv run --all-extras` (`pyright`, `ruff check .`, `ruff format --check`, targeted
  `pytest`). A bare `uv run` prunes the optional `tui` extra and reports false import errors.
- Do not run the full suite; targeted selectors only, and report which were run.
- Falsify each behaviour: break it, watch the test go red, restore, watch it go green, report both.
- Drive the result on a real behind-schema scratch squad, not only in unit tests: hand-downgrade
  `schema_version`, then confirm the intended command runs and the others still do not.
- `sq check` clean before handback. No ticket ids in source or test filenames.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 954 add-subtask "<title>"`; track with `sq task 954 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Inventory every remedy that names a gate-refused command

<!-- sq:subtask:ST1:body -->
Before deciding anything, establish how wide the false-remedy surface actually is. The 0.14 to
0.15 runner was found pointing at `sq repair` from three abort messages and twice more in its
module docstring; it is very unlikely to be the only place.

Sweep for every message, docstring and piece of documentation that tells an operator to run a
command, and mark the ones that are only reachable from a state where the schema gate refuses
them: the migration runners, `sq migrate up`'s own output, the index store's module docstring
(which names `sq repair` as the loss-less heal for the markdown-ahead-of-index direction), the
adopter-facing docs, and the managed regions.

For each hit record: which state it fires in, whether the schema is necessarily behind in that
state, and what the operator can actually run. That table is the input to the narrowing decision —
if most hits turn out to be reachable only with a current schema, the gate change shrinks a lot.

Validate the sweep against a known positive before trusting a zero result from any pattern.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Narrow what repair may do on a behind-schema squad, then exempt it

<!-- sq:subtask:ST2:body -->
Lands only after the ruling described in the task scope. The implementation is whichever narrowing
is chosen; what is fixed regardless is the shape of the obligation.

Whatever is exempted must be **reconcile-only** in the behind-schema window. `sq repair` today also
runs the retired-region strip sweep and the roster body-tag convergence, both of which rewrite item
bodies using the installed package's vocabulary; letting those touch a pre-migration corpus is the
staleness the gate exists to prevent, and is a content rewrite rather than a reconciliation. An
exemption that carries those sweeps along is not the fix, it is a second, quieter version of the
same bug.

The gate's two other behaviours stay intact: a squad **ahead** of the package is still refused
outright, and every command that answers from vocabulary is still refused while the schema is
behind. Widening the exemption tuple is the last line of the change, not the first.

`sq repair` already uses `get_service_bypassing_index_cross_check` rather than the ordinary service
accessor, on the argument that its whole job is reconciling in states other commands refuse. That
is the same argument, one layer up, and is the natural place to look for the seam.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Drive the escape end to end on a behind-schema squad

<!-- sq:subtask:ST3:body -->
The proof is a scratch squad, not a unit test: hand-downgrade `schema_version` below the installed
package's, then confirm the exempted path runs and produces a squad the operator can work in, and
that everything the gate should still refuse still exits 1 with its message.

Cover at least: a behind-schema squad with a clean index; one with markdown genuinely ahead of the
index (the state an interrupted migration leaves); one with a skewed item; and a squad **ahead** of
the package, which must still be refused.

Assert the operator's position after the escape, not just its exit code — that the reconcile
happened, that no body was rewritten under the old schema, and that `sq migrate up` then runs to
completion from there. A test that only checks the command no longer exits 1 proves nothing about
whether the squad is usable.

Falsify each: break the narrowing, watch the test go red, restore, watch it go green, report both.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-15T09:00:25Z] Robert Architect:
  - Ruled in ADR-955 (refs this task). The answer is a rule about operations, not an exemption list.
    
    **The reconcile licence.** Behind the schema gate an operation may run only if it is (1) vocabulary-blind — no spec-resolved type/status/prefix/folder/ref-kind/view/badge value decides its behaviour; (2) content-neutral — it writes no body and no frontmatter value, only derived state (the index), stamped at the *corpus's* schema, not the installed one; (3) convergent — it leaves the squad no further from a successful `sq migrate up`. Anything failing (1) or (2) is a migration step and belongs in a versioned runner. That is what the next migration inherits.
    
    **`sq repair` is not exempted, in any form** — not wholesale, not behind a "skip the sweeps" flag. It reads installed vocabulary at six points and writes at four (the ref fold + canonical re-encoding, vocab validation, the retired-region strip, the body-tag convergence, retired role `extra` keys), globs by the active spec's folders, and stamps `SCHEMA_VERSION` into the rebuilt index. Its own docstring also derives its strip-ordering proof *from* the gate refusing it, so an exemption deletes a construction proof.
    
    **ST2 is rescoped, and the gate is not touched.** The licensed subset is separable — structural scan vs semantic sweep — but as its own narrow routine, not a mode on `repair`; and its home is `migrate up`'s **unconditional pre-pass**, before the first runner. That closes the deadlock inside the one command already permitted, so the exempt set stays at one. Later widening arrives as a declared capability on the command plus a meta-test binding the exempt set to it, never a second literal in a tuple.
    
    **One obligation the task does not have yet:** `migrate up` builds via `get_service()`, so a behind-schema squad carrying `.overrides/workflow.toml` can still be refused by `open_service`'s live-index cross-check — for the same class of reason the gate exempted it. The exempt command must build through `get_service_bypassing_index_cross_check()`, or the exemption is nominal.
    
    **ST1 stands and now has a rule to sweep against:** a remedy may only name a command permitted in the state it fires in. Three sites read — the 0.14/0.15 runner's messages and docstring; `_index/_store.py`'s module docstring (true at current schema, false behind the gate, and it must say which); `_itemfile.skew_message` (correct for its ordinary callers, so a runner composes its own remedy clause rather than inheriting it). A meta-test over runner modules is the cheap enforcement.
    
    **Ahead-of-package is unchanged**, and now derived rather than incidental: it fails content-neutrality, because this package cannot round-trip a newer corpus, so a rebuilt index is a lossy write of derived state. Its message already names a remedy that exists.
    
    Left open in the ADR: no deliberate verb for a licensed reconcile; a runner whose own refusal is the wall is not fixed by this; whether the licence should also govern reads.
    
    @manager ADR-955 is in its initial status for op-pierre. ST2/ST3 land against the licence, not against a chosen command.
<!-- sq:discussion:end -->
