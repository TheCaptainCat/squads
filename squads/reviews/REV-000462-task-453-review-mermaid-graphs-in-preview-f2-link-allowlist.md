---
id: REV-462
sequence_id: 462
type: review
title: 'TASK-453 review: mermaid graphs in preview + F2 link allowlist'
status: Approved
author: reviewer
refs:
- TASK-453
subentities:
- local_id: F1
  title: CSP/mermaid render path is sound but unverified in a live webview host
  status: Open
  severity: medium
- local_id: F2
  title: 'F2 link-scheme allowlist: no bypass found, well-tested'
  status: Fixed
  severity: low
- local_id: F3
  title: Graph builders are mermaid-injection-safe and match the core CLI convention
  status: Open
  severity: low
- local_id: F4
  title: Packaging clean; vsce large-file warning benign
  status: Open
  severity: low
created_at: '2026-07-17T15:07:13Z'
updated_at: '2026-07-17T15:10:04Z'
---
<!-- sq:body -->
Independent review of TASK-453 (Ada built it): two collapsible mermaid graphs in the owned WebviewPanel preview (children/subtree from sq tree --json, ref graph from sq graph --json), the locally-vendored CSP-nonce'd mermaid renderer, and the REV-461 F2 markdown link-scheme allowlist. Covers REV-448 F11.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 462 add-finding "…" --severity medium`; track with `sq review 462 finding <n> update --status <Status>`._

<!-- sq:summary -->
| Finding | Severity | Status | Assignee | Title |
| --- | --- | --- | --- | --- |
| F1 | 🟡 medium | Open |  | CSP/mermaid render path is sound but unverified in a live webview host |
| F2 | 🟢 low | Fixed |  | F2 link-scheme allowlist: no bypass found, well-tested |
| F3 | 🟢 low | Open |  | Graph builders are mermaid-injection-safe and match the core CLI convention |
| F4 | 🟢 low | Open |  | Packaging clean; vsce large-file warning benign |
<!-- sq:summary:end -->

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — CSP/mermaid render path is sound but unverified in a live webview host

<!-- sq:finding:F1:head -->
**Status:** 🔴 Open
**Severity:** 🟡 Medium
<!-- sq:finding:F1:head:end -->

<!-- sq:finding:F1:body -->
Assessment of Ada's nonce-injection technique (previewDocument.ts mermaidRenderScript + itemPreviewManager render()): SOUND, and I recommend keeping it over the unsafe-inline fallback.

CSP is 'default-src none; style-src nonce-<n>; script-src nonce-<n>' — no unsafe-inline, no unsafe-eval, no CDN. Mermaid is vendored locally (media/mermaid.min.js from the pinned devDependency via scripts/copy-mermaid.js), loaded through a nonce'd <script src> against a media/-scoped localResourceRoots. The dist IIFE build is fully static (no dynamic import/eval), so no unsafe-eval is needed. Confirmed no remote fetch.

The <style>-element nonce-stamping (DOMParser detached-parse -> set .nonce + setAttribute on every <style> -> importNode into the live DOM) is the standard, correct way to satisfy style-src nonce for a dynamically produced stylesheet. securityLevel:'strict' disables htmlLabels + click handlers and runs DOMPurify, so foreignObject-HTML / inline on* handlers / injected <script> are not a vector — and even if one slipped through, script-src nonce-only blocks it. No XSS path found; the design opens no hole.

TWO caveats, both fail-CLOSED (fidelity, not security):
1. Nonces cover <style> ELEMENTS only, never inline style="" ATTRIBUTES. Mermaid's serialized SVG can carry inline style attrs (e.g. root svg max-width, some edge/marker styling); under this CSP those attributes are dropped. Most visible styling comes from the injected <style> block (CSS classes) + our own nonce'd PREVIEW_STYLES (.sq-graph-output svg{max-width:100%}), so impact is likely cosmetic — but unquantified.
2. The entire render path (DOMParser+importNode nonce cloning, SVG-namespaced <style> nonce honoring) is browser/webview-specific and is NOT exercisable by any test here (vitest has no CSP-enforcing DOM). The string wiring is asserted; the runtime behavior is not.

My call on nonce-injection vs. the documented fallback (narrow style-src 'unsafe-inline', never script-src): KEEP the nonce technique — it is correct and maximally strict, and on this page default-src 'none' already denies CSS exfiltration channels. Do NOT pre-emptively switch to unsafe-inline. But this MUST be discharged by a live render check (extension-host smoke or manual VS Code open) before the feature is called Done — same deferral pattern as TASK-452's untestable webview wiring. If that check shows broken diagrams, the fallback is acceptable and, given default-src 'none', only marginally weaker (note: with a nonce present, browsers ignore 'unsafe-inline' for style elements — the fallback must drop the style nonce, not add unsafe-inline alongside it).
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — F2 link-scheme allowlist: no bypass found, well-tested

<!-- sq:finding:F2:head -->
**Status:** 🟡 Fixed
**Severity:** 🟢 Low
<!-- sq:finding:F2:head:end -->

<!-- sq:finding:F2:body -->
markdown.ts renderLink + isSafeLinkUrl: SAFE_LINK_SCHEME=/^(https?|mailto):/i applied to url.trim(); a url that is itself a bare item id routes through the internal a.sq-item-link mechanism; everything else is dropped to escaped visible text. No bypass found:

- Allowlist (not denylist) — only http/https/mailto emit an href; javascript:/data:/vbscript:/file:/relative/protocol-relative all fall through to text.
- Whitespace-obfuscation (java\tscript:) is impossible: the link regex captures the url as [^)\s]+, so no whitespace/control char can sit inside the scheme.
- Attribute breakout is impossible: a safe href is emitted through escapeHtml, so a stray quote becomes &quot; and cannot escape the attribute.
- Item-id self-link to currentId is suppressed (plain text), matching linkifyPlainText.

Well-tested (test/markdown.test.ts: safe/unsafe/case-insensitive/relative/protocol-relative + item-id routing + self-link). Correctly Fixed. Closes REV-461 F2.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Graph builders are mermaid-injection-safe and match the core CLI convention

<!-- sq:finding:F3:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F3:head:end -->

<!-- sq:finding:F3:body -->
graphDiagrams.ts — both builders are mermaid-injection-safe and correct:

- mermaidNodeId folds all non-word chars to _ (item ids are [A-Z][A-Z0-9]*-\d+ so only the hyphen changes); matches core _refs.py::_safe_id.
- mermaidNodeLabel wraps HTML-escaped text in mermaid quotes; the double-escape (escape for mermaid's entity-aware label, then escape again for the hidden <pre>) round-trips exactly: <pre>.textContent decodes the outer HTML layer, leaving the mermaid-entity layer for mermaid to interpret. Verified a title with & / < / " cannot break out of the quotes or inject markup.
- mermaidEdgeLabel HTML-escapes + folds a stray | to / (defense-in-depth over a controlled vocab).
- edgeLabel gives depends-on a direction-sensitive 'depends on'/'required by' and any other kind its name verbatim — VERIFIED to match the core CLI (src/squads/_services/_refs.py::graph_to_mermaid _label, lines 249-252); Ada's mirror claim is accurate.
- Ref-graph dedups nodes by id and edges by (from,to,label), sorts edges for determinism, and handles seen-revisits as real edges into the existing box. Subtree is a plain TD tree.

Tested against literal cases (incl. <script>, a|b) + the committed tree.json/graph.json fixtures (which I confirmed match live sq output). One low-severity robustness note, not blocking: a title containing a newline would break the mermaid line (escapeHtml doesn't strip \n) -> diagram fails to render (shows 'Failed to render diagram.'), not a security issue; sq titles are single-line by convention so this is theoretical.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — Packaging clean; vsce large-file warning benign

<!-- sq:finding:F4:head -->
**Status:** 🔴 Open
**Severity:** 🟢 Low
<!-- sq:finding:F4:head:end -->

<!-- sq:finding:F4:body -->
Packaging verified clean:

- vsce ls / vsce package: media/mermaid.min.js ships; out/src/**/*.js ships; NO src/*.ts, NO test/, NO fixtures, NO node_modules. VSIX = 995KB.
- .vscodeignore + .gitignore correctly treat media/ as a reproducible build product (like out/), vendored by npm run compile; copy-mermaid.js excluded from the VSIX.
- vsce's 'mermaid.min.js is large (3.4MB)' warning is BENIGN and inherent to the deliberate no-CDN self-contained bundling (ADR-427 CSP-locked webview); the 3.4MB uncompressed source packs to ~995KB. Acceptable.
- copy-mermaid.js CommonJS require() is fine: it's a dev-time build helper, explicitly eslint-ignored (scripts/**) and not part of the tsc build. No action needed.

Gate all green: npm run check clean (tsc strict + eslint 0-warn + prettier), npm test 122/122, npm run test:canary 8/8 (adds an sq graph --json describe block).

Out-of-scope observation (NOT a TASK-453 finding): resources/squads-icon-vscode.svg ships in the VSIX but is REV-448 F13 in-flight icon work, not this task; package.json still points the container icon at squads-icon-mono.svg. Flag for whoever lands F13.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-07-17T15:08:32Z] Paul Reviewer:
  - RECOMMENDED VERDICT: APPROVE. The TASK-453 diff is correct, well-tested, and secure. F2 (link allowlist) is soundly fixed with no bypass; the two graph builders are mermaid-injection-safe and faithfully mirror the core CLI; packaging is clean (VSIX 995KB, no src/test leak). Gate green: check clean, 122/122 unit, 8/8 canary, vsce ls clean.
  - One condition to discharge (F1, medium): the CSP nonce-injection render path is SOUND and fail-closed — I recommend keeping it over the unsafe-inline fallback — but it is not exercisable by any test here and mermaid's inline style="" attributes are not covered by the style nonce. Before FEAT-449/US1 is called Done, validate the actual mermaid render in a live extension-host smoke test or a manual VS Code open (same deferral pattern as TASK-452's untestable webview wiring). This does not block the code merge; it blocks calling the visual behavior verified.
  - Per my do-not-self-approve rule: findings + recommended verdict recorded; the Approved status transition is left to the approver (main loop / operator). @tech-lead over to you.
<!-- sq:discussion:end -->
