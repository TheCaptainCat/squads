---
id: FEAT-898
sequence_id: 898
type: feature
title: 'Validator assignment grammar: level, threshold, required context'
status: Done
parent: EPIC-540
author: product-owner
priority: high
refs:
- MILE-867:targets
- ADR-864:implements
description: 'The gating foundation ADR-864 orders first: a selection declares its
  level, its parameter/threshold, and its required context'
subentities:
- local_id: US1
  title: Declare a validator's level (error|warn) in its selection
  status: Done
- local_id: US2
  title: 'Declared floor: a selection may raise level, never lower it'
  status: Done
- local_id: US3
  title: Move validator thresholds from module constants into the spec
  status: Done
- local_id: US4
  title: Declare each validator's required context; gate builds its runnable set
  status: Done
- local_id: US5
  title: parent_present becomes selectable at warn
  status: Done
created_at: '2026-09-03T09:02:24Z'
updated_at: '2026-09-08T14:56:29Z'
---
<!-- sq:body -->
## Why this is first

ADR-864's accepted build order opens here because everything else in the catalog build-out
depends on it. Today a validator hardcodes its own level (error aborts create/update; warn is
advisory everywhere) and an adopter can select a validator but not say how much they mean it.
That single missing dimension is why real checks either shipped bundled-and-noisy (the
contract-currency rule) or stayed unbundled entirely (the requires-a-parent check, whose own
docstring says turning it on would error on every parentless item already on disk).

## Scope

- A selection can carry a **declared level**, subject to a **declared floor** a selection may
  raise but not lower — for the members whose level is load-bearing (e.g.
  `subentity_container_marker` stays error; see Correction below).
- A **threshold/parameter lives in the spec**, not a module constant — the `:<param>` suffix
  stops being documentary-only and gets read back at runtime.
- The **context a validator requires is declared**, the gate builds its runnable set from the
  context it actually holds, and an assertion over the catalog enforces the correspondence
  (this is what discharges ADR-864's gate correction: non-participation stops being an accident
  of a sentinel, and no docstring asserts a catalog-wide property nothing verifies).

## Correction carried in from the ADR (not open to re-litigation here)

Two rulings from ADR-864's gate-clause correction carry into this feature unchanged:
- the create/update gate is **not** widened to the item's on-disk text;
- `subentity_container_marker` **keeps `error`** — it is not demoted by this feature.

One consequence worth stating because it is easy to miss: with a level on the assignment,
`parent_present` (Part 1's requires-a-parent check, deliberately in no category bundle) becomes
**selectable at warn**. The cliff that kept it unbundled was its level, not its rule.
<!-- sq:body:end -->

## User Stories

_Add with `sq feature 898 add-story "As a <role>, I want … so that …"`; track with `sq feature 898 story <n> update --status <Status>`._

<!-- sq:stories -->

<!-- sq:story:US1 -->
### US1 — Declare a validator's level (error|warn) in its selection

<!-- sq:story:US1:body -->
As a project maintaining its own .overrides/workflow.toml, I want to declare a validator selection's level, so that I can dial how much I mean a rule instead of it being fixed all-or-nothing by the catalog.

Acceptance: a selection's level is declared (e.g. a level suffix on the assignment or a per-type map), validated at spec load the same way the existing parameter suffix is; error aborts create/update as today, warn stays advisory everywhere; the bundled catalog's current per-member levels are the defaults when a project declares no override.
<!-- sq:story:US1:body:end -->

#### Discussion

<!-- sq:story:US1:discussion -->
<!-- sq:story:US1:discussion:end -->
<!-- sq:story:US1:end -->

<!-- sq:story:US2 -->
### US2 — Declared floor: a selection may raise level, never lower it

<!-- sq:story:US2:body -->
As a project, I want a declared floor that a selection may raise but never lower for the validators whose level is load-bearing, so that a project cannot silently weaken a check the engine's own correctness depends on.

Acceptance: attempting to declare a level below a member's floor is a spec-load error naming the member and its floor; subentity_container_marker's floor is error (see the Correction in the body — this is carried in from ADR-864's gate-clause ruling, not decided here); which members carry a load-bearing floor is enumerated and tested.
<!-- sq:story:US2:body:end -->

#### Discussion

<!-- sq:story:US2:discussion -->
<!-- sq:story:US2:discussion:end -->
<!-- sq:story:US2:end -->

<!-- sq:story:US3 -->
### US3 — Move validator thresholds from module constants into the spec

<!-- sq:story:US3:body -->
As a project, I want a validator's threshold or parameter (e.g. the sub-entity title-length limit) declared in the spec instead of hardcoded as a module constant, so every squad isn't stuck with our number.

Acceptance: the existing :<param> suffix, which is documentary-only today and never read back at runtime, is read back and drives the check; a project can override the threshold in its own spec; the bundled default reproduces today's behaviour exactly (same threshold value, same message).
<!-- sq:story:US3:body:end -->

#### Discussion

<!-- sq:story:US3:discussion -->
<!-- sq:story:US3:discussion:end -->
<!-- sq:story:US3:end -->

<!-- sq:story:US4 -->
### US4 — Declare each validator's required context; gate builds its runnable set

<!-- sq:story:US4:body -->
As the engine, I want each validator to declare the context it requires (e.g. the active clock, the full corpus, a single item) and the gate to build its runnable set from the context it actually holds, so non-participation is a declared fact instead of an accident of a naming sentinel.

Acceptance: every catalog member declares its required context; an assertion over the whole catalog enforces that every member's declared context is one the gate can supply somewhere; the create/update gate runs only the subset whose required context it holds at that call site — no silent no-op member.
<!-- sq:story:US4:body:end -->

#### Discussion

<!-- sq:story:US4:discussion -->
<!-- sq:story:US4:discussion:end -->
<!-- sq:story:US4:end -->

<!-- sq:story:US5 -->
### US5 — parent_present becomes selectable at warn

<!-- sq:story:US5:body -->
As a project, I want parent_present selectable at warn now that level is declarable, so I can adopt the convention without the create/update-time cliff that kept it unbundled (its own docstring: turning it on would error on every parentless item already on disk).

Acceptance: parent_present can be selected at warn in a project's own spec without erroring on existing parentless items; selecting it at error still behaves as today; this project's bundled spec is not changed by this story on its own (selection is a project choice, not a new bundled default).
<!-- sq:story:US5:body:end -->

#### Discussion

<!-- sq:story:US5:discussion -->
<!-- sq:story:US5:discussion:end -->
<!-- sq:story:US5:end -->
<!-- sq:stories:end -->

## Discussion

<!-- sq:discussion -->
- [2026-09-08T14:01:58Z] Theo Writer:
  - Documented the validator selection grammar for adopters. Docs only — no source, tests or spec touched.
    
    **Where.** The reference lives in `docs/overrides.md`, as a new `#### Validators: the checks a type runs, and how loud they are`, sibling to `#### Items: custom work types`. `validators` is a field of `[items.<type>]` that only ever appears in `.overrides/workflow.toml`, and that file is what overrides.md documents; it already carried two `validators = [...]` snippets with no grammar behind them. Also: `validators` added to the optional-field list in both docs' item-type reference, one row added to overrides.md's hard-stop error table, and `docs/workflow.md`'s "Keeping a contract current" extended with the multi-target form and the level note (that section is where an adopter arrives from the usage side).
    
    **Verified against the shipped code, by driving a throwaway squad** (fresh `sq init`, `.overrides/workflow.toml`, removed afterwards) — every error message and finding quoted in the text is copied from a real run, not paraphrased:
    
    - All four entry shapes load; param precedes level; a reversed `name@level:param` fails closed reading the whole tail as a level, and `@warn@error` likewise.
    - `error` -> `sq check` exit 3; `warn` -> exit 0. Both drove the write door too.
    - Floor: `parent_acyclic@warn` and `subentity_container_marker@warn` refused with the floor message; both accepted at `@error`; `item_status_valid@warn` and `no_status_banner@error` accepted.
    - Threshold: `subentity_title_max:40` moves both the `sq check` finding and the `add-<kind>` create-time advisory to 40; `:0` and `:abc` refused; with no override a 49-char title is silent.
    - Repeats: two `ref_rule_target_present:<T>` entries with different targets load clean and produce one combined finding naming both, and satisfying either edge clears it; the same param twice is refused; two `subentity_title_max:<n>` entries are refused with the first-match reason; `@level` alone never separates two entries.
    - `parent_present@warn` loads over an existing parentless item, warns at exit 0, and refuses neither the create nor an ordinary update. Bare and `@error` both refuse both. That is the cliff, driven.
    - Raising a level does **not** always give a write gate: `no_status_banner@error` and `ref_rule_target_present:contract@error` make `sq check` exit 3 while every write and the transition to a delivered status still succeed. Documented as the rule (frontmatter+index checks gate; file-text and corpus-type-scan checks do not), not as a list.
    - `[selected]` has no `validators` section, so there is no deselection surface — but a type's own bundled list is an ordinary array leaf: replacing `[items.epic] validators` silently drops the bundled `no_parent` and epics start taking a parent. Driven with a control (the `$(*items.epic.validators)` splat form keeps it and the loader then refuses the contradiction).
    - `--force` on a status update as the designed recovery for an off-graph status: driven end to end (plain update refused, `--force` succeeds, finding clears).
    
    **Deliberately left out.** No enumeration of the full validator name catalog or of the core/category bundles — the catalog is declared to grow, nothing lists it back through the CLI, and an exhaustive-looking list is the line that rots first. The text names only the checks it actually explains and says plainly that an unrecognised name is refused at load. It also states, rather than papers over, that no command lists a type's effective set.
    
    **One stale statement found elsewhere, not fixed:** `docs/overrides.md` § "`[selected]` — dropping a built-in" says the accepted `[selected]` section keys are `items`, `statuses`, `lifecycles`, `collections`, `subentity_kinds`, `roles` and `ref_kinds`. The live refusal message lists `views` as an eighth. The adjacent top-level-section lists in both docs already include `views`, so this one list is the outlier. Left alone per scope — @manager for the call on who fixes it.
    
    **Also for the record, not mine:** `tests/meta` currently fails the stray-ticket gate on two uncommitted source comments — `src/squads/_cli/_role.py:484` and `src/squads/_cli/_skill.py:333`, both carrying an ADR id. Absent from HEAD, so they belong to the concurrent view/skill work, and they will block a commit. @manager to route.
    
    `uv run sq check` clean. `tests/meta` + `tests/cli/test_docs_cli.py`: 284 passed, the only failures the two source violations above; `docs/` is clean in that gate. Did not run the full suite.
- [2026-09-08T14:07:32Z] Theo Writer:
  - Follow-up pass on the validator-grammar docs: the stale `[selected]` key list corrected, and the write-gate rule moved to the point of decision. Still docs only.
    
    **1. `[selected]` key list — corrected to eight, driven not assumed.** Drove the refusal in a fresh throwaway squad rather than adding `views` on the routing note. Output:
    
    ```
    selected.bogus: unknown [selected] section 'bogus' — use one of the accepted [selected] sections in v0.15.0: ['collections', 'items', 'lifecycles', 'ref_kinds', 'roles', 'statuses', 'subentity_kinds', 'views']
    ```
    
    Then drove `views` as a real filter, not just a name in an error string: `selected.views` omitting `milestone_rollup` drops it, and the loader correctly refuses next because `[items.milestone]` still attaches it — `views entry 'milestone_rollup' does not name a declared [views] entry — 'milestone_rollup' was dropped from a [selected] list (selected.views)`. Adding `[items.milestone] views = []` alongside loads clean with five views listed. So it is a working section key.
    
    Two corrections beyond adding the key, both from what the drive showed:
    - The sentence said the eight were "the same set the top level accepts". They are not quite — top level also accepts `selected` itself. Now reads "the sections the top level accepts, less `[selected]` itself".
    - Added the refusal output plus the same escape hatch the top-level-sections paragraph already carries ("the list to trust rather than this one"). That list rotted once by exactly one key; now a reader who hits the eighth-key case has the authoritative source in front of them instead of a hand-maintained enumeration.
    
    **2. The write-gate rule — the problem was worse than placement.** The `error` bullet in the level definition read `**error** — sq check exits 3, and the create/update gate refuses the write`. That bullet *was* the overclaim, and a bullet list is what a reader deciding a level skims. Promoting the caveat alone would have left the false sentence sitting above it.
    
    Restructured so the order matches the decision:
    - The `error` bullet now says only what is unconditionally true (`sq check` exits `3`) and that gate participation depends on the check, not the level.
    - The rule follows immediately, as a blockquote — the idiom this file already uses for a rule a reader must not miss (the prefix/folder warning). Text: a check that reads only frontmatter and the index takes part in the gate; a check that reads the item's file text, or which types exist, is reported and sits the gate out whatever level you give it.
    - Added the failure mode in the adopter's own words: "Select either of those at `error` expecting a blocked write and you get a red pipeline over an unchanged workflow."
    - The retroactive-refusal warning (ordinary edits on already-failing items start being refused) moved to *after* the rule and is now scoped to gating checks, since that is the only kind it applies to. It ends by pointing at the `parent_present@warn` route through.
    
    **Re-verified all three cases against the current tree**, because the gate call site (`_services/_base.py`) is under concurrent edit and my earlier numbers predated it. Unchanged:
    - `subentity_title_max:40@error` (frontmatter+index) — `sq check` 3, ordinary update refused (exit 1).
    - `no_status_banner@error` (reads file text) — the write that created the banner exit 0, `sq check` 3, ordinary update exit 0.
    - `ref_rule_target_present:contract@error` (corpus type scan) — every transition through to a delivered status exit 0, `sq check` 3 with the finding at error level.
    
    Gates: `tests/meta` + `tests/cli/test_docs_cli.py` 286 passed, 0 failed — the two stray ADR-id source comments I reported last pass are gone from the working tree, so that gate is green again. All cross-file doc anchors resolve. `uv run sq check` clean. My diff is `docs/overrides.md` and `docs/workflow.md` only. Did not run the full suite; no commit.
- [2026-09-08T14:56:29Z] Catherine Manager:
  - Closed. The validator assignment grammar ships: a level suffix on the selection (@ rather than a second colon, since the param separator already owns that), a declared floor a selection may raise but not lower, thresholds resolved from the spec rather than module constants, and the multi-versus-single-selection distinction declared per member with an import-time assert closing the classification. parent_present is now selectable at warn -- the cliff that kept it unbundled was its level, not its rule.
  - REV-925 Approved: six findings, F1/F2/F4/F5/F6 Verified and F3 WontFix. Two were caused by the fixes themselves -- F5 by over-generalising F1s duplicate rule to a member whose resolver reads only its first match, and F6 by broadening a message that then contradicted itself. Both closed at the class level rather than the instance: the multi/single split is declared and asserted, so the next parameterised member cannot be added without someone classifying it.
  - Also delivered against this feature: the grammar, the floor and the write-gate rule are now documented for adopters in docs/overrides.md and docs/workflow.md. Driving them turned up an adopter-visible fact the code comments did not state -- raising a level does not always give a write gate, because a check that reads the items file text or scans the corpus cannot run on the gate path at all. The reviewer confirmed the code already declares that distinction per member and a tests/meta check re-derives it, so the docs describe a real property rather than an aspiration.
<!-- sq:discussion:end -->
