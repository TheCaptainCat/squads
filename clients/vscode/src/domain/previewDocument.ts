/**
 * Assembles the full webview HTML document for an item preview: a strict, self-contained
 * CSP (no remote content, no `unsafe-inline` — both the `<style>` and `<script>` tags carry
 * the same per-render nonce), the rendered dossier body, the two collapsible mermaid graph
 * sections, and the inline client script that both intercepts clicks on `a.sq-item-link`
 * (posting them back to the extension host) and renders the graphs' mermaid source via the
 * bundled renderer.
 *
 * Kept `vscode`-free/pure — `nonce` and the mermaid script's webview uri are passed in rather
 * than computed here, so this (and the markdown rendering it wraps) is unit-testable with no
 * host; only `itemPreviewManager.ts` touches the real `vscode.WebviewPanel` API.
 */
import type { SqOutcome } from '../sqAdapter';
import { escapeHtml, renderMarkdownToHtml } from './markdown';
import { OPEN_ITEM_COMMAND } from './previewMessages';

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
details.sq-graph .sq-graph-output svg {
  max-width: 100%;
  height: auto;
}
`;

/** Delegated click/auxclick handling for `a.sq-item-link`: a plain click (or ctrl/cmd-click)
 * requests same-panel navigation; a middle-click (`auxclick`, button 1) requests a new panel.
 * `%s` is substituted with the shared `OPEN_ITEM_COMMAND` constant so the wire format can
 * never drift from what `previewMessages.ts`'s `parseOpenItemMessage` accepts. */
function clientScript(command: string): string {
  return `(function () {
  const vscode = acquireVsCodeApi();
  function post(event, newTab) {
    const target = event.target.closest('a.sq-item-link');
    if (!target) { return; }
    event.preventDefault();
    const id = target.getAttribute('data-item-id');
    if (!id) { return; }
    vscode.postMessage({ command: '${command}', id: id, newTab: newTab });
  }
  document.addEventListener('click', function (event) {
    if (event.button !== 0) { return; }
    post(event, event.ctrlKey || event.metaKey);
  });
  document.addEventListener('auxclick', function (event) {
    if (event.button !== 1) { return; }
    post(event, true);
  });
})();`;
}

/** Renders every `.sq-graph-source` element's mermaid text into its paired output `<div>`,
 * using the mermaid renderer loaded by the preceding `<script src>` tag (global `mermaid`).
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
 */
function mermaidRenderScript(nonce: string): string {
  return `(function () {
  if (typeof mermaid === 'undefined') { return; }
  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
  var nonce = '${nonce}';
  var sections = [
    { source: '${CHILDREN_GRAPH_SOURCE_ID}', output: '${CHILDREN_GRAPH_OUTPUT_ID}' },
    { source: '${REFS_GRAPH_SOURCE_ID}', output: '${REFS_GRAPH_OUTPUT_ID}' },
  ];
  sections.forEach(function (section, index) {
    var sourceEl = document.getElementById(section.source);
    var outputEl = document.getElementById(section.output);
    if (!sourceEl || !outputEl) { return; }
    var text = sourceEl.textContent || '';
    if (!text.trim()) { return; }
    mermaid.render('sq-mermaid-render-' + String(index), text).then(function (result) {
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
      outputEl.replaceChildren(document.importNode(svgEl, true));
    }).catch(function () {
      outputEl.textContent = 'Failed to render diagram.';
    });
  });
})();`;
}

/** Renders an `sq show <id> --raw` outcome to the HTML fragment shown in the panel body. On
 * failure this returns an actionable message (never blank/stale content) — the caller is
 * still responsible for firing the accompanying VS Code notification. */
export function renderOutcomeHtml(id: string, outcome: SqOutcome<string>): string {
  const markdown =
    outcome.kind === 'success'
      ? outcome.data
      : `# Squads: unable to load ${id}\n\n${outcome.message}`;
  return renderMarkdownToHtml(markdown, id);
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
 * that part. When `mermaidSource` is present the hidden `<pre>` holds the escaped diagram
 * source the client script reads via `textContent` (so it comes back out unescaped) and
 * renders into the adjacent output `<div>`; otherwise the message stands in for it. */
function buildGraphSection(spec: GraphSectionSpec): string {
  const inner =
    spec.outcome.mermaidSource === null
      ? `<p class="sq-graph-empty">${escapeHtml(spec.outcome.message ?? 'No data available.')}</p>`
      : `<pre class="sq-graph-source" id="${spec.sourceId}" hidden>${escapeHtml(spec.outcome.mermaidSource)}</pre><div class="sq-graph-output" id="${spec.outputId}">Rendering…</div>`;
  return `<details class="sq-graph" open><summary>${escapeHtml(spec.title)}</summary>${inner}</details>`;
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

export interface PreviewDocumentParams {
  readonly title: string;
  readonly bodyHtml: string;
  readonly nonce: string;
  /** The bundled mermaid renderer's webview uri (`itemPreviewManager.ts` resolves this via
   * `webview.asWebviewUri` against a `media/`-scoped `localResourceRoots`) — loaded through a
   * nonce'd `<script src>` tag, same as every other script on this page; no CDN, no
   * `node_modules` shipped, see `scripts/copy-mermaid.js`. */
  readonly mermaidScriptUri: string;
  /** Pre-rendered `<details>` markup for the two graph sections (`buildGraphsHtml`) — kept
   * separate from `bodyHtml` (the dossier) both visually and in the DOM. */
  readonly graphsHtml: string;
}

/** The complete `<!DOCTYPE html>` document set as the panel's `webview.html`. */
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
<article>${params.bodyHtml}</article>
${params.graphsHtml}
<script nonce="${params.nonce}" src="${params.mermaidScriptUri}"></script>
<script nonce="${params.nonce}">${clientScript(OPEN_ITEM_COMMAND)}
${mermaidRenderScript(params.nonce)}</script>
</body>
</html>`;
}
