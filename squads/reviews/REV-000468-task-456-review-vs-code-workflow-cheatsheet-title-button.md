---
id: REV-468
sequence_id: 468
type: review
title: 'TASK-456 review: VS Code workflow cheatsheet title button'
status: Approved
author: reviewer
refs:
- TASK-456:addresses
subentities:
- local_id: F1
  title: Blockquoted mermaid fence could collide on line-derived DOM id
  status: WontFix
  severity: low
created_at: '2026-07-17T16:00:15Z'
updated_at: '2026-07-17T16:01:50Z'
---
<!-- sq:body -->
Independent review of TASK-456 — the view-title button opening the workflow cheatsheet (`sq workflow --raw`) in the extension's owned webview with live-rendered mermaid. Reviewed the scoped diff under `clients/vscode/**` (sqAdapter, domain/markdown, domain/previewDocument, itemPreviewManager, commands, package.json, tests, fixture) against HEAD; the meta-view/icon changes co-present in the working tree are out of scope here.

Verdict: recommend APPROVE. All checks pass; one Low, non-blocking robustness note (see finding).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 468 add-finding "…" --severity medium`; track with `sq review 468 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | WontFix |  | Blockquoted mermaid fence could collide on line-derived DOM id |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Blockquoted mermaid fence could collide on line-derived DOM id

<!-- sq:finding:F1:head -->
**Status:** ⚫ Wont Fix
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
`mermaidFenceIds(start)` derives the source/output DOM ids from the fence's start line index (`sq-mermaid-fence-<line>-source/output`), unique within a single render pass. But `renderMarkdownToHtml` recurses for blockquotes and threads `renderMermaidFences` through, restarting line numbering at 0 for the inner render — so a top-level mermaid fence at line 0 and a mermaid fence nested inside a blockquote (inner line 0) would both mint `sq-mermaid-fence-0-*`, a duplicate id (`getElementById` would then resolve only the first, dropping the second diagram's render).

Purely theoretical for the actual input: the workflow cheatsheet carries no blockquoted mermaid, and the diff is faithful to the committed fixture (verified byte-identical to live `sq workflow --raw`). Non-blocking. If hardening is ever wanted, derive the id from a per-pass counter or prefix the recursion depth. Recording for the record, not gating approval.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T16:00:54Z] Paul Reviewer:
  - Recommend APPROVE (leaving status for the approver — not self-approving).
  - Verified against HEAD, TASK-456 scope only: getWorkflowRaw mirrors getRaw (argv ['workflow','--raw'], full exit-code/spawn mapping, unit-tested 4 ways); renderMermaidFences defaults false so the item-preview path (renderOutcomeHtml → 2-arg call) is unregressed and still renders mermaid as plain code; renderWorkflowHtml opts in. Generalized render script scans querySelectorAll('.sq-graph-source') + data-output-id — N-diagram, no fixed pair; markdown test derives fence count from the fixture dynamically.
  - CSP stays strict: buildPreviewHtml policy unchanged (default-src 'none'; style-src/script-src nonce-only), reused verbatim for the workflow panel; same DOMParser + per-render-nonce mechanism, no unsafe-inline/eval. Separate owned panel (squadsWorkflowPreview) tracked via activeWorkflowPanel independent of activePanel — reuse-or-create + guarded onDidDispose; opening the cheatsheet never steals the item panel and vice versa.
  - F8 caveat resolved: diagrams render live in the webview, not fenced code; built-in markdown.showPreview is NOT used (only a doc-comment reference remains). Fixture byte-identical to live 'sq workflow --raw' (8 mermaid blocks — the brief's '9' is off, immaterial to the N-agnostic scan), no ticket-ID tokens.
  - Gates: npm run check clean (tsc/eslint --max-warnings 0/prettier); npm test 145/145; npm run test:canary 8/8. Button/view-title wiring + live render are CI/manual (accepted). One Low finding F1 (theoretical blockquoted-mermaid id collision) — WontFix, non-blocking.
<!-- sq:discussion:end -->
