---
id: TASK-782
sequence_id: 782
type: task
title: Fix the blank-name bypass, the skew report, and two stale comments
status: Done
author: tech-lead
assignee: python-dev
priority: medium
refs:
- BUG-778:fixes
- BUG-779:fixes
- BUG-780:fixes
- REV-770:addresses
description: 'Three defects in and beside the role-projection seam: an operator-reachable
  blank name, a duplicated skew warning plus a mis-named test, and two false in-code
  justifications'
subentities:
- local_id: ST1
  title: Refuse a blank operator-supplied role name at one seam
  status: Done
- local_id: ST2
  title: Report one skew divergence once, and fix the interrupted-write test
  status: Done
- local_id: ST3
  title: Correct two false in-code justifications in the same seam
  status: Done
created_at: '2026-08-22T09:50:14Z'
updated_at: '2026-08-22T14:17:41Z'
---
<!-- sq:body -->
Three defects in and beside the role-projection seam, one owner. Subtask order is the order they
should be done in: ST1 is a real hole an operator can drive into a generated file today, ST2 is the
observable-behaviour change the projection introduced plus the test that was supposed to pin it, and
ST3 is comment-only accuracy work on the same code.

## Handoff, for all three subtasks

**Do not edit `CHANGELOG.md`.** Hand the tech lead your adopter-facing entry text in your handoff
comment and it gets applied there.

Per subtask: ST1 warrants an entry (an operator-reachable blank name now refuses). ST2's entry
depends on what it ends up changing — say what you think it should say. **ST3 needs no changelog
entry at all**: it changes no behaviour, and a comment correction is not adopter-facing. Say so
rather than inventing one.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 782 add-subtask "<title>"`; track with `sq task 782 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Refuse a blank operator-supplied role name at one seam |  |
| ST2 | Done |  | Report one skew divergence once, and fix the interrupted-write test |  |
| ST3 | Done |  | Correct two false in-code justifications in the same seam |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Refuse a blank operator-supplied role name at one seam

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
The blank/whitespace-string refusal lives entirely in `_apply_override` — the merge point for a
`.overrides/roles/<slug>.toml`. The two CLI paths that let an operator set a name directly never
reach it, because both build a `RoleDef` straight from the CLI argument: `activate_role` via
`dc_replace(role, full_name=name)`, `add_dev` via `resolve_dev_role`/`dev_role`. `Item.title`'s own
`NonEmpty` constraint is satisfied by a whitespace-only string.

Driven, fresh squad:

```
sq dev add --tech go --name "   "
  added (`go-dev`) ROLE-12                                            exit 0
  frontmatter                title: '   ', extra.full_name: '   '
  CLAUDE.md                  - **   ** — Go developer (`go-dev`)
  .claude/agents/go-dev.md   "You are **   **, the Go developer on this project."
  sq check                                                            exit 0

sq role activate architect --name "   "
  activated (ROLE-13)                                                 exit 0
  frontmatter                title: '   ', extra.full_name: '   '
  CLAUDE.md                  - **   ** — architect (`architect`)
  sq check                                                            exit 0
```

The same value through the already-fixed override path on the same squad refuses at exit 1, naming
the file and the field. So this is the same symptom the override refusal was written to stop —
including the `.claude/` pointer's identity sentence, the surface that was called the worst instance
because it is prose an agent reads as its own identity — reachable through two documented flags.

## The shape to avoid, and where the paths actually converge

**Do not add a second check at each call site.** The whole point of the original finding was one
refusal for one rule; three copies of the rule in three places is the defect being re-created in a
tidier form, and the fourth path added later would start the hole over.

Read the three paths and they do converge: every one of them ends in a `RoleDef` whose `full_name` is
the operator-supplied string — the override path through `role_spec_to_def`, `activate_role` through
`dc_replace` (which runs `__post_init__`, since `RoleDef` is a frozen dataclass), and `add_dev`
through `dev_role`'s constructor call. That construction point is the one place all three reach.
Use it, or name a better single seam and say why it is better — but the deliverable is **one place
that enforces the rule**, not three that agree today.

## The override path's message must not change

The override refusal produces an adopter-facing message naming the file and every offending field.
That message is the reason the file path's check exists where it does, and it must read exactly as it
reads today. If the shared enforcement point cannot produce it, the file-path check stays as the
message-shaping layer on top of the structural one — that is not a second copy of the rule, it is one
rule with a better message for the one input that has a filename to name.

While you are there: `_refuse_blank_strings`' docstring justifies its placement with "the only place
a `RoleSpec` is built from adopter-editable text is this function". These two flags are adopter-editable
text arriving by another route, so that sentence is part of what this defect proved wrong. Correct it.

## The empty-string asymmetry — drive it, do not assume it

`--name ""` and `--name "   "` behave differently, and the two commands differ from each other:

- `dev_role` tests `if name:`, so `--name ""` is falsy and falls through to the pool name — driven,
  `sq dev add --tech rust --name ""` produces a normal pool name, not a blank one.
- `activate_role` tests `if name is not None:`, so `--name ""` does *not* fall through the same way.

**Drive both commands with `""` and with `"   "` before deciding what each should do.** The reported
behaviour covers `sq dev add` for the empty case; the activate path was not separately driven and the
code differs, so do not carry the claim across. The intended end state is that both forms refuse for
the same reason the override path refuses them, rather than one being silently ignored and the other
silently accepted — but confirm what each does now, and say so.

## Acceptance criteria

- `sq dev add --tech <t> --name "   "` and `sq role activate <slug> --name "   "` both refuse, at a
  non-zero exit, with a message that names the offending field. No role item is created, and no
  generated file is written — assert the absence, not just the exit code.
- Both commands refuse `--name ""` too, with the behaviour of each before the change recorded in the
  handoff.
- **Both role kinds**: a bundled slug through `activate`, and a developer slug through `dev add`.
- The override path's refusal message is **byte-identical** to today's — its own test asserts the
  exact string.
- **One enforcement point.** State in the handoff where it is, and that no per-call-site copy of the
  rule was added. A test that constructs a `RoleDef` (or whatever seam you chose) with a blank
  `full_name` directly and expects a refusal, so the rule is pinned at the seam rather than only
  through two CLI commands.
- A valid name still works unchanged on both commands, including a name with internal whitespace
  (`"Ada Lovelace"`) and one with leading/trailing whitespace around real content — decide and state
  whether the latter is trimmed or preserved.
- `_refuse_blank_strings`' docstring no longer claims the override file is the only adopter-editable
  path.
- `sq check` is clean on the resulting squad, and the previously-driven blank squads are no longer
  reachable.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Report one skew divergence once, and fix the interrupted-write test

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Two deliverables here, both settled. The larger question the reported behaviour raises is **not** this
subtask's to answer — see "Referred, and not to be decided in code" below, and do not implement
either answer to it as a side effect of the two deliverables.

## The observable change, re-driven

`title`/`description` are ordinary top-level frontmatter keys, so `frontmatter_skew` compares them on
every write — `_without_permitted_extra_skew` structurally cannot exempt a top-level field, only a
key inside `extra`. With the index rolled back on an activated role's `title`/`description` to
simulate an interrupted write (markdown ahead — the state invariant 8 sanctions), `sq sync` reports:

```
warning: ROLE-2: on-disk frontmatter has diverged from the index (description, title)
         — run `sq repair` before mutating ROLE-2 again
warning: ROLE-2: on-disk frontmatter has diverged from the index (description, title)
         — run `sq repair` before mutating ROLE-2 again
synced managed files to this squads version                       exit 0
index title: 'Rob'    markdown title: 'Ada Lovelace'              (both unchanged)
sq check                                                          exit 0, no mention
sq repair                                                         heals both sides
```

Driven on the commit before the projection, rolling back `extra.full_name` instead: `sq sync` exits 0
with no warning and both sides agree again after one sync, because that key sits in
`PERMITTED_EXTRA_SKEW` and was never compared.

**Framing this matters.** The old behaviour was a silent self-heal of a real divergence, which is
arguably the worse of the two — the guard doing its job here is correct and documented. So this is not
a restoration job, and nothing in this subtask should be built to make sync silent again.

## Deliverable 1 — the report is duplicated, and that is a defect on its own terms

The identical warning line prints once per writer that hits the same skew check on the same role. The
roster loop now runs three writers per role (`_refresh_catalog_extra`, `_refresh_role_skills_extra`,
`_project_roster_item`), each appending its own message to the same collection, so one divergence
reads as two or more separate problems and names `sq repair` two or more times.

One divergence on one item is one thing to report. Deduplicate where the messages are assembled or
reported, not by removing a writer's ability to report — a second, genuinely different message about
the same item must still get through.

Note while you are there, and report rather than fix: once this triggers, the role is stuck for
*every* refresh writer, so its `extra.skills` cache and rendered body also stop refreshing, not only
the catalog/title merge. Say whether the deduplicated message should say that, since an operator
reading "run `sq repair`" does not currently learn how much has stopped.

## Deliverable 2 — the test names a shape it does not cover

`tests/service/test_role_projects_resolved_name_and_mission_onto_item_fields.py::test_repair_and_a_further_sync_are_unaffected_by_the_interrupted_role_write`
patches `maintenance.update_frontmatter` with a raising stand-in. That function's own last statement
is the `_aio.atomic_write_text` call, so replacing the whole function means the markdown write is
never reached and the transaction that would commit the index is never entered. The state left behind
is **nothing written on either side** — not the shape the name promises (markdown written, index
commit not reached). It also never calls `svc.repair()`, despite that being the first word of its name,
and its `assert not second_sync` holds only for the shape it actually creates: a retry from a clean
state, where the second attempt simply succeeds.

The test is not worthless — it is a real falsifier for the in-memory rollback on a failed write, and
that coverage must survive. The defect is that its name claims a different, uncovered shape.

**The test must cover the shape in its own name**, or be renamed to the shape it covers and the named
shape covered by a new test alongside it. Either resolution is fine; a test whose name promises
coverage it does not provide is not.

## Referred, and not to be decided in code

The reported behaviour raises a question this subtask does not answer: a projected field is derived
data with exactly one writer, so should a divergence on it be healed by re-deriving the projection
rather than refused as skew? That question is being routed to the architect, because answering it
touches two things a dev should not move alone:

- **Direction.** `_refresh_catalog_extra` operates on the item as loaded from the *index*, and the
  name precedence's tier 2 is the item's own stored value — so "re-derive" would resolve a divergence
  by adopting the index's copy and writing it to markdown. That is index-ahead-of-markdown becoming
  authoritative, which is the direction invariant 8 exists to forbid; `sq repair` rebuilds the index
  *from* markdown, which is the sanctioned direction. Any heal-by-re-derivation has to answer this
  before it is safe, not after.
- **A standing rule.** The projection decision states the skew guard needs zero change and that
  extending its exemption to these fields is a regression, not a hardening.

**So in this subtask: do not extend the skew guard's exemption to `title`/`description`, and do not
add a re-derive heal path.** Both deliverables above are independent of that answer and stand whichever
way it lands.

## Acceptance criteria

- One divergence on one role produces **exactly one** warning line from a single `sq sync`, asserted
  by count rather than by substring presence.
- A second, genuinely different message about the same item still reaches the operator — covered by a
  test, so the deduplication cannot swallow real information.
- The `sq repair` → `sq sync` sequence after a real divergence still converges and stays silent
  afterwards, unchanged.
- The interrupted-write test covers the shape its name states: markdown written, index commit not
  reached, then a `svc.repair()` call and a further sync — or it is renamed to what it does cover and
  the named shape gets its own test. State which resolution you chose.
- **The existing rollback coverage survives.** Whatever you do to that test, the in-memory rollback on
  a failed write is still falsified by something: break the rollback and a test must go red. Drive it
  and report both directions.
- No change to `PERMITTED_EXTRA_SKEW`, `_without_permitted_extra_skew`, or `frontmatter_skew`, and no
  new heal path — assert the guard's membership is unchanged.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Correct two false in-code justifications in the same seam

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Two stale in-code justifications in the same seam. **Comment-only: no behaviour changes, no test
behaviour changes.** The value is that a future implementer reads a reason that actually holds.

The rule for both corrections: **state the reason that is true, not a softened version of the false
one.** Hedging a false premise into a vaguer one leaves the next reader with the same wrong model.

## 1. `_RECONCILED_EXTRA_KEYS`' comment states a false premise

`src/squads/_roles/_catalog.py`. The comment justifying keeping `description` out of `extra_keys()`
(and so out of `PERMITTED_EXTRA_SKEW`) reads:

> `description` carries no such legacy corpus: before this table existed, nothing ever wrote
> `extra.description`, so there is no lagging index to forgive …

False. `git show ea891a6:src/squads/_services/_roster.py` — the 0.13.0 release tag — already writes
`X.DESCRIPTION: role.description` explicitly at both `activate_role` and `add_dev`, the same two
lines it is at today, predating the table by several releases. Every role item in every existing
squad already carries `extra.description`.

**The conclusion survives for a different reason:** `create` writes that key inside its own
transaction, so markdown and index have never disagreed on it, and no exemption is owed on that
ground. The test docstring covering the same design
(`tests/unit/test_role_def_extra_keys.py`) already states the correct narrower claim — "no legacy
corpus that ever wrote `extra.description` **outside a transaction**" — so only the code comment
overreaches. Bring the comment into line with the test, not the other way round.

The comment closes with a rule for the next field: "a field belongs here … exactly when adding it
there would be a pure widening of the guard's exemption with no legacy case to justify it." A reader
applying that rule asks "was this key ever written before?" and gets the wrong answer for
`description` itself. The rule that actually holds — and that `PERMITTED_EXTRA_SKEW` exists for — is
**"was it ever written to markdown *outside* a transaction"**. Correct the rule as well as the
premise; the rule is the part that will be reused.

### Report, do not fix, in the same file

Now that `to_extra()` splats `_RECONCILED_EXTRA_KEYS` alongside `_EXTRA_FIELD_KEYS`, the explicit
`X.DESCRIPTION: role.description` at both create sites is a redundant second declaration of a value
already in the dict it overwrites. Harmless while the two agree; a future change to that table's
getter would silently not apply at create time, because the explicit line would keep winning.
Removing the two lines would make the table the single source of the mapping it claims to be — but
that is a behaviour-adjacent change and this subtask is comment-only. **Say in your handoff whether
it should be done and as what; do not do it here.**

## 2. `open_service`'s `resolved_spec` docstring misnames its own callers

`src/squads/_services/_service.py`. The docstring says the CLI root callback "is the one caller that
supplies it", and that "Every other caller — direct test calls, `sq ui`, the cross-check-bypassing
fallback path — leaves this `None`". Two of those three named exceptions are wrong:

- **`sq ui`** calls `get_service()`. The root `@app.callback()` binds the active spec for every
  invocation, `sq ui` included, so `ctx.active_spec` is populated by the time `ui()` runs. `sq ui` is
  sync and never crosses the async bridge, so the read-scope key is absent from `root.meta` and
  `get_service()` falls to `_build_plain_service()`, which calls
  `open_service(..., resolved_spec=ctx.active_spec)` — non-`None`. `sq ui` opts out of the read scope
  and the per-invocation `Service` memo, not out of `resolved_spec`.
- **The bypass path.** `get_service_bypassing_index_cross_check`'s step 1 is a direct `get_service()`
  call, so it supplies `resolved_spec` too. Only its steps 2/3 construct a `Service` directly, and
  that helper never calls `open_service` at all.

A direct test call remains a correct example. The same misattribution appears verbatim in two
docstrings in `tests/cli/test_workflow_cross_check_once_per_invocation.py`
(`test_open_service_direct_call_ignores_an_unrelated_ambient_spec` and
`test_resolved_spec_is_the_documented_opt_in_kwarg_default`). Both tests are sound — each exercises a
genuine direct `open_service()` call with no `resolved_spec` — so only the named example changes,
never the test bodies.

This matters because the enumeration **is** the safety argument for the per-invocation memo: "one
caller supplies the shortcut, everyone else validates independently." If the accurate answer is
instead "every CLI caller supplies it, and only non-CLI callers validate independently", that is a
materially larger claim about how much of the surface trusts a cached resolution. Write the claim
that is true, and if it is the larger one, let it read as the larger one rather than trimming it back
to sound like the old sentence.

There is no behavioural consequence today: `sq ui` builds one `Service` at startup and the TUI never
calls `open_service`/`get_service` again, so the cross-check runs once for that session either way.

## Acceptance criteria

- Each corrected comment states the reason that actually holds: the transaction-scoped write for
  `_RECONCILED_EXTRA_KEYS`, and the accurate caller enumeration for `resolved_spec`.
- The `_RECONCILED_EXTRA_KEYS` comment's forward-looking rule reads "written to markdown outside a
  transaction", not "ever written".
- The `_RECONCILED_EXTRA_KEYS` comment and `tests/unit/test_role_def_extra_keys.py`'s docstring now
  make the same claim as each other.
- All three `resolved_spec` misattributions are corrected — the one in `_service.py` and the two test
  docstrings — with **no test body changed**.
- **No behaviour change anywhere.** `git diff` touches comments, docstrings and `#:` blocks only; the
  full suite passes without any test being modified to accommodate this subtask.
- The redundant-create-site observation is reported in the handoff, not acted on.
- **No changelog entry** — say so in the handoff rather than supplying text.
- `uv run --all-extras pyright`, `ruff check`, `ruff format --check` and the full `pytest` suite are
  green; `uv run sq check` is clean.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T09:51:12Z] Olivia Lead:
  - One task, three subtasks, ordered ST1 (operator-reachable hole) then ST2 (behaviour change plus the mis-named test) then ST3 (comment-only). Refs: fixes all three bugs, addresses the review.
  - ST1: read the three paths and they do converge — every one ends in a RoleDef whose full_name is the operator string (role_spec_to_def for the file, dc_replace for activate since RoleDef is a frozen dataclass so __post_init__ runs, dev_role for dev add). Body names that as the single seam, requires the override message byte-identical (its own test asserts the string), and forbids the per-call-site shape. Also flagged that _refuse_blank_strings docstring claims the override file is the only adopter-editable path, which this defect disproves.
  - ST1 correction to the bug: the empty-string claim does not carry across commands. dev_role tests `if name:` (falsy fallthrough, as driven) but activate_role tests `if name is not None:`, so --name "" takes a different path there and was not separately driven. Body requires both commands driven with "" and "   " before deciding, rather than inheriting the dev-add result.
  - ST2 is scoped to the two settled deliverables (deduplicate the per-writer warning; make the interrupted-write test cover the shape its name states, keeping the rollback falsifier alive). The heal-vs-refuse question is explicitly NOT decided there and the body forbids both answers as side effects — see my handback for why I am routing it to the architect.
- [2026-08-22T10:16:11Z] Elias Python:
  - ST1 (BUG-778): seam is RoleDef.__post_init__ (src/squads/_roles/_catalog.py) -- all three paths (override merge via role_spec_to_def, activate_role's dc_replace, add_dev's dev_role() call) converge on constructing a RoleDef, and __post_init__ runs on every one incl. dataclasses.replace on a frozen dataclass. Only full_name is checked there -- the override's other fields stay _refuse_blank_strings's own job (kept, message untouched, its docstring's false only-adopter-editable-path claim corrected).
  - ST1 four driven cases: dev add --name '' and '   ' both now refuse (changed dev_role's if name: to if name is not None:, matching activate_role, so an explicit blank is no longer silently treated as omitted); role activate --name '' and '   ' both refuse (already used is not None, just never reached a check before). All four: exit!=0, message names full_name, no role item created, no generated file written -- pinned in tests/cli/test_blank_role_name_is_refused_at_the_shared_seam.py and at the seam directly in tests/unit/test_role_def_refuses_a_blank_full_name.py.
  - ST1 whitespace decision: padding around real content (e.g. '  Ada Lovelace  ') is accepted and stored verbatim, not trimmed -- matches the override path's own _refuse_blank_strings, which also only .strip()s to test blankness. Pinned by test.
  - ST1 changelog: 'A blank or whitespace-only --name on sq dev add / sq role activate is now refused, matching the existing role-override behaviour.'
  - ST2 (BUG-779) dedup: return list(dict.fromkeys(skipped)) at the end of sync() -- collapses exact-duplicate text only. Evidence: test_an_interrupted_index_commit_is_healed_by_repair_then_a_further_sync_is_silent asserts len([msg for msg in sync() if role.id in msg]) == 1 on a reproduced disk-ahead skew (both _refresh_catalog_extra and _refresh_role_skills_extra would otherwise each append the identical line). A second, genuinely different message on the SAME item (an unrenderable-model WARN alongside a real title skew, no override involved since override+bad-model is a separate pre-existing interaction) still gets through both, pinned in test_a_second_genuinely_different_message_about_the_same_item_still_gets_through.
  - ST2 test rename: test_repair_and_a_further_sync_are_unaffected_by_the_interrupted_role_write -> test_a_raised_write_rolls_back_in_memory_and_a_retry_from_a_clean_state_succeeds (states what it actually covers: in-memory rollback + clean retry, body unchanged). Added test_an_interrupted_index_commit_is_healed_by_repair_then_a_further_sync_is_silent for the shape the old name promised (index rolled back directly, disk stays ahead; one warning; svc.repair() heals; further sync silent).
  - ST2 rollback falsifier driven both directions: with the except-block's rollback intact, both tests pass; with it deliberately gutted to a bare 'pass' (temporary, reverted), both test_a_raised_write_rolls_back... and the pre-existing test_a_simulated_write_failure_leaves_the_item_truthful_to_disk_on_title_too go red (the corrupted in-memory item surfaces as a downstream skew). Restored and reverified green.
  - ST2 changelog: 'sq sync no longer reports the same frontmatter/index divergence more than once per sync.'
  - ST3 (BUG-780): comment-only, no behaviour change, git diff touches comments/docstrings only. _RECONCILED_EXTRA_KEYS's comment (_catalog.py) now says activate_role/add_dev always wrote extra.description inside their own transaction (verified: git show ea891a6:src/squads/_services/_roster.py lines 56/87), so markdown and index never disagreed on it -- and its forward rule now reads 'written to markdown outside a transaction', matching tests/unit/test_role_def_extra_keys.py's docstring exactly. open_service's resolved_spec docstring (_service.py) and the two test docstrings in tests/cli/test_workflow_cross_check_once_per_invocation.py now say sq ui and the bypass path's own first step both go through get_service() and so already supply resolved_spec; only a direct open_service() call (a test, typically) leaves it None. No test body changed.
  - ST3 reported, not fixed: the explicit X.DESCRIPTION: role.description lines at both create sites (_roster.py:56/87) are now a redundant second declaration of a value to_extra() already includes via _RECONCILED_EXTRA_KEYS -- harmless today, but a future change to that table's getter would silently not apply at create time since the explicit line keeps winning. Removing the two lines would make the table the sole source; left alone here since this subtask is comment-only.
  - ST3 changelog: none -- comment-only, no adopter-facing change.
  - Gates: pyright 0 errors, ruff check all passed, ruff format 533 files already formatted, tests/meta + all touched module tests green (332+ passed across the targeted runs), sq check clean, sq repair a stable no-op (rebuilt index identical on a repeated run). Commit c6a03b2e6122094e291048a9fafcc2759bd82c1a on release/0.14, unpushed; only src/squads/_roles/_catalog.py, src/squads/_roles/_resolver.py, src/squads/_services/_maintenance.py, src/squads/_services/_service.py, tests/cli/test_blank_role_name_is_refused_at_the_shared_seam.py (new), tests/unit/test_role_def_refuses_a_blank_full_name.py (new), tests/cli/test_workflow_cross_check_once_per_invocation.py, tests/service/test_role_projects_resolved_name_and_mission_onto_item_fields.py staged -- no squads/ files touched.
<!-- sq:discussion:end -->
