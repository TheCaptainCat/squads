import { describe, expect, it } from 'vitest';

import {
  buildGraphsHtml,
  buildPreviewHtml,
  type GraphOutcome,
  renderOutcomeHtml,
} from '../src/domain/previewDocument';
import { OPEN_ITEM_COMMAND } from '../src/domain/previewMessages';

const MERMAID_URI = 'vscode-webview://abc/media/mermaid.min.js';
const NO_GRAPHS = buildGraphsHtml(
  { mermaidSource: null, message: 'none' },
  { mermaidSource: null, message: 'none' },
);

describe('renderOutcomeHtml', () => {
  it('renders the raw sq show --raw text as HTML on success', () => {
    const html = renderOutcomeHtml('TASK-452', {
      kind: 'success',
      data: '# TASK-452 — Title\n\nBody.',
    });
    expect(html).toContain('<h1>');
    expect(html).toContain('Body.');
  });

  it('renders an actionable message on failure instead of blank/stale content', () => {
    const html = renderOutcomeHtml('TASK-452', {
      kind: 'runtime-error',
      message: 'Schema mismatch: run `sq migrate up`.',
      exitCode: 1,
    });
    expect(html).toContain('Squads: unable to load TASK-452');
    expect(html).toContain('Schema mismatch');
  });
});

describe('buildPreviewHtml', () => {
  const html = buildPreviewHtml({
    title: 'TASK-452',
    bodyHtml: '<p>hello</p>',
    graphsHtml: NO_GRAPHS,
    mermaidScriptUri: MERMAID_URI,
    nonce: 'abc123',
  });

  it('locks the CSP down to the render nonce, no remote content, no unsafe-inline', () => {
    expect(html).toContain(
      "Content-Security-Policy\" content=\"default-src 'none'; style-src 'nonce-abc123'; script-src 'nonce-abc123'\"",
    );
    expect(html).not.toContain('unsafe-inline');
    expect(html).not.toContain('unsafe-eval');
    expect(html).not.toContain('http://');
    expect(html).not.toContain('https://');
  });

  it('stamps the same nonce on the style tag and both script tags', () => {
    expect(html).toContain('<style nonce="abc123">');
    expect(html.match(/<script nonce="abc123"/g)).toHaveLength(2);
  });

  it('loads the bundled mermaid renderer via a nonce-carrying script src (no CDN)', () => {
    expect(html).toContain(`<script nonce="abc123" src="${MERMAID_URI}"></script>`);
  });

  it('embeds the rendered body once', () => {
    expect(html.match(/<p>hello<\/p>/g)).toHaveLength(1);
  });

  it('embeds the graph sections after the dossier body, not inside it', () => {
    const articleEnd = html.indexOf('</article>');
    const graphsIndex = html.indexOf('class="sq-graph"');
    expect(articleEnd).toBeGreaterThan(-1);
    expect(graphsIndex).toBeGreaterThan(articleEnd);
  });

  it('escapes the title', () => {
    const withUnsafeTitle = buildPreviewHtml({
      title: '<x>',
      bodyHtml: '',
      graphsHtml: '',
      mermaidScriptUri: MERMAID_URI,
      nonce: 'n',
    });
    expect(withUnsafeTitle).toContain('<title>&lt;x&gt;</title>');
  });

  it('posts the same command constant the host-side parser accepts', () => {
    expect(html).toContain(`command: '${OPEN_ITEM_COMMAND}'`);
  });

  it('intercepts a plain click and a middle-click distinctly (newTab true/false)', () => {
    expect(html).toContain('post(event, event.ctrlKey || event.metaKey)');
    expect(html).toContain('post(event, true)');
    expect(html).toContain("addEventListener('click'");
    expect(html).toContain("addEventListener('auxclick'");
  });

  it('stamps the mermaid render nonce onto every style tag found in a rendered svg', () => {
    expect(html).toContain("styles[i].setAttribute('nonce', nonce)");
    expect(html).toContain('mermaid.initialize');
  });
});

describe('buildGraphsHtml', () => {
  const withSource: GraphOutcome = { mermaidSource: 'flowchart TD\n  A["a"]' };
  const withoutSource: GraphOutcome = { mermaidSource: null, message: 'sq graph failed: boom' };

  it('renders each graph as its own independently-foldable <details> section', () => {
    const html = buildGraphsHtml(withSource, withSource);
    expect(html.match(/<details class="sq-graph" open>/g)).toHaveLength(2);
    expect(html).toContain('Children / Subtree');
    expect(html).toContain('Ref Graph');
  });

  it('hides the mermaid source in the DOM (client script reads it, user never sees raw text)', () => {
    const html = buildGraphsHtml(withSource, withSource);
    expect(html).toContain('class="sq-graph-source"');
    expect(html).toContain('hidden>flowchart TD');
  });

  it('escapes the embedded mermaid source', () => {
    const html = buildGraphsHtml({ mermaidSource: 'A["<script>"]' }, withSource);
    expect(html).toContain('A[&quot;&lt;script&gt;&quot;]');
    expect(html).not.toContain('<script>"');
  });

  it('shows the failure message in place of a diagram, section still present', () => {
    const html = buildGraphsHtml(withoutSource, withoutSource);
    expect(html).toContain('sq graph failed: boom');
    expect(html).not.toContain('class="sq-graph-source"');
    expect(html.match(/<details class="sq-graph" open>/g)).toHaveLength(2);
  });
});
