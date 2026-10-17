---
id: TASK-1048
sequence_id: 1048
type: task
title: Enforce operator slug grammar and one author namespace
status: InProgress
parent: FEAT-980
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-979:implements
- REV-1026:addresses
description: Operator slugs op-…, skills out of the author namespace, roster_slug_valid,
  the 0.16 migration refusal, and --as squads refused (ADR-979 A1–A5)
subentities:
- local_id: ST1
  title: Operator slug grammar at creation; skills out of the author namespace
  status: Done
  assignee: python-dev
  story: US2
- local_id: ST2
  title: Default roster_slug_valid check
  status: InProgress
  assignee: python-dev
  story: US2
- local_id: ST3
  title: 0.16 migration refuses a role or operator in breach
  status: InProgress
  assignee: python-dev
  story: US3
- local_id: ST4
  title: Refuse --as squads in every comment writer
  status: InProgress
  assignee: python-dev
  story: US2
- local_id: ST5
  title: Docs and CHANGELOG for the operator slug rule
  status: Todo
  assignee: tech-writer
  story: US5
created_at: '2026-10-16T11:18:03Z'
updated_at: '2026-10-16T11:25:14Z'
---
<!-- sq:body -->
Builds ADR-979 amendments A1 to A5, confirmed by op-pierre on 2026-10-16. The amendment text in ADR-979 ("Amendments — 2026-10-16") is the spec; the subtasks add acceptance only. A6 (the slug fallback in the 0.16 migration) is already built and is out of scope here.

## Scope

- Operator slug grammar `op-[a-z0-9][a-z0-9-]*` at the roster creation seam, and one author namespace of roles plus operators plus the reserved `operator`/`squads`; skills fall outside it (A1, A2).
- A new default `sq check` rule, `roster_slug_valid` (A3).
- The 0.16 migration refuses a role or operator in breach, replacing today's report line (A4).
- `--as squads` refused by every comment writer, the importer included (A5).
- The MANUAL text and the adopter docs that state the old behaviour.

## Out of scope

The rest of REV-1026 F5 (an importer actor not in the roster). Any stronger author match than slug equality (A5). Rewriting a header already written.

## Testing

One table-driven test per behaviour, over slug shapes rather than one case per branch: grammar position and character class (prefix, case, spaces, empty tail, double hyphen, digits, reserved words, a live role's slug), and the same table run through every entry path the subtask names. Each refusal asserts exit 1 and an unchanged squad (no file written, index unchanged).

## Verification

A migration dry run on a copy of this repository's squad, made under the scratchpad (never under the live tree or a bare /tmp), with the dev tree: it must report how many operators and roles break the rule. Expected here: zero, since the only operator is `op-pierre`. Paste the count in the handoff comment.

## Gates

`uv run --all-extras pyright`, `ruff check`, `ruff format --check`, the touched tests, and `sq check` clean. No ticket IDs in code or test names; docstrings one or two sentences.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 1048 add-subtask "<title>"`; track with `sq task 1048 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Operator slug grammar at creation; skills out of the author namespace

<!-- sq:subtask:ST1:body -->
ADR-979 A1 and A2. The rule sits at the roster creation seam that already holds the role rule (`_check_roster_slug`, `_services/_base.py`), so every operator creation path inherits it.

## Acceptance

- Operator creation refuses any slug outside `op-[a-z0-9][a-z0-9-]*`, explicit or derived, with exit 1 and nothing written, on `sq operator add --slug` and the importer's operator `create`.
- The message names the rule and, when one exists, the compliant form: `operator slug 'Anna' must start with 'op-' and be lowercase letters, digits and hyphens (e.g. 'op-anna')`.
- A typed slug is never lowercased or prefixed: the stored slug is the one typed and accepted.
- The derived default (`operator_slug`, `_util.py`) is accepted for an ASCII, an accented, a non-Latin and a punctuation-only name (the last two give `op-untitled` or a compliant form).
- `agent_registered` builds its set from roles and operators only (`registered_slugs`, `_services/_validators.py`): an item whose author or assignee names a skill slug is now reported.
- Skill slugs stay unique among skills and in the grammar, and are otherwise unconstrained: the bundled `squads` skill still loads and `sq skill squads show` works.

## Tests (one table per behaviour)

- Creation table, run through both `operator add --slug` and the importer: `squads`, `operator`, `qa` with role `qa` live, `Bad Slug`, `OP-UP`, `op-`, `op--x`, `Op-anna`, `op-anna ` (trailing space), `op_anna` refused; `op-anna`, `op-a1`, `op-1`, `op-ann-lee` and the derived default accepted. Each refusal asserts an unchanged squad.
- `agent_registered` table: author or assignee naming a role, a developer role, an operator, a retired role, a retired operator (pass); a skill slug, an unknown slug (reported).
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-10-16T11:25:07Z] Elias Python:
  - Done. Falsified with 5 mutants, all red: operator rule off (24 red), importer derived slug back to slugify (1), registered set back to every roster type (2), skill author exemption off (1), suggestion removed (25). Importer-created operators now derive op-<first name> like operator add (they derived slugify(title) before, which the rule would refuse).
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Default roster_slug_valid check

<!-- sq:subtask:ST2:body -->
ADR-979 A3. A new squad-global `sq check` rule, `roster_slug_valid`, on by default at `error`.

## Acceptance

- Reports each role and operator, live or retired, whose slug is outside its A1 grammar (role: not `operator`/`squads`, not starting with `op-`; operator: `op-[a-z0-9][a-z0-9-]*`), or that shares its slug with another entry of the author namespace (roles and operators; skills do not count).
- One issue per entry, naming the item, the slug, the rule broken and, for a shared slug, the other holders: `OP-12: operator slug 'qa' does not start with 'op-'; it is also held by ROLE-5`.
- The message carries the remedy, addressing by id: `sq operator <id> rm --purge`, then `sq operator add` under the same name.
- Report-only: it gates no write, like `default_designation_duplicated`. A test proves an unrelated write still succeeds on a squad holding a breaching entry.
- Selectable and severity-overridable like the other default rules; the bundled spec lists it.
- `sq check` on this repository's squad stays clean.

## Tests (one table per behaviour)

- Breach table, entries written by hand into a scratch squad's files (creation can no longer produce them): operator `squads`, `operator`, `qa` beside live role `qa`, `Bad Slug`, `OP-UP`, `op-`; two operators sharing `op-ann` (both reported, each naming the other); a retired breaching operator; a role holding `op-dev`; a skill holding `squads` (not reported); a compliant roster (no issue).
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — 0.16 migration refuses a role or operator in breach

<!-- sq:subtask:ST3:body -->
ADR-979 A4. The 0.16 planning pass (`_migrations/_v0_15_to_v0_16.py`) checks the roster before any header resolves, and a breach refuses the run. This replaces today's report line, "An operator whose slug does not start with `op-` is listed in the run's report; nothing is refused".

## Acceptance

- Every role and operator item, live and retired, is checked against A1 and A2 (the same predicate as `roster_slug_valid`, shared, not duplicated) before any header is resolved.
- A breach is one file-level line per entry, in the same report as the header failures, counted toward the same exit 1 with nothing written: `operators/OP-000012-qa.md: operator slug 'qa' does not start with 'op-'; also held by ROLE-5`.
- Each entry is reported once; the headers that name it are not also listed.
- A role in breach of decision 2 or the grammar is reported the same way.
- `_HEADER_MANUAL` drops the "nothing is refused" paragraph and gives the remedy, run with the release the squad is stamped for: `sq operator <id> rm --purge`, then `sq operator add "<the same full name>"`, then `sq migrate up` again; why the purge is required (a plain `rm` keeps the file and the reconcile re-indexes it); `update --assignee` for open items assigned to the old slug; an item's `author` keeps the old slug, which `agent_registered` names. For a role: rename the project role file to a compliant slug, activate it again, purge the old one.
- A6's title-then-operator-slug resolution keeps working beside the new check.

## Tests (one table per behaviour)

- Refusal table: each breach kind (reserved slug, live role's slug, out of grammar, shared operator slug, retired breaching entry, role holding `op-`), alone and beside a header failure. Every file in the squad hashes identically before and after, and the error lists each breach once.
- A compliant squad migrates as today.

## Dry run

On a copy of this repository's squad under the scratchpad, run the dev tree's `sq migrate up`: report the number of breaching operators and roles (expected 0; `op-pierre` conforms) in the handoff comment. Never run it on the live squad.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — Refuse --as squads in every comment writer

<!-- sq:subtask:ST4:body -->
ADR-979 A5. `squads` resolves for no actor, whatever the roster holds, so system entries stay immutable by rule.

## Acceptance

- `--as squads` is refused with exit 1 and nothing written by every comment writer: item `comment`, sub-entity `comment`, `sq board post`, any roster-entity comment verb, and the importer's `as` (event-level and the `--as` default). The refusal holds even when a roster entry holds `squads` (a hand-edited file).
- Rename and retype still write `squads` system entries internally.
- `--as operator` keeps resolving to the anonymous author before the roster is read, even when an entry holds `operator`.
- The author match stays slug equality (ADR-1013 §9); no stronger match is added.

## Tests (one table per behaviour)

- Writer table: each writer above × (`squads` with no entry holding it, `squads` held by a hand-written operator) refused; × a live role and an `op-` operator accepted. Each refusal asserts the item file unchanged.
- `operator` table: with and without an entry holding `operator`, the header names the anonymous author.
- A retype still writes a `squads` header.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Docs and CHANGELOG for the operator slug rule

<!-- sq:subtask:ST5:body -->
The adopter-facing text that states the old behaviour, rewritten to the A1–A5 rules once the code lands (REV-1031 F8 lists the migration passages). Describe the tool, not how it was built.

## Acceptance

- `docs/stability.md` Tier 1, beside the header grammar: drop "Operator slugs are not checked against these rules" and the paragraph after it; state that an operator slug is `op-[a-z0-9][a-z0-9-]*`, refused otherwise by `sq operator add --slug` and the importer, that `--as squads` is refused, and that a role or operator in breach does not migrate. Correct "the 0.16 migration neither reports nor refuses it" for a role in breach.
- `docs/migration.md`, "Upgrading to 0.16": replace "The report also names any operator whose slug does not start with `op-`; nothing is refused for it" with the refusal and the purge-and-add remedy; re-check the operator matching rule against A6 (title first, then an operator's slug) and the other two REV-1031 F8 passages.
- The 0.16 CHANGELOG entry: the reserved-slug bullet no longer says operator slugs are unchecked or that the migration ignores a role in breach; a bullet covers the operator slug rule, `roster_slug_valid`, `--as squads`, and the migration refusal.
- The `sq operator add --help` text names the slug rule if the help does not already.
- Text matches the built messages and the final `_HEADER_MANUAL` word for word where it quotes them; every example run against the dev tree.
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
