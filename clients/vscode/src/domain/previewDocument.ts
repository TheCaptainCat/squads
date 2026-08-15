/**
 * Assembles the full webview HTML document for an item preview — a strict, self-contained CSP
 * (no remote content, no `unsafe-inline`), the rendered dossier body, the two collapsible mermaid
 * graph sections, the sub-entities and discussion sections, and the inline client script (see
 * `buildPreviewHtml`).
 *
 * Kept `vscode`-free/pure — `nonce` and the mermaid script's webview uri are passed in rather
 * than computed here, so this (and the markdown rendering it wraps) is unit-testable with no
 * host; only `itemPreviewManager.ts` touches the real `vscode.WebviewPanel` API.
 */
import type { SqOutcome } from '../sqAdapter';
import type { SqDiscussionEntry, SqSubEntity } from '../types';
import {
  type FieldBindingsByType,
  NO_BADGE_VOCABULARY,
  NO_FIELD_BINDINGS,
  resolveItemBadges,
} from './badgeCatalog';
import { MERMAID_NODE_ID_ESCAPE_SOURCE } from './graphDiagrams';
import type { ItemDirectory } from './itemDirectory';
import type { ItemIdMatcher } from './itemIdPattern';
import { escapeHtml, renderMarkdownToHtml } from './markdown';
import {
  NAVIGATE_HISTORY_COMMAND,
  OPEN_ITEM_COMMAND,
  REFRESH_COMMAND,
  TOGGLE_FOLD_COMMAND,
  UPDATE_CONTENT_COMMAND,
} from './previewMessages';
import type { RoleDirectory } from './roleDirectory';

const ARTICLE_MOUNT_ID = 'sq-article';
const SUBENTITIES_MOUNT_ID = 'sq-subentities';
const DISCUSSION_MOUNT_ID = 'sq-discussion';

const CHILDREN_GRAPH_SOURCE_ID = 'sq-children-graph-source';
const CHILDREN_GRAPH_OUTPUT_ID = 'sq-children-graph';
const REFS_GRAPH_SOURCE_ID = 'sq-refs-graph-source';
const REFS_GRAPH_OUTPUT_ID = 'sq-refs-graph';

/** Marks a `.sq-graph-source` whose mermaid node ids are real item ids, so the webview's
 * post-render pass knows it may stamp them as navigable (`mermaidRenderScript`). Only the two
 * structured graph sections carry it: they are built from `sq tree`/`sq graph --json`, where
 * every node IS an item. A diagram that came from a ```mermaid``` fence — a hand-authored one
 * in a project's own cheatsheet template, say — carries whatever node ids its author wrote, so
 * stamping those would offer the reader a click that opens nothing. Opt-in by construction:
 * a future item-bearing diagram has to say so, and anything else is inert by default. */
const ITEM_NODES_ATTRIBUTE = 'data-sq-item-nodes';

/** Stable fold ids for the two graph `<details>` sections — the `ToggleFoldMessage`/
 * `ExpansionTracker` identity used to restore open/closed state across a refresh (see
 * `buildGraphSection`). Distinct from the source/output ids above, which wire the mermaid
 * *rendering* rather than fold tracking. */
export const CHILDREN_GRAPH_FOLD_ID = 'children';
export const REFS_GRAPH_FOLD_ID = 'refs';

const PREVIEW_STYLES = `
body {
  font-family: var(--vscode-font-family, sans-serif);
  color: var(--vscode-editor-foreground);
  padding: 0.5rem 1.5rem 2rem;
  line-height: 1.55;
}
a.sq-item-link { color: var(--vscode-textLink-foreground); text-decoration: none; }
a.sq-item-link:hover { text-decoration: underline; }
h1, h2, h3 { border-bottom: 1px solid var(--vscode-panel-border, transparent); padding-bottom: 0.3em; }
code, pre { font-family: var(--vscode-editor-font-family, monospace); }
pre {
  background: var(--vscode-textCodeBlock-background);
  padding: 0.75rem;
  overflow-x: auto;
  border-radius: 4px;
}
code { background: var(--vscode-textCodeBlock-background); padding: 0.1em 0.3em; border-radius: 3px; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; margin: 1rem 0; }
th, td { border: 1px solid var(--vscode-panel-border); padding: 0.3em 0.7em; text-align: left; }
blockquote {
  margin: 0.5rem 0;
  padding: 0.2rem 1rem;
  border-left: 3px solid var(--vscode-textBlockQuote-border, var(--vscode-panel-border));
  background: var(--vscode-textBlockQuote-background);
}
details.sq-graph {
  margin: 1rem 0;
  border: 1px solid var(--vscode-panel-border, transparent);
  border-radius: 4px;
  padding: 0.4rem 0.9rem;
}
details.sq-graph summary {
  cursor: pointer;
  font-weight: 600;
  padding: 0.3rem 0;
}
details.sq-graph .sq-graph-empty {
  color: var(--vscode-descriptionForeground);
}
.sq-mermaid-block {
  margin: 1rem 0;
}
.sq-graph-output svg {
  max-width: 100%;
  height: auto;
}
.sq-graph-output .node[data-item-id] {
  cursor: pointer;
}
.sq-comment {
  margin: 0.9rem 0;
  padding-top: 0.6rem;
  border-top: 1px solid var(--vscode-panel-border, transparent);
}
.sq-comment:first-of-type {
  border-top: none;
  padding-top: 0;
}
.sq-comment-header {
  font-size: 0.9em;
  color: var(--vscode-descriptionForeground);
  margin-bottom: 0.3rem;
}
.sq-comment-author {
  font-weight: 600;
  color: var(--vscode-editor-foreground);
}
.sq-subentity {
  margin: 0.9rem 0;
  padding-top: 0.6rem;
  border-top: 1px solid var(--vscode-panel-border, transparent);
}
.sq-subentity:first-of-type {
  border-top: none;
  padding-top: 0;
}
.sq-subentity-header {
  margin-bottom: 0.2rem;
}
.sq-subentity-id {
  font-weight: 600;
  margin-right: 0.4em;
}
.sq-subentity-head {
  font-size: 0.9em;
  color: var(--vscode-descriptionForeground);
  margin-bottom: 0.3rem;
}
.sq-subentity-body summary {
  cursor: pointer;
  color: var(--vscode-descriptionForeground);
}
/* fixed, not sticky: this document renders inside a nested webview iframe whose own scrolling
   doesn't carry sticky positioning along in practice (verified empirically -- a sticky element
   here scrolls off-screen with the rest of the content instead of pinning), so the toolbar is
   pinned directly against the iframe's own viewport instead. .sq-nav-toolbar-spacer (emitted
   right after it -- see buildHistoryToolbarHtml) reserves the same height in the normal flow so
   fixed positioning doesn't pull it out of the layout and let content render underneath it. */
.sq-nav-toolbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  box-sizing: border-box;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1.5rem;
  background: var(--vscode-editor-background);
  border-bottom: 1px solid var(--vscode-panel-border, transparent);
}
.sq-nav-toolbar-spacer {
  height: 2.75rem;
}
.sq-nav-title {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.sq-nav-buttons {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}
.sq-nav-button {
  font: inherit;
  font-size: 1rem;
  line-height: 1;
  color: var(--vscode-foreground);
  background: var(--vscode-button-secondaryBackground, transparent);
  border: 1px solid var(--vscode-panel-border, transparent);
  border-radius: 4px;
  width: 1.8rem;
  height: 1.8rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  cursor: pointer;
}
.sq-nav-button:hover:not(:disabled) {
  background: var(--vscode-button-secondaryHoverBackground, var(--vscode-toolbar-hoverBackground));
}
.sq-nav-button:disabled {
  opacity: 0.4;
  cursor: default;
}
`;

/** Delegated click/auxclick handling for `a.sq-item-link`/`g.node[data-item-id]` (including a
 * resolved `@<slug>` role mention, which shares the same `data-item-id` attribute) — a plain
 * click (or ctrl/cmd-click) requests same-panel navigation, a middle-click (`auxclick`, button 1)
 * a new panel — plus the in-content toolbar's back/forward (`[data-sq-nav]` -> `navCommand`) and
 * refresh (`[data-sq-refresh]` -> `refreshCommand`) buttons, checked first since both are
 * disjoint element kinds. A `disabled` nav button doesn't dispatch a click at all in a Chromium
 * webview, but the handler still re-checks `.disabled` defensively rather than relying solely on
 * that platform behavior.
 *
 * All listeners are bound once, on `document`, in this outer IIFE — never re-bound after a
 * same-item patch — so a button living inside content a patch replaces (the toolbar is part of
 * `articleHtml`) keeps working after its container is swapped out from under it: only the DOM
 * node changes identity, not the delegated listener.
 *
 * Also listens, capture phase (see `previewMessages.ts`'s `ToggleFoldMessage` for why), for a
 * toggle on a tracked fold and reports it back as a `ToggleFoldMessage`.
 *
 * Handles the host's `updateCommand` message (`UpdateContentMessage`, see `previewMessages.ts`)
 * by patching the three mount points in place via `innerHTML` and re-running the mermaid render
 * pass (`window.__sqRenderMermaid`) over whatever new `.sq-graph-source` elements just landed.
 * The replacement HTML's own fold `<details>` already carry the right `open` attribute (stamped
 * by `itemPreviewManager.ts`'s render before the message is even sent), so setting it at parse
 * time here never itself fires a spurious `toggle` back to the host.
 *
 * Every *fresh* load (a genuine navigation) resets scroll with a real `window.scrollTo(0, 0)`
 * rather than counting on a browser's default fresh-document scroll position — VS Code's webview
 * host doesn't document that guarantee. */
function clientScript(
  openCommand: string,
  updateCommand: string,
  navCommand: string,
  refreshCommand: string,
  toggleFoldCommand: string,
): string {
  return `(function () {
  window.scrollTo(0, 0);
  const vscode = acquireVsCodeApi();
  function post(event, newTab) {
    const target = event.target.closest('a.sq-item-link, g.node[data-item-id]');
    if (!target) { return; }
    event.preventDefault();
    const id = target.getAttribute('data-item-id');
    if (!id) { return; }
    vscode.postMessage({ command: '${openCommand}', id: id, newTab: newTab });
  }
  document.addEventListener('click', function (event) {
    if (event.button !== 0) { return; }
    const navTarget = event.target.closest('[data-sq-nav]');
    if (navTarget) {
      if (navTarget.disabled) { return; }
      event.preventDefault();
      vscode.postMessage({ command: '${navCommand}', direction: navTarget.getAttribute('data-sq-nav') });
      return;
    }
    const refreshTarget = event.target.closest('[data-sq-refresh]');
    if (refreshTarget) {
      event.preventDefault();
      vscode.postMessage({ command: '${refreshCommand}' });
      return;
    }
    post(event, event.ctrlKey || event.metaKey);
  });
  document.addEventListener('auxclick', function (event) {
    if (event.button !== 1) { return; }
    post(event, true);
  });
  document.addEventListener('toggle', function (event) {
    const target = event.target;
    if (!target || !target.matches || !target.matches('[data-sq-fold-id]')) { return; }
    const id = target.getAttribute('data-sq-fold-id');
    if (!id) { return; }
    vscode.postMessage({ command: '${toggleFoldCommand}', id: id, open: target.open });
  }, true);
  window.addEventListener('message', function (event) {
    const message = event.data;
    if (!message || message.command !== '${updateCommand}') { return; }
    document.getElementById('${ARTICLE_MOUNT_ID}').innerHTML = message.articleHtml;
    document.getElementById('${SUBENTITIES_MOUNT_ID}').innerHTML = message.subEntitiesHtml;
    document.getElementById('${DISCUSSION_MOUNT_ID}').innerHTML = message.discussionHtml;
    if (typeof window.__sqRenderMermaid === 'function') { window.__sqRenderMermaid(); }
  });
})();`;
}

/** Renders every `.sq-graph-source` element's mermaid text into its paired output `<div>` (via
 * `data-output-id` — a generic scan, not a fixed list, so it covers both the two structured graph
 * sections and any inline ```mermaid``` fences a dossier's own body carries), using the mermaid
 * renderer loaded by the preceding `<script src>` tag. `flowchart.wrappingWidth` pairs with
 * `graphDiagrams.ts`'s markdown-string node labels for real text-metric wrapping.
 *
 * CSP note (kept strict — no `unsafe-inline`/`unsafe-eval` added for this): mermaid's own
 * `render()` builds each diagram by inserting a plain, un-nonced `<style>` tag carrying its
 * generated CSS into the returned SVG markup. Assigning that markup via `innerHTML` as-is
 * would make the browser silently disable that stylesheet under this page's `style-src
 * 'nonce-*'` policy (diagram present, but unstyled). Instead the returned SVG is parsed
 * (detached, via `DOMParser` — no CSP applies to a detached document), this render's nonce is
 * stamped onto every `<style>` found in it, and only then are the resulting *nodes* (not the
 * raw string) inserted into the live document. If a future mermaid version needs something this
 * can't cover, the documented fallback is a narrowly-scoped `style-src 'unsafe-inline'` (never
 * `script-src`) — flagged for review rather than applied speculatively.
 *
 * Node-click wiring: mermaid's `click` directive is disabled under `securityLevel: 'strict'`, so
 * navigation is wired here instead, after render — and only for a source that declares its node
 * ids to be item ids (`ITEM_NODES_ATTRIBUTE`; see that constant for why the default is inert).
 * Each rendered node's id
 * (`<diagramId>-flowchart-<nodeId>-<n>`, `nodeId` being what `graphDiagrams.ts`'s `mermaidNodeId`
 * produced) is decoded back to the real item id and stamped as `data-item-id` for
 * `clientScript`'s shared click handling. The decode undoes that module's escape and nothing
 * else — its pattern is interpolated from `MERMAID_NODE_ID_ESCAPE_SOURCE` rather than written
 * out again here, so the encoder cannot change without this changing with it, and a node id
 * that carries no escape (a hand-authored ```mermaid``` fence's own node) decodes to itself.
 *
 * Exposed as `window.__sqRenderMermaid` (rather than a run-once IIFE) so `clientScript` can
 * re-invoke it after a same-item refresh patches in fresh `.sq-graph-source` elements —
 * `callSeq` lives in the enclosing closure so every `mermaid.render` call gets a unique id for
 * the life of the page, not just the first render. */
function mermaidRenderScript(nonce: string): string {
  return `(function () {
  var callSeq = 0;
  window.__sqRenderMermaid = function () {
    if (typeof mermaid === 'undefined') { return; }
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      flowchart: { wrappingWidth: 200 },
    });
    var nonce = '${nonce}';
    var nodeIdPattern = /-flowchart-([A-Za-z0-9_]+)-\\d+$/;
    var escapePattern = /${MERMAID_NODE_ID_ESCAPE_SOURCE}/g;
    var stampsItemNodes = function (sourceEl) {
      return sourceEl.hasAttribute('${ITEM_NODES_ATTRIBUTE}');
    };
    var decodeNodeId = function (encoded) {
      return encoded.replace(escapePattern, function (whole, hex) {
        return String.fromCharCode(parseInt(hex, 16));
      });
    };
    var sources = document.querySelectorAll('.sq-graph-source');
    sources.forEach(function (sourceEl) {
      var outputId = sourceEl.getAttribute('data-output-id');
      var outputEl = outputId ? document.getElementById(outputId) : null;
      if (!outputEl) { return; }
      var text = sourceEl.textContent || '';
      if (!text.trim()) { return; }
      var renderId = 'sq-mermaid-render-' + String(callSeq++);
      mermaid.render(renderId, text).then(function (result) {
        var parsed = new DOMParser().parseFromString(result.svg, 'image/svg+xml');
        var svgEl = parsed.documentElement;
        if (!svgEl || svgEl.nodeName === 'parsererror') {
          outputEl.textContent = 'Failed to render diagram.';
          return;
        }
        var styles = svgEl.querySelectorAll('style');
        for (var i = 0; i < styles.length; i++) {
          styles[i].setAttribute('nonce', nonce);
          styles[i].nonce = nonce;
        }
        if (stampsItemNodes(sourceEl)) {
          var nodes = svgEl.querySelectorAll('.node');
          for (var j = 0; j < nodes.length; j++) {
            var match = nodeIdPattern.exec(nodes[j].getAttribute('id') || '');
            if (!match) { continue; }
            nodes[j].setAttribute('data-item-id', decodeNodeId(match[1]));
          }
        }
        outputEl.replaceChildren(document.importNode(svgEl, true));
      }).catch(function () {
        outputEl.textContent = 'Failed to render diagram.';
      });
    });
  };
  window.__sqRenderMermaid();
})();`;
}

/** A dossier's contiguous metadata bullet block (`- **key:** value` — the `--raw` contract:
 * title, blank, bullets, blank, body verbatim). Matched only right after the title so a body
 * paragraph that happens to start with a similar-looking bullet is never mistaken for
 * metadata. */
const DOSSIER_METADATA_BULLET = /^- \*\*[\w-]+:\*\* /;

/** The index of the first non-blank line at/after `start`. */
function skipBlankLines(lines: readonly string[], start: number): number {
  let i = start;
  while (i < lines.length && (lines[i] ?? '').trim() === '') {
    i++;
  }
  return i;
}

/** The index just past the last contiguous metadata-bullet line starting at `start`. */
function skipMetadataBullets(lines: readonly string[], start: number): number {
  let i = start;
  while (i < lines.length && DOSSIER_METADATA_BULLET.test(lines[i] ?? '')) {
    i++;
  }
  return i;
}

/** Splits a clean `sq show <id> --raw` dossier into its metadata header (title + bullet list)
 * and the rest — its prose body — so the two can be rendered as separate HTML fragments with
 * the graph sections injected between them (graphs directly under the metadata header,
 * above the body). Falls back to an empty header (the whole text treated as body) when the
 * input doesn't start with the expected title-then-bullets shape — e.g. a synthesized failure
 * message — rather than guessing past what it can actually detect. */
export function splitDossierMarkdown(markdown: string): { header: string; body: string } {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  if (!(lines[0] ?? '').startsWith('# ')) {
    return { header: '', body: markdown };
  }
  const bulletStart = skipBlankLines(lines, 1);
  const bulletEnd = skipMetadataBullets(lines, bulletStart);
  if (bulletEnd === bulletStart) {
    return { header: '', body: markdown };
  }
  const bodyStart = skipBlankLines(lines, bulletEnd);
  return {
    header: lines.slice(0, bulletEnd).join('\n'),
    body: lines.slice(bodyStart).join('\n'),
  };
}

/** The plain-text title line a `splitDossierMarkdown` header fragment starts with, for the
 * sticky in-content toolbar's compact title slot (`buildHistoryToolbarHtml`) — a *copy*, not a
 * move: the heading stays in `headerHtml` too, rendered as a full, never-truncated `<h1>` in the
 * body, since a title truncated to the toolbar's width would otherwise be the reader's only
 * complete view of it. Plain text (the toolbar escapes it, and reuses it as a hover-tooltip
 * `title=`), not HTML. Falls back to `''` when `header` doesn't start with an H1 —
 * `renderOutcomeHtml` covers that case with the item id instead. */
function extractTitleLine(header: string): string {
  if (!header.startsWith('# ')) {
    return '';
  }
  const newlineIndex = header.indexOf('\n');
  return newlineIndex === -1 ? header.slice(2) : header.slice(2, newlineIndex);
}

/** The dossier split into its rendered pieces — see `splitDossierMarkdown`. `titleText` is a
 * plain-text *copy* of the heading (for the in-content toolbar's compact title slot,
 * `buildHistoryToolbarHtml`) — `headerHtml` still carries the full heading too, unchanged. */
export interface DossierHtml {
  readonly titleText: string;
  readonly headerHtml: string;
  readonly bodyHtml: string;
}

/** Renders an `sq show <id> --raw` outcome to the HTML/text fragments shown in the panel: the
 * metadata header fragment and prose body, split by `splitDossierMarkdown` so the caller can
 * inject the graph sections between them, plus `titleText` for the sticky toolbar's compact
 * title slot (see `extractTitleLine`). On failure the message renders entirely as `bodyHtml`
 * with an empty header and `id` itself as the title — the caller is still responsible for firing
 * the accompanying VS Code notification. `roles`, when given, resolves `@<slug>` mentions in the
 * dossier body (see `domain/roleDirectory.ts`); `ids` is the squad's declared-prefix id grammar
 * (`domain/itemIdPattern.ts`) and `items` the hover text each linked id carries
 * (`domain/itemDirectory.ts`), both threaded through to every markdown render below. */
export function renderOutcomeHtml(
  id: string,
  outcome: SqOutcome<string>,
  roles?: RoleDirectory,
  ids?: ItemIdMatcher,
  items?: ItemDirectory,
): DossierHtml {
  if (outcome.kind !== 'success') {
    return {
      titleText: id,
      headerHtml: '',
      bodyHtml: renderMarkdownToHtml(
        `# Squads: unable to load ${id}\n\n${outcome.message}`,
        id,
        false,
        undefined,
        ids,
        items,
      ),
    };
  }
  const { header, body } = splitDossierMarkdown(outcome.data);
  const titleText = extractTitleLine(header);
  return {
    titleText: titleText === '' ? id : titleText,
    headerHtml: renderMarkdownToHtml(header, id, false, undefined, ids, items),
    bodyHtml: renderMarkdownToHtml(body, id, false, roles, ids, items),
  };
}

/** Renders an `sq workflow --raw` outcome to the HTML fragment shown in the workflow-cheatsheet
 * panel body. Unlike `renderOutcomeHtml` (an item dossier), this document isn't an item — there
 * is no id to suppress a self-link on, and its markdown carries its own ```mermaid``` diagrams
 * inline rather than fetching a separate graph, so it opts into `renderMarkdownToHtml`'s live-
 * mermaid mode instead of the item preview's plain-code default. */
export function renderWorkflowHtml(outcome: SqOutcome<string>): string {
  const markdown =
    outcome.kind === 'success'
      ? outcome.data
      : `# Squads: unable to load the workflow cheatsheet\n\n${outcome.message}`;
  return renderMarkdownToHtml(markdown, undefined, true);
}

/** One graph section's content: either mermaid source ready to render, or (on a failed/empty
 * fetch) a plain message shown in its place — the section still appears, never silently
 * dropped. */
export interface GraphOutcome {
  readonly mermaidSource: string | null;
  readonly message?: string;
}

interface GraphSectionSpec {
  readonly title: string;
  readonly sourceId: string;
  readonly outputId: string;
  readonly outcome: GraphOutcome;
  /** Stable fold-tracking id (`CHILDREN_GRAPH_FOLD_ID`/`REFS_GRAPH_FOLD_ID`) stamped as
   * `data-sq-fold-id`, so a toggle here reports back through `ToggleFoldMessage`. */
  readonly foldId: string;
  /** Whether this fold should render `open`, per the caller's per-panel fold tracker — `false`
   * on a fresh load (no tracked state yet), restored across a same-item refresh otherwise. */
  readonly open: boolean;
}

/** One collapsible `<details>` graph section — native fold/unfold, no client JS needed beyond the
 * `toggle` report wired in `clientScript`. Collapsed by default on a fresh load (`open` reflects
 * the caller's fold tracker) — a graph is supplementary detail, not something that should push
 * the dossier body below the fold. When `mermaidSource` is present the hidden `<pre>` holds the
 * escaped diagram source, which the client script reads via `textContent` (so it comes back out
 * unescaped); `data-output-id` points the render script at the adjacent output `<div>`. Otherwise
 * the message stands in for it. */
function buildGraphSection(spec: GraphSectionSpec): string {
  const inner =
    spec.outcome.mermaidSource === null
      ? `<p class="sq-graph-empty">${escapeHtml(spec.outcome.message ?? 'No data available.')}</p>`
      : `<pre class="sq-graph-source" id="${spec.sourceId}" data-output-id="${spec.outputId}" ${ITEM_NODES_ATTRIBUTE} hidden>${escapeHtml(spec.outcome.mermaidSource)}</pre><div class="sq-graph-output" id="${spec.outputId}">Rendering…</div>`;
  const openAttr = spec.open ? ' open' : '';
  return `<details class="sq-graph" data-sq-fold-id="${escapeHtml(spec.foldId)}"${openAttr}><summary>${escapeHtml(spec.title)}</summary>${inner}</details>`;
}

/** The two graph sections (children/subtree, ref graph), each independently collapsible and kept
 * separate from the dossier body and from each other. `childrenOpen`/`refsOpen` restore each
 * section's prior open/closed state across a same-item refresh (see
 * `CHILDREN_GRAPH_FOLD_ID`/`REFS_GRAPH_FOLD_ID` and `itemPreviewManager.ts`'s per-panel
 * `ExpansionTracker`). */
export function buildGraphsHtml(
  children: GraphOutcome,
  refs: GraphOutcome,
  childrenOpen = false,
  refsOpen = false,
): string {
  return [
    buildGraphSection({
      title: 'Children / Subtree',
      sourceId: CHILDREN_GRAPH_SOURCE_ID,
      outputId: CHILDREN_GRAPH_OUTPUT_ID,
      outcome: children,
      foldId: CHILDREN_GRAPH_FOLD_ID,
      open: childrenOpen,
    }),
    buildGraphSection({
      title: 'Ref Graph',
      sourceId: REFS_GRAPH_SOURCE_ID,
      outputId: REFS_GRAPH_OUTPUT_ID,
      outcome: refs,
      foldId: REFS_GRAPH_FOLD_ID,
      open: refsOpen,
    }),
  ].join('\n');
}

/** The discussion section's content, mirroring `GraphOutcome`'s success/failure shape: the
 * parsed comment list (`sq show <id> --json`'s `discussion` array) on success, or a plain
 * failure message shown in its place on a failed fetch — never silently dropped. Unlike a graph
 * section, a *successful* but empty list (the common case — most items carry no comments) folds
 * away to nothing rather than an empty section with nothing to show (see `buildDiscussionHtml`).
 */
export interface DiscussionOutcome {
  readonly entries: readonly SqDiscussionEntry[] | null;
  readonly message?: string;
}

/** One comment: an author + ISO-timestamp header, then its body rendered through the same
 * markdown renderer the dossier body uses (so item-id references — and, when `roles` resolves
 * them, `@<slug>` role mentions — inside a comment linkify the same way, and `currentId` still
 * suppresses a self-link). */
function buildCommentHtml(
  entry: SqDiscussionEntry,
  currentId: string | undefined,
  roles: RoleDirectory | undefined,
  ids: ItemIdMatcher | undefined,
  items: ItemDirectory | undefined,
): string {
  return (
    `<div class="sq-comment"><div class="sq-comment-header">` +
    `<span class="sq-comment-author">${escapeHtml(entry.author)}</span> ` +
    `<span class="sq-comment-ts">${escapeHtml(entry.ts)}</span></div>` +
    `<div class="sq-comment-body">${renderMarkdownToHtml(entry.body, currentId, false, roles, ids, items)}</div></div>`
  );
}

/** The collapsible discussion/comments section, appended after the dossier body and the graph
 * sections — see `DiscussionOutcome` for the failure/empty/populated behavior. `roles`, when
 * given, resolves `@<slug>` mentions in a comment's body (see `domain/roleDirectory.ts`). */
export function buildDiscussionHtml(
  outcome: DiscussionOutcome,
  currentId?: string,
  roles?: RoleDirectory,
  ids?: ItemIdMatcher,
  items?: ItemDirectory,
): string {
  if (outcome.entries === null) {
    return (
      `<details class="sq-graph" open><summary>Discussion</summary>` +
      `<p class="sq-graph-empty">${escapeHtml(outcome.message ?? 'No data available.')}</p></details>`
    );
  }
  if (outcome.entries.length === 0) {
    return '';
  }
  const comments = outcome.entries
    .map((entry) => buildCommentHtml(entry, currentId, roles, ids, items))
    .join('\n');
  const count = String(outcome.entries.length);
  return `<details class="sq-graph" open><summary>Discussion (${count})</summary>${comments}</details>`;
}

/** The sub-entities section's content, mirroring `DiscussionOutcome`'s success/failure shape:
 * the parsed sub-entity list (`sq show <id> --json`'s `subentities` array) on success, or a
 * plain failure message shown in its place on a failed fetch. A *successful* but empty list
 * (most items carry no sub-entities) folds away to nothing, same as `buildDiscussionHtml`. */
export interface SubEntitiesOutcome {
  readonly entities: readonly SqSubEntity[] | null;
  readonly message?: string;
}

/** What the head line needs to label a sub-entity's declared badge fields: the parent item's
 * type, and the sub-entity field bindings to join it through (`domain/badgeCatalog.ts`). Both
 * optional — an unknown type or an unavailable kind catalog labels each field by its raw code
 * instead, which is a degrade, not a failure. */
export interface SubEntityFieldContext {
  readonly itemType?: string | undefined;
  readonly fieldBindings?: FieldBindingsByType | undefined;
}

/** The head badge line for one sub-entity — status, then every declared badge field the
 * sub-entity actually carries, then assignee and story (each omitted when absent; `story` is
 * subtasks only). The badge fields come from the payload's own spec-resolved `badges` map and
 * are labelled from the kind's declared `fields`, so a project that renames or adds an axis is
 * followed here with no client change and no badge axis is named in this file. The three
 * remaining literals are the sub-entity model's own structural fields, not declared vocabulary
 * — and a kind that maps no parent story simply never carries one, so that part omits itself.
 *
 * Plain text, not the spec's rendered badge glyph, and the raw badge *code* rather than its
 * display label — this preview head doesn't fetch/join the collections catalog
 * (`sq workflow collections --json`) the way the tree tooltip does, same raw-code convention
 * `graphDiagrams.ts` uses. That is why the vocabulary passed to `resolveItemBadges` here is
 * deliberately the empty one. */
function buildSubEntityHeadLine(entity: SqSubEntity, fields: SubEntityFieldContext = {}): string {
  const parts = [`Status: ${escapeHtml(entity.status)}`];
  const badges = resolveItemBadges(
    fields.itemType ?? '',
    entity.badges,
    fields.fieldBindings ?? NO_FIELD_BINDINGS,
    NO_BADGE_VOCABULARY,
  );
  for (const badge of badges) {
    parts.push(`${escapeHtml(badge.fieldLabel)}: ${escapeHtml(badge.badgeLabel)}`);
  }
  if (entity.assignee !== null) {
    parts.push(`Assignee: ${escapeHtml(entity.assignee)}`);
  }
  if (entity.story !== null) {
    parts.push(`Story: ${escapeHtml(entity.story)}`);
  }
  return parts.join(' · ');
}

/** A sub-entity's own comments block, mirroring `buildDiscussionHtml`'s markup (same `<details
 * class="sq-graph" open>` wrapper, same `buildCommentHtml` per entry) so a reader recognises it
 * as the same kind of thing, just scoped to the sub-entity rather than the whole item. `entries`
 * is `undefined` for an older-`sq` payload that omits the key entirely (see `isSqSubEntity`) and
 * treated exactly like an empty array — both fold away to nothing, the same graceful-empty
 * behaviour `buildDiscussionHtml` gives the item-level section.
 *
 * Deliberately carries no `data-sq-fold-id`: the block always renders `open` and its state is
 * never restored across a refresh, so it can't collide with — or reset — the sub-entity body
 * fold's tracking, which *is* keyed by `local_id` (see `buildSubEntityHtml`). */
function buildSubEntityDiscussionHtml(
  entries: readonly SqDiscussionEntry[] | undefined,
  currentId: string | undefined,
  roles: RoleDirectory | undefined,
  ids: ItemIdMatcher | undefined,
  items: ItemDirectory | undefined,
): string {
  if (entries === undefined || entries.length === 0) {
    return '';
  }
  const comments = entries
    .map((entry) => buildCommentHtml(entry, currentId, roles, ids, items))
    .join('\n');
  const count = String(entries.length);
  return `<details class="sq-graph" open><summary>Discussion (${count})</summary>${comments}</details>`;
}

/** One sub-entity: its local id + title as a header, the head badge line always visible, its body
 * as collapsible prose (when it has one) rendered through the same markdown renderer the
 * dossier/discussion sections use — a blank body renders no `<details>` at all — and, last, its
 * own comments block (see `buildSubEntityDiscussionHtml`; absent/empty folds away the same way).
 * The body fold's `data-sq-fold-id` is the sub-entity's own `local_id` — stable across a
 * same-item refresh (which is what `open`, from the caller's per-panel tracker, is keyed on), but
 * *not* unique across items (a different item can reuse the same local id), which is why
 * `itemPreviewManager.ts` resets its per-panel tracker on every navigation to a different item
 * rather than keying trackers by local id alone. */
function buildSubEntityHtml(
  entity: SqSubEntity,
  currentId: string | undefined,
  roles: RoleDirectory | undefined,
  open: boolean,
  fields: SubEntityFieldContext,
  ids: ItemIdMatcher | undefined,
  items: ItemDirectory | undefined,
): string {
  const header =
    `<div class="sq-subentity-header"><span class="sq-subentity-id">${escapeHtml(entity.local_id)}</span>` +
    `<span class="sq-subentity-title">${escapeHtml(entity.title)}</span></div>`;
  const head = `<div class="sq-subentity-head">${buildSubEntityHeadLine(entity, fields)}</div>`;
  const openAttr = open ? ' open' : '';
  const body =
    entity.body.trim() === ''
      ? ''
      : `<details class="sq-subentity-body" data-sq-fold-id="${escapeHtml(entity.local_id)}"${openAttr}><summary>Body</summary>${renderMarkdownToHtml(entity.body, currentId, false, roles, ids, items)}</details>`;
  const discussion = buildSubEntityDiscussionHtml(entity.discussion, currentId, roles, ids, items);
  return `<div class="sq-subentity">${header}${head}${body}${discussion}</div>`;
}

/** The collapsible sub-entities section: a feature's stories, a task's subtasks, a review's
 * findings — in `sq show <id> --json`'s `subentities` array order. Mirrors `buildDiscussionHtml`'s
 * failure/empty/populated shape, including the `roles` pass-through for `@<slug>` mentions.
 * `isBodyOpen` restores a sub-entity body fold's prior open/closed state across a same-item
 * refresh; the wrapper `<details>` this function renders always stays `open` regardless.
 * `fields` labels each sub-entity's declared badge fields — see `SubEntityFieldContext`. */
export function buildSubEntitiesHtml(
  outcome: SubEntitiesOutcome,
  currentId?: string,
  roles?: RoleDirectory,
  isBodyOpen: (localId: string) => boolean = () => false,
  fields: SubEntityFieldContext = {},
  ids?: ItemIdMatcher,
  items?: ItemDirectory,
): string {
  if (outcome.entities === null) {
    return (
      `<details class="sq-graph" open><summary>Sub-entities</summary>` +
      `<p class="sq-graph-empty">${escapeHtml(outcome.message ?? 'No data available.')}</p></details>`
    );
  }
  if (outcome.entities.length === 0) {
    return '';
  }
  const entries = outcome.entities
    .map((entity) =>
      buildSubEntityHtml(entity, currentId, roles, isBodyOpen(entity.local_id), fields, ids, items),
    )
    .join('\n');
  const count = String(outcome.entities.length);
  return `<details class="sq-graph" open><summary>Sub-entities (${count})</summary>${entries}</details>`;
}

/** The in-content back/forward/refresh toolbar (see `previewMessages.ts`'s module doc for why it
 * exists instead of a native title-bar button) and, doubling as it, the item's title bar
 * (`titleText` — `renderOutcomeHtml`'s extracted heading, or the item id as a fallback). Pinned
 * to the top of the preview's viewport (`.sq-nav-toolbar`'s `position: fixed` in
 * `PREVIEW_STYLES` — see that rule's comment for the spacer it pairs with). A real `disabled`
 * attribute at either end of history, so the browser itself dims/inerts the button with no
 * CSS-only state to keep in sync; `itemPreviewManager.ts`'s `render` recomputes
 * `canGoBack`/`canGoForward` from the panel's current history on every render, so this never goes
 * stale. The refresh button posts a `RefreshMessage` and is styled as a sibling of the arrow
 * buttons with no disabled state — unlike the arrows, refreshing is always valid. Buttons are
 * plain glyphs; `title`/`aria-label` carry the text for hover/screen readers. */
export function buildHistoryToolbarHtml(
  titleText: string,
  canGoBack: boolean,
  canGoForward: boolean,
): string {
  const refresh = `<button type="button" class="sq-nav-button" data-sq-refresh title="Refresh" aria-label="Refresh">&#8635;</button>`;
  const back = `<button type="button" class="sq-nav-button" data-sq-nav="back"${canGoBack ? '' : ' disabled'} title="Back" aria-label="Back">&#8592;</button>`;
  const forward = `<button type="button" class="sq-nav-button" data-sq-nav="forward"${canGoForward ? '' : ' disabled'} title="Forward" aria-label="Forward">&#8594;</button>`;
  const escapedTitle = escapeHtml(titleText);
  const title = `<span class="sq-nav-title" title="${escapedTitle}">${escapedTitle}</span>`;
  return (
    `<div class="sq-nav-toolbar">${title}<div class="sq-nav-buttons">${refresh}${back}${forward}</div></div>` +
    `<div class="sq-nav-toolbar-spacer"></div>`
  );
}

export interface PreviewDocumentParams {
  readonly title: string;
  /** Pre-rendered markup for the in-content back/forward toolbar (`buildHistoryToolbarHtml`),
   * positioned above everything else in `<article>` — `''` for a document with no navigation
   * history (the workflow cheatsheet panel, which isn't an item). */
  readonly toolbarHtml: string;
  /** The dossier's metadata header fragment (title + bullet list, full and untruncated — a
   * plain-text *copy* of just the heading also appears in `toolbarHtml`'s compact title slot,
   * see `renderOutcomeHtml`) — rendered above the graph sections. Empty when there's no
   * detectable header (e.g. a failure message; see `splitDossierMarkdown`), in which case the
   * graphs simply sit at the top of `<article>`. */
  readonly headerHtml: string;
  /** The dossier's prose-body fragment, rendered below the graph sections. */
  readonly bodyHtml: string;
  readonly nonce: string;
  /** The bundled mermaid renderer's webview uri (`itemPreviewManager.ts` resolves this via
   * `webview.asWebviewUri` against a `media/`-scoped `localResourceRoots`) — loaded through a
   * nonce'd `<script src>` tag, same as every other script on this page; no CDN, no
   * `node_modules` shipped, see `scripts/copy-mermaid.js`. */
  readonly mermaidScriptUri: string;
  /** Pre-rendered `<details>` markup for the two graph sections (`buildGraphsHtml`) —
   * positioned between `headerHtml` and `bodyHtml`, directly under the metadata header and
   * above the prose body, rather than after it. */
  readonly graphsHtml: string;
  /** Pre-rendered markup for the sub-entities section (`buildSubEntitiesHtml`, possibly `''` —
   * no sub-entities), appended after `bodyHtml` and before `discussionHtml`. */
  readonly subEntitiesHtml: string;
  /** Pre-rendered `<details>` markup for the discussion section (`buildDiscussionHtml`,
   * possibly `''` — no comments yet), appended after `subEntitiesHtml`. */
  readonly discussionHtml: string;
}

/** The `<article>` mount point's inner HTML. Shared by `buildPreviewHtml` (a fresh load) and
 * `itemPreviewManager.ts`'s same-item-refresh `UpdateContentMessage` (a DOM patch) so the two are
 * always byte-identical — including the toolbar's enabled/disabled state, since the caller
 * recomputes `toolbarHtml` from the current history on every render, patch included. */
export function buildArticleHtml(
  toolbarHtml: string,
  headerHtml: string,
  graphsHtml: string,
  bodyHtml: string,
): string {
  return `${toolbarHtml}\n${headerHtml}\n${graphsHtml}\n${bodyHtml}`;
}

/** The complete `<!DOCTYPE html>` document set as the panel's `webview.html`. The three mount
 * points (`#sq-article`, `#sq-subentities`, `#sq-discussion`) are what `clientScript`'s
 * `updateCommand` handler patches on a same-item refresh — stable ids so that path never has to
 * touch anything outside them (the `<head>`, the CSP, the loaded scripts, all untouched, since
 * the page itself never reloads for that path). */
export function buildPreviewHtml(params: PreviewDocumentParams): string {
  const csp = [
    "default-src 'none'",
    `style-src 'nonce-${params.nonce}'`,
    `script-src 'nonce-${params.nonce}'`,
  ].join('; ');

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${escapeHtml(params.title)}</title>
<style nonce="${params.nonce}">${PREVIEW_STYLES}</style>
</head>
<body>
<article id="${ARTICLE_MOUNT_ID}">${buildArticleHtml(params.toolbarHtml, params.headerHtml, params.graphsHtml, params.bodyHtml)}</article>
<div id="${SUBENTITIES_MOUNT_ID}">${params.subEntitiesHtml}</div>
<div id="${DISCUSSION_MOUNT_ID}">${params.discussionHtml}</div>
<script nonce="${params.nonce}" src="${params.mermaidScriptUri}"></script>
<script nonce="${params.nonce}">${clientScript(OPEN_ITEM_COMMAND, UPDATE_CONTENT_COMMAND, NAVIGATE_HISTORY_COMMAND, REFRESH_COMMAND, TOGGLE_FOLD_COMMAND)}
${mermaidRenderScript(params.nonce)}</script>
</body>
</html>`;
}
