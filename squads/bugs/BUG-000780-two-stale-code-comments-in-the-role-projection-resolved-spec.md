---
id: BUG-780
sequence_id: 780
type: bug
title: Two stale code comments in the role-projection/resolved_spec seam
status: Verified
author: qa
severity: low
refs:
- REV-770
created_at: '2026-08-22T09:35:10Z'
updated_at: '2026-08-22T10:33:10Z'
---
<!-- sq:body -->
Two stale in-code justifications in the same recent seam, both re-verified against source
rather than restated. Neither changes behaviour; both are accuracy defects in text a future
implementer will read and trust.

## `RoleDef._RECONCILED_EXTRA_KEYS`' comment states a false premise

The comment justifying keeping `description` out of `extra_keys()` (and so out of
`PERMITTED_EXTRA_SKEW`) reads:

    description carries no such legacy corpus: before this table existed, nothing ever wrote
    extra.description, so there is no lagging index to forgive …

Checked directly against history: `git show ea891a6:src/squads/_services/_roster.py` (the
0.13.0 release tag) already has `X.DESCRIPTION: role.description` written explicitly at both
`activate_role` and `add_dev` — the same two lines (56 and 87) it is at today. That predates the
table this comment defends by several releases; every role item in every existing squad already
carries `extra.description`. The premise is false.

The *conclusion* survives, for a different reason than the one stated: `create` writes that key
inside its own transaction, so markdown and index have never disagreed on it, and no exemption
is owed for that reason. The test docstring covering the same ground
(`tests/unit/test_role_def_extra_keys.py`) already states the correct, narrower claim — "no
legacy corpus that ever wrote `extra.description` **outside a transaction**" — so only the code
comment overreaches, not the test that was written against the same design.

Worth correcting rather than shrugging at because the comment closes with a rule for the next
field to use: "a field belongs here, not in `_EXTRA_FIELD_KEYS`, exactly when adding it there
would be a pure widening of the guard's exemption with no legacy case to justify it." A reader
who takes that rule at face value and asks "was this key ever written before?" gets the wrong
answer for `description` itself, which was. The rule that actually holds — and that
`PERMITTED_EXTRA_SKEW` exists for — is "was it ever written to markdown *outside* a
transaction", not "was it ever written at all".

Same table, a second small consequence, also confirmed by reading the current source: now that
`to_extra()` splats `_RECONCILED_EXTRA_KEYS` alongside `_EXTRA_FIELD_KEYS`, the explicit
`X.DESCRIPTION: role.description` at both create sites is a redundant second declaration of a
value already present in the dict it overwrites. Harmless while the two agree; a future change
to `_RECONCILED_EXTRA_KEYS`'s getter would silently not apply at create time, because the
explicit line would keep winning. Removing the two explicit lines makes the table the single
source of the mapping it already claims to be.

## `open_service`'s `resolved_spec` docstring misnames its own callers, confirmed by reading the call graph

The docstring says: "The CLI's root callback … is the one caller that supplies it … Every other
caller — direct test calls, `sq ui`, the cross-check-bypassing fallback path — leaves this
`None`." Traced the actual call graph rather than the prose:

- **`sq ui`.** `_cli/_ui.py` calls `get_service()`. The Typer app's root `@app.callback()`
  (`_cli/__init__.py`) calls `bind_active_spec` for every invocation, `sq ui` included, so
  `ctx.active_spec` is already populated by the time `ui()` runs. `sq ui` is a sync command
  that never crosses `command`'s sync/async bridge, so `_READ_SCOPE_META_KEY` is never in
  `root.meta`; `get_service()` therefore falls to its `else` branch, `_build_plain_service()`,
  which unconditionally calls `open_service(..., resolved_spec=ctx.active_spec)` — a non-`None`
  value. `sq ui` opts out of the read scope and the per-invocation `Service` memo (the thing its
  own docstring says it opts out of), not out of `resolved_spec`.
- **The bypass path.** `get_service_bypassing_index_cross_check`'s step 1 is a direct call to
  `get_service()` — the same path above, so it also supplies `resolved_spec`. Only its
  steps 2/3 (`_build_bypass_fallback_service`) construct a `Service` directly, and that helper
  never calls `open_service` at all — it goes straight to `load_workflow_spec`/`bundled_spec`.

The same misattribution appears twice more, verbatim, in
`tests/cli/test_workflow_cross_check_once_per_invocation.py`'s docstrings:
`test_open_service_direct_call_ignores_an_unrelated_ambient_spec` ("exactly what a test, `sq
ui`, or a second `IndexStore` … makes") and
`test_resolved_spec_is_the_documented_opt_in_kwarg_default` ("every existing direct caller
(tests, `sq ui`, the bypass fallback) is unaffected"). Both tests are sound on their own terms —
each exercises a genuine direct `open_service()` call with no `resolved_spec` — only the named
example (`sq ui`) is wrong; a direct test call and the bypass fallback's own construction are
correct examples on their own.

No behavioural consequence today: `sq ui` builds exactly one `Service` at startup and hands it
to the TUI, which never calls `open_service`/`get_service` again (confirmed: `grep -rn
"open_service\|get_service" src/squads/_tui/` is empty), so the cross-check still runs exactly
once for that session either way — the memo's absence for `sq ui` just means it is not shared
with anything, since nothing else asks.

Filed anyway, because the enumeration is the actual safety argument for the per-invocation
memo: "one caller supplies the shortcut, everyone else validates independently." If the real
answer is instead "every CLI caller supplies it, and only non-CLI callers validate
independently", that is a materially different and larger claim about how much of the surface
trusts a cached resolution, and the docstring making that claim should say so accurately rather
than naming the wrong exception.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-22T10:26:10Z] Mara Tester:
  - Verified on c6a03b2. git diff for every file this commit touches: the _RECONCILED_EXTRA_KEYS comment hunk in _catalog.py and the resolved_spec docstring hunk in _service.py are pure comment/docstring edits -- no line outside a #: comment or a triple-quoted docstring changed in either hunk (checked against the same commit's unrelated __post_init__ code addition in the same file, which is BUG-778's, to confirm the two are cleanly separable hunks). Both test-docstring hunks in tests/cli/test_workflow_cross_check_once_per_invocation.py are likewise docstring-only -- no assertion or test body line changed. tests/unit/test_role_def_extra_keys.py itself is untouched by this commit (git show c6a03b2 -- that path is empty), confirming it already held the correct wording and only the code comment needed correcting to match it.
  - Same claim confirmed on both sides: _catalog.py's comment now reads '...exactly when it was never written to markdown outside a transaction... since description itself was, from inside one'; test_role_def_extra_keys.py already said '...no legacy corpus that ever wrote extra.description outside a transaction'. Same rule, same wording basis, on both sides -- the point of the finding.
  - Same for the resolved_spec docstrings: _service.py's open_service and both test docstrings in test_workflow_cross_check_once_per_invocation.py now agree that sq ui and the bypass path's first step both reach get_service() and so already supply resolved_spec, and that only a direct open_service() call (chiefly a test) leaves it None -- the same, corrected enumeration in all three places.
  - Holds fully. Status note: InProgress on disk, not Fixed -- not transitioning (the CLI's own guard refuses InProgress -> Verified without --force). Flagging for whoever should move it to Fixed first.
- [2026-08-22T10:33:06Z] Catherine Manager:
  - Fix landed in c6a03b2 on release/0.14 (TASK-782), shipping in 0.13.1. Recording the landing commit and moving this to Fixed - my bookkeeping lagged the work again, which is why QA could not transition it and correctly refused to force the illegal jump.
<!-- sq:discussion:end -->
