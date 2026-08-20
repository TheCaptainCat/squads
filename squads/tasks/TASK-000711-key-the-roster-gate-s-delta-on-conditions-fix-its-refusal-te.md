---
id: TASK-711
sequence_id: 711
type: task
title: Key the roster gate's delta on conditions, fix its refusal texts
status: Done
parent: FEAT-691
author: tech-lead
priority: urgent
refs:
- REV-706:addresses
- ADR-697:implements
description: Condition-keyed delta comparison, direction-correct remedies, the two-holder
  report, and the verb's help and reference text
subentities:
- local_id: ST1
  title: Compare the delta on the condition, not on its rendering
  status: Done
  story: US5
- local_id: ST2
  title: Name a remedy the transition direction will accept
  status: Done
  story: US5
- local_id: ST3
  title: State the reason the meaningless-unlink guard tested
  status: Done
  story: US5
- local_id: ST4
  title: Report two holders of the default designation
  status: Done
  story: US6
- local_id: ST5
  title: Describe both status flags in adopter vocabulary
  status: Done
  story: US3
- local_id: ST6
  title: Count the scopes kind in the ref-kind reference
  status: Done
- local_id: ST7
  title: Leave no gap where the omitted default-role line was
  status: Done
created_at: '2026-07-31T11:47:02Z'
updated_at: '2026-07-31T12:41:36Z'
---
<!-- sq:body -->
## Context

`_services/_retirement.py::enforce` gates a roster status transition in the pure, pre-write half
of `_set_status_model`, against the transaction's own snapshot. `_services/_config_integrity.py`
holds the clause predicates and the single `render_finding` composition that both the gate and
the `sq check` reporter render through. ADR-697 §7-§9 plus its 2026-07-31 amendment note are the
contract; where a shipped docstring restates the pre-amendment text, the docstring is what is
wrong.

The gate's two-pass structure is right and stays. What is owed here is a comparison key, three
message texts, one reporter line, two `--help` strings, a documentation count, and a template
whitespace fix.

## Compare on the condition, not on its rendering

`enforce` computes its delta by whole-object set membership over `ConfigIntegrityFinding`:
`before = set(check_all(...))`, then `[f for f in check_all(...) if f not in before]`. The
dataclass carries `message` and `severable_targets`, and both enumerate the currently-live
roles — so a pre-existing violation whose enumeration *shrinks* is a different object, is absent
from `before`, and reads as newly introduced. The transition is then refused for a condition it
did not create and strictly improved. On a squad where an archived skill is scoped to two live
roles:

```
$ sq check
error SKILL-19: config integrity: not live (status 'Archived') but still scoped to live role(s):
  manager, qa — remedy: …
$ sq role qa status Archived
error: cannot move ROLE-5 to 'Archived': the resulting projection would be structurally invalid:
- SKILL-19: not live (status 'Archived') but still scoped to live role(s): manager
```

Retiring `qa` removes one of the two live roles preloading a missing skill — strictly fewer broken
preloads — and is refused for it. The same event is refused through the bulk importer's pre-pass,
so a replay of that history is blocked too.

Compare on a key that identifies the *condition* rather than its rendering: `(clause, entry,
kind)`, all three already on the dataclass. Raise only on keys absent from `before`, and keep
rendering and severing the *after* finding's own `message`/`severable_targets`, so a refusal still
enumerates the current state. The always-on floor escapes this today only because its message
names no role or type — an invariant message is not the property that makes the comparison
correct, so nothing may rely on it.

Both directions are owed as tests: a shrinking pre-existing stored-edge violation must not refuse,
and a growing one still must.

## Name a remedy the transition will accept

The stored-edge finding's remedy — "pass `--unlink`, or run `sq skill <addr> unlink-role <role>`
first" — is written for the retirement direction, and the same finding is rendered on a
reactivation, where `--unlink` is refused as meaningless. The state is reached legitimately:
retire the role, then the skill (allowed, and correct), then reactivate the role. The refusal
leads with the one step that cannot work and never names either step that can — severing the edge
with `sq skill <addr> unlink-role <role>`, or reactivating the skill.

Refusing that reactivation is right and does not change. What changes is that a remedy is a
property of the situation, not of the predicate: the finding's condition text stays identical
across every surface that renders it — ADR-697's amendment rules the gate and the reporter two
renderings of one predicate — and only the remedy varies with what the caller can actually offer.
The reporter is a third such situation, with no transition in play at all: "pass `--unlink`" is
not something a report can offer either, so whatever shape carries the remedy has to serve
report-mode as well as both transition directions.

If that shape looks like it needs ADR-697 to move, stop and say so rather than forking the
condition text per caller.

## State the reason the guard actually tested

`is_retirement` is `old_status in live and item.status not in live`, which is correct. The guard
rejecting `--unlink` on anything else still describes only one of the two cases it now covers: it
asserts the target status is live, which is false for a move between two non-live statuses.

```
$ sq role qa status Archived --unlink --force     # qa is already Archived
error: --unlink is meaningless here: ROLE-5 is moving to 'Archived', which is live — the flag
  only applies to a retirement
```

State the tested reason instead — the entry is not moving out of a live status — and name both
statuses. A lifecycle declaring two non-live statuses reaches this with no `--force` at all, and
ADR-696 §3 permits exactly that lifecycle.

## Report two holders of the default designation

`Service.set_default_role` clears every other holder it finds, because the projection resolves the
designation by first match and nothing validates a single holder at item level. That convergence
is right and does not change. Nothing *reports* the state, so a squad already carrying two holders
keeps an arbitrary winner in its generated region with `sq check` clean, and the only signal is an
adopter noticing the wrong name in their own config. The state is reachable through the bulk
importer's `update` event, the one path that writes the key outside that method.

Report it: more than one `role` item carrying `is_default` is a `sq check` error naming the
holders, with `sq role <addr> set-default` as the remedy — a remedy that now exists.

**Report-only.** This must not become a clause the retirement gate evaluates. Delta scoping would
still let it fire on a transition that *introduces* the condition — reactivating an archived role
carrying the key while a live role also carries it — and there is no remedy in that direction:
`set_default_role` refuses a non-live target, and no interactive command clears the key on a
non-live role. That is precisely the lock-out the withdrawn default-role clause was withdrawn for.
Whichever validator seam the predicate lands in, prove the retirement path did not inherit it.

## Describe both flags on the verb in adopter vocabulary

Both live on `register_status_verb` in `_cli/_common.py`:

- `--unlink`'s help says it severs "the config-integrity clauses' severable edges (today: a custom
  skill's `scopes` edges)" — the engine's internal vocabulary on an adopter-facing surface,
  presupposing a concept `--help` never defines. Say what it does in the words `docs/roles.md`
  already establishes: on a retirement, remove the scoping the refusal named — a custom skill's
  link to a role — then re-run the check rather than override it; refused on any other transition.
- `--force` carries no help text at all, in the same options block, and it is the more dangerous
  of the two. It covers the lifecycle's own transition edge and never a config-integrity refusal —
  say so.

No clause or tier identifier in either string.

## Count `scopes` as the ninth ref kind

`VALID_REF_KINDS` holds nine kinds. `docs/stability.md`'s "Ref-kind vocabulary (closed at 1.0)"
says "The eight built-in kinds are frozen" and lists eight, and the ref-kind cheatsheet
(`_rendering/templates/workflow_static.md.j2`, which renders both the `squads` skill and `sq
workflow`) says "exactly eight kinds" above an eight-row table. Both omit `scopes` — the kind the
tool now shows an adopter in a `--help` line and in a refusal's remedy text, so a reference
claiming eight is contradicted by the tool's own output.

Correct the count and add the row on both surfaces (meaning, direction convention, consumer: a
skill's link to a role, stored on the skill, read by the preload resolver and the retirement
gate). The cheatsheet is generated output — `sq sync` after editing the template, and refresh
`tests/goldens/workflow_cheatsheet.txt`, `tests/goldens/workflow_cheatsheet_raw.txt`,
`tests/goldens/agents_md_section.txt` and `clients/vscode/test/fixtures/workflow-raw.txt`; the
count is also asserted in a unit test of the cheatsheet's static/dynamic split.

Count correction only. Whether the vocabulary is closed at nine, or the ninth kind earns different
treatment, is a challenge already commissioned on ADR-49 for a later release — do not reopen it
here, and do not edit ADR-49's body.

## Leave no gap where the default-role line was

`_rendering/templates/claude/claude_section.md.j2`'s two `{% if default_role_full_name %}` blocks
(around lines 45 and 61) are not whitespace-trimmed, so a squad with no live designated role
renders a double blank line where the default-role line and the orchestration paragraph were. Trim
the block tags, and refresh the managed-section golden and the template manifest.

## Owed to the architect, not to whoever implements this

ADR-697 §9 states that the default designation has no owning verb, that no interactive command
writes `is_default`, and that building that verb is work owed on its own item; its consequences
section says an adopter "has only reactivation as a way back … until that verb exists".
`sq role <addr> set-default` now exists and meets every constraint §9 sets — a move rather than a
set, clearing every other holder in one transaction, refusing a non-live target — and the
retirement warning names it as the first way back. §9's heading, those statements and that
consequences line need a dated amendment note restating them against what the surface now offers.
No decision changes. An implementer must not rewrite an Accepted decision's body: `@architect`
owns that edit, and it is not part of any subtask here.

## Out of scope

Attributing a `--unlink` severance to an actor — the roster `status` verb takes no `--as` at all,
so that is a decision about the whole roster verb family rather than a defect in the flag. Making
the playbook resolve per-request against the active spec. A `--dry-run` shape. Changing whether a
reactivation is refused. The ref-kind vocabulary decision itself, and ADR-49's body. ADR-697's own
text.

## Acceptance

- A pre-existing stored-edge violation whose enumeration shrinks does not refuse the transition
  that shrinks it, and the same event replays through the importer; a transition that *grows* such
  a violation is still refused. Both directions covered by tests.
- Every refusal names a remedy whose every step the tool accepts in that direction — including the
  reactivation direction, where `--unlink` is not one of them. The condition text a gate renders
  and the one the reporter renders stay identical for the same finding.
- A `--unlink` on a move between two non-live statuses states that the entry is not moving out of
  a live status, and names both statuses.
- `sq check` names both holders of a duplicated `is_default` with `set-default` as the remedy and
  exits 3, while no roster status transition — retirement or reactivation — is refused for that
  condition.
- `sq role <addr> status --help` describes `--unlink` and `--force` in adopter vocabulary, with no
  clause or tier identifier and no undefined concept.
- `docs/stability.md` and the rendered ref-kind cheatsheet both state nine kinds and carry a
  `scopes` row; every regenerated artifact and golden agrees.
- A squad with no live designated role renders the managed region with no blank-line gap where the
  default-role line and paragraph were.
- `uv run --all-extras pytest`, `pyright`, `ruff check`, `ruff format --check` and `sq check` are
  all clean, `tests/meta` included.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 711 add-subtask "<title>"`; track with `sq task 711 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Compare the delta on the condition, not on its rendering | US5 |
| ST2 | Done |  | Name a remedy the transition direction will accept | US5 |
| ST3 | Done |  | State the reason the meaningless-unlink guard tested | US5 |
| ST4 | Done |  | Report two holders of the default designation | US6 |
| ST5 | Done |  | Describe both status flags in adopter vocabulary | US3 |
| ST6 | Done |  | Count the scopes kind in the ref-kind reference |  |
| ST7 | Done |  | Leave no gap where the omitted default-role line was |  |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Compare the delta on the condition, not on its rendering

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US5 — As an operator, retiring a still-depended-on roster entry is refused, with a remedy
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Key the delta on `(clause, entry, kind)` instead of whole-object membership over
`ConfigIntegrityFinding`, and raise only on keys absent from the pre-transition snapshot. The
rendered `message` and the `severable_targets` set both enumerate the live roles, so today a
pre-existing violation whose enumeration shrinks is a different object and reads as newly
introduced — retiring one of two live roles that preload an archived skill is refused for a
condition it strictly improved, through the CLI and through the importer alike. The two-pass
structure stays; the *after* finding is still what gets rendered and severed, so a refusal keeps
enumerating current state. Cover both directions: a shrinking pre-existing stored-edge violation
must not refuse, a growing one must.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Name a remedy the transition direction will accept

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US5 — As an operator, retiring a still-depended-on roster entry is refused, with a remedy
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Make the remedy a property of the situation rather than of the predicate. The stored-edge finding
names `--unlink` first, and that finding is also rendered on a reactivation, where `--unlink` is
refused as meaningless — so the refusal leads with the step that cannot work and names neither of
the two that can (`sq skill <addr> unlink-role <role>`, or reactivating the skill). The condition
text stays identical across every surface that renders it, per ADR-697's amendment; only the
remedy varies. Three situations need serving, not two: retirement, reactivation, and the
`sq check` reporter, which has no transition in play and cannot offer `--unlink` either. Refusing
the reactivation itself does not change.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — State the reason the meaningless-unlink guard tested

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US5 — As an operator, retiring a still-depended-on roster entry is refused, with a remedy
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
The guard rejecting `--unlink` on a non-retirement asserts that the target status is live. Since a
retirement is a move out of a live status, that guard now also covers a move between two non-live
statuses, where the assertion is false — the message tells the operator the opposite of the truth
about their own lifecycle vocabulary. State the reason the predicate tested: the entry is not
moving out of a live status, naming both the status it leaves and the one it enters. A lifecycle
declaring two non-live statuses, which ADR-696 §3 permits, reaches this with no `--force` at all.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Report two holders of the default designation

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US6 — As a team, sq check reports a roster entry already in a broken config state
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
More than one `role` item carrying `is_default` becomes a `sq check` error naming the holders,
with `sq role <addr> set-default` as the remedy. Today the projection resolves the designation by
first match, nothing validates a single holder at item level, and nothing reports the state — so a
squad that reached it (through the importer update event, the only other path that writes the key)
keeps an arbitrary winner in its generated region with a clean check, and the only signal is an
adopter noticing the wrong name. `set_default_role` converges the state correctly when invoked;
that behaviour does not change.

Report-only, deliberately. Do not add it to the clause set the retirement gate evaluates: delta
scoping would still fire it on a transition that introduces the condition — reactivating a
non-live role carrying the key while a live role also carries it — and no remedy exists in that
direction, since `set_default_role` refuses a non-live target and no interactive command clears
the key on a non-live role. Prove the retirement and reactivation paths did not inherit the
predicate.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Describe both status flags in adopter vocabulary

<!-- sq:subtask:ST5:head -->
**Status:** 🟢 Done
**Implements:** US3 — As a team, the generated CLI help and skill text teach the new verb
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
Both flags on the roster `status` verb (`register_status_verb` in `_cli/_common.py`). `--unlink`
describes itself as severing the config-integrity clauses' severable edges, which is the engine's
vocabulary on an adopter-facing surface and presupposes a concept `--help` never defines: restate
it in the words `docs/roles.md` already uses — on a retirement, remove the scoping the refusal
named, a custom skill's link to a role, then re-run the check rather than override it; refused on
any other transition. `--force` has no help text at all in the same options block and is the more
dangerous of the two: say that it covers the lifecycle's own transition edge alone and never a
config-integrity refusal. No clause or tier identifier in either string.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Count the scopes kind in the ref-kind reference

<!-- sq:subtask:ST6:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST6:head:end -->

<!-- sq:subtask:ST6:body -->
`VALID_REF_KINDS` holds nine kinds, while `docs/stability.md` says the eight built-in kinds are
frozen and the ref-kind cheatsheet (`_rendering/templates/workflow_static.md.j2`, rendering both
the `squads` skill and `sq workflow`) says exactly eight above an eight-row table. Neither
includes `scopes`, which the tool now shows an adopter in a `--help` line and in a refusal remedy,
so the reference is contradicted by the tool output. Correct the count on both surfaces and add
the row: a skill link to a role, stored on the skill, read by the preload resolver and the
retirement gate. Regenerate the cheatsheet with `sq sync` and refresh
`tests/goldens/workflow_cheatsheet.txt`, `tests/goldens/workflow_cheatsheet_raw.txt`,
`tests/goldens/agents_md_section.txt` and `clients/vscode/test/fixtures/workflow-raw.txt`; the
count is also asserted in a unit test of the cheatsheet static/dynamic split. Count correction
only — the question of whether the vocabulary should be closed at nine is commissioned on ADR-49
for a later release, and ADR-49 body stays untouched.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->

<!-- sq:subtask:ST7 -->
### ST7 — Leave no gap where the omitted default-role line was

<!-- sq:subtask:ST7:head -->
**Status:** 🟢 Done
<!-- sq:subtask:ST7:head:end -->

<!-- sq:subtask:ST7:body -->
The two `{% if default_role_full_name %}` blocks in
`_rendering/templates/claude/claude_section.md.j2` (around lines 45 and 61) carry untrimmed block
tags, so a squad with no live designated role renders a double blank line where the default-role
line and the orchestration paragraph were. Trim them so the omission leaves clean prose with no
gap, then refresh the managed-section golden and the template manifest.
<!-- sq:subtask:ST7:body:end -->

#### Discussion

<!-- sq:subtask:ST7:discussion -->
<!-- sq:subtask:ST7:discussion:end -->
<!-- sq:subtask:ST7:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-31T11:49:20Z] Olivia Lead:
  - Findings closed, subtask by subtask: ST1 = F14, ST2 = F15, ST3 = F16, ST4 = F17, ST5 and ST6 = F19 (the two halves the judgement call asked to be folded in together), ST7 = the untrimmed default-role blocks noted on F13. Story mapping: ST1/ST2/ST3 to US5, ST4 to US6, ST5 to US3. ST6 and ST7 map to no story — a pre-existing reference gap and a rendering residue, neither of them a criterion of the six.
  - Sequence: ST1 first and alone. It changes what the gate refuses at all, and ST2/ST3 are message texts on refusals it selects. ST4 next (report-only, no clause), then ST5-ST7, which touch no engine code. ST6 regenerates two goldens plus a VS Code fixture, so keep it out of the same tree as any concurrent run.
  - ADR-697 section 9 and its consequences line still say the designation verb is owed, after set-default landed. That amendment is @architect work and is deliberately not a subtask here — an implementer must not rewrite an Accepted decision body.
- [2026-07-31T12:16:27Z] Elias Python:
  - All 7 subtasks done, findings F14/F15/F16/F17/F19 marked Fixed (comments cite the fix on each).
  - F14: delta keyed on (clause, entry, kind), not whole-object equality -- falsified against the pre-fix code (shrinking-violation + importer-replay tests both went red without the key change, green with it).
  - F15: render_finding(unlink_available=...) makes the remedy a property of the caller's situation; condition text unchanged. F16: --unlink-meaningless message states the tested reason and both statuses.
  - F17: report-only default_designation_duplicated validator; proved the retirement/reactivation path does not evaluate it (planted two-holder state, both transitions still succeed).
  - F19: --help reworded (--unlink + --force, adopter vocabulary, no clause/kind identifier); VALID_REF_KINDS=9 documented as nine with a scopes row in docs/stability.md + workflow_static.md.j2; goldens + VS Code fixture + template manifest regenerated. ADR-49 untouched.
  - Gates clean: pyright/ruff check/ruff format on the touched set + full pyright; sq check clean. Full pytest suite left to the operator per brief.
<!-- sq:discussion:end -->
