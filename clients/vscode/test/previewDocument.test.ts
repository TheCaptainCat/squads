import { describe, expect, it } from 'vitest';

import {
  buildDiscussionHtml,
  buildGraphsHtml,
  buildPreviewHtml,
  type DiscussionOutcome,
  type GraphOutcome,
  renderOutcomeHtml,
  renderWorkflowHtml,
} from '../src/domain/previewDocument';
import { OPEN_ITEM_COMMAND } from '../src/domain/previewMessages';

const MERMAID_URI = 'vscode-webview://abc/media/mermaid.min.js';
const NO_GRAPHS = buildGraphsHtml(
  { mermaidSource: null, message: 'none' },
  { mermaidSource: null, message: 'none' },
);
const NO_DISCUSSION = buildDiscussionHtml({ entries: [] });

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

describe('renderWorkflowHtml', () => {
  it('renders the raw sq workflow --raw text as HTML on success', () => {
    const html = renderWorkflowHtml({
      kind: 'success',
      data: '## Team workflow\n\nSome prose.',
    });
    expect(html).toContain('<h2>');
    expect(html).toContain('Some prose.');
  });

  it('renders a fenced mermaid diagram live, not as plain code (unlike the item dossier path)', () => {
    const html = renderWorkflowHtml({
      kind: 'success',
      data: '```mermaid\nflowchart TD\n  A --> B\n```',
    });
    expect(html).toContain('class="sq-graph-source"');
    expect(html).not.toContain('language-mermaid');
  });

  it('renders an actionable message on failure instead of blank/stale content', () => {
    const html = renderWorkflowHtml({
      kind: 'runtime-error',
      message: 'Schema mismatch: run `sq migrate up`.',
      exitCode: 1,
    });
    expect(html).toContain('Squads: unable to load the workflow cheatsheet');
    expect(html).toContain('Schema mismatch');
  });
});

describe('buildPreviewHtml', () => {
  const html = buildPreviewHtml({
    title: 'TASK-452',
    bodyHtml: '<p>hello</p>',
    graphsHtml: NO_GRAPHS,
    discussionHtml: NO_DISCUSSION,
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

  it('embeds the discussion section after the graph sections', () => {
    const withDiscussion = buildPreviewHtml({
      title: 'TASK-452',
      bodyHtml: '<p>hello</p>',
      graphsHtml: NO_GRAPHS,
      discussionHtml: buildDiscussionHtml({
        entries: [{ author: 'Ada Typescript', ts: '2026-07-17T00:00:00Z', body: 'A comment.' }],
      }),
      mermaidScriptUri: MERMAID_URI,
      nonce: 'abc123',
    });
    const lastGraphIndex = withDiscussion.lastIndexOf('Ref Graph');
    const discussionIndex = withDiscussion.indexOf('A comment.');
    expect(lastGraphIndex).toBeGreaterThan(-1);
    expect(discussionIndex).toBeGreaterThan(lastGraphIndex);
  });

  it('escapes the title', () => {
    const withUnsafeTitle = buildPreviewHtml({
      title: '<x>',
      bodyHtml: '',
      graphsHtml: '',
      discussionHtml: '',
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

  it('renders every .sq-graph-source generically (data-output-id lookup), not a fixed pair', () => {
    // Regression guard: the render script must scan by class/attribute, not a hardcoded
    // two-section list, so it also covers however many inline mermaid fences a document's own
    // markdown carries (e.g. the workflow cheatsheet).
    expect(html).toContain("querySelectorAll('.sq-graph-source')");
    expect(html).toContain("getAttribute('data-output-id')");
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

  it('gives each source element a data-output-id pointing at its own output element', () => {
    const html = buildGraphsHtml(withSource, withSource);
    expect(html.match(/data-output-id="sq-children-graph"/g)).toHaveLength(1);
    expect(html.match(/data-output-id="sq-refs-graph"/g)).toHaveLength(1);
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

describe('buildDiscussionHtml', () => {
  const twoComments: DiscussionOutcome = {
    entries: [
      { author: 'Elias Python', ts: '2026-07-16T18:14:07Z', body: '- First comment.' },
      { author: 'Ada Typescript', ts: '2026-07-16T18:19:50Z', body: '- Second **comment**.' },
    ],
  };

  it('renders no section at all when there is no discussion yet (graceful)', () => {
    expect(buildDiscussionHtml({ entries: [] })).toBe('');
  });

  it('renders one collapsible <details> section holding every comment', () => {
    const html = buildDiscussionHtml(twoComments);
    expect(html.match(/<details class="sq-graph" open>/g)).toHaveLength(1);
    expect(html).toContain('Discussion (2)');
  });

  it('renders each comment as an author + ISO-timestamp header, then its markdown body', () => {
    const html = buildDiscussionHtml(twoComments);
    expect(html).toContain('Elias Python');
    expect(html).toContain('2026-07-16T18:14:07Z');
    expect(html).toContain('Ada Typescript');
    expect(html).toContain('2026-07-16T18:19:50Z');
    // Bodies render through the same markdown renderer the dossier body uses.
    expect(html).toContain('<li>First comment.</li>');
    expect(html).toContain('<li>Second <strong>comment</strong>.</li>');
  });

  it('preserves discussion order (oldest first, as sq show --json emits it)', () => {
    const html = buildDiscussionHtml(twoComments);
    expect(html.indexOf('Elias Python')).toBeLessThan(html.indexOf('Ada Typescript'));
  });

  it('escapes the author and timestamp', () => {
    const html = buildDiscussionHtml({
      entries: [{ author: '<script>', ts: '2026-01-01T00:00:00Z', body: 'hi' }],
    });
    expect(html).toContain('&lt;script&gt;');
    expect(html).not.toContain('<script>');
  });

  it('suppresses a self-link when a comment mentions the current item id', () => {
    const html = buildDiscussionHtml(
      { entries: [{ author: 'a', ts: '2026-01-01T00:00:00Z', body: 'see TASK-452' }] },
      'TASK-452',
    );
    expect(html).toContain('TASK-452');
    expect(html).not.toContain('data-item-id="TASK-452"');
  });

  it('links a different item id mentioned in a comment', () => {
    const html = buildDiscussionHtml(
      { entries: [{ author: 'a', ts: '2026-01-01T00:00:00Z', body: 'see TASK-100' }] },
      'TASK-452',
    );
    expect(html).toContain('data-item-id="TASK-100"');
  });

  it('shows a failure message in place of the section on a failed fetch (never silently blank)', () => {
    const html = buildDiscussionHtml({ entries: null, message: 'sq show --json failed: boom' });
    expect(html).toContain('sq show --json failed: boom');
    expect(html).toContain('<details class="sq-graph" open><summary>Discussion</summary>');
  });
});
