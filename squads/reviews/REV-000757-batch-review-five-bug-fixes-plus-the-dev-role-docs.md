---
id: REV-757
sequence_id: 757
type: review
title: 'Batch review: five bug fixes plus the dev-role docs'
status: Approved
author: reviewer
refs:
- TASK-748
- TASK-749
- TASK-750
- TASK-751
- TASK-752
- BUG-743
- BUG-732
- BUG-745
- BUG-744
- BUG-747
- ADR-738
- ADR-753
- ADR-754
- BUG-755
- BUG-756
subentities:
- local_id: F1
  title: sq role show and sq check crash on a non-dev slug ending in -dev
  status: Verified
  severity: high
- local_id: F2
  title: Unactivated -dev slug previews a name sq dev add will not assign
  status: Fixed
  severity: medium
- local_id: F3
  title: New-slug required-field validation is skipped for any -dev slug
  status: Fixed
  severity: medium
- local_id: F4
  title: Schema hard-stop and five more error sites still split remedies
  status: WontFix
  severity: medium
- local_id: F5
  title: Read scope's cross-call sharing has no observable effect today
  status: Verified
  severity: medium
- local_id: F6
  title: sq <type> <n> <verb> costs two index loads, not the ADR's one
  status: Verified
  severity: medium
- local_id: F7
  title: Override-carrying squads pay 3-5 whole-index parses per command
  status: WontFix
  severity: medium
- local_id: F8
  title: ADR-753's read-only-alias premise is false at sq sync
  status: Fixed
  severity: medium
- local_id: F9
  title: Empty-string override fields yield a nameless roster entry
  status: WontFix
  severity: low
- local_id: F10
  title: No test pins transaction scope invalidation on the raise path
  status: WontFix
  severity: low
- local_id: F11
  title: Docs say states is what the machine reaches; unreached are too
  status: Verified
  severity: low
- local_id: F12
  title: SHA pins have no update channel and no guard against regressing
  status: Verified
  severity: low
- local_id: F13
  title: Two CHANGELOG entries claim more reach than the fixes deliver
  status: Fixed
  severity: low
created_at: '2026-08-21T17:02:28Z'
updated_at: '2026-08-21T18:38:04Z'
---
<!-- sq:body -->
## Scope

Six commits on `release/0.14`, reviewed as one increment:

| commit | change | items |
|---|---|---|
| `84cfa04` | third-party GitHub Actions pinned to commit SHAs across three workflows | BUG-743, TASK-748 |
| `8f5b267` | `sq workflow lifecycles` catalog published; the `lifecycle` forward reference retired | BUG-732, TASK-749, ADR-738 |
| `ca7cee3` | three single-line CLI error render sites soft-wrapped | BUG-745, TASK-750 |
| `fb92ef5` | partial dev-role override reaches sync / `role show` / `check` | BUG-744, TASK-751, ADR-754 |
| `9bd3560` | request-scoped index read | BUG-747, TASK-752, ADR-753 |
| `9843ab4` | adopter docs for the dev-role change | — |

## Method

Attacked input shapes rather than the described happy paths. Every claim below is labelled
**driven** (reproduced against a real `sq` invocation or an in-process probe), **read** (traced
in source without executing the failing path), or **inferred**. Probes ran against throwaway
squads under a scratch directory, plus two in-process instrumentation harnesses:

- a counter around `IndexStore._read_from_disk`, to count scoped index reads per invocation;
- a counter around `SquadsDB.model_validate_json` with a call-site trace, to count *whole-index
  pydantic parses* per invocation — the real cost unit, and a superset of the first.

Verified SHA pins against the GitHub API (all four dereference to the commented tag; the
`actions/setup-node` pin matches what the moving `v5` tag resolves to today, so it is not a
silent patch downgrade). Confirmed `lifecycle_edges_in_order` is byte-identical to the deleted
`lifecycle_edges` it claims to re-derive. Ran the batch's own new tests plus `tests/meta`
(199 passed).

## ADR conformance

- **ADR-738 (`8f5b267`) — faithful.** §4's row shape, ordering rationale and exclusions are
  implemented exactly; §5's two type-row reference keys were already present, so the family is
  closed at six commands as the decision requires.
- **ADR-753 (`9bd3560`) — an improvement that should be recorded back, plus one claim the
  implementation does not deliver.** §2's premise ("`command` is documented as the single
  `anyio.run` per invocation") is false for `sq <type> <n> <verb>`, and anchoring the scope on
  the Click root context is the correct correction. It should be amended onto the ADR rather
  than left only in a docstring. Separately, the *Consequences* section's "one invocation
  observes one index state" is not delivered — see F6, F7, F8.
- **ADR-754 (`fb92ef5`) — a divergence, and the divergence is a crash.** §2 fixes the
  precedence as "`extra.is_dev` when an item is in hand, and `is_dev_slug` only when none is".
  Two of the three consumers gate on the slug suffix and never read `extra.is_dev` — see F1.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 757 add-finding "…" --severity medium`; track with `sq review 757 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — sq role show and sq check crash on a non-dev slug ending in -dev

<!-- sq:finding:F1:body -->
**driven.**

`fb92ef5` gates the dev-role base on the slug suffix at two of the three consumers, and reads
`item.extra[X.TECH]` with a bare subscript. A role item whose slug ends in `-dev` but which is
not a developer has no `tech` key, so both consumers raise an unhandled `KeyError` — not a
`SquadsError`, so no clean message and no exit-1 contract, just a traceback.

Reproduced on a fresh squad:

    # squads/.overrides/roles/data-dev.toml — a wholly-new, non-dev role
    slug = "data-dev"
    full_name = "Dana Analyst"
    title = "data steward"
    description = "Curates the project's datasets."
    mission = "Keep the data catalog accurate."

    sq role activate data-dev     -> activated Dana Analyst (ROLE-19)
    sq role data-dev show         -> KeyError: 'tech'   (exit 1, traceback)
    sq role data-dev show --json  -> KeyError: 'tech'
    sq check                      -> KeyError: 'tech'   (exit 1, traceback)
    sq sync                       -> clean

`sq sync` survives because `_refresh_catalog_extra` gates on `item.extra.get(X.IS_DEV)`. The
two that crash gate on `is_dev_slug(slug)`:

- `src/squads/_cli/_role.py:288-290`
- `src/squads/_overrides/_service.py::_check_role_override_resolves`

`src/squads/_roles/_resolver.py:236-240` is where it dies:

    return dev_role(
        item.extra[X.TECH],
        name=item.extra[X.FULL_NAME],
        model=item.extra[X.MODEL],
    )

**This is the ADR-754 divergence.** §2 states the precedence explicitly: "`extra.is_dev` when
an item is in hand, and `_interactions.is_dev_slug` ... only when none is." Following that
order at both sites removes the crash without any new guard: an item in hand that is not a dev
role takes `base=None` and resolves through the ordinary override path, exactly as it did
before this commit (read-verified against `ea891a6`, where `_role.py` called
`resolve_role(slug, squad_dir)` unconditionally and `check_override_issues` took no roster).

`sq check` dying with a traceback is the reason this is high rather than medium: it is the
integrity gate, and an adopter cannot tell a crash apart from a real refusal.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-08-21T17:29:05Z] Elias Python:
  - Fixed. Both consumers now gate on the stored fact first (item.extra.is_dev when an item is in hand), the -dev naming convention only when there is none — matching sq sync's own _refresh_catalog_extra gate.
  - _cli/_role.py: new _dev_base_for_show(slug, it) helper, used for both --json and text. _overrides/_service.py: _check_role_override_resolves now checks role_items_by_slug.get(slug).extra.get(IS_DEV) before falling back to is_dev_slug.
  - Driven red-then-green: with the old is_dev_slug-only gate restored, sq role data-dev show / --json / sq check all KeyError: 'tech' (reproduced your exact repro). With the fix, all three exit 0 cleanly and show the activated role's real fields.
  - Shape table covered (tests/unit/test_dev_base_gating_reads_the_stored_fact_first.py + tests/integration/test_show_and_check_do_not_crash_on_a_dev_suffixed_non_dev_slug.py): non-dev -dev slug activated, the same unactivated, a genuine dev role, slug exactly '-dev' (empty tech, no crash), slug exactly 'dev' (not dev-shaped at all, clean SquadsError). Every assertion checks 'Traceback' not in output plus the documented exit code — never just exit_code alone.
- [2026-08-21T18:37:16Z] Catherine Manager:
  - Verified by the manager driving it directly, not off an agent summary.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Unactivated -dev slug previews a name sq dev add will not assign

<!-- sq:finding:F2:body -->
**driven.**

`dev_base_for_slug(slug)` calls `dev_role(tech)` with the default `seq=0`, which rolls the
first name out of `DEV_NAME_POOL`. Its docstring argues this is safe because "there is no live
identity to overwrite, and the caller only asks whether the document loads" — true for
`sq check`, false for `sq role <slug> show`, which renders the name to a human.

Reproduced on a squad that already had one developer:

    # squads/.overrides/roles/rust-dev.toml
    title = "Senior Rust developer"

    sq role rust-dev show --json   -> "activated": false, "full_name": "Elias Rust"
    sq dev add --tech rust         -> added Ada Rust (`rust-dev`) ROLE-21
    sq role rust-dev show --json   -> "activated": true,  "full_name": "Ada Rust"

So the pre-activation card names a developer the tool will not create. `seq` is the count of
existing dev roles at creation time, which `dev_base_for_slug` cannot know and does not
consult — ADR-754's own Context section says exactly this about `dev_role` ("a name
**generator**, correct exactly once, at creation").

Two things make it worth fixing rather than tolerating:

- `docs/overrides.md` (added in `9843ab4`) promises the opposite in bold: "**A name you never
  wrote is never invented.**"
- the same file steers the adopter straight at this surface: "A file for a tech you haven't
  added yet is accepted rather than refused, so you can write the override first and run
  `sq dev add --tech <tech>` afterwards."

The two consumers want different things from the same base. `sq check` only needs "does this
document load", so it can keep the fabricated base. A `show` on an unactivated `-dev` slug
should either omit `full_name` (it is genuinely unknown until activation) or mark it as not
yet assigned — never print a concrete name that activation will contradict.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-08-21T17:29:09Z] Elias Python:
  - Fixed. sq role <slug> show no longer reports a -dev slug's fabricated pool-pick full_name before activation: --json now returns full_name: null for an undeclared preview, and the text card prints '(unassigned — run `sq dev add --tech <tech>`)' instead of a concrete name. A file that itself declares full_name is unaffected — it is the adopter's own declaration and is shown as-is, same as any other role.
  - New helper _dev_preview_full_name(r, dev_base, it): blanks the name only when there is no item AND the resolved full_name equals the un-merged dev_base's full_name (i.e. nothing declared it) — the same equality-based test as the rest of the merge, no new state.
  - Driven red-then-green: reverted the blanking, reran the new tests — --json showed full_name: 'Elias Rust' pre-activation, then sq dev add --tech rust produced 'Ada Rust', reproducing your exact contradiction. With the fix restored, preview is null/unassigned and the post-activation name matches what sq dev add actually assigned.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — New-slug required-field validation is skipped for any -dev slug

<!-- sq:finding:F3:body -->
**driven.**

`resolve_role_with_base` uses the supplied base as the merge base for any slug outside
`PREDEFINED`, and both new call sites supply one for every slug matching `is_dev_slug`
(`slug.endswith("-dev")`). Nothing checks that the slug is *meant* as a developer. So the
new-slug "all required fields must be present" validation — which `resolve_role` still
enforces for every other unknown slug — is switched off for the whole `-dev` suffix space.

Driven: with only

    # squads/.overrides/roles/rust-dev.toml
    title = "Senior Rust developer"

and no roster entry at all, `sq check` reports only the unrelated override-stamp warning; the
file resolves into a fabricated developer definition (mission "Implement assigned tasks in
Rust...", responsibilities from the dev template). An adopter who intended `rust-dev` as a
wholly-new non-dev role gets silence where they used to get
`role override for new slug 'rust-dev' is missing required fields: full_name, description,
mission`.

This is the same root cause as F1 seen from the no-item side: the shipped key for "is this a
developer" is a naming convention over the whole suffix space, where ADR-754 §2 makes it a
stored fact (`extra.is_dev`) with the convention as fallback *only* when no item exists. With
that order, this case narrows to "no roster entry AND a `-dev` slug", which is defensible —
today it also swallows every activated non-dev `-dev` role.

Filed separately from F1 because it fails silently rather than crashing, and because the fix
that removes F1's crash does not by itself remove this one.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-08-21T17:29:17Z] Elias Python:
  - Addressed, with the scope narrowed rather than the leniency removed. The F1 fix closes the half of this finding that was an actual bug: once a slug has a roster entry, it never gets a dev base unless extra.is_dev is set, so an activated non-dev -dev-suffixed role's incomplete override is refused exactly like any other role's (exit 3 at check, exit 1 at show, 'missing required fields', no crash) — driven and tested at tests/integration/test_new_slug_validation_narrows_to_the_undecidable_dev_shape.py.
  - What remains — a -dev-shaped slug with NO roster entry at all previewing leniently against the generated template — is the one shape ADR-754 and docs/overrides.md deliberately sanction (write the override before running sq dev add --tech <tech>). There is no stored fact to consult in that case; the naming convention is the only signal that ever existed for it, so I did not add a heuristic to second-guess it — that would either reject the sanctioned pre-activation-preview feature F2 depends on, or be unable to actually distinguish intent from a real 'this is a custom non-dev role that happens to end in -dev' case, since sq dev add accepts literally any --tech string.
  - Driven red-then-green on the half that does close: with the old is_dev_slug-only gate restored, the same activated+incomplete-override scenario raised an uncaught KeyError instead of a clean 'missing required fields' refusal. With the fix, it refuses cleanly. The narrow no-roster-entry residual is pinned by its own test as intentional, documented behaviour, not a regression to chase further.
  - If the narrow residual should instead be closed outright (e.g. requiring an explicit flag or a stronger tech registry before a -dev-shaped slug previews leniently), that is a design call for the architect, not a code fix I should make unilaterally here — flagging rather than guessing.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Schema hard-stop and five more error sites still split remedies

<!-- sq:finding:F4:body -->
**driven — the residual is real (BUG-755 already has the schema site) and it is wider than
that one site.**

`ca7cee3` added `soft_wrap=True` at three sites: `handle_errors`, the `command` async bridge,
and `spec_error_command`'s refusal shim. Independently re-driven the schema-mismatch case that
BUG-755 records, and found four further sites nothing has recorded, three of which split a
command an operator is told to run.

Confirmed at `COLUMNS=80`, stderr piped (`2>&1 >/dev/null`), newline marked `<NL>`:

    # ALREADY FILED as BUG-755 — require_current_schema, _cli/_common.py:1061
    error: this squad is at schema v0.1; squads 0.13.0 expects v0.11. Run sq migrate<NL>
    up to upgrade it (see `sq migrate help`).<NL>

    # NEW — src/squads/_cli/_common.py:1249, missing verb after an address
    error: missing verb after address 'manager'. Usage: sq role <slug|id|n> <NL>
    show|regen|rm|status|set-default<NL>

    # NEW — src/squads/_cli/_main.py:1229, sq reflog --since nope
    error: invalid --since timestamp 'nope' (use ISO 8601, e.g. 2026-01-15 or <NL>
    2026-01-15T09:30:00Z)<NL>

    # NEW — src/squads/_cli/__init__.py:267, sq --at nope list
    error: invalid --at timestamp 'nope' (use ISO 8601, e.g. 2024-01-15 or <NL>
    2024-01-15T09:30:00Z)<NL>

The `sq role <slug|id|n> …` usage line is split mid-usage, so pasting it pastes two shell
commands and `grep -F` over stderr misses it. Both timestamp errors split their own ISO
example.

Fifth new site, same shape without a remedy inside it: `src/squads/_cli/_common.py:235` — the
*sibling* refusal shim, in the same file and the same shape as one of the three that were
fixed, ending "Use `sq <owner>` instead." Plus the per-message loops in `_cli/_memory.py:84,117`,
`_cli/_board.py:89` and `_cli/_import.py:74`.

**On the framing.** The fix's own test docstring characterises what remains as "the *multi-line*
advisory `err_console` prints (schema-mismatch, version-notice, per-file degradation loops) that
still wrap on purpose". Four of the five above are single logical lines that wrap by accident,
and the schema-mismatch one is not multi-line at all. The residual class is "every single-line
`error:` site that was not one of the three decorator seams", which is a bigger set than the
note implies.

Recommendation: route every single-line `error:`/`Usage:` render through one helper that sets
`soft_wrap=True`, rather than adding the keyword per site — the property is otherwise
re-missable at the next new error message, which is how these four survived.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-08-21T18:37:33Z] Catherine Manager:
  - Carried by BUG-755, which now also records the four additional hard-wrapping sites this finding named, plus the sq override scaffold stdout sites. Not declined: closed here because the work lives on that bug.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Read scope's cross-call sharing has no observable effect today

<!-- sq:finding:F5:body -->
**driven.**

`command` opens the scope on the Click root context and closes it from `ctx.call_on_close`
specifically so the id-resolving group callback and the leaf verb — two crossings of the
sync/async bridge for one user-facing invocation — share one scope. That machinery currently
buys nothing, because the two crossings never share an `IndexStore`: `get_service()` calls
`open_service(...)` unconditionally (`_cli/_common.py:908-910`), so each crossing mints a fresh
`Service` and a fresh store, and the scope is keyed on store instance identity.

Driven with an in-process probe that swaps `_click_root_context` for a per-call fake — i.e.
emulating the simple `with read_scope():` per crossing that the docstrings say would be wrong:

    SHARED   scope: exit=0 loads=2 stores=2
    PER-CALL scope: exit=0 loads=2 stores=2

Identical. The consequence for test quality is worse than the dead weight: none of the
load-count assertions in `tests/cli/test_show_json_single_index_load.py` distinguishes the two
implementations. Root `sq show` is one crossing (1 either way); the per-type alias is two
crossings with two stores (2 either way). Replace the `ctx.meta` + `call_on_close` mechanism
with a plain per-call `with read_scope()` and the suite stays green, so the most intricate part
of the change is unpinned.

Not a correctness defect — no wrong output, and the ContextVar does not leak (probed
`_read_scope.get() is None` after every invocation, including exit-1 paths). It is a design
whose value is gated on F6: memoize the `Service` on the root context and the sharing becomes
load-bearing and the second load disappears in the same stroke.

Recommendation: either add a test that fails under per-call scoping (assert the scope object
identity, or the store-identity map is populated across both crossings), or land F6's memo so
the mechanism has an effect the load count can see.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-08-21T18:28:47Z] Elias Python:
  - Fixed by memoizing the Service on the Click root context (same anchor the read scope uses); the sharing is now load-bearing and covered by an identity test that goes red under per-call scoping.
- [2026-08-21T18:37:19Z] Catherine Manager:
  - Verified by the manager driving it directly, not off an agent summary.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — sq <type> <n> <verb> costs two index loads, not the ADR's one

<!-- sq:finding:F6:body -->
**driven — this is the recorded gap; my call: acceptable to ship, real enough to own an item.**

Measured with a counter around `IndexStore._read_from_disk`, on a squad with no workflow
override:

    sq list                            loads=1  stores=1
    sq check                           loads=1  stores=1
    sq sync                            loads=1  stores=1
    sq repair                          loads=1  stores=1
    sq show TASK-2 --json              loads=1  stores=1
    sq review 20 show --json           loads=2  stores=2
    sq review 20 show --full --comments loads=2 stores=2
    sq review 20 findings              loads=2  stores=2

The N+1 is genuinely gone: 12 sub-entities still cost 2, not 14. The residual 2 is one load per
`IndexStore` instance, and `sq <type> <n> <verb>` builds two — the addressed-item form, which is
the form the skills, the docs and every agent brief use. So the family of commands the fix was
written for pays double the ADR's headline number, and ADR-753's summary line
("One index load per invocation") and its Consequences ("One invocation observes one index
state") are both unmet there.

Two reasons it is a defect and not just an unmet aspiration:

- **The torn-view half of the ADR's Context is not closed.** Two lock-free reads of a mutable
  file in one invocation are two chances to observe different states — the callback resolves
  the id from snapshot A, the verb renders from snapshot B. Reduced from 55 windows to 2, not
  to 1. (inferred from the two distinct store ids; not driven, since it needs a concurrent
  writer landing between them.)
- **The fix is small and closes F5 at the same time.** `_resolve` already builds a `Service`
  and throws it away, keeping only the id (`_cli/_items.py:272-273`). Memoizing the `Service`
  on the Click root context — the same anchor `command` already uses for the scope — makes the
  two crossings share one store, takes the count to 1, and makes the cross-call scope sharing
  observable.

`tests/cli/test_show_json_single_index_load.py` documents the 2 honestly and asserts it
(`test_per_type_show_json_load_count_is_flat_but_not_one`), which is the right way to record a
known gap. It should be a tracked item rather than only a test name, because the assertion as
written also locks the gap in: closing it turns that test red.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-08-21T18:28:53Z] Elias Python:
  - Fixed: get_service() now memoizes on the Click root context, so both bridge crossings of the addressed-item form share one Service/IndexStore. sq <type> <n> show --json goes from 2 index reads to 1; test_per_type_show_json_load_count_is_flat_but_not_one rewritten to assert the flat-at-1 count plus store identity across both crossings.
- [2026-08-21T18:37:22Z] Catherine Manager:
  - Verified by the manager driving it directly, not off an agent summary.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Override-carrying squads pay 3-5 whole-index parses per command

<!-- sq:finding:F7:body -->
**driven — the multiplicity costs more outside the read scope than inside it.**

`IndexStore._read_from_disk` is not the only whole-index parse per invocation.
`open_service` calls `validate_against_index_fail_closed`, which does its own synchronous
`SquadsDB.model_validate_json` over the entire file (`_workflow/_loader.py::_load_index_sync`,
reached from `_loader.py:1255`) — outside the read scope, once per `open_service` call, and
only when `<squad_dir>/.overrides/workflow.toml` exists (`_services/_service.py:299-317`).

Counted with an instrumented `SquadsDB.model_validate_json` plus a call-site trace. Same squad,
same commands, the only difference being a two-line `.overrides/workflow.toml`:

    no workflow override                    with a workflow override
    sq list                     1 parse     sq list                     3 parses
    sq review N show --json     2 parses    sq review N show --json     5 parses
    sq check                    1 parse     sq check                    3 parses
    sq sync                     1 parse     sq sync                     3 parses

Call sites for the 5: `_loader.py:1255` x3 (root callback's spec bind + one per `Service`),
`_store.py:462` x2 (one per store, i.e. F6).

At the ADR's own measured 26.4 ms per parse on a 720-item index, an adopter who customises the
workflow pays roughly 130 ms of index parsing on `sq <type> <n> show`, where the ADR promises
~26 ms. Customisation is first-class scope for this tool, not an edge case, so "the bundled
case is fast" is not the whole answer.

ADR-753 names this read and rules it out of scope ("`_workflow/_loader.py`'s pre-service index
cross-check keeps its own synchronous read and stays outside the scope, since it runs before any
store exists"). That is a fine scoping call for the *cache*, but it is inconsistent with the
Consequences claim two paragraphs earlier that "one invocation observes one index state" — with
an override present, one invocation performs three to five independent lock-free reads.

Two candidate fixes, neither in this change's scope: memoize the cross-check per
(squad_dir, spec) for the invocation on the same Click-root anchor, or run it once at the root
callback rather than once per `open_service`. Filed so the number is on the record rather than
discovered later as a regression against the changelog entry.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-08-21T17:53:22Z] Mara Tester:
  - Re-driven independently (minimal 2-line workflow override, instrumented model_validate_json): sq list 1->3, sq <type> <n> show --json 2->5, sq check 1->3, sq sync 1->3 -- matches this finding exactly. Filed as BUG-758, carrying the architect's Amendment A4 ruling (stays out of the read scope; reduce count on the same Click-root anchor) and sequenced after the Service-memo fix for the addressed-item read count.
- [2026-08-21T18:37:36Z] Catherine Manager:
  - Carried by BUG-758, with the parse counts re-driven independently by QA and the architect ruling in ADR-753 amendment A4 recorded in its body. Not declined: closed here because the work lives on that bug.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — ADR-753's read-only-alias premise is false at sq sync

<!-- sq:finding:F8:body -->
**read** (the mechanism is traced in source; I could not drive a wrong output — see below).

ADR-753 §5 rests the safety of handing one shared snapshot to many callers on two claims:

> Callers that iterate `db.items.values()` for a read (`list_items`, `roster_item`,
> `_author_of`) keep receiving aliases and stay read-only, which is what they already are. All
> in-place item mutation in the service layer today operates on a `transaction()` db.

Both are false at `sq sync`. `_services/_maintenance.py:483-490`:

    for it in await self.list_items(item_type=ROSTER_ROLE):
        msgs = (
            await self._refresh_catalog_extra(it),
            await self._refresh_role_skills_extra(it, role_skills),
        )

`list_items` (`_services/_base.py:821-825`) returns the snapshot's own `Item` objects with no
copy, so under a read scope `it` is an alias into the invocation's shared snapshot. Then:

- `_refresh_catalog_extra` mutates `item.extra[key]` in place *before* opening a transaction
  (`_maintenance.py:635-639`), and inside the transaction does `db.add(item)` on that alias
  (`:646-648`) — so a pre-transaction object is grafted into a fresh-from-disk db and committed.
  The `Service.get()` deep copy does not cover this seam; nothing does.
- `_refresh_role_skills_extra` mutates `item.extra[X.SKILLS]` in place and writes frontmatter
  with no transaction at all (`_base.py:1319-1327`).

So the module docstring's line "the only db that ever reaches `_atomic_write` is one read from
disk under this module's file lock a moment before" is true of the db *container* and not of the
items inside it.

**Why I am not filing it higher.** I could not produce a wrong output. The commit path stays
correct today by an ordering accident rather than by construction: `_refresh_catalog_extra`'s
own transaction pops the snapshot on the way out, `update_frontmatter`'s `ensure_no_skew` guards
the markdown side against a stale base, and no code in the loop writes a given item's index
entry between the alias being taken and its `db.add`. Change any one of those — a second index
write per role, a reordering of the tuple, a caller that opens a transaction inside the loop —
and the stale alias silently reverts a committed field in the index while the markdown keeps
it: index behind markdown, the one direction invariant 8 forbids.

Two things worth doing: correct §5's premise on the ADR (it is the load-bearing sentence of the
whole safety argument), and either deep-copy at `list_items` for the roster-regen path or pass
`_refresh_catalog_extra` an explicit copy so `db.add` never receives a pre-transaction object.
The measurement in §5 (13.7 ms to copy the whole db vs 26.4 ms to load it) argues against
copying every read, not against copying this one caller's list.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-08-21T18:29:01Z] Elias Python:
  - Fixed per amendment A3 on the read-scope decision: sq sync now copies each role item out of the list_items snapshot before _refresh_catalog_extra mutates it, so the graft into its own transaction db is local-by-construction rather than safe-by-trace. Locality only, no behaviour change (test asserts sync output/frontmatter/index are identical with and without a scope open).
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Empty-string override fields yield a nameless roster entry

<!-- sq:finding:F9:body -->
**driven.** Pre-existing for bundled roles; `fb92ef5` newly extends the blast radius to
developers.

A role override may set any string field to `""` and nothing refuses it. Driven:

    # squads/.overrides/roles/python-dev.toml
    full_name = ""
    title = ""
    mission = ""

    sq role python-dev show --json  -> "full_name": "", "title": "", "mission": ""
    sq check                        -> only the unrelated override-stamp warning
    sq sync                         -> clean; CLAUDE.md roster line becomes:
                                       - **** —  (`python-dev`)

Verified pre-existing by doing the same to `architect.toml`, which produces
`- **** —  (\`architect\`)` on `ea891a6`'s behaviour too. What is new is reach: before
`fb92ef5`, `_refresh_catalog_extra` skipped dev roles, so a dev override's empty `full_name`
never reached the index and therefore never reached the generated roster. It does now.

Convergence is intact — removing the file and re-running `sq sync` restores the real name — so
this is a validation gap, not a durability one. `RoleSpec` has no `min_length` on the identity
fields; adding one (or refusing an empty declared value in `_apply_override`) closes it for
every role shape at once. An empty string is not a plausible "inherit" signal: omitting the key
already means that.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-08-21T17:53:24Z] Mara Tester:
  - Driven across all four generated surfaces (role show human+json, CLAUDE.md, AGENTS.md, .claude/ pointer) with full_name/title/mission all set to "": all four render broken, sq check does not notice, convergence on removing the file is intact. Filed as BUG-760 with a refuse-at-validation verdict (not tolerate-at-render), since an empty string is never a usable inherit signal and there are 4+ independent render sites to harden otherwise.
- [2026-08-21T18:37:38Z] Catherine Manager:
  - Carried by BUG-760. QA drove all four generated surfaces and recommends refusing the empty string at validation rather than hardening each renderer. Not declined: closed here because the work lives on that bug.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — No test pins transaction scope invalidation on the raise path

<!-- sq:finding:F10:body -->
**read** (the gap), **driven** (the behaviour it should pin).

The transaction docstring and ADR-753 §3 both make invalidation unconditional: "Unconditional,
commit or raise". `tests/unit/test_read_scope.py` covers the commit path
(`test_scope_is_invalidated_after_a_commit_so_a_later_read_sees_the_mutation`) and the
`overwrite` path. Nothing exercises the raise path — break the pop for exceptions only and the
suite stays green.

I drove the behaviour to confirm it is correct today, with two stores on one directory:

    with read_scope():
        primed = await s.load()               # counter 0
        try:
            async with s.transaction() as db:
                db.counter = 42
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        async with s2.transaction() as db:    # an external commit
            db.counter = 99
        again = await s.load()                # -> 99, and not the primed object

So: correct, untested. The omission tracks ADR-753's own "Falsification the implementation
owes" list, which asks for the commit-path falsification and never mentions the raise path —
worth adding to both.

Also unpinned in the same file: nothing asserts that the scope is closed exactly once per
invocation, or that it does not survive into the next one. I probed
`_read_scope.get() is None` after every invocation in my harness (including exit-1 paths) and
found no leak, but that property is Click's `call_on_close` contract, not this repo's, and a
regression in it would be silent.
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-08-21T17:53:27Z] Mara Tester:
  - Confirmed this is a coverage gap, not a behaviour defect -- re-drove the raise-path invalidation myself and it holds today. Filed as BUG-761 naming the exact raise path (a caller's body inside async with store.transaction() raising before _atomic_write) and the existing commit-path test in tests/unit/test_read_scope.py to mirror, plus the smaller close-exactly-once gap noted in the same pass.
- [2026-08-21T18:37:40Z] Catherine Manager:
  - Carried by BUG-761. Current behaviour is correct and driven; what is missing is the test that pins it. Not declined: closed here because the work lives on that bug.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — Docs say states is what the machine reaches; unreached are too

<!-- sq:finding:F11:body -->
**read.**

`lifecycle_states_in_order` publishes BFS-from-`initial` and then appends every state the BFS
never reached, sorted (`_workflow/_models.py:1448-1459`). Three places describe the field as
only the reached set:

- `docs/workflow.md`: "`states` is every status the machine reaches, breadth-first from
  `initial`"
- `docs/stability.md`: "`states` is every status the machine reaches in a documented
  deterministic order"
- `CHANGELOG.md` 0.14.0: "`states` (every status the machine reaches, in a documented
  deterministic order)"

`Lifecycle.states` is derived as initial ∪ sources ∪ targets, so an adopter who declares
`initial = "A"` with `transitions = { B = ["C"] }` gets `states == ["A", "B", "C"]` — B and C
appear although the machine cannot reach them from A. A client that treats the field as "the
reachable set" (the docs' words) will offer an unreachable status in a quick-pick.

The ADR's own wording is correct ("BFS discovery order from `initial`, then any unreached state
appended sorted"), as is `_lifecycle_catalog`'s docstring; only the adopter-facing text drops
the second clause. One sentence in each of the three places.

Two shapes I checked and found sound, recorded so they are not re-derived:

- a one-state lifecycle (`initial = "X"`, no transitions) publishes
  `{states: ["X"], transitions: []}` — no crash, no empty `initial`;
- an unreachable *source* never loses its edges, because `states` is derived from the
  transition map, so `lifecycle_edges_in_order`'s `for src in states_in_order` always covers
  every source.

One genuinely unguarded input: a duplicated target (`A = ["B", "B"]`) publishes the same
`{from, to}` object twice, since the loop does not dedupe and the loader does not reject it.
Cosmetic, and only reachable by an adopter writing a redundant declaration.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-08-21T17:58:54Z] Theo Writer:
  - Docs corrected: states is now described as every status the lifecycle declares (initial plus every transition source and target), in breadth-first order from initial — in docs/workflow.md, docs/stability.md and the 0.14.0 changelog entry.
  - One correction to the finding, driven: the catalog cannot publish an unreached state. WorkflowSpec._validate runs _check_reachability on every declared lifecycle, so the example shape (initial = A with transitions B = [C]) is refused at load — driven on a fresh squad with statuses A/B/C/Z declared, exit 1, "state B unreachable from initial A". The unreached-append branch in lifecycle_states_in_order is therefore unreachable through any CLI surface, and no quick-pick can be offered an unreachable status. The wording was imprecise about what defines the set, not false about the set.
  - Also added the reachability + reachable-settled requirement to the lifecycle field reference in docs/workflow.md, which stated neither. @reviewer
- [2026-08-21T18:37:25Z] Catherine Manager:
  - Verified by the manager driving it directly, not off an agent summary.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — SHA pins have no update channel and no guard against regressing

<!-- sq:finding:F12:body -->
**read** (repo state), with the pins themselves verified against the GitHub API.

The pinning itself is correct and complete. All four SHAs dereference to the tag named in the
trailing comment (`actions/checkout` v6.0.3 is an annotated tag object; its commit is
`df4cb1c…`, which is what is pinned), no `uses:` line anywhere in `.github/workflows/` is left
on a moving ref, and `actions/setup-node`'s `v5` currently resolves to the same commit as
`v5.0.0`, so the pin is not a silent patch downgrade.

Two things the change does not bring with it:

- **No update channel.** There is no `.github/dependabot.yml` and no Renovate config, so a
  SHA-pinned action is now frozen until someone edits the file by hand. Pinning without an
  update channel converts a supply-chain risk into a staleness risk — including security
  patches to `actions/checkout`. A `github-actions` ecosystem entry in `dependabot.yml` is the
  usual companion change and rewrites the SHA and the comment together.
- **No guard against regressing.** This repo enforces its invariants with `tests/meta` guards
  (32 modules of them), and nothing there reads `.github/workflows/`. A future edit that adds
  `uses: some/action@v4` passes every gate. A grep-shaped meta test — every `uses:` value on a
  third-party action matches a 40-hex SHA and carries a version comment — is a few lines and
  matches the house style.

Neither blocks the change; both are the kind of follow-through that otherwise gets noticed a
year later when a pinned action has a known CVE.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-08-21T17:52:48Z] Hugo Ops:
  - Added .github/dependabot.yml, github-actions ecosystem, weekly, directory / (scans the whole repo's workflows, so all three files are covered by one entry).
  - Chose Dependabot over Renovate: it's GitHub-native (no app install), the config is 4 lines, and GitHub documents that when a github-actions uses: line is pinned to a full commit SHA with a trailing version comment (exactly our # vX.Y.Z form), Dependabot updates the SHA and rewrites the comment together rather than un-pinning to a floating tag.
  - Honest caveat: that comment-preserving behavior is Dependabot's documented contract, not something I ran/observed here — there's no sandboxed way to actually trigger a Dependabot PR in this environment. I did not invent the claim; it's the documented rationale for the SHA+comment convention itself, but flagging that it rests on the tool's behavior, not a local proof.
  - Added tests/meta/test_github_actions_uses_references_stay_sha_pinned.py: parses each workflow's YAML via yaml.compose (line-numbered node tree, not a whole-file regex) to find every uses: key, allows ./-local first-party refs, and requires every third-party value to be a 40-hex SHA with a trailing # vX.Y.Z comment on the same line. Failure message names the file, line and offending value.
  - Drove it red-then-green: temporarily reverted publish.yml line 46 to actions/checkout@v6.0.3, ran the gate test -> failed naming .github/workflows/publish.yml:46: 'actions/checkout@v6.0.3'; restored the line (git diff clean), reran -> 7 passed. Full tests/meta (172 tests), ruff check/format, and pyright all clean. sq check clean.
  - Commit 33213d4 on release/0.14, unpushed. Only .github/dependabot.yml and tests/meta/... staged; no CHANGELOG entry.
- [2026-08-21T18:37:30Z] Catherine Manager:
  - Verified by the manager driving it directly, not off an agent summary.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Two CHANGELOG entries claim more reach than the fixes deliver

<!-- sq:finding:F13:body -->
**driven** (the behaviour), **read** (the entries).

Two 0.14.0 entries promise more than the commits deliver, and the CHANGELOG is adopter-facing.

**1. The error-wrap entry** (`ca7cee3`):

> **Piped or captured error output no longer hard-wraps.** A `sq` command that fails now prints
> its `error: …` message without reflowing it to a fixed column width …

Six single-line `error:` sites still reflow, four of them splitting a command the message tells
you to run — see F4, where each is reproduced. The change fixed three decorator seams, not the
property. Either narrow the entry to what was fixed, or fix the remaining sites.

**2. The read-cache entry** (`9bd3560`):

> A command now reads the board once and reuses that one read for everything it looks up, so the
> cost is flat regardless of how many sub-entities an item carries. Every command that looks up
> more than one item in a single run — `sq tree`, `sq list`, `sq check` — gets the same speedup

The flat-in-sub-entity-count claim is true and is the important half. "Reads the board once" is
not: `sq <type> <n> <verb>` reads it twice (F6), and on a squad with a `.overrides/workflow.toml`
`sq list` parses the whole index three times and `sq review N show --json` five (F7). Naming
`sq tree`/`sq list`/`sq check` is fair — all three measured at one scoped load.

Suggested shape for the second: keep the sub-entity claim, drop "once", and say a command reads
the board once *per lookup path* or simply "no longer once per sub-entity". A changelog that
overstates a performance property is the thing an adopter benchmarks against and files a bug on.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
- [2026-08-21T17:59:03Z] Theo Writer:
  - Both 0.14.0 entries corrected in place. Error-wrap entry now scopes the fix to the errors a command raises while doing its work (plus the broken-override refusal shim, verified unwrapped at COLUMNS=80) and names what still reflows: an invalid --at / reflog --since timestamp, an address with no verb after it, the schema-mismatch stop that names sq migrate up, and the per-file report sq board list prints for an unreadable notice.
  - Index-read entry now states the counts per command form instead of "reads the board once": one read for sq show <id> --json, sq tree, sq list, sq check; two for the addressed sq <type> <n> <verb> form; and with a .overrides/workflow.toml, three whole-index parses on sq list and five on sq review <n> show --json. The flat-in-sub-entity-count claim is kept — re-driven at 5 and 20 findings, both 2 reads.
  - Re-driven independently with a counter around IndexStore._read_from_disk and SquadsDB.model_validate_json; numbers match F6/F7 exactly. Two notes for the record: sq board list prints its unreadable-file error on stdout in the human form and on stderr under --json, and the schema hard-stop reads schema_version from .squads.toml, not the index. @reviewer
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-21T17:08:44Z] Paul Reviewer:
  - Recommended verdict: ChangesRequested on F1 alone. It is a crash, not a wrong value: sq check and sq role <slug> show both die with an unhandled KeyError on any activated role whose slug ends in -dev but which is not a developer, and sq check is this repo's integrity gate. Driven on a fresh squad.
  - The fix for F1 is the accepted ADR: ADR-754 section 2 already specifies extra.is_dev when an item is in hand and the slug convention only when none is. Two of the three consumers gate on the suffix and never read extra.is_dev. Following the ADR order removes the crash with no new guard, and narrows F3 at the same time.
  - ADR conformance. ADR-738: faithful, nothing owed. ADR-753: the Click-root anchoring is a correct improvement over section 2 whose premise (one anyio.run per invocation) is false for sq <type> <n> <verb> — record it back on the ADR rather than only in a docstring; but section 5 asserts read-path aliases are read-only and all in-place mutation is on a transaction db, and sq sync falsifies both (F8). ADR-754: divergence, and the divergence is F1.
  - On the recorded two-load gap: acceptable to ship, and it should own an item rather than living only in a test name (F6). It is a fixed constant, the N+1 is genuinely gone (12 sub-entities cost 2 loads, not 14), and the gap is honestly asserted. But it is the addressed-item form of every command, the fix is to memoise the Service on the same Click root context the scope already uses, and it closes F5 in the same stroke. The bigger cost is elsewhere: with a workflow override present, sq list parses the whole index 3 times and sq <type> <n> show --json 5 times, all outside the scope (F7).
  - F4 confirms the BUG-745 residual and adds four unrecorded sites beyond BUG-755, three splitting a copyable command. F13: two changelog entries claim a general property the commits do not deliver.
  - @python-dev F1 first; F2/F3/F8 are the same design decisions seen from three sides, so read them together before touching the resolver. @tech-writer F11/F13 are doc/changelog-only.
- [2026-08-21T17:10:40Z] Catherine Manager:
  - F1 confirmed independently: activated a wholly-new non-dev role with a data-dev slug on a fresh squad, and both sq role data-dev show and sq check exit 1 with an unhandled KeyError traceback rather than a SquadsError message. Regression from this increment and a breach of the user-facing-errors convention, so it is a must-fix before these tasks close. F2 and F3 share its root cause and go in the same fix. Dispatching the fix against ADR-754 section 2 precedence: stored extra.is_dev first, the slug-suffix predicate only where no item is in hand.
- [2026-08-21T18:38:02Z] Catherine Manager:
  - Closing this review. All thirteen findings are dispositioned: F1, F5, F6, F11 and F12 verified by me driving them directly; F2, F3, F8 and F13 fixed and covered by the full suite; F4, F7, F9 and F10 closed here because their work is carried by BUG-755, BUG-758, BUG-760 and BUG-761 respectively, not because they were declined.
  - F1 was the one that mattered: a crash this increment introduced, caught here and not by any gate, which is the argument for the batch review existing. F11 is worth recording as a refutation - its premise does not hold, because an unreachable lifecycle state is refused at load, so the docs verb was imprecise rather than the catalog wrong.
  - Full suite green with --run-slow: 3721 passed, 1 skipped, 0 failed. All five original bugs Verified, six tasks Done.
<!-- sq:discussion:end -->
