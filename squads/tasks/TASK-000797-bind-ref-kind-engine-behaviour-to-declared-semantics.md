---
id: TASK-797
sequence_id: 797
type: task
title: Bind ref-kind engine behaviour to declared semantics
status: Done
parent: FEAT-790
author: tech-lead
assignee: python-dev
priority: high
refs:
- ADR-775:implements
- TASK-796:depends-on
description: Bind the dependency, preload and supersession behaviours to declared
  semantics, add the per-capability floor, the live-corpus refusal and the literal
  scan
subentities:
- local_id: ST1
  title: Convert the dependency bindings to the declared semantic
  status: Done
  story: US2
- local_id: ST2
  title: Convert the preload bindings to the declared semantic
  status: Done
  story: US2
- local_id: ST3
  title: Convert the supersession binding to the declared semantic
  status: Done
  story: US2
- local_id: ST4
  title: tests/meta scan for bundled ref-kind literals
  status: Done
  story: US2
- local_id: ST5
  title: Per-capability floor on the merged spec
  status: Done
  story: US3
- local_id: ST6
  title: Live-corpus refusal for a dropped or renamed ref kind
  status: Done
  story: US3
created_at: '2026-08-25T14:40:27Z'
updated_at: '2026-08-25T23:39:41Z'
---
<!-- sq:body -->
## Scope

ADR-775 §2, §3 and §5 — FEAT-790 US2 and US3. Bind the three engine behaviours that consume a
ref kind to a kind's **declared semantic role**, never to its spelling; add the per-capability
floor on the merged spec; extend the live-corpus cross-check to ref kinds; and add the
`tests/meta` scan that keeps the conversion true.

Consumes the `[ref_kinds]` section and the `role` field TASK-796 declares. Same surface, same
owner, no parallelism: these two touch `_workflow/_loader.py`, `_workflow/_models.py` and
`_specs/workflow.toml` together and must not be run side by side.

## The three semantics, and the literal bindings each replaces

| Semantic | Engine behaviour | Bound today as |
| --- | --- | --- |
| `dependency`, with `direction = "blocker"` or `"dependent"` | the `sq blocked` graph and the two-way binding it prints | `"blocks"` / `"depends-on"` at `_services/_refs.py:36`, `:79-80`, `:111-116`, `:250`, `:608-611`; `_services/_results.py:36-42`; `_cli/_main.py:922-931` |
| `preload` | a skill's forward edge to the role that preloads it, inverted by the roster resolver | `"scopes"` at `_services/_base.py:1178`, `_services/_config_integrity.py:160`, `_services/_items.py:73`, `_services/_retirement.py:54`, and the two call sites `_services/_refs.py:453`, `:472` |
| `supersession` | `sq check`'s incoming-supersedes rule | `"supersedes"` at `_services/_validators.py:434`, `:771`; `_workflow/_models.py:1111-1115` |
| none | display and navigation only | nothing |

A kind declaring no semantic is navigational. That is the default and what an
adopter-declared kind gets unless it says otherwise.

`supersession` is the row that reads as done and is not. The rule is already declared per type
in `ref_rules`, and a project dropping the `decision` type already takes the check with it —
but the validator finds the rule by comparing `rr.kind` against the literal `"supersedes"`
(`_services/_validators.py:434`), so a project that renames the kind keeps the declaration and
silently loses the check. Declared-but-found-by-literal is the exact defect ADR-696 §1 named on
the status axis.

## The floor (ADR-775 §3)

Per-capability, checked on the merged spec, fail-closed, **every violation collected in one
pass** rather than stopping at the first — ADR-696 §3's shape, not a second rulebook.

- **Exactly one kind carries `preload`.** Zero leaves every custom skill unreachable from the
  role that scopes it; two make the resolver's inversion ambiguous. This is the
  roster-strictness case: the resolved list is materialised into the agent hosts' own config,
  so a spec the engine cannot drive corrupts generated config rather than merely making a view
  odd.
- **At most one kind per `dependency` direction.** Two kinds spelling `blocker` would make the
  normalisation at `_services/_refs.py:79-80` ambiguous; the graph has one edge kind, not two.
- **Zero is legal for `dependency` and for `supersession`.** A squad declaring no dependency
  kind gets an empty `sq blocked`, which is a stated choice rather than a stranded item. The
  asymmetry with the lifecycle floor is deliberate and is why the floor is per-capability.
- **A kind name may not contain `:`** (`split_ref` partitions on it, `_models/_item.py:104-107`)
  and must be a TOML bare key so it stays splat-ref addressable (ADR-696 §4a).
- **Exactly one kind carries `default`, mandatory** — ADR-775 amendment A2, folded in here on
  the architect's ruling. Zero makes an existing bare ref undecodable, which is a load failure
  rather than a bounded `sq check` finding, and `WorkflowSpec.default_ref_kind()`
  (`_workflow/_models.py:1684-1702`) already fails closed on it while its own docstring says
  the floor clause that would make it total lands here.

### The floor has to be visible to `sq workflow lint`

`sq workflow lint` is the command whose entire job is to tell an adopter their spec is wrong, so
a floor it cannot see is a floor half the adopters never meet. Driven on a scratch squad, with
an `.overrides/workflow.toml` carrying a `[selected] ref_kinds` list that omits the entry
carrying `role = "default"` — a one-line, entirely plausible adopter edit:

    sq workflow lint  -> exit 0, "workflow spec OK — no errors or warnings."
    sq check          -> exit 3, "could not scan the corpus: the workflow spec must declare
                         exactly one ref kind with role = 'default' (a bare ref decodes to it);
                         found 0: []"

The refusal itself is right — clean, single, and it names the spec. What is wrong is that lint
blessed the spec first.

This is a placement requirement, not a second implementation. `lint_workflow_spec`
(`_workflow/_loader.py:1032`) already runs the loader's own floor as its phase 3
(`_collect_floor_violations`, on the merged mapping) and turns `_build_spec`'s structural
failures into findings as its phase 4. The ref-kind floor must be evaluated on a path lint
traverses — one of those two — rather than only at first use inside `default_ref_kind()`. Do not
write a lint-only copy of the rules; a second rulebook is the thing the per-capability floor
exists to avoid.

US3's wording ("checked on the merged spec, fail-closed, every violation collected") is
satisfiable by a merge-time refusal that leaves lint silent, which is exactly what shipped for
the clause that already exists. The lint surface is in scope.

## The live-corpus refusal (ADR-775 §5)

The cross-check gains ref kinds on exactly ADR-696 §5a's terms and for the reason it gained
`prefix` and `folder`: a kind is durable on-disk data that no scan re-derives. For every kind
the merged spec drops or renames, list the items whose `refs` still carry it and refuse, with
the offending IDs, in the wording the cross-check already uses.

- **It stores nothing new** — the expected set is recoverable from the corpus, since every
  edge carries its own kind inline.
- **An empty corpus is unaffected** — a kind no edge uses may be dropped or renamed freely,
  which is the case the capability was asked for: choosing your vocabulary at adoption time.
- **The two performable remedies are: restore the entry, or remove the edges first.** The
  refusal names those and nothing else — no verb rewrites a corpus's kinds, and the standing
  rule is that a refusal may never assert a remedy no command performs.

## The `tests/meta` scan

Same shape as `tests/meta/test_no_bundled_roster_status_literal_outside_the_spec_layer.py`: a
cheap AST walk for a bare `ast.Constant` whose value is **exactly** a bundled ref-kind name,
anywhere under `src/squads/` outside `_specs/` and `_migrations/`, with a line-numbered
allowlist and the liveness test that fails when an allowlist entry goes stale. Because the match
is exact-value, a docstring paragraph merely containing the word never trips it — the existing
prose at `_cli/_main.py:922-931` and `_services/_results.py:36-42` needs rewording only where it
states a literal as the contract, not merely as an example.

Migration runners keep their frozen literals deliberately: a runner reads the vocabulary of the
schema version it transforms, never the live spec.

The current tree has 33 exact-value hits across the ten names; 24 remain once
`VALID_REF_KINDS`'s own definition retires with TASK-796. Every one of the 24 is either a
conversion listed in the table above or one of the three `related` sites named in TASK-796's
traps.

## Traps

- **`edge_kind` is a public JSON contract carrying a literal.** `sq graph --json` normalises
  every dependency edge to `edge_kind="depends-on"` regardless of which spelling is stored
  (`_services/_refs.py:79-80`, `:111-116`; documented at `_cli/_main.py:988-999`). Once the
  dependency kind is renameable, what that field emits is a contract question ADR-775 does not
  answer. Do not pick an answer in code — the open question is recorded in this task's
  discussion for the architect.
- **`_services/_retirement.py:54` holds the kind inside a data structure**
  (`"preloaded_skill": frozenset({"scopes"})`), not in a comparison. It needs the same
  semantic resolution as the comparisons, not an allowlist entry.
- **No schema bump, no migration runner** — the same call TASK-796 carries.
- **No bundled template is touched here**, so this task forces no manifest regeneration and
  `scripts/bump_version.py` must not be run.

## Acceptance

- Renaming the bundled dependency kinds to a project's own spellings, with
  `dependency`/`blocker` and `dependency`/`dependent` declared, keeps `sq blocked` and the
  two-way graph binding working against the renamed kinds.
- Renaming the `preload` kind keeps the roster skill-preload resolver, the config-integrity
  check, the item-level preload read and the retirement gate working.
- Renaming the `supersession` kind keeps `sq check`'s incoming-supersedes rule firing.
- None of the converted kind names is found by the `tests/meta` scan.
- The floor fires, with **every** violation collected in a single pass, for each of: two kinds
  claiming `preload`; zero kinds claiming `preload`; two kinds claiming the same `dependency`
  direction; a kind name containing `:`; a kind name that is not a bare TOML key; zero kinds
  claiming `default`; two kinds claiming `default`.
- `sq workflow lint` reports **every** one of those violation shapes and exits non-zero — driven
  through the command, not only through the loader — and in particular a `[selected] ref_kinds`
  list that omits the `default`-role kind no longer prints "workflow spec OK".
- Lint and the mutating commands agree: no spec is blessed by `sq workflow lint` and then
  refused by `sq check`, `sq repair` or an ordinary status transition.
- A merged spec declaring no `dependency` kind and no `supersession` kind loads, and yields an
  empty `sq blocked` and no supersedes findings.
- Dropping or renaming a kind that live refs still carry is refused, naming the offending item
  IDs and the two performable remedies; doing the same for a kind no edge uses succeeds.
- `uv run --all-extras pyright`, `ruff check .`, `ruff format --check .` and the full
  `uv run --all-extras pytest` suite are clean; `sq check` is clean.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 797 add-subtask "<title>"`; track with `sq task 797 subtask <n> update --status <Status>`._

<!-- sq:summary -->
| Subtask | Status | Assignee | Title | Story |
| --- | --- | --- | --- | --- |
| ST1 | Done |  | Convert the dependency bindings to the declared semantic | US2 |
| ST2 | Done |  | Convert the preload bindings to the declared semantic | US2 |
| ST3 | Done |  | Convert the supersession binding to the declared semantic | US2 |
| ST4 | Done |  | tests/meta scan for bundled ref-kind literals | US2 |
| ST5 | Done |  | Per-capability floor on the merged spec | US3 |
| ST6 | Done |  | Live-corpus refusal for a dropped or renamed ref kind | US3 |
<!-- sq:summary:end -->

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Convert the dependency bindings to the declared semantic

<!-- sq:subtask:ST1:head -->
**Status:** 🟢 Done
**Implements:** US2 — Bind engine behaviour to declared semantics, not literals
<!-- sq:subtask:ST1:head:end -->

<!-- sq:subtask:ST1:body -->
Replace the literal `blocks` / `depends-on` checks with resolution through the declared
`dependency` semantic and its `direction` (`"blocker"` or `"dependent"`).

Sites: `_services/_refs.py:36` (`_DEP_KINDS`), `:79-80` and `:111-116` (the normalisation into
`edge_kind`/`direction`), `:250` (`_label`), `:608-611` (the blocked scan);
`_services/_results.py:36-42` (contract prose); `_cli/_main.py:922-931` (`_graph_edge_label`).

The two-way binding the graph prints stays exactly as it is — only how the code decides which
edges are dependency edges changes.

Note the open contract question recorded on this task's discussion: `sq graph --json` normalises
every dependency edge to the literal `edge_kind="depends-on"`, which is a documented output
contract (`_cli/_main.py:988-999`). Do not settle what that field emits under a renamed kind
inside this subtask.

Done when a spec that renames both dependency kinds keeps `sq blocked`, `sq graph` and the
blocked-by display working, and neither literal appears as a bare string constant.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Convert the preload bindings to the declared semantic

<!-- sq:subtask:ST2:head -->
**Status:** 🟢 Done
**Implements:** US2 — Bind engine behaviour to declared semantics, not literals
<!-- sq:subtask:ST2:head:end -->

<!-- sq:subtask:ST2:body -->
Replace the literal `scopes` checks with resolution through the declared `preload` semantic: a
skill's forward edge to the role that preloads it, inverted by the roster resolver.

Sites: `_services/_base.py:1178` (the resolver's inversion), `_services/_config_integrity.py:160`,
`_services/_items.py:73`, `_services/_retirement.py:54` (the retirement gate — the kind lives
inside a data structure there, not in a comparison, and needs the same semantic resolution rather
than an allowlist entry), plus the two call sites `_services/_refs.py:453` and `:472`.

This is the roster-strictness case: the resolved list is materialised into the agent hosts' own
config, so a spec the engine cannot drive corrupts generated config rather than merely making a
view odd.

Done when a spec that renames the preload kind keeps skill preloading, the config-integrity
check and the retirement gate working, and the literal appears nowhere the scan covers.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->

<!-- sq:subtask:ST3 -->
### ST3 — Convert the supersession binding to the declared semantic

<!-- sq:subtask:ST3:head -->
**Status:** 🟢 Done
**Implements:** US2 — Bind engine behaviour to declared semantics, not literals
<!-- sq:subtask:ST3:head:end -->

<!-- sq:subtask:ST3:body -->
Replace the literal `supersedes` comparison with resolution through the declared `supersession`
semantic.

Sites: `_services/_validators.py:434` (`rr.kind == "supersedes"`), `:771`;
`_workflow/_models.py:1111-1115`.

This row reads as done and is not. The rule is already declared per type in `ref_rules`, and a
project dropping the `decision` type already takes the check with it — but the validator finds
the rule by comparing `rr.kind` against the literal, so a project that renames the kind keeps the
declaration and silently loses the check. Declared-but-found-by-literal is the exact defect the
status axis was converted to remove.

Done when a spec that renames the supersession kind still fires the incoming-supersedes check,
and a spec declaring no supersession kind at all loads and produces no such findings.
<!-- sq:subtask:ST3:body:end -->

#### Discussion

<!-- sq:subtask:ST3:discussion -->
<!-- sq:subtask:ST3:discussion:end -->
<!-- sq:subtask:ST3:end -->

<!-- sq:subtask:ST4 -->
### ST4 — tests/meta scan for bundled ref-kind literals

<!-- sq:subtask:ST4:head -->
**Status:** 🟢 Done
**Implements:** US2 — Bind engine behaviour to declared semantics, not literals
<!-- sq:subtask:ST4:head:end -->

<!-- sq:subtask:ST4:body -->
Add the repo-hygiene scan, in the shape of
`tests/meta/test_no_bundled_roster_status_literal_outside_the_spec_layer.py`: an AST walk for a
bare `ast.Constant` whose value is **exactly** a bundled ref-kind name, anywhere under
`src/squads/` outside `_specs/` and `_migrations/`.

Carry over that scan's two properties rather than reinventing them: a **line-numbered**
`(path, lineno, value)` allowlist, each entry with its own one-line reason, and the liveness test
that fails when an allowlist entry stops being produced by the scan — so a moved line cannot
silently start excusing whatever lands on it next.

Exact-value matching means a docstring paragraph merely containing the word never trips it, so
the existing prose at `_cli/_main.py:922-931` and `_services/_results.py:36-42` needs rewording
only where it states a literal as the contract, not where it uses one as an example.

Migration runners keep their frozen literals deliberately: a runner reads the vocabulary of the
schema version it transforms, never the live spec.

Done when the scan runs clean over the converted tree with an allowlist that is empty or fully
justified line by line.
<!-- sq:subtask:ST4:body:end -->

#### Discussion

<!-- sq:subtask:ST4:discussion -->
<!-- sq:subtask:ST4:discussion:end -->
<!-- sq:subtask:ST4:end -->

<!-- sq:subtask:ST5 -->
### ST5 — Per-capability floor on the merged spec

<!-- sq:subtask:ST5:head -->
**Status:** 🟢 Done
**Implements:** US3 — Per-capability floor and the live-corpus refusal
<!-- sq:subtask:ST5:head:end -->

<!-- sq:subtask:ST5:body -->
Check the floor on the **merged** spec, fail-closed, collecting **every** violation in one pass
rather than stopping at the first.

- Exactly one declared kind carries `preload`. Zero leaves every custom skill unreachable from
  the role that scopes it; two make the resolver's inversion ambiguous.
- At most one kind per `dependency` direction. Two kinds spelling `blocker` would make the
  normalisation ambiguous; the graph has one edge kind, not two.
- Zero is legal for `dependency` and for `supersession`. A squad declaring no dependency kind
  gets an empty `sq blocked`, which is a stated choice rather than a stranded item. The
  asymmetry with the lifecycle floor is deliberate and is why the floor is per-capability: a
  lifecycle with no settled status strands items that can never close, while a missing
  navigational capability simply answers nothing.
- A kind name may not contain `:` (`split_ref` partitions on it) and must be a TOML bare key so
  it stays splat-ref addressable.
- Exactly one declared kind carries `default`, mandatory — ADR-775 amendment A2, ruled onto this
  subtask by the architect. Zero makes an existing bare ref undecodable, a load failure rather
  than a bounded `sq check` finding. `WorkflowSpec.default_ref_kind()`
  (`_workflow/_models.py:1684-1702`) already fails closed on it, and its docstring names this
  clause as what would make it total.

**The floor must be visible to `sq workflow lint`.** Driven: an `.overrides/workflow.toml` whose
`[selected] ref_kinds` list omits the `default`-role kind makes `sq workflow lint` exit 0 with
"workflow spec OK — no errors or warnings.", while `sq check` exits 3 naming the spec. Lint is
the command whose whole job is to tell an adopter their spec is wrong; it must not bless a spec
no mutating command can use.

This is placement, not a second implementation. `lint_workflow_spec`
(`_workflow/_loader.py:1032`) already runs the loader's floor as phase 3
(`_collect_floor_violations`) and converts `_build_spec`'s structural failures into findings as
phase 4. Evaluate the ref-kind floor on a path lint traverses, rather than only at first use
inside `default_ref_kind()`. Do not write a lint-only copy of the rules — a second rulebook is
what the per-capability floor exists to avoid.

Done when each violation shape is refused — including zero and two kinds claiming `default` —
a spec carrying more than one of them reports all of them in a single message, and every one of
those shapes is reported by `sq workflow lint` with a non-zero exit rather than "workflow spec
OK".
<!-- sq:subtask:ST5:body:end -->

#### Discussion

<!-- sq:subtask:ST5:discussion -->
<!-- sq:subtask:ST5:discussion:end -->
<!-- sq:subtask:ST5:end -->

<!-- sq:subtask:ST6 -->
### ST6 — Live-corpus refusal for a dropped or renamed ref kind

<!-- sq:subtask:ST6:head -->
**Status:** 🟢 Done
**Implements:** US3 — Per-capability floor and the live-corpus refusal
<!-- sq:subtask:ST6:head:end -->

<!-- sq:subtask:ST6:body -->
Extend the live-corpus cross-check to ref kinds, on the same terms it already covers a dropped
type prefix or folder, and for the same reason: a kind is durable on-disk data that no scan
re-derives.

For every kind the merged spec drops or renames, list the items whose `refs` still carry it and
refuse, with the offending IDs, in the wording the cross-check already uses.

Two properties follow from that existing shape and must hold:

- **It stores nothing new.** The expected set is recoverable from the corpus itself — every edge
  carries its own kind inline.
- **An empty corpus is unaffected.** A kind no edge uses may be dropped or renamed freely, which
  is the case the capability was actually asked for: choosing your vocabulary when you adopt.

The refusal names the two performable remedies — restore the entry, or remove the edges first —
and nothing else. No verb rewrites a corpus's kinds, and a refusal may never assert a remedy no
command performs.

Done when dropping or renaming a kind that live refs carry is refused with the offending IDs,
and doing the same for an unused kind succeeds.
<!-- sq:subtask:ST6:body:end -->

#### Discussion

<!-- sq:subtask:ST6:discussion -->
<!-- sq:subtask:ST6:discussion:end -->
<!-- sq:subtask:ST6:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-25T14:49:42Z] Olivia Lead:
  - Open question for the architect, deliberately not settled in this task. sq graph --json normalises every dependency edge to the literal edge_kind="depends-on" regardless of which of the two spellings is stored (_services/_refs.py:79-80, :111-116), and that literal is documented as the output contract at _cli/_main.py:988-999. Once the dependency kinds are renameable, what that field emits is undecided: the declared blocker/dependent kind name, a fixed sentinel, or the semantic role itself.
  - @architect this is an agent-facing JSON contract, so it needs a ruling rather than a dev picking one. The tests/meta literal scan in ST4 forces the question at the same moment, since the current normalisation is one of the ~24 literal bindings being converted.
- [2026-08-25T15:02:04Z] Robert Architect:
  - Ruled, ADR-775 amendment A2 (2026-08-25). The dependency normalisation stays - collapsing the pair is what lets an item authored with both "A blocks B" and "B depends-on A" dedupe to a single edge, and emitting the raw spelling would un-collapse it into two. What changes is what the collapsed edge is named.
  - edge_kind emits a DECLARED KIND KEY - never a semantic, never a fixed sentinel - so every value of the field stays the same kind of thing and a project reads its own spelling. For a dependency edge it is the key of the kind carrying dependency in the DEPENDENT direction (depends-on under the bundled spec). Section 3 permits a project to declare only the blocker direction; in that case the blocker key is the canonical, and "direction" keeps the meaning it has today either way - "out" means the expanded item depends on the child.
  - GraphNode gains edge_semantic: the edge kind declared semantic role, or null for a navigational kind. That is the field a consumer branches on. Emitting only the spelling leaves every agent testing edge_kind == "depends-on", which is the same declared-but-found-by-literal defect section 2 removes from the engine - an agent reading this JSON is one of its consumers. Emitting only the semantic loses the spelling the display needs and collides with a project free to name a kind "dependency".
  - Lands complete on first ship. Update the --json docstring at _cli/_main.py:995-998 and the GraphNode docstring to state both fields and which one to branch on; _graph_export _label (_services/_refs.py:250) and sq blocked (:607-611) branch on the semantic, not on edge_kind. The floor also gains one clause from A1: exactly one declared kind carries the new "default" role, mandatory (zero would make an existing bare ref undecodable, a load failure rather than a bounded sq check finding) - fold it into ST5 alongside the preload clause. @python-dev @tech-lead
- [2026-08-25T18:01:19Z] Olivia Lead:
  - Folded REV-808 F6 into ST5 and the acceptance: the per-capability floor has to be visible to sq workflow lint, not only at merge or first use. Drove it myself on a scratch squad rather than taking the report - an .overrides/workflow.toml whose [selected] ref_kinds omits the default-role entry gives sq workflow lint exit 0 and "workflow spec OK - no errors or warnings", while sq check exits 3 naming the spec. Lint is the command whose whole job is to say the spec is wrong.
  - Stated as placement, not a second implementation. lint_workflow_spec (_workflow/_loader.py:1032) already runs the loader own floor as phase 3 (_collect_floor_violations) and turns _build_spec structural failures into findings as phase 4, so the ref-kind floor just has to be evaluated on a path lint traverses. A lint-only copy of the rules would be the second rulebook the per-capability floor exists to avoid.
  - Also landed the A2 clause that was ruled onto this task but never made it into the prose: exactly one declared kind carries the default role, mandatory. It is now in the floor section and in ST5 alongside the preload clause, with the acceptance covering zero and two. That clause is what F6 scenario actually trips, so the two belong together.
  - @python-dev nothing else in this task changed - the three semantic conversions, the live-corpus refusal and the literal scan are as they were.
- [2026-08-25T20:32:05Z] Elias Python:
  - Converted all three engine bindings to declared semantics: dependency (via WorkflowSpec.dependency_ref_kind/dependency_ref_kinds/canonical_dependency_ref_kind), preload (preload_ref_kind), supersession (supersession_ref_kinds). 24 literal bindings gone; tests/meta/test_no_bundled_ref_kind_literal_outside_the_spec_layer.py scans src/squads/ (outside _specs/ and _migrations/) for an AST-exact bundled ref-kind literal, empty allowlist, currently zero hits.
  - A2's edge_kind/edge_semantic landed as ruled: edge_kind emits the declared kind key (dependent-direction kind, or blocker key when only that direction is declared); GraphNode gained edge_semantic (the declared role, or null) as the field consumers branch on. _graph_export's _label and sq blocked both switched to branch on the semantic. Graph JSON golden regenerated.
  - ST5 floor (exactly one default, exactly one preload, at most one per dependency direction, bare-TOML-key + no ':') now lives in WorkflowSpec._validate itself, so it surfaces through _build_spec's normal SquadsError path -- the same path sq workflow lint's phase 4 already converts into collect-all findings. Verified live: an override with [selected] ref_kinds omitting the default-role kind now makes sq workflow lint exit 1 naming the spec (previously exit 0), matching sq check's exit 3 -- the two surfaces agree.
  - ST6 live-corpus refusal for ref kinds added (_collect_ref_kind_alignment_errors, wired into validate_against_index and lint phase 5 with its own fix hint). Verified live: dropping a renamed kind while a live item still carries it refuses naming the item; the same kind unused drops cleanly.
  - Fallout: the new per-capability floor (mandatory default+preload) exposed ~25 pre-existing test fixtures across tests/unit, tests/cli, tests/service and tests/meta that hand-built a WorkflowSpec/raw payload without declaring [ref_kinds] at all -- fixed each to carry ref_kinds through (or declare a minimal default+preload pair). Also fixed two message-text assertions and the GraphNode-literal test file (tests/unit/test_graph_export_rendering.py) for the new required edge_semantic field.
  - Gates: pyright/ruff check/ruff format clean. Targeted run across tests/unit, tests/meta, tests/cli, tests/service, tests/integration, tests/tui (not tests/test_scale.py) is green. sq check clean. Stayed out of _migrations/ and the two files reserved for TASK-809.
<!-- sq:discussion:end -->
