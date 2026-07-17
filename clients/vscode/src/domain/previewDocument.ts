/**
 * Assembles the full webview HTML document for an item preview: a strict, self-contained
 * CSP (no remote content, no `unsafe-inline` — both the `<style>` and `<script>` tags carry
 * the same per-render nonce), the rendered dossier body, and the inline client script that
 * intercepts clicks on `a.sq-item-link` and posts them back to the extension host.
 *
 * Kept `vscode`-free/pure — `nonce` and `cspSource` are passed in rather than computed here,
 * so this (and the markdown rendering it wraps) is unit-testable with no host; only
 * `itemPreviewManager.ts` touches the real `vscode.WebviewPanel` API.
 */
import type { SqOutcome } from '../sqAdapter';
import { escapeHtml, renderMarkdownToHtml } from './markdown';
import { OPEN_ITEM_COMMAND } from './previewMessages';

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

export interface PreviewDocumentParams {
  readonly title: string;
  readonly bodyHtml: string;
  readonly nonce: string;
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
<script nonce="${params.nonce}">${clientScript(OPEN_ITEM_COMMAND)}</script>
</body>
</html>`;
}
