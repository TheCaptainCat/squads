import { describe, expect, it } from 'vitest';

import { buildPreviewHtml, renderOutcomeHtml } from '../src/domain/previewDocument';
import { OPEN_ITEM_COMMAND } from '../src/domain/previewMessages';

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
  const html = buildPreviewHtml({ title: 'TASK-452', bodyHtml: '<p>hello</p>', nonce: 'abc123' });

  it('locks the CSP down to the render nonce, no remote content, no unsafe-inline', () => {
    expect(html).toContain(
      "Content-Security-Policy\" content=\"default-src 'none'; style-src 'nonce-abc123'; script-src 'nonce-abc123'\"",
    );
    expect(html).not.toContain('unsafe-inline');
    expect(html).not.toContain('http://');
    expect(html).not.toContain('https://');
  });

  it('stamps the same nonce on both the style and script tags', () => {
    expect(html).toContain('<style nonce="abc123">');
    expect(html).toContain('<script nonce="abc123">');
  });

  it('embeds the rendered body once', () => {
    expect(html.match(/<p>hello<\/p>/g)).toHaveLength(1);
  });

  it('escapes the title', () => {
    const withUnsafeTitle = buildPreviewHtml({ title: '<x>', bodyHtml: '', nonce: 'n' });
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
});
