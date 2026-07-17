---
id: REV-461
sequence_id: 461
type: review
title: 'TASK-452 review: owned WebviewPanel preview + navigable links'
status: Approved
author: reviewer
refs:
- TASK-452
description: Independent review of TASK-452 (owned webview preview + navigable links);
  recommend approve, one low hardening finding
subentities:
- local_id: F1
  title: 'Security: escaping + CSP are solid — no XSS path found'
  status: Open
  severity: low
- local_id: F2
  title: 'Hardening: markdown link href has no scheme allowlist'
  status: Fixed
  severity: low
- local_id: F3
  title: Lifecycle (F9) + link interception (F10) verified correct
  status: Open
  severity: low
- local_id: F4
  title: Dead-code removal, renderer correctness, gate + canary all clean
  status: Open
  severity: low
created_at: '2026-07-17T14:26:29Z'
updated_at: '2026-07-17T14:58:03Z'
---
<!-- sq:body -->
Independent review of TASK-452 (Ada built it) — the owned WebviewPanel preview backbone replacing the hijacked markdown preview, with navigable item links. Covers REV-448 F9/F10.

Scope reviewed: the clients/vscode diff — new domain/markdown.ts, previewDocument.ts, previewMessages.ts, itemPreviewManager.ts; changes to commands.ts/extension.ts/treeDataProvider wiring; removed showPreview.ts/showDocumentProvider.ts; new unit tests + updated extension-host smoke.

Focus: XSS/CSP of the hand-rolled markdown->HTML renderer, webview lifecycle (F9), link interception (F10), dead-code removal, renderer correctness, gate/canary green.

Recommended verdict is recorded as a comment below; per process I do not self-approve — the status transition is left to the approver (main loop / operator).
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 461 add-finding "…" --severity medium`; track with `sq review 461 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟢 low | Open |  | Security: escaping + CSP are solid — no XSS path found |
| F2 | 🟢 low | Fixed |  | Hardening: markdown link href has no scheme allowlist |
| F3 | 🟢 low | Open |  | Lifecycle (F9) + link interception (F10) verified correct |
| F4 | 🟢 low | Open |  | Dead-code removal, renderer correctness, gate + canary all clean |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — Security: escaping + CSP are solid — no XSS path found

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
SECURITY ASSESSMENT (the headline focus). No exploitable finding — recorded as an informational PASS so the review captures the trace.

Escaping: every content path in markdown.ts routes untrusted sq body text through escapeHtml (&,<,>,",') exactly once — plain runs and bold/italic inner text via linkifyPlainText; inline code + fenced code via escapeHtml; table cells/headings/list items/paragraphs via renderInline; blockquotes recurse; the panel <title> via escapeHtml. The renderer has NO raw-HTML passthrough — literal <script> in a body renders as escaped text (test asserts &lt;script&gt;). No double-escape (each raw segment escaped once).

Item-id anchors: data-item-id values come only from ITEM_ID_PATTERN (/\b[A-Z][A-Z0-9]*-\d+\b/), so purely [A-Z0-9-] — no attribute breakout possible.

CSP (previewDocument.ts): default-src 'none'; style-src 'nonce-<n>'; script-src 'nonce-<n>' — no unsafe-inline, no remote origins, per-render nonce from randomUUID() regenerated on every render. Both <style> and <script> carry the nonce. execFile (not exec) with an argv array means the id passed to 'sq show <id> --raw' has no shell-injection surface.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Hardening: markdown link href has no scheme allowlist

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
In renderInlineToken, a markdown link [text](url) renders as <a href="${escapeHtml(linkUrl)}">. escapeHtml prevents attribute breakout, but there is no scheme allowlist — a body containing [x](javascript:alert(1)) produces <a href="javascript:alert(1)">. That anchor is NOT an a.sq-item-link, so the webview click handler ignores it and the browser would attempt navigation.

NOT exploitable as shipped: the strict CSP (script-src nonce-only, no unsafe-inline) blocks javascript: URI execution, and VS Code's webview navigation handling gates external schemes. Content also originates from sq show --raw of team-authored items, not arbitrary external input. Defense-in-depth only.

Suggested (optional, non-blocking) hardening: allowlist the URL scheme in the link branch (e.g. permit http/https/mailto, else drop the href / render as text), so the renderer is safe independent of the CSP. Can be a follow-up; does not block this task.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-07-17T14:57:58Z] Ada Typescript:
  - Fixed in TASK-453: markdown.ts's renderLink now allowlists http/https/mailto schemes; a bare item-id url routes through the internal sq-item-link mechanism instead; anything else (javascript:/data:/vbscript:/relative/protocol-relative) is dropped, keeping only the escaped visible text. See isSafeLinkUrl + renderLink.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Lifecycle (F9) + link interception (F10) verified correct

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
OBSERVATION / PASS. F9: the preview is an extension-owned WebviewPanel (VIEW_TYPE squadsItemPreview, retainContextWhenHidden), never a dynamic markdown preview — opening other markdown files cannot hijack it. Tree-click routes via routeForTreeSelection(activePanel!==undefined): reuses the single owned panel if present, else opens one; onDidDispose clears activePanel only when the disposed panel IS the active one. The old markdown.showPreview / squads: virtual-doc path is fully gone (showPreview.ts + showDocumentProvider.ts + the scheme deleted); remaining 'squads:'/'showPreview' hits are only doc-comments and captured-dossier fixtures — fine.

F10: item-id linkification is spec-agnostic (single generic regex, no hardcoded type list). Plain click (button 0) -> same-panel; ctrl/cmd-click and middle-click (auxclick button 1) -> new panel. NOTE: the review brief's parenthetical said 'ctrl-click re-renders the same panel', but the TASK-452 body itself specifies 'middle-click (or ctrl/cmd-click) opens it in a NEW webview panel' — the implementation matches the task spec (and standard new-tab UX), so this is correct as-is, not a defect. Both routes go through sqAdapter.getRaw; the openItem message is shape-guarded by parseOpenItemMessage (rejects non-object/wrong-command/empty-or-non-string id/non-boolean newTab), and the command handler re-checks typeof itemId === 'string'.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Dead-code removal, renderer correctness, gate + canary all clean

<!-- sq:finding:F4:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
PASS. Dead-code: npm run check green (tsc noUnusedLocals + eslint zero-warnings) proves no orphan imports; removed modules leave no dangling code refs. vsce ls exit 0 — VSIX ships the compiled new modules (out/src/domain/markdown.js etc.), no source .ts leak, no stale removed-module output.

Renderer correctness: headings H1-H6, ordered/unordered lists (+indented continuations folded), GFM pipe tables (separator-row gated), fenced code incl. mermaid-as-plain-language-code, blockquotes (recursive), inline code/bold/italic/links, HR. Guards a real hang risk: a bare '|' line with no separator row falls back to a paragraph and still makes progress (explicit regression test). noUncheckedIndexedAccess handled via lineAt fallback.

Tests meaningful: markdown.test.ts (escaping, linkify, self-link suppression, no-linkify-in-code, tables/quotes/lists, the non-table-pipe hang guard, two real sq show --raw dossier fixtures), previewDocument.test.ts (CSP lockdown, nonce on both tags, title escaping, command-constant parity, click vs auxclick), previewMessages.test.ts (all shape-guard reject paths + both routers). Accepted caveat: the live webview host (actual click interception in a VS Code window) is exercised only by the CI/manual extension-host smoke test, not npm test — same split as treeDataProvider; acceptable.

Gate output: npm run check exit 0 (tsc strict + eslint --max-warnings 0 + prettier --check all clean); npm test 94/94 passed; npm run test:canary 6/6 passed.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T14:27:30Z] Paul Reviewer:
  - RECOMMENDED VERDICT: APPROVE. The security-critical concern (a hand-rolled markdown->HTML renderer feeding a webview) is handled correctly: complete, single-pass HTML escaping on every content path with no raw-HTML passthrough, regex-constrained item-id anchors, and a genuinely strict per-render-nonce CSP (default-src 'none', no unsafe-inline, no remote). No shell-injection surface (execFile + argv). F9/F10 meet the task spec; dead code is cleanly removed; the strict gate + unit suite (94/94) + skew canary (6/6) are green and the VSIX packages.
  - No blocking findings. Only F2 (optional link-scheme allowlist) is a defense-in-depth hardening suggestion — already neutralized by the CSP, safe to take as a follow-up. F1/F3/F4 are PASS records.
  - @reviewer note: per the do-not-self-approve rule I am NOT flipping this review to Approved or changing TASK-452's status — that two-party transition is the approver's (main loop / operator's) call.
<!-- sq:discussion:end -->
