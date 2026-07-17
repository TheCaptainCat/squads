import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import { ITEM_ID_PATTERN, linkifyPlainText, renderMarkdownToHtml } from '../src/domain/markdown';

function fixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

describe('ITEM_ID_PATTERN / linkifyPlainText', () => {
  it('matches a formatted item id but not a bare sub-entity local id', () => {
    expect('TASK-452'.replace(ITEM_ID_PATTERN, 'X')).toBe('X');
    expect('F9'.replace(ITEM_ID_PATTERN, 'X')).toBe('F9');
    expect('US1'.replace(ITEM_ID_PATTERN, 'X')).toBe('US1');
  });

  it('wraps every match in a data-item-id anchor', () => {
    const html = linkifyPlainText('see ADR-427 and TASK-452');
    expect(html).toContain('<a class="sq-item-link" href="#" data-item-id="ADR-427">ADR-427</a>');
    expect(html).toContain('<a class="sq-item-link" href="#" data-item-id="TASK-452">TASK-452</a>');
  });

  it('leaves currentId as plain text (no self-link)', () => {
    const html = linkifyPlainText('TASK-452 refers to ADR-427', 'TASK-452');
    expect(html).not.toContain('data-item-id="TASK-452"');
    expect(html).toContain('data-item-id="ADR-427"');
    expect(html.startsWith('TASK-452')).toBe(true);
  });

  it('escapes HTML-significant characters', () => {
    expect(linkifyPlainText('<script>&"\'')).toBe('&lt;script&gt;&amp;&quot;&#39;');
  });
});

describe('renderMarkdownToHtml', () => {
  it('renders headings, a metadata bullet list, and a paragraph', () => {
    const html = renderMarkdownToHtml('# TASK-452 — Title\n\n- **status:** Ready\n\nBody text.');
    expect(html).toContain('<h1>');
    expect(html).toContain('<ul><li><strong>status:</strong> Ready</li></ul>');
    expect(html).toContain('<p>Body text.</p>');
  });

  it('linkifies item ids found inside a metadata bullet, including inside bold text', () => {
    const html = renderMarkdownToHtml('- **refs:** ADR-427 (addresses), TASK-434 (depends-on)');
    expect(html).toContain('data-item-id="ADR-427"');
    expect(html).toContain('data-item-id="TASK-434"');
  });

  it('renders a fenced code block verbatim, escaped, with no linkification', () => {
    const html = renderMarkdownToHtml('```\nADR-427\n```');
    expect(html).toBe('<pre><code>ADR-427</code></pre>');
  });

  it('tags a fenced code block with its language class (mermaid renders as plain code — a later task)', () => {
    const html = renderMarkdownToHtml('```mermaid\ngraph TD;\n```');
    expect(html).toBe('<pre><code class="language-mermaid">graph TD;</code></pre>');
  });

  it('renders inline code without linkifying ids inside it', () => {
    const html = renderMarkdownToHtml('Run `sq show TASK-452 --raw` to see it.');
    expect(html).toContain('<code>sq show TASK-452 --raw</code>');
    expect(html).not.toContain('data-item-id');
  });

  it('renders a GFM-style pipe table', () => {
    const html = renderMarkdownToHtml('| A | B |\n| --- | --- |\n| 1 | 2 |');
    expect(html).toBe(
      '<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>',
    );
  });

  it('renders a blockquote', () => {
    const html = renderMarkdownToHtml('> quoted text');
    expect(html).toBe('<blockquote><p>quoted text</p></blockquote>');
  });

  it('renders a horizontal rule', () => {
    expect(renderMarkdownToHtml('---')).toBe('<hr>');
  });

  it('renders an ordered list', () => {
    expect(renderMarkdownToHtml('1. first\n2. second')).toBe(
      '<ol><li>first</li><li>second</li></ol>',
    );
  });

  it('never hangs on a line containing a pipe that is not a real table', () => {
    // Regression guard: a `|` with no separator row below must still make block-parsing
    // progress (paragraph fallback), not loop forever.
    const html = renderMarkdownToHtml('a | b is not a table\n\nnext paragraph');
    expect(html).toContain('a | b is not a table');
    expect(html).toContain('next paragraph');
  });

  it('renders the real TASK-452 sq show --raw fixture without crashing and linkifies its refs', () => {
    const html = renderMarkdownToHtml(fixture('show-raw-with-links.txt'), 'TASK-452');
    expect(html).toContain('<h1>');
    expect(html).not.toContain('data-item-id="TASK-452"'); // self-link suppressed
    expect(html).toContain('data-item-id="FEAT-449"');
    expect(html).toContain('data-item-id="ADR-427"');
    expect(html).not.toContain('data-item-id="F9"');
    expect(html).not.toContain('data-item-id="F10"');
  });

  it('renders the TASK-430 sq show --raw fixture (no crash, clean prose)', () => {
    const html = renderMarkdownToHtml(fixture('show-raw.txt'));
    expect(html).toContain('Open sq show --raw');
    expect(html).toContain('data-item-id="TASK-430"');
  });
});
