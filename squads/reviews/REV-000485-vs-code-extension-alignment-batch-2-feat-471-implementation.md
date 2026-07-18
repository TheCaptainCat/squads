---
id: REV-485
sequence_id: 485
type: review
title: 'VS Code extension alignment batch 2 (FEAT-471): implementation review'
status: Approved
author: reviewer
refs:
- FEAT-471:addresses
- REV-448:addresses
subentities:
- local_id: F1
  title: 'Stale comment: collections vocab now IS surfaced (preview head)'
  status: Verified
  severity: low
- local_id: F2
  title: F17 watcher glue has no unit test (only resolveSquadDir is covered)
  status: WontFix
  severity: low
- local_id: F3
  title: 'MarkdownString tooltip: assignee not markdown-escaped'
  status: Verified
  severity: low
created_at: '2026-07-18T21:29:21Z'
updated_at: '2026-07-18T21:37:45Z'
---
<!-- sq:body -->
Independent implementation review of FEAT-471 (REV-448 findings F15–F26), across TASK-475..484 —
the whole working-tree diff vs HEAD (core Python + the `clients/vscode` TypeScript client),
against the ACCEPTED contract in ADR-474 (Part A generic collections, Part B status roles).
Reviewed the actual code, not the dev summaries.

## Verdict: approve-worthy — no must-fix items

Every one of F15–F26 is implemented and meets its "Desired" spec, and the core JSON surfaces
match ADR-474 byte-for-byte. Only three low-severity polish items below; none block.

## What was verified clean

- **Correctness (core JSON shapes)** — verified against goldens AND live CLI: the per-item
  `badges` map (field-code keyed, non-null only) on `tree`/`list`/`show` + each `subentities`
  entry; `sq workflow collections --json` (`{collection,label,ordered,default,badges[{code,label,emoji}]}`);
  `sq workflow statuses --json` (`{status,terminal,role,badge}`); the type catalog's added
  `fields[{code,label,collection}]`. All shapes exact.
- **Additive superset** — existing `priority`/`severity`/`extra` and the legacy `priority` key
  are untouched; `badges` is layered alongside (golden diffs are pure additions; a dedicated
  test proves the bundled keys survive and a custom collection rides the same map). `role="active"`
  added only to `InProgress`/`Active` — no existing consumer changes. No schema bump/migration.
- **Spec-driven client (the F20 anti-pattern is avoided)** — badges render by joining
  field→collection→vocabulary through the two catalogs (`badgeCatalog.ts`), no hardcoded emoji
  or collection literal; active-green keys on `role == "active"` via the statuses-catalog join
  (`statusRole.ts`), never a literal status name. Every catalog fetch degrades gracefully to a
  documented fallback. The only hardcoded literals are the 3 reserved meta-type icons and the
  `"active"` role string — both contractually fixed and explicitly endorsed (F22 / ADR B2).
- **ADR-427 consumer-only** — the F17 watcher treats `.squads.json` as a change *trigger* only
  (`squadWatcher.ts` never parses it for data); squad-dir resolution mirrors core `_paths.py`
  walk-up + `.squads.toml` `squad_dir` key, and no-ops for remote/unresolved workspaces.
- **Conventions** — no real sq item IDs in src/tests; new test files named by behavior; new Rich
  tables escape via `e()`; preview fragments escape via `escapeHtml`; no status prose in bodies;
  no markers touched; no `datetime.now()`.
- **DRY** — `resolve_badges` correctly hoisted to `_badges.py` and reused by `_refs.py` and the
  three item surfaces; the frozen field-set + golden + drift-test treatment is applied to both
  new catalogs, matching the ADR-459 pattern the ADR mandates.
- **Gates** — pyright 0/0, ruff clean, full Python suite green; client typecheck + eslint clean,
  250 vitest + 14 skew-canary green; `sq check` clean.

## Acceptance coverage (F15–F26): all met

F15 sub-entities in preview · F16 webview tab icon (light/dark pair) · F17 `.squads.json` watch
· F18 roster drops assignee · F19 hover collection badges · F20 generic collections surface ·
F21 `squads.typeIcons` override · F22 meta-type icons · F23 graphs collapsed + repositioned ·
F24 label wrapping · F25 clickable graph nodes · F26 active-green. F15/F23/F24/F25 carry explicit
previewDocument tests; F19/F20/F26 carry badgeCatalog/statusRole/treeMapping + core JSON tests.

See findings for the three low items.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 485 add-finding "…" --severity medium`; track with `sq review 485 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Verified |  | Stale comment: collections vocab now IS surfaced (preview head) |
| F2 | 🟢 low | WontFix |  | F17 watcher glue has no unit test (only resolveSquadDir is covered) |
| F3 | 🟢 low | Verified |  | MarkdownString tooltip: assignee not markdown-escaped |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Stale comment: collections vocab now IS surfaced (preview head)

<!-- sq:finding:F1:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
clients/vscode/src/domain/previewDocument.ts::buildSubEntityHeadLine — the doc comment states the sub-entity head shows raw severity codes because "no machine surface exposes that vocabulary to the client yet". That is now stale: this same batch (TASK-450-lineage / ADR-474 Part A) shipped `sq workflow collections --json`, so the vocabulary IS surfaced. The raw-code head is still acceptable per F15 (which only requires the head line), but the justification is factually wrong and masks a deliberate inconsistency: the tree tooltip (F19) renders real glyphs via the collections catalog while the preview head does not. Fix: correct the comment (the preview simply doesn't fetch/join the catalog here), or — as a follow-up enhancement, not required by F15 — plumb the resolved badges into the preview head for parity with the hover. Non-blocking.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-07-18T21:36:03Z] Ada Typescript:
  - Fixed: corrected the buildSubEntityHeadLine doc comment in clients/vscode/src/domain/previewDocument.ts — it no longer claims no machine surface exposes the vocabulary; now states plainly that this preview head just doesn't fetch/join the collections catalog (unlike the tree tooltip), per F15's raw-code head being deliberate.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — F17 watcher glue has no unit test (only resolveSquadDir is covered)

<!-- sq:finding:F2:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
clients/vscode/src/squadWatcher.ts (F17/TASK-477) — the pure resolution helpers (resolveSquadDir/parseSquadDirKey/findSquadConfig in domain/squadDir.ts) are unit-tested, but watchSquadIndex itself is not: the non-file-scheme no-op, the unresolved-squad-dir no-op, and the 150ms debounce coalescing (create+change burst -> one refresh) have no coverage. This is consistent with the project's testing boundary — vscode-API-bound glue (treeItemRendering.ts, the providers, itemPreviewManager) is not vitest-covered and the extension-host suite doesn't exercise it either — so it is not a regression in discipline. Flagged low because the debounce/no-op branches are non-trivial logic that could be extracted behind the injectable env (as squadDir already is) and unit-tested. Non-blocking.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-18T21:32:00Z] Catherine Manager:
  - WontFix: the untested surface is the VS Code host glue (createFileSystemWatcher wiring), which needs an extension host to exercise — consistent with the project's existing boundary that vscode-glue isn't vitest-tested. The pure squad-dir resolution helpers (resolveSquadDir) and debounce logic ARE unit-tested. Not worth a host-harness for the wiring.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — MarkdownString tooltip: assignee not markdown-escaped

<!-- sq:finding:F3:head -->
**Status:** 🟢 Verified
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
clients/vscode/src/treeItemRendering.ts::toTreeItem now wraps the tooltip in `new vscode.MarkdownString(node.tooltip)` (F19) so badge glyphs render on their own line. buildTooltip (domain/displayNode.ts) interpolates the assignee display name unescaped, so a name containing markdown metacharacters (_ * `) would render as emphasis/code in the tooltip. Not a security issue — MarkdownString.isTrusted defaults false, so no command-link injection — but it is an escaping inconsistency versus the preview, which escapes all interpolated fields. Field/badge/status text is spec-controlled and safe; assignee is the only user-derived line. Fix: markdown-escape the interpolated values (or at least assignee) before joining. Low/nit.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-07-18T21:36:08Z] Ada Typescript:
  - Fixed: added escapeTooltipMarkdown (clients/vscode/src/domain/displayNode.ts) — backslash-escapes backtick/asterisk/underscore, applied to the assignee line in buildTooltip so a name with markdown metacharacters can't render as emphasis/code in the MarkdownString tooltip. id/type/status/badges stay unescaped (spec-controlled, safe). Added coverage in test/displayNode.test.ts.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
