---
id: REV-1166
sequence_id: 1166
type: review
title: Review the workflow, overrides, index, models and migrations sweep
status: Approved
author: reviewer
refs:
- TASK-1127
description: 'Commit aabe10f7: TASK-1127 ST3 docstring and comment sweep of the integrity-core
  packages.'
subentities:
- local_id: F1
  title: Reflog-append site now carries the read-scope comment from the finally block;
    the append comment is gone
  status: Verified
  severity: medium
- local_id: F2
  title: 'v0_5_to_v0_7 docstring: escaped \\b became \b, a backspace character the
    AST check cannot see'
  status: Verified
  severity: low
- local_id: F3
  title: Rewritten prose keeps nonexistent _check_* and _check_views names; LEVEL_RANK
    called private but imported
  status: Verified
  severity: low
- local_id: F4
  title: 'Six rewrites now ambiguous or wrong: global spec, effective_prefix, repad,
    read scope, vocab, ruling'
  status: Verified
  severity: low
- local_id: F5
  title: History residue in rewritten docstrings and comments in models, loader and
    overrides
  status: Verified
  severity: low
- local_id: F6
  title: 'Rewrap collateral: list continuations unindented in three docstrings; Layer
    naming dropped in store'
  status: Verified
  severity: low
- local_id: F7
  title: F6 fix indented only the first line of the artifact-key paragraph in the
    manifest docstring
  status: Verified
  severity: low
created_at: '2026-10-26T13:42:37Z'
updated_at: '2026-10-26T13:57:50Z'
---
<!-- sq:body -->
Review of commit aabe10f7 (TASK-1127 ST3): the docstring and comment sweep of `src/squads/_workflow/`, `_specmerge.py`, `_overrides/`, `_index/`, `_models/` and `_migrations/` (37 files).

## Scope and method

- Read every deleted docstring and comment hunk next to its replacement and asked, for each removed sentence, whether it carried a constraint the code does not show: lock order, transaction and commit ordering, the skew-direction rule and its exemptions, reflog never-raise and buffer-time snapshots, marker and section contracts, frozen-vocabulary rules in runners, merge and splat rules, validation phases.
- Checked rewrites against the code where they make a claim (bundled spec global, `LEVEL_RANK` users, `_strip_ref_rule_targets_of_dropped_types`, `check_ref_kinds_floor`).
- Collateral scans: compiled every changed module at both revisions and searched docstrings for control characters; resolved every `:func:`/`:meth:`/`:data:` target and every underscored backticked name in the added prose; scanned every comment run for mixed `#:`/`#` prefixes (the scanner was checked against a planted positive first).
- Migration runners keep their version references. The CLAUDE.md pointers into these docstrings still hold, including the skew-direction rule and its exemptions in the `_index/_store.py` module docstring.

## Result

The sweep keeps the integrity-core constraints: the lock order and try/finally rule, the skew-direction rule with both exemptions, the read-scope isolation from the commit path, the failure model, the buffer-time snapshot, the ContextVar ownership caveat, merge order, token territory, collect-all versus fail-fast, the frozen-vocabulary rules and the mid-chain skew rule all survive. The `#:` blocks are intact. The findings are one comment that is now false at its site, one escape the wrapper broke, stale names carried into rewritten text, a handful of rewrites that are now ambiguous or wrong, history residue, and list formatting.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1166 add-finding "…" --severity medium`; track with `sq review 1166 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Reflog-append site now carries the read-scope comment from the finally block; the append comment is gone

<!-- sq:finding:F1:body -->
`src/squads/_index/_store.py:461`, inside `transaction()`, directly above `if ctx.reflog_ops:`. The new comment reads:

> Unconditional, commit or raise: drop any snapshot this store filed so a later read in the invocation cannot see pre-mutation state.

That is the read-scope comment from the `finally` block (line 483), duplicated onto the reflog-append block. It is false here: this block runs only after a successful commit and appends the reflog, it drops no snapshot. The deleted comment it replaced was:

> Reflog append: strictly after os.replace, inside all locks. Guarded so any error degrades to a warning — never surfaces from an already-committed mutation (never-raise contract). Each entry replays its OWN buffer-time ts/actor/session snapshot (see `_ReflogOp`) — not one snapshot shared across every buffered op.

The docstring and the `except` tag still state the never-raise half, but the site comment that someone editing the append block reads now describes another block. Restore a one-line reflog comment here (after `os.replace`, under the locks, never raises, each op replays its own snapshot).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-26T13:54:43Z] `python-dev` Elias Python:
  - Fixed: the reflog-append block in transaction() has its own comment again (after os.replace, under all locks, never raising, each op replaying its own buffer-time snapshot); the read-scope comment stays only in the finally.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — v0_5_to_v0_7 docstring: escaped \\b became \b, a backspace character the AST check cannot see

<!-- sq:finding:F2:body -->
`src/squads/_migrations/_v0_5_to_v0_7.py:11`, module docstring. The parent had `whole-word (``\\bOLD\\b``)`; the rewrite has `whole-word (``\bOLD\b``)`. The docstring is not a raw string, so `\b` is now a backspace character: `m.__doc__` contains `'whole-word (``\x08OLD\x08``) across '`. It is the only control character in any docstring of the 37 files at either revision (checked by scanning `ast.get_docstring` on both trees).

The docstring-stripped AST comparison cannot see this. Restore `\\b` (or make the docstring raw).
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-26T13:54:46Z] `python-dev` Elias Python:
  - Fixed: \\\\b restored in the 0.5 to 0.7 docstring. A scan of every docstring in src/ now finds control characters only in four untouched _cli command docstrings; none in the files this sweep changed.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Rewritten prose keeps nonexistent _check_* and _check_views names; LEVEL_RANK called private but imported

<!-- sq:finding:F3:body -->
Rewritten prose that still names functions that do not exist, or states a false scope:

- `src/squads/_workflow/_validator_names.py:176` `_check_ref_rule_targets`, `:183` `_check_selections_that_cannot_fire`, `:253` and `:401` `_check_validators_assignment`, `:368` `_check_category_consistency`. The functions are `check_ref_rule_targets`, `check_selections_that_cannot_fire`, `check_validators_assignment` and `check_category_consistency` in `_workflow/_validity.py`.
- `src/squads/_workflow/_loader.py:625` (`_parse_view`): "cross-referenced later by ``_check_views``"; the function is `check_views`.
- `src/squads/_workflow/_validator_names.py:214` (`LEVEL_RANK`): "Private: external callers ask only whether a selection clears the floor". `_workflow/_validity.py:45` imports it and indexes it at line 529.

Each of these lines was rewritten in this commit, so the names were in hand. Found by resolving every `:func:`/`:meth:`/`:data:` target in the added prose against `src/`.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-26T13:54:48Z] `python-dev` Elias Python:
  - Fixed: check_ref_rule_targets, check_selections_that_cannot_fire, check_validators_assignment, check_category_consistency and check_views named correctly; LEVEL_RANK now says only the Plane-1 level check reads it.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Six rewrites now ambiguous or wrong: global spec, effective_prefix, repad, read scope, vocab, ruling

<!-- sq:finding:F4:body -->
Rewrites that are now ambiguous or wrong:

- `_workflow/_models.py:653` (`WorkflowSpec`): "there is no process-global spec". `_workflow/__init__.py` holds `_BUNDLED_SPEC`, loaded once at import. The rule (CLAUDE.md) is no process-global *mutable* or active spec; say that.
- `_models/_item.py:55` (`effective_prefix`): "In production it never runs". The function runs on every `Item.id`; it is the fallback branch that never runs.
- `_models/_index.py:92` (`allocate_id`): "``sq migrate repad <width>`` raises it" reads as repad raising the error. The parent said repad raises the padding.
- `_index/_store.py:370` (`_read_from_disk`): "the one implementation behind :meth:`load` and :meth:`transaction`, which must never consult or fill the read scope" now attaches the rule to `load` too, which is the scope's only consumer. The parent scoped it to `transaction`.
- `_models/_vocab.py:5-6`: "Folder resolution stays in ``SquadPaths.folder_for``/``squad_relative``, not here, without a dedicated design decision" lost its verb; the parent said do not fold it in here without a design decision.
- `_migrations/_v0_14_to_v0_15.py:20`: "which that ruling fences off". The rewrite deleted the sentence that introduced the architecture ruling, so "that ruling" has no referent.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-26T13:54:51Z] `python-dev` Elias Python:
  - Fixed by hand: the global-spec claim now says no process-global mutable or active spec (bundled spec loaded once, read-only); effective_prefix says the fallback branch never runs; allocate_id says raising the padding via repad lifts the limit; _read_from_disk scopes the read-scope rule to transaction again; _vocab regains its verb; the 0.14 to 0.15 runner says the step must not extend into the standing sweep.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — History residue in rewritten docstrings and comments in models, loader and overrides

<!-- sq:finding:F5:body -->
Rewritten text that still narrates a before state that exists only in the history (stranger test):

- `_models/_item.py:410` (`_empty_list_if_unset`): "The empty string is kept because the earlier ``list(data.get(key, []) or [])`` accepted it".
- `_models/_item.py:292-293` (`from_frontmatter`): "coercing there having put ``TypeError``/``ValueError`` outside the ``except``".
- `_models/_markers.py:77` (`view_tag_parts`): "a recogniser accepting only the bare form returned ``None`` silently for the real producers' output".
- `_workflow/_models.py:628` (`_BUNDLED_CONTAINER_HEADINGS`): "keyed by kind alone, this table outranked an adopter's declared plural ... rendering "## User Stories" above a container marked `sq:outcomes`". The `subentity_container_heading` docstring was rewritten to the present tense ("must not get"); this comment was not.
- `_workflow/_loader.py:1179` (`_collect_unreachable_status_errors`): "judging against the flat spec-wide set let ``sq workflow lint`` call a corpus clean while ``sq check`` ... called the item an error", and `:1493`: "closing lint's disagreement with `sq check`".
- `_overrides/_service.py:1501-1502` (`_check_role_override_resolves`): "no reporter loaded one, so ``sq check`` ... could say "no issues" while ``sq sync`` was impossible; workflow and playbook overrides are already reported".

Each keeps a real constraint; state it in the present tense (for example: lint judges per lifecycle so it agrees with `sq check`).
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-26T13:54:54Z] `python-dev` Elias Python:
  - Fixed: the empty-string, coercion, bare-form recogniser, container-heading, lint-agreement and role-override-reporting texts now state the constraint in the present tense.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Rewrap collateral: list continuations unindented in three docstrings; Layer naming dropped in store

<!-- sq:finding:F6:body -->
Formatting collateral from the rewrap:

- Lists in module docstrings lost their continuation indent, so each item's second and later lines sit at column 0: `_specmerge.py:7-20` (numbered), `_workflow/_loader.py:13-25` (numbered), `_overrides/_manifest.py:7-18` (bulleted). In reStructuredText that ends the list item at the first continuation line. Indent the continuations by the marker width.
- `_index/_store.py`: the module docstring now numbers the locks 1, 2, 3 and dropped the "Layer N" names, while the code comments (lines 305, 309, 311, 326, 443-449, 489-495) and the `overwrite` docstring (568-571) still say "Layer 1/2/3". Either keep "Layer" in the module docstring or say "lock N" in the comments.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-26T13:54:56Z] `python-dev` Elias Python:
  - Fixed: list continuations indented in _specmerge, _loader and _manifest; the store docstring and the transaction() docstring use Layer 1/2/3 like the code comments. All edits by hand, not the wrapping tool.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — F6 fix indented only the first line of the artifact-key paragraph in the manifest docstring

<!-- sq:finding:F7:body -->
`src/squads/_overrides/_manifest.py:18-21`, module docstring, introduced by the F6 fix in 892f1b58. The paragraph after the bullet list now indents only its first line:

```
  An artifact key is its path relative to the ``squads`` package root
(``_rendering/templates/agents/role.md.j2``, ``_specs/workflow.toml``), unique by construction,
```

That paragraph is not part of the content-store bullet; it was a separate paragraph at column 0 in aabe10f7. Remove the two-space indent on that line so the whole paragraph sits at column 0 again.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-26T13:57:25Z] `python-dev` Elias Python:
  - Fixed: removed the stray two-space indent on the artifact-key paragraph in the _manifest module docstring; the other two F6 files (_specmerge, _loader) have no partial indents.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-26T13:43:11Z] `reviewer` Paul Reviewer:
  - Six findings (one medium, five low); verdict: changes requested, prose only. @python-dev F1 is the one that matters: the reflog-append block in `transaction()` now carries the read-scope comment from the `finally` block. F2 is a broken escape that the docstring-stripped AST comparison cannot see. F3 to F6 are stale names, imprecise rewrites, history residue and list indentation. No integrity-core constraint was lost apart from the F1 site comment. Migration runners keep their version references, and the CLAUDE.md pointers still hold.
    
    Out of scope for this prose review, a code observation for triage (driven): `_strip_ref_rule_targets_of_dropped_types` in `_workflow/_loader.py` matches `v.partition(":")[2] in dropped_types`, so a level-suffixed `ref_rule_target_present:contract@warn` survives a `[selected].items` drop of `contract`; the unsuffixed entry is stripped. Inferred, not driven: `check_ref_rule_targets` then refuses the dangling target, which is the brick this helper exists to prevent.
- [2026-10-26T13:45:23Z] `qa` Mara Tester:
  - Driven: the level-suffix gap reproduces. Filed BUG-1167 (targets MILE-1051): with @warn the squad is bricked, without it the entry is stripped.
- [2026-10-26T13:56:24Z] `reviewer` Paul Reviewer:
  - Re-review of 892f1b58. I checked F1 to F6 against the code and they hold, so they are now Verified. LEVEL_RANK's new claim is right: `_check_validator_level` is its only reader. My control-character scan at HEAD finds only form feeds (`\f`, Click's help-truncation marker) in the `_cli` callbacks `tree`, `role_catalog`, `role_list` and `set_default_role`. They are identical at aabe10f7^, so they predate the sweep and are intentional. The mixed `#:`/`#` scan is clean. @python-dev one new low finding, F7: the F6 fix indented only the first line of the artifact-key paragraph in `_overrides/_manifest.py`. It is a one-line fix; the review stays InReview until then.
- [2026-10-26T13:57:49Z] `reviewer` Paul Reviewer:
  - F7 verified at 4c322797: the artifact-key paragraph is back at column 0. All seven findings are Verified; approving.
<!-- sq:discussion:end -->
