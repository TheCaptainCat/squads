/**
 * Assembles the full webview HTML document for an item preview: a strict, self-contained
 * CSP (no remote content, no `unsafe-inline` — both the `<style>` and `<script>` tags carry
 * the same per-render nonce), the rendered dossier body, the two collapsible mermaid graph
 * sections, the collapsible sub-entities section (F15, `buildSubEntitiesHtml`, built from
 * `sq show <id> --json`'s `subentities` array), the collapsible discussion/comments section
 * (F14, `buildDiscussionHtml`, built from the same call's `discussion` array), and the inline
 * client script that both intercepts clicks on `a.sq-item-link` (posting them back to the
 * extension host) and renders the graphs' mermaid source via the bundled renderer.
 *
 * Kept `vscode`-free/pure — `nonce` and the mermaid script's webview uri are passed in rather
 * than computed here, so this (and the markdown rendering it wraps) is unit-testable with no
 * host; only `itemPreviewManager.ts` touches the real `vscode.WebviewPanel` API.
 */
import type { SqOutcome } from '../sqAdapter';
import type { SqDiscussionEntry, SqSubEntity } from '../types';
import { escapeHtml, renderMarkdownToHtml } from './markdown';
import {
  NAVIGATE_HISTORY_COMMAND,
  OPEN_ITEM_COMMAND,
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

/** Delegated click/auxclick handling for both `a.sq-item-link` (dossier/comment/sub-entity
 * body links — including a resolved `@<slug>` role mention, which carries the role item's id
 * in the same attribute) and `g.node[data-item-id]` (a rendered graph node — F25, the attribute
 * stamped post-render by `mermaidRenderScript`): a plain click (or ctrl/cmd-click) requests
 * same-panel navigation; a middle-click (`auxclick`, button 1) requests a new panel. Both
 * element kinds carry the target id in the same `data-item-id` attribute, so one selector/lookup
 * handles either — no new message type needed for a role mention. `openCommand` is substituted
 * with the shared `OPEN_ITEM_COMMAND` constant so the wire format can never drift from what
 * `previewMessages.ts`'s `parseOpenItemMessage` accepts.
 *
 * Also delegates clicks on the in-content back/forward toolbar (`[data-sq-nav]`, built by
 * `buildHistoryToolbarHtml`) to `navCommand` (`NAVIGATE_HISTORY_COMMAND`) — checked *before* the
 * link/graph-node handling above since it's a disjoint element kind. A `disabled` button (the
 * end of history — `buildHistoryToolbarHtml` never renders one enabled past that point) doesn't
 * dispatch a click at all in a Chromium webview, but the handler still re-checks `.disabled`
 * defensively rather than relying solely on that platform behavior.
 *
 * Also listens for the host's `updateCommand` message (`UpdateContentMessage`) — a same-item
 * refresh's replacement HTML for the three stable mount points — and patches them in place via
 * `innerHTML` rather than navigating, then re-runs the mermaid render pass
 * (`window.__sqRenderMermaid`, defined by `mermaidRenderScript`) over whatever new
 * `.sq-graph-source` elements just landed. Patching in place (as opposed to reassigning
 * `panel.webview.html`, which reloads the page) is what preserves the reader's scroll
 * position for that path — nothing here calls `scrollTo` for a patch, deliberately: the page
 * never navigates, so the browser's own scroll position is simply never disturbed.
 *
 * Every *fresh* load of this document (a genuine navigation — `itemPreviewManager.ts`'s
 * `'reload'` mode: a new panel, or reusing the panel for a different item) explicitly resets to
 * the top on parse — a real `window.scrollTo(0, 0)` rather than counting on a browser's default
 * fresh-document scroll position, since VS Code's webview host doesn't document that guarantee. */
function clientScript(openCommand: string, updateCommand: string, navCommand: string): string {
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
    post(event, event.ctrlKey || event.metaKey);
  });
  document.addEventListener('auxclick', function (event) {
    if (event.button !== 1) { return; }
    post(event, true);
  });
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

/** Renders every `.sq-graph-source` element's mermaid text into its paired output `<div>`
 * (found via its `data-output-id` attribute — a generic scan, not a fixed list, so it covers
 * both the two structured graph sections and however many inline ```mermaid``` fences a
 * document's own markdown body carries), using the mermaid renderer loaded by the preceding
 * `<script src>` tag (global `mermaid`). `flowchart.wrappingWidth` pairs with
 * `graphDiagrams.ts`'s markdown-string node labels (F24) so a long label wraps onto multiple
 * lines from real text-metric measurement instead of overflowing/cropping at the node's edge.
 *
 * CSP note (kept strict — no `unsafe-inline`/`unsafe-eval` added for this): mermaid's own
 * `render()` builds each diagram by inserting a plain, un-nonced `<style>` tag carrying its
 * generated CSS into the returned SVG markup. Assigning that markup via `innerHTML` as-is
 * would make the browser silently disable that stylesheet under this page's `style-src
 * 'nonce-*'` policy (diagram present, but unstyled). Instead the returned SVG is parsed
 * (detached, via `DOMParser` — no CSP applies to a detached document), this render's nonce is
 * stamped onto every `<style>` found in it, and only then are the resulting *nodes* (not the
 * raw string) inserted into the live document — so the stylesheet already carries a matching
 * nonce the moment it's connected and CSP allows it, with no policy relaxation at all. If a
 * future mermaid version needs something this can't cover, the documented fallback is a
 * narrowly-scoped `style-src 'unsafe-inline'` (never `script-src`) — flagged for review rather
 * than applied speculatively.
 *
 * Node-click wiring (F25): mermaid's `click` directive is disabled under `securityLevel:
 * 'strict'`, so navigation is wired here instead, after render. Every rendered flowchart node
 * gets an `id` of the form `<diagramId>-flowchart-<nodeId>-<n>` (`nodeId` being exactly what
 * `graphDiagrams.ts`'s `mermaidNodeId` produced when building the source) — `nodeId` is
 * recovered from that id and un-sanitized back to the real item id (undoing `mermaidNodeId`'s
 * hyphen->underscore fold; an item id has exactly one such character, so this is lossless),
 * then stamped onto the node as `data-item-id` so `clientScript`'s shared
 * `a.sq-item-link`/`g.node[data-item-id]` click handling picks it up like any other link.
 *
 * Exposed as `window.__sqRenderMermaid` (rather than a run-once IIFE) so `clientScript`'s
 * `updateCommand` handler can re-invoke it after a same-item refresh patches in fresh
 * `.sq-graph-source` elements — the render-id counter (`callSeq`) lives in the enclosing closure
 * so it keeps counting up across every call, not just the initial one, guaranteeing every
 * `mermaid.render` invocation for the life of the page gets its own id. */
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
        var nodes = svgEl.querySelectorAll('.node');
        for (var j = 0; j < nodes.length; j++) {
          var match = nodeIdPattern.exec(nodes[j].getAttribute('id') || '');
          if (!match) { continue; }
          nodes[j].setAttribute('data-item-id', match[1].replace(/_/g, '-'));
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
 * the graph sections injected between them (F23: graphs directly under the metadata header,
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
 * move: the heading stays right where it always was in `headerHtml` too (rendered as a full,
 * never-truncated `<h1>` in the body), since a title truncated down to the toolbar's width would
 * otherwise be the reader's only complete view of it. Plain text out (the toolbar escapes it,
 * and also uses it verbatim as a hover-tooltip `title=` attribute so even the ellipsis'd copy is
 * inspectable), not HTML. Falls back to an empty string when `header` doesn't start with an H1
 * — `renderOutcomeHtml` covers that case with the item id instead, same as it always showed
 * *something* identifying for a header-less dossier. */
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
 * metadata header fragment (title + bullet list, full and untruncated) and the prose body, split
 * by `splitDossierMarkdown` so the caller can inject the graph sections between them (F23) —
 * plus `titleText`, a plain-text copy of just the heading for the sticky toolbar's compact title
 * slot above both (see `extractTitleLine`). On failure the message renders entirely as
 * `bodyHtml` with an empty header and `id` itself as the title (never blank/stale content) — the
 * caller is still responsible for firing the accompanying VS Code notification. `roles`, when
 * given, resolves `@<slug>` mentions found in the dossier body the same way the discussion/
 * sub-entity sections do (see `domain/roleDirectory.ts`). */
export function renderOutcomeHtml(
  id: string,
  outcome: SqOutcome<string>,
  roles?: RoleDirectory,
): DossierHtml {
  if (outcome.kind !== 'success') {
    return {
      titleText: id,
      headerHtml: '',
      bodyHtml: renderMarkdownToHtml(`# Squads: unable to load ${id}\n\n${outcome.message}`, id),
    };
  }
  const { header, body } = splitDossierMarkdown(outcome.data);
  const titleText = extractTitleLine(header);
  return {
    titleText: titleText === '' ? id : titleText,
    headerHtml: renderMarkdownToHtml(header, id),
    bodyHtml: renderMarkdownToHtml(body, id, false, roles),
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
}

/** One collapsible `<details>` graph section — native fold/unfold, no client JS needed for
 * that part. Collapsed by default (F23: no `open` attribute) — a graph is supplementary detail,
 * not something that should push the dossier body below the fold. When `mermaidSource` is
 * present the hidden `<pre>` holds the escaped diagram source the client script reads via
 * `textContent` (so it comes back out unescaped); its `data-output-id` points the generic
 * render script (see `mermaidRenderScript`) at the adjacent output `<div>` it renders into.
 * Otherwise the message stands in for it. */
function buildGraphSection(spec: GraphSectionSpec): string {
  const inner =
    spec.outcome.mermaidSource === null
      ? `<p class="sq-graph-empty">${escapeHtml(spec.outcome.message ?? 'No data available.')}</p>`
      : `<pre class="sq-graph-source" id="${spec.sourceId}" data-output-id="${spec.outputId}" hidden>${escapeHtml(spec.outcome.mermaidSource)}</pre><div class="sq-graph-output" id="${spec.outputId}">Rendering…</div>`;
  return `<details class="sq-graph"><summary>${escapeHtml(spec.title)}</summary>${inner}</details>`;
}

/** The two graph sections (children/subtree, ref graph), each independently collapsible and
 * kept separate from the dossier body and from each other. */
export function buildGraphsHtml(children: GraphOutcome, refs: GraphOutcome): string {
  return [
    buildGraphSection({
      title: 'Children / Subtree',
      sourceId: CHILDREN_GRAPH_SOURCE_ID,
      outputId: CHILDREN_GRAPH_OUTPUT_ID,
      outcome: children,
    }),
    buildGraphSection({
      title: 'Ref Graph',
      sourceId: REFS_GRAPH_SOURCE_ID,
      outputId: REFS_GRAPH_OUTPUT_ID,
      outcome: refs,
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
): string {
  return (
    `<div class="sq-comment"><div class="sq-comment-header">` +
    `<span class="sq-comment-author">${escapeHtml(entry.author)}</span> ` +
    `<span class="sq-comment-ts">${escapeHtml(entry.ts)}</span></div>` +
    `<div class="sq-comment-body">${renderMarkdownToHtml(entry.body, currentId, false, roles)}</div></div>`
  );
}

/** The collapsible discussion/comments section (F14), appended after the dossier body and the
 * graph sections. A failed fetch degrades to an inline failure message inside the same
 * `<details>` shell the graph sections use (consistent styling, never silently blank); a
 * successful fetch with no comments yet renders no section at all — nothing to fold open.
 * `roles`, when given, resolves `@<slug>` role mentions found in a comment's body (see
 * `domain/roleDirectory.ts`). */
export function buildDiscussionHtml(
  outcome: DiscussionOutcome,
  currentId?: string,
  roles?: RoleDirectory,
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
    .map((entry) => buildCommentHtml(entry, currentId, roles))
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

/** The head badge line for one sub-entity — status / severity / assignee / story, each field
 * omitted when absent (`severity`: findings only; `story`: subtasks only). Plain text, not the
 * spec's rendered badge glyph — this preview head doesn't fetch/join the collections catalog
 * (`sq workflow collections --json`) the way the tree tooltip does; shows the raw code, same
 * convention `graphDiagrams.ts` uses for priority. Deliberate; parity with the hover tooltip
 * is a possible follow-up, not required here. */
function buildSubEntityHeadLine(entity: SqSubEntity): string {
  const parts = [`Status: ${escapeHtml(entity.status)}`];
  if (entity.severity !== null) {
    parts.push(`Severity: ${escapeHtml(entity.severity)}`);
  }
  if (entity.assignee !== null) {
    parts.push(`Assignee: ${escapeHtml(entity.assignee)}`);
  }
  if (entity.story !== null) {
    parts.push(`Story: ${escapeHtml(entity.story)}`);
  }
  return parts.join(' · ');
}

/** One sub-entity: its local id + title as a header, the head badge line always visible, and
 * (when it has one) its body as collapsible prose rendered through the same markdown renderer
 * the dossier body and discussion comments use (mermaid-fences off, `currentId` still
 * suppresses a self-link, `roles` resolves any `@<slug>` mention the same way) — a blank body
 * renders no `<details>` at all rather than an empty fold. */
function buildSubEntityHtml(
  entity: SqSubEntity,
  currentId: string | undefined,
  roles: RoleDirectory | undefined,
): string {
  const header =
    `<div class="sq-subentity-header"><span class="sq-subentity-id">${escapeHtml(entity.local_id)}</span>` +
    `<span class="sq-subentity-title">${escapeHtml(entity.title)}</span></div>`;
  const head = `<div class="sq-subentity-head">${buildSubEntityHeadLine(entity)}</div>`;
  const body =
    entity.body.trim() === ''
      ? ''
      : `<details class="sq-subentity-body"><summary>Body</summary>${renderMarkdownToHtml(entity.body, currentId, false, roles)}</details>`;
  return `<div class="sq-subentity">${header}${head}${body}</div>`;
}

/** The collapsible sub-entities section (F15): a feature's stories, a task's subtasks, a
 * review's findings — in `sq show <id> --json`'s `subentities` array order. Mirrors
 * `buildDiscussionHtml`'s failure/empty/populated shape exactly, including the `roles`
 * pass-through for `@<slug>` mentions in a sub-entity's body. */
export function buildSubEntitiesHtml(
  outcome: SubEntitiesOutcome,
  currentId?: string,
  roles?: RoleDirectory,
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
    .map((entity) => buildSubEntityHtml(entity, currentId, roles))
    .join('\n');
  const count = String(outcome.entities.length);
  return `<details class="sq-graph" open><summary>Sub-entities (${count})</summary>${entries}</details>`;
}

/** The in-content back/forward toolbar: VS Code's `editor/title/navigation` menu
 * doesn't reliably surface inline buttons for a plain `createWebviewPanel` panel — confirmed by
 * screenshot in the extension dev host, not just by reading the docs — so this rendered-in-page
 * toolbar is the primary back/forward control (the `alt+left`/`alt+right` keybindings remain a
 * secondary path to the same commands). A real `disabled` attribute at either end of history, so
 * the browser itself dims and inert-s the button — no separate CSS-only "looks disabled" state
 * to keep in sync. `itemPreviewManager.ts`'s `render` recomputes `canGoBack`/`canGoForward` from
 * the panel's current `PreviewHistory` on every render (both `'reload'` and `'patch'`), so this
 * never goes stale relative to the history it reflects.
 *
 * Doubles as the item's title bar (`titleText` — `renderOutcomeHtml`'s extracted heading, or
 * the item id as a fallback): pinned to the top of the preview's own viewport as the reader
 * scrolls (`position: fixed` in `PREVIEW_STYLES`'s `.sq-nav-toolbar` rule — see that rule's
 * comment for why `fixed`, not `sticky`), reading `title … ←  →`, title on the left (truncating
 * with an ellipsis rather than shoving the buttons off — `.sq-nav-title`'s `text-overflow`), nav
 * on the right. The buttons are plain arrow glyphs, not text — `title`/`aria-label` still carry
 * "Back"/"Forward" for the hover tooltip and screen readers, so the control stays discoverable
 * without a text label competing for the toolbar's limited width. The trailing
 * `.sq-nav-toolbar-spacer` reserves the fixed bar's height in the normal document flow, so the
 * graphs/body/etc. that follow don't render underneath it. */
export function buildHistoryToolbarHtml(
  titleText: string,
  canGoBack: boolean,
  canGoForward: boolean,
): string {
  const back = `<button type="button" class="sq-nav-button" data-sq-nav="back"${canGoBack ? '' : ' disabled'} title="Back" aria-label="Back">&#8592;</button>`;
  const forward = `<button type="button" class="sq-nav-button" data-sq-nav="forward"${canGoForward ? '' : ' disabled'} title="Forward" aria-label="Forward">&#8594;</button>`;
  const escapedTitle = escapeHtml(titleText);
  const title = `<span class="sq-nav-title" title="${escapedTitle}">${escapedTitle}</span>`;
  return (
    `<div class="sq-nav-toolbar">${title}<div class="sq-nav-buttons">${back}${forward}</div></div>` +
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
   * see `renderOutcomeHtml`) — rendered above the graph sections, per F23. Empty when there's no
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
  /** Pre-rendered `<details>` markup for the two graph sections (`buildGraphsHtml`) — F23:
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

/** The `<article>` mount point's inner HTML — the back/forward toolbar, then header + graphs +
 * body, in F23's fixed order (toolbar first). Shared by `buildPreviewHtml` (a fresh
 * load) and `itemPreviewManager.ts`'s same-item-refresh `UpdateContentMessage` (a DOM patch) so
 * the two are always byte-identical: a refresh never shows different content than a fresh load
 * of the same dossier would — including the toolbar's enabled/disabled state, since the caller
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
<script nonce="${params.nonce}">${clientScript(OPEN_ITEM_COMMAND, UPDATE_CONTENT_COMMAND, NAVIGATE_HISTORY_COMMAND)}
${mermaidRenderScript(params.nonce)}</script>
</body>
</html>`;
}
