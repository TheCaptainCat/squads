---
id: REV-1169
sequence_id: 1169
type: review
title: Review the CLI, TUI and remaining packages comment sweep
status: Approved
author: reviewer
refs:
- TASK-1127
description: 'Commit 3d5ef16b: TASK-1127 ST4 and ST5 docstring and comment sweep.'
subentities:
- local_id: F1
  title: 'find_markers docstring: the two readings lost their antecedent when the
    defining sentence was cut'
  status: Verified
  severity: low
- local_id: F2
  title: '_role_source_applies docstring split mid-sentence: an orphan ROSTER_ROLE
    parenthetical opens the body'
  status: Verified
  severity: low
- local_id: F3
  title: 'History residue in swept _cli/_common.py: parse_badge_code replaces the
    former per-axis parsers'
  status: Verified
  severity: low
created_at: '2026-10-26T14:58:12Z'
updated_at: '2026-10-26T15:01:09Z'
---
<!-- sq:body -->
Review of commit 3d5ef16b (TASK-1127 ST4 and ST5): the docstring and comment sweep of `src/squads/_cli/`, `_tui/`, `_backends/`, `_interactions/`, `_roles/`, `_rendering/`, `_memory/`, `_board/` and the top-level modules (50 `src/` files).

## Scope and method

- Read every deleted docstring and comment hunk beside its replacement and asked, for each removed sentence, whether it carried a constraint the code does not show: the marker position-blindness and `reject_markers` rule, the `AgentBackend` contract (managed-region warning, five per-host questions, non-abstract defaults, the seven-method surface), the `.claude` pointer containment rule, the atomic-write split, the markdown-before-index ordering, the read-scope and `Service` memo gate, the advertise-versus-dispatch split, fail-soft help versus refusing answer surfaces.
- No code change: my own script compared the docstring-stripped AST (bare string statements stripped too) of all 50 files against the parent; all equal.
- Typer callbacks: no docstring of any function decorated with a `command`/`callback` decorator changed. The `--help` output of 49 commands and groups (root, `list`, `tree`, `renumber`, `search`, `graph`, `import`, `override`, `role catalog/list`, addressed role verbs, `create <type>`, `task <n>` verbs and sub-entity groups, `workflow`, `check`, `repair`, `migrate`, `sync`, `adopt`, `init`, `ui`, ...) is byte-identical between the parent tree and HEAD in a scratch squad. The `\f` in `tree`, `role_catalog`, `role_list` and `set_default_role` is present and untouched; it is the only control character in any docstring of the changed files.
- `build_item_app` in `_cli/_items.py` and its neighbours read correctly; no mixed `#:`/`#` comment run and no stray `#     #` prefix in any changed file (scanner checked on a planted positive). No doubled words.
- Every `:func:`/`:meth:`/`:data:`/`:class:` target and backticked identifier in the added prose resolves against `src/`; spot-checked owner pairs (`RosterProjection.project_item`, `ViewsMixin.view_tag_present`, `ServiceCore._check_priority`, `MaintenanceMixin._repair_body_tag`, `CheckMixin._scan_for_check`, `IndexStore._atomic_write_sync`, `RoleDef.from_item`, ...). `from_extra_or_item` and `_project_roster_item` are gone from `src/`.
- Targeted tests at `-n 4`: `tests/meta`, the help-summary and shared-flag CLI tests and the managed-section/cheatsheet goldens, 538 passed.

## Result

The sweep keeps the constraints that matter: `find_markers` still states position-blindness and that `reject_markers` is the real guard; the `AgentBackend` docstring keeps the managed-region warning rule, the five questions, the containment rule and the non-abstract-default rationale; `_aio` keeps the regenerable-versus-data write split and the not-found propagation contract; `_itemfile` keeps the markdown-before-commit ordering; `command`/`get_service` keep the one-marker gate and the `sq ui` opt-out; the alias, dropped-type and override-failed refusal paths keep their advertise-versus-dispatch reasons. The findings are one dangling referent in the marker docstring, one split sentence, and one history residue.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1169 add-finding "…" --severity medium`; track with `sq review 1169 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — find_markers docstring: the two readings lost their antecedent when the defining sentence was cut

<!-- sq:finding:F1:body -->
`src/squads/_sections.py:126-132`, `find_markers` docstring. The new second paragraph reads:

> it refuses marker-shaped text and says backticks do not help. The two readings agree wherever the guard runs and diverge for a corpus adopted from outside squads, ...

"The two readings" has no antecedent any more. The parent defined them in the sentence the rewrite deleted:

> "A quoted tag is not matched" invites the belief that a corpus is safe because its authors quoted; it is safe because a guard refused it at the door. Those two readings agree everywhere the guard runs and diverge exactly where it does not

This is the docstring the CLAUDE.md marker gotcha points at, and the dropped sentence is the point of the paragraph: a corpus is marker-safe because `reject_markers` refused input at the door, not because authors quoted, so the two explanations only come apart for an adopted corpus. Restore one sentence naming the two readings (safe because quoted versus safe because the guard refused it), or rephrase so the divergence clause stands on its own.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T15:00:02Z] `python-dev` Elias Python:
  - Fixed: prose restored/rejoined by hand, AST equals HEAD, tests/meta green.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — _role_source_applies docstring split mid-sentence: an orphan ROSTER_ROLE parenthetical opens the body

<!-- sq:finding:F2:body -->
`src/squads/_views.py:313-317`, `_role_source_applies` docstring:

```
"""A ``role`` source's one host constraint: *item_type* must be the declared role type.

(:data:`~squads._workflow._models.ROSTER_ROLE`.) Whether this role item's slug resolves against
```

The summary-line split cut the sentence in two: the parenthetical that names the role type now opens the second paragraph on its own, followed by a stray full stop. Move the reference back into the sentence it belongs to, either the summary line or the body, or drop it.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T15:00:05Z] `python-dev` Elias Python:
  - Fixed: prose restored/rejoined by hand, AST equals HEAD, tests/meta green.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — History residue in swept _cli/_common.py: parse_badge_code replaces the former per-axis parsers

<!-- sq:finding:F3:body -->
`src/squads/_cli/_common.py:2545-2546`, `parse_badge_code` docstring, in a file this commit swept:

> The one generic value-parser for every flat badge axis (priority/severity/a project's own custom axis) — replaces the former hand-written pair of per-axis parsers.

"replaces the former hand-written pair" is history about the code, which the comment rule moves out of source. Found by grepping the comments and docstrings of the 50 changed files for history phrasing; it is the only hit that is history rather than present-state prose ("no longer declares" describing a spec, "legacy" naming a format). Drop the clause.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T15:00:08Z] `python-dev` Elias Python:
  - Fixed: prose restored/rejoined by hand, AST equals HEAD, tests/meta green.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T14:58:24Z] `reviewer` Paul Reviewer:
  - Review summary: 3 low findings (F1 dangling referent in the find_markers docstring, F2 split sentence in _role_source_applies, F3 history residue in parse_badge_code). No lost constraint, no stale name, no code change, no Typer help change (49 help screens byte-identical with the parent, the four intentional form feeds untouched). Recommended verdict: approve once F1 to F3 are fixed; all three are one-line prose edits.
    
    On the ceiling guard: I agree with not adding a docstring-length guard. The after-counts show the long docstrings are the contract-dense ones (the store module, AgentBackend, the loader and merge modules), so a ceiling low enough to matter needs an allowlist, and one high enough to need none catches nothing. More importantly, the defects three reviews of this sweep found were lost constraints, dangling referents, wrong rewrites and names that do not exist; a length guard cannot see any of them and rewards exactly the truncation that produced the first two. If a mechanical guard is wanted, the better candidate is the stale-name check both the dev and the reviews ran by hand: every :func:/:meth:/:data:/:class: target in a docstring must resolve to a definition in src/. It needs no allowlist, has a natural liveness row, and caught real defects in each increment (the _check_* names, from_extra_or_item, _project_roster_item). That is a separate decision for the operator.
- [2026-10-26T15:00:51Z] `reviewer` Paul Reviewer:
  - F1 to F3 verified at 02a68345: find_markers now names both explanations (guard refused vs authors quoted) before "The two diverge", so the antecedent is clear; _role_source_applies reads as one sentence; parse_badge_code history clause gone. Approved.
<!-- sq:discussion:end -->
