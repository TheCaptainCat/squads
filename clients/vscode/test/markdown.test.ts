import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  isSafeLinkUrl,
  ITEM_ID_PATTERN,
  linkifyPlainText,
  renderMarkdownToHtml,
} from '../src/domain/markdown';

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

describe('isSafeLinkUrl (REV-461 F2 scheme allowlist)', () => {
  it('allows http, https, and mailto', () => {
    expect(isSafeLinkUrl('https://example.com/docs')).toBe(true);
    expect(isSafeLinkUrl('http://example.com')).toBe(true);
    expect(isSafeLinkUrl('mailto:a@example.com')).toBe(true);
  });

  it('is case-insensitive on the scheme', () => {
    expect(isSafeLinkUrl('HTTPS://example.com')).toBe(true);
  });

  it('rejects javascript:, data:, vbscript:, and file: urls', () => {
    expect(isSafeLinkUrl('javascript:evil')).toBe(false);
    expect(isSafeLinkUrl('data:text/html;base64,PHNjcmlwdD4=')).toBe(false);
    expect(isSafeLinkUrl('vbscript:evil')).toBe(false);
    expect(isSafeLinkUrl('file:///etc/passwd')).toBe(false);
  });

  it('rejects a scheme-less relative or protocol-relative url', () => {
    expect(isSafeLinkUrl('docs/readme.md')).toBe(false);
    expect(isSafeLinkUrl('//evil.example.com')).toBe(false);
  });
});

describe('renderMarkdownToHtml: link hrefs (REV-461 F2)', () => {
  it('keeps a safe http(s) link href intact', () => {
    expect(renderMarkdownToHtml('[docs](https://example.com/docs)')).toBe(
      '<p><a href="https://example.com/docs">docs</a></p>',
    );
  });

  it('keeps a mailto link href intact', () => {
    expect(renderMarkdownToHtml('[mail me](mailto:a@example.com)')).toBe(
      '<p><a href="mailto:a@example.com">mail me</a></p>',
    );
  });

  it('drops the href for a javascript: url, keeping only the escaped visible text', () => {
    const html = renderMarkdownToHtml('[x](javascript:evil)');
    expect(html).toBe('<p>x</p>');
  });

  it('drops the href for a data: url', () => {
    const html = renderMarkdownToHtml('[x](data:text/html;base64,PHNjcmlwdD4=)');
    expect(html).toBe('<p>x</p>');
  });

  it('routes a link whose url is itself a bare item id through the internal item-link mechanism', () => {
    const html = renderMarkdownToHtml('[see it](TASK-452)');
    expect(html).toBe('<p><a class="sq-item-link" href="#" data-item-id="TASK-452">see it</a></p>');
  });

  it('suppresses the self-link when the link url is the current item id', () => {
    expect(renderMarkdownToHtml('[self](TASK-452)', 'TASK-452')).toBe('<p>self</p>');
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

  it('tags a fenced code block with its language class (mermaid renders as plain code by default)', () => {
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

describe('renderMarkdownToHtml: renderMermaidFences (workflow cheatsheet)', () => {
  it('renders a mermaid fence as a live-render source/output pair, not plain code', () => {
    const html = renderMarkdownToHtml('```mermaid\ngraph TD;\n```', undefined, true);
    expect(html).not.toContain('<code');
    expect(html).toContain('class="sq-graph-source"');
    expect(html).toContain('class="sq-graph-output"');
    expect(html).toContain('graph TD;');
  });

  it('links each source element to its own output element via data-output-id', () => {
    const html = renderMarkdownToHtml('```mermaid\ngraph TD;\n```', undefined, true);
    const sourceMatch = /id="([^"]+)"[^>]*data-output-id="([^"]+)"/.exec(html);
    if (sourceMatch === null) {
      throw new Error('expected a source element with data-output-id');
    }
    const outputId = sourceMatch[2];
    if (outputId === undefined) {
      throw new Error('expected the data-output-id capture group to match');
    }
    expect(html).toContain(`id="${outputId}"`);
  });

  it('gives multiple mermaid fences distinct, non-colliding ids', () => {
    const html = renderMarkdownToHtml(
      '```mermaid\ngraph TD;\n```\n\nsome prose\n\n```mermaid\nflowchart LR;\n```',
      undefined,
      true,
    );
    // Matches only the real `id="..."` attributes (the source `<pre>` and the output `<div>`),
    // not the `data-output-id="..."` attribute — which carries the same value as the output
    // element's own id and would otherwise double-count it.
    const ids = [
      ...html.matchAll(/(?<!data-output-)id="(sq-mermaid-fence-\d+-(?:source|output))"/g),
    ].map((match) => match[1]);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids.length).toBe(4);
  });

  it('leaves a non-mermaid fence as plain code even with the flag on', () => {
    const html = renderMarkdownToHtml('```bash\nsq workflow --raw\n```', undefined, true);
    expect(html).toBe('<pre><code class="language-bash">sq workflow --raw</code></pre>');
  });

  it('renders the real sq workflow --raw fixture without crashing, with every diagram live', () => {
    const raw = fixture('workflow-raw.txt');
    const fenceCount = (raw.match(/```mermaid/g) ?? []).length;
    const html = renderMarkdownToHtml(raw, undefined, true);
    expect(fenceCount).toBeGreaterThan(0);
    expect(html.match(/class="sq-graph-source"/g)).toHaveLength(fenceCount);
    expect(html).not.toContain('language-mermaid');
  });
});
