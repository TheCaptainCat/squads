---
id: REV-523
sequence_id: 523
type: review
title: 'sq ui browse-first increment: lazy TUI, read-only Service, error bridge'
status: Approved
parent: EPIC-28
author: reviewer
refs:
- FEAT-513
- FEAT-514
- ADR-516
subentities:
- local_id: F1
  title: Missing-extra guard is too broad — masks nested import errors
  status: Fixed
  severity: medium
- local_id: F2
  title: tui extra floor pin is unverified and too low for the APIs used
  status: Fixed
  severity: medium
- local_id: F3
  title: Glance line hardcodes the priority axis, not spec-generic
  status: Open
  severity: low
created_at: '2026-07-21T11:46:06Z'
updated_at: '2026-07-21T12:05:04Z'
---
<!-- sq:body -->
## Scope

Independent review of the browse-first `sq ui` increment (the diff from the
planning commit to HEAD across `src/`, `tests/`, `pyproject.toml`, and the CI
workflow). Reviewed against the accepted architecture decision (ADR) pinning the
Textual stack, the optional `tui` extra, the in-process read-only `Service`
layer, and the module placement, plus the two browse-first feature acceptances
(shell + tree navigation; reader panel with body / sub-entities / discussion
tabs).

## What holds up

- **Lazy import / lean core.** Nothing on the CLI-import path pulls Textual; the
  `_tui` package and `textual` are imported only inside the `ui` command body.
  A subprocess test with `textual` forced unimportable confirms `sq --help`
  still exits 0. The extra is declared under optional-dependencies, CI switched
  to sync all extras so the layer actually runs.
- **Read-only, in-process.** The app and reader call only read/query surfaces
  (`tree_view`, `get`, `read_body`, `read_discussion`) plus discussion/badge
  formatting helpers — no mutating service calls. No shelling out to `--json`.
- **Sync command, no nested loop.** `ui` is a plain sync Typer command decorated
  with the sync error bridge (not the `anyio.run` async bridge), so Textual's
  own loop runs unobstructed; async `Service` methods are awaited from Textual's
  loop inside the app.
- **Layering / acyclicity.** `_tui` imports strictly downward
  (`_services` / `_models` / `_rendering` / discussion / badges); nothing below
  imports it. Graph stays acyclic.
- **Reuse over duplication.** Tree parity comes from `tree_view()`; sub-entity
  columns/rows and comment splitting reuse the shared discussion helpers; the
  status/priority badges resolve through the workflow spec, not hardcoded
  strings. Dynamic content is escaped before hitting Rich markup.
- **The shared error-bridge change is correct and beneficial.** Escaping every
  `SquadsError` message before printing does not double-escape any legitimate
  markup: no `SquadsError` in the tree carries intended Rich markup — the
  `[red]error:[/red]` prefix lives outside the escaped span. It actively fixes
  latent cases where bracketed literals in error text (e.g. an indexed context
  like `ref_rule[0]` in the workflow loader, or a bracketed catalog tag in the
  role loader, and the new install hint's own `squads[tui]`) were being eaten by
  Rich as pseudo-markup. Full suite stays green.
- **Tests exercise the acceptance.** Launch/quit leaves no running app; tree
  matches `tree_view` structure; sibling / into-child / back-to-parent nav;
  selection populates and reselection refreshes the reader; markdown body
  renders as blocks with a blank-body empty state; sub-entities table + empty
  states (including a type with no sub-entity kind); ordered discussion with
  author + empty state; keyboard tab switching; at-a-glance header with graceful
  unassigned; clean error outside a squad; clean missing-extra message with no
  traceback. The new layer is documented in the conventions doc and registered
  in the meta ticket-ID scanner. No stray ticket IDs in the new source.

## Overall

Functionally sound and well-tested for the shipped environment; nothing here is
a defect in this repo's own run (all gates green). The findings are two
deviations from the binding architecture decision that bite *adopters* /
future maintainers, plus one spec-genericity nit. They are cheap to address and
worth resolving before this rides a release.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 523 add-finding "…" --severity medium`; track with `sq review 523 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Fixed |  | Missing-extra guard is too broad — masks nested import errors |
| F2 | 🟡 medium | Fixed |  | tui extra floor pin is unverified and too low for the APIs used |
| F3 | 🟢 low | Open |  | Glance line hardcodes the priority axis, not spec-generic |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Missing-extra guard is too broad — masks nested import errors

<!-- sq:finding:F1:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Concerns: FEAT-513 / ADR-516 (§2, "clean failure when the extra is missing").

The `ui` command wraps the import of the whole app module in
`except ModuleNotFoundError`, and that import transitively pulls the entire
`_tui` package plus several first-party modules (services, discussion, badges,
workflow, models). The ADR prescribed a *narrow* guard around `import textual`
specifically.

Consequence: any `ModuleNotFoundError` raised *inside* that transitive chain —
a mistyped first-party import introduced by a future refactor, or a genuinely
broken/partial Textual install whose missing sub-dependency surfaces as
`ModuleNotFoundError` — is silently rewritten to "install the tui extra" and
exits 1 with no traceback. The real cause is masked, turning a normal
stack-trace debugging session into a wild-goose chase toward an extra that is
in fact already installed.

Fix (cheap, matches the ADR): guard only `import textual` and let the app
import happen *outside* the guard, or gate on the exception actually being
about textual (e.g. its `name`/module). Note the existing missing-extra test
monkeypatches `__import__` to fail for `textual`/`textual.*` only, so it does
not exercise — and would not catch — the nested-failure misreport.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-21T12:00:44Z] Elias Python:
  - Narrowed the guard to a bare 'import textual' only; _tui._app now imports outside the try, so a nested first-party ModuleNotFoundError propagates with its real message instead of being rewritten to the install hint.
  - Added a test that fakes a first-party import failure inside _tui._app's chain and asserts it is NOT masked (real exception/message surfaces).
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — tui extra floor pin is unverified and too low for the APIs used

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟡 Medium
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
Concerns: ADR-516 (§1, "floor set against the widgets actually used") / FEAT-514.

The optional extra pins `textual>=0.16.0`. The code relies on APIs well newer
than that floor — notably `await <markdown>.update(...)` (the Markdown widget's
update returning an awaitable is a much later addition; awaiting it against an
old Textual would raise at runtime), the tabbed-content / tab-pane widgets, the
`.content` accessor on static widgets, and the parametrized tree / node-message
generics.

The whole suite runs against a current Textual (8.x), so a too-low floor is
invisible to CI. An adopter whose resolver lands on an old-but-satisfying
Textual (>= 0.16, pre-awaitable-update) would get exactly the runtime traceback
from `sq ui` that the clean-failure design set out to avoid — just displaced
from "extra missing" to "extra too old". The ADR explicitly delegated setting
the floor "against the widgets actually used"; 0.16.0 reads as a placeholder,
not a verified floor.

Fix: bump the floor to the earliest Textual release that actually provides the
awaitable Markdown update plus the tabbed-content / static-content surfaces in
use, verified against Textual's changelog.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-21T12:00:50Z] Elias Python:
  - Verified against Textual's CHANGELOG: our code awaits Markdown.update(...), which only became awaitable at 0.29.0 ('Make Markdown.update optionally awaitable') -- newer than Tree (0.6.0), Markdown's existence (0.11.0), TabbedContent (0.16.0), and VerticalScroll (0.20.0). Bumped the floor from 0.16.0 to 0.29.0.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Glance line hardcodes the priority axis, not spec-generic

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
Concerns: FEAT-514 (status/priority/assignee at a glance).

The reader's at-a-glance header resolves exactly one badge axis by the literal
code "priority". Status resolves generically via the spec, and reading the
value through the field code (rather than a label) means a *relabeled* priority
still shows. But a project that renames the field's code, drops the priority
field, or adds its own ordered badge axis (all supported by the generalized
badge-collections model) gets nothing extra surfaced at a glance.

This is correct for the bundled workflow and matches the feature's literal
wording, so it is a nit, not a blocker. The fully spec-generic form — iterate
the type's badge fields from the spec (as list-filtering already does) and
render each present one — would keep the at-a-glance line honest for custom
workflows and remove the last hardcoded axis. Reasonable to defer, but worth
recording so it is a deliberate choice rather than an oversight.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-21T11:51:00Z] Catherine Manager:
  - F3 (glance line resolves only the priority axis, not the type's full spec badge-field set) is deferred — not in this fix round. Rationale: matches FEAT-514's wording, works for the bundled workflow, and is a cheap follow-up if an adopter re-codes/drops priority. Fixing F1 + F2 (+ BUG-522 scroll, BUG-524 test gap) in this round.
- [2026-07-21T12:05:02Z] Catherine Manager:
  - Approving: F1 (guard narrowed to a bare textual import; nested first-party ModuleNotFoundError now propagates) and F2 (floor bumped to textual>=0.29.0, pinned to awaitable Markdown.update) are Fixed and verified; F3 deferred with rationale above. Also fixed alongside: BUG-522 (reader tabs now scroll) and BUG-524 (status now asserted). Full suite green.
<!-- sq:discussion:end -->
