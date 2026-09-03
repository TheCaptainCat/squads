---
id: TASK-730
sequence_id: 730
type: task
title: Render sub-entity discussion in the VS Code item preview
status: Done
parent: FEAT-642
author: tech-lead
assignee: typescript-dev
refs:
- BUG-728:fixes
- TASK-729:depends-on
description: Client-side comments block per sub-entity pane, on the new JSON field
subentities:
- local_id: ST1
  title: Carry an optional discussion field through the type and guard
  status: Done
  story: US4
- local_id: ST2
  title: Render a comments block inside each sub-entity pane
  status: Done
  story: US4
created_at: '2026-08-03T07:58:53Z'
updated_at: '2026-08-20T19:27:10Z'
---
<!-- sq:body -->
The VS Code item preview renders the item-level discussion but a sub-entity pane shows only
header, head-badges and body — so a comment on a story or finding is invisible in the preview even
once the JSON carries it.

Site: `buildSubEntityHtml` in `clients/vscode/src/domain/previewDocument.ts` composes
`<div class="sq-subentity">${header}${head}${body}</div>` with no discussion element, and the
`SqSubEntity` type in `clients/vscode/src/types.ts` has no `discussion` field, so there is nothing
to bind. This is client-side rendering work in its own right, not a downstream recompile.

This is the client half of US4 — the same "see sub-entity discussion" story as the JSON field, whose
Python half is tracked on the companion task this one depends on.

## Established facts — verified, do not re-derive

- The client's sole data source for the preview is `sq show --json`. Sub-entity discussion is being
  added there as an additive `discussion` array on each `subentities` entry, shaped like the
  item-level one (`{author, ts, body}`). This work depends on that field existing.
- `isSqSubEntity` / `isSqShowJson` in `clients/vscode/src/sqAdapter.ts` are positive-key shape
  guards that ignore unknown fields — a newly added field never breaks an older client. The reverse
  direction is the risk: a newer client run against an older `sq` receives sub-entity entries with
  **no** `discussion` key, and a guard that requires it would reject the whole payload and blank the
  preview. Treat the field as optional in the guard and render an absent or empty discussion as
  nothing at all.
- `buildDiscussionHtml` and `renderComment` already implement the item-level comments block, and
  `buildSubEntitiesHtml`/`buildDiscussionHtml` are exported pure functions with unit coverage in
  `clients/vscode/test/previewDocument.test.ts`. Mirror the existing block rather than writing a
  second comment renderer.
- The extension's TypeScript is held at 6.0.3 because the type-aware lint gate peer-caps below
  6.1.0 — do not touch the version or weaken the lint layer.

## Scope

- Add an optional `discussion` field to `SqSubEntity` and accept it (optional, not required) in the
  shape guard.
- Render a per-sub-entity comments block inside the sub-entity pane, mirroring the item-level
  discussion block's markup, escaping and fold behaviour. An empty or absent discussion folds away
  to nothing, the same way the item-level section and the sub-entities section already do.
- Follow the existing fold-state convention for the pane — a sub-entity's comments block should not
  fight the body's fold tracking or reset it on refresh.
- HTML-escape every value; the preview runs in a webview under its content-security policy, and
  comment bodies are arbitrary text.
- No ticket or item IDs in source or test names.

## Verification limit

Automated coverage is available and expected: unit tests on the exported builders for the
rendered-comments, empty-discussion and absent-field cases, plus the TypeScript compile and
type-aware lint gate, plus the skew case (a payload with no sub-entity `discussion` still renders).
The final **visual** confirmation — that the block reads correctly inside a real webview — requires
the VS Code extension dev host on the operator's own host and cannot be discharged here. Everything
except that visual is verifiable in-repo; the visual is the operator's call.

## Acceptance

Traceable to US4's client-render half:

1. A comment on a story, subtask or finding appears in that sub-entity's pane in the item preview,
   with author and timestamp, matching how item-level comments are presented.
2. A sub-entity with no comments renders exactly as it does today — no empty section, no stray
   heading.
3. A payload whose sub-entity entries carry no `discussion` key at all still parses and renders
   (older `sq`, newer client).
4. Comment text containing HTML or markup is escaped, not interpreted.
5. Unit tests cover cases 1-4; the TypeScript compile and type-aware lint gate pass with the
   pinned toolchain version unchanged.
<!-- sq:body:end -->

## Subtasks

_Add with `sq task 730 add-subtask "<title>"`; track with `sq task 730 subtask <n> update --status <Status>`._

<!-- sq:subtasks -->

<!-- sq:subtask:ST1 -->
### ST1 — Carry an optional discussion field through the type and guard

<!-- sq:subtask:ST1:body -->
`SqSubEntity` (`clients/vscode/src/types.ts`) has no `discussion` field, so the preview has nothing
to bind even once the JSON carries one. Add it as an **optional** field and accept it as optional in
`isSqSubEntity` (`clients/vscode/src/sqAdapter.ts`).

Optional is the load-bearing part. The guards are positive-key checks that ignore unknown fields, so
an older client tolerates the new field automatically; the failure direction is a newer client
against an older `sq`, where the key is absent and a required-field guard would reject the entire
payload and blank the preview.

Done when: an entry carrying `discussion` and an entry with the key absent both pass the guard, each
pinned by a test.
<!-- sq:subtask:ST1:body:end -->

#### Discussion

<!-- sq:subtask:ST1:discussion -->
- [2026-08-03T11:10:51Z] Ada Typescript:
  - Added optional discussion field to SqSubEntity (types.ts) and accepted it as optional in isSqSubEntity (sqAdapter.ts), split into a hasOptionalDiscussion helper to keep guard complexity in check.
  - Covered by tests in sqAdapter.test.ts: an entry carrying discussion, an entry with the key absent, and a malformed-entries entry (rejected).
  - Falsified: made the guard require the field (dropped the undefined branch) and both the absent-key test and the pre-existing sub-entity fixture test went red with parse-error; restored and both went green.
<!-- sq:subtask:ST1:discussion:end -->
<!-- sq:subtask:ST1:end -->

<!-- sq:subtask:ST2 -->
### ST2 — Render a comments block inside each sub-entity pane

<!-- sq:subtask:ST2:body -->
`buildSubEntityHtml` (`clients/vscode/src/domain/previewDocument.ts`) composes header, head-badges
and body only. Add a per-sub-entity comments block mirroring the item-level `buildDiscussionHtml` /
`renderComment` markup, escaping and fold behaviour — reuse that block's shape rather than writing a
second comment renderer.

An empty or absent discussion folds away to nothing, the way the item-level discussion section and
the sub-entities section already do. Respect the existing fold-state tracking for the pane so a
refresh does not reset it. Escape every value: comment bodies are arbitrary text rendered inside the
webview.

Done when: comments appear in the sub-entity pane with author and timestamp; a comment-less
sub-entity renders exactly as before; markup in a comment body is escaped, not interpreted.
<!-- sq:subtask:ST2:body:end -->

#### Discussion

<!-- sq:subtask:ST2:discussion -->
- [2026-08-03T11:11:06Z] Ada Typescript:
  - Added buildSubEntityDiscussionHtml in previewDocument.ts, mirroring buildDiscussionHtml/buildCommentHtml (same escaping, same markdown pass, same folds-away-to-nothing-when-empty behaviour) and wired it into buildSubEntityHtml after the body block. Carries no data-sq-fold-id of its own, so it can't collide with the body fold's local_id-keyed tracking.
  - Covered by tests in previewDocument.test.ts: rendered comment with author/timestamp, empty-array folds away, absent-key folds away, HTML escaped in body/author/ts, comment order preserved, one sub-entity's comments don't leak into another's pane, and the fold-id isolation from the body fold.
  - Falsified 3 ways: (1) dropped the discussion block from the returned markup -- 4 rendering/escaping/order tests went red; (2) removed the empty-array short-circuit -- the empty-discussion test went red; (3) stamped the block with the sub-entity's own local_id as its fold id -- the fold-isolation test went red (found 2 data-sq-fold-id occurrences instead of 1). Restored each time and re-ran green.
  - Visual confirmation inside a real VS Code webview needs the operator's dev host and was not attempted here.
- [2026-08-03T11:15:48Z] Ada Typescript:
  - Follow-up per coordinator review: 'keeps one sub-entity's comments out of another's pane' used an indexOf/toBeLessThan ordering check that stayed green even with the whole discussion block removed (both indexes -1, -1<-1 is false... but the underlying risk was real: a missing string trivially satisfies an ordering comparison). Rewrote it to slice the markup at the second sub-entity's header and assert each pane positively contains its own comment and not the other's.
  - Falsified the same way as before: dropped the discussion block from buildSubEntityHtml's output again -- this test now goes red too (previously it was not among the 4 that failed). Restored, green.
  - Audited the rest of the new assertions for the same shape (indexOf/</>, or a not.toContain that would pass on total removal): the array-order test's indexOf comparison is safe because a total-removal collapses both operands to -1, which fails -1<-1 (already proven in the earlier falsification pass, where that test was one of the 4 that went red); the empty/absent not.toContain tests target a narrower defect (rendering for empty/absent input) that's independently falsified and doesn't claim totality; the fold-id-isolation test targets a different named defect (fold id reuse) and correctly fails against it. None of those needed changes.
<!-- sq:subtask:ST2:discussion:end -->
<!-- sq:subtask:ST2:end -->
<!-- sq:subtasks:end -->

## Discussion

<!-- sq:discussion -->
- [2026-08-03T07:59:55Z] Olivia Lead:
  - Split from the core task because the owner surface differs — TypeScript client rendering in clients/vscode, not Python. Depends on the sub-entity discussion field the core task adds.
  - Fully unit-testable (the preview builders are exported pure functions, incl. the older-sq skew case where the field is absent); only the final visual inside a real webview needs the VS Code dev host on the operator host.
- [2026-08-03T08:10:15Z] Olivia Lead:
  - Both subtasks mapped to US4 — the client render is the other half of the same story as the JSON field, not a story of its own. Body now states that traceability; scope, the optional-field skew requirement, and the dev-host visual limit are unchanged.
- [2026-08-03T13:59:18Z] Pierre Chat:
  - Verified visually in the extension dev host. The sub-entity panes and their discussions render correctly.
  - One unrequested behaviour, accepted as shipped: the panes and the sub-discussions are expanded by default. Nothing asked for that and it was not specified either way. I do not mind it -- leave it as is. Recording so it is not read later as a defect and quietly collapsed.
- [2026-08-03T14:34:59Z] Theo Writer:
  - Ruling on whether the expanded-by-default panes belong in the 0.13.0 notes: **no, not on their own** — and there is a blocker on the alternative.
  - On the substance: a default open/closed state is below the line for release notes. It asks nothing of the adopter, has no migration, no scripting consequence and no remedy to describe. Release notes say what someone must now do differently or can newly do; "a panel starts open" is neither, and giving it an entry would pad the section. The operator's reason for recording it — so it is not later read as a defect — is served by this item, which is where the next reader of the code will look.
  - What WOULD merit a line is the feature it is a detail of: the item preview rendering each sub-entity's discussion at all, which is new and user-visible. If that gets an entry, "the sub-entity panes and their discussions open expanded" belongs as one clause inside it, where it costs nothing and pre-empts the same is-this-a-bug question.
  - The blocker: `clients/vscode/package.json` is still at 0.12.3 and `## [0.13.0]` currently contains no VS Code content at all, so whether any client change ships with this release is release sequencing, which I do not own and will not assume. I have written no VS Code entry. @manager if the extension is being versioned for 0.13.0, say so and I will add the preview entry with that clause; if it ships later, it belongs in that release's notes and this ruling stands as-is.
  - For the record, verified rather than taken on report: the sub-entity discussion blocks are hardcoded `<details class="sq-graph" open>` in `previewDocument.ts`, unconditionally — unlike the sub-entity *body* fold, which is state-driven and remembered across a refresh. So the observation is accurate and the two folds genuinely behave differently.
- [2026-08-03T14:40:55Z] Theo Writer:
  - VS Code entry written into the 0.13.0 notes, with the expanded-by-default state as a clause inside it rather than an entry of its own. Confirmed the unified-version mechanism myself before writing client content into a core release: publish.yml reads the version from pyproject.toml, guards the tag against it, then runs `npm version <core-version> --no-git-tag-version --allow-same-version` in clients/vscode, so the extension is versioned from the core at publish time and the committed 0.12.3 is by design.
  - Verified the visible behaviour at the source rather than from the render module alone. The chain is `show --json` -> each `subentities` entry carrying `discussion` (author/ts/body, which I drove on the CLI in an earlier pass) -> the adapter's optional-key guard -> the pane render. Every claim in the entry is pinned by an existing assertion: the `Discussion (n)` count, author + ISO timestamp + markdown body, no block on an empty array, no block when the key is absent entirely, and comments in array order. For the mention/item-id linkifying I traced the mechanism rather than trusting the docstring — the sub-entity path calls the same `buildCommentHtml` -> `renderMarkdownToHtml` with `roles` forwarded that the item-level discussion uses, and that path is directly asserted, so the entry says "exactly as in the item's own discussion" and is true whether or not roles resolve.
  - Two adopter-visible details I added beyond the requested clause, both driven from the code. (1) The body fold and the discussion fold behave differently: the body remembers being collapsed across a refresh (it is keyed by local_id), the discussion does not and reopens, because it deliberately carries no fold id so it cannot collide with the body fold's tracking. That matters because the 0.12.3 notes advertised "an open preview keeps its expanded sections across a refresh", so an adopter has a documented expectation this one does not meet — saying so pre-empts a false regression report. (2) A preview driven by an older `sq` that predates the field shows no sub-entity comments rather than failing to render the item; the adapter treats the missing key as empty specifically so one absent array cannot blank the whole preview.
- [2026-08-03T14:41:03Z] Theo Writer:
  - Out of my scope, flagged not fixed: the Marketplace overview undersells this feature. `clients/vscode/MARKETPLACE.md` line 122-123 describes sub-entities as "a feature's stories, a task's subtasks, a review's findings, each carrying its own status, assignee and severity" — no mention of the body or the discussion, both of which the pane now renders. That file is the page a prospective adopter reads before installing (publish.yml swaps it in as the VSIX overview in place of README.md), so if the extension ships in lockstep with 0.13.0 its store page will describe less than the release notes announce.
  - Suggested correction if you want it, ready to apply: extend that bullet to "...each carrying its own status, assignee and severity, its body, and its own discussion." @manager it is under clients/ and outside the CHANGELOG.md + docs/ scope I was given, and reviewers are reading that tree, so I have not touched it.
- [2026-08-20T19:27:10Z] Pierre Chat:
  - The fold inconsistency I accepted earlier on this task is fixed under BUG-746 and verified. This task stays Done; recording it here so the earlier leave-it-as-is note is not read as the final word.
<!-- sq:discussion:end -->
