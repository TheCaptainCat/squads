import { describe, expect, it } from 'vitest';

import { renderBoardHtml, sortNoticesNewestFirst } from '../src/domain/boardView';
import type { SqBoardNotice } from '../src/types';

function notice(overrides: Partial<SqBoardNotice> = {}): SqBoardNotice {
  return {
    n: 1,
    id: 'a1',
    summary: 'A notice.',
    author: 'op-pierre',
    author_name: 'Pierre Chat',
    body: '',
    posted_at: '2026-01-01T00:00:00Z',
    until: null,
    ...overrides,
  };
}

function success(data: SqBoardNotice[]): { kind: 'success'; data: SqBoardNotice[] } {
  return { kind: 'success', data };
}

describe('sortNoticesNewestFirst', () => {
  it('orders by posted_at descending', () => {
    const notices = [
      notice({ id: 'old', posted_at: '2026-01-01T00:00:00Z' }),
      notice({ id: 'new', posted_at: '2026-01-03T00:00:00Z' }),
      notice({ id: 'mid', posted_at: '2026-01-02T00:00:00Z' }),
    ];

    expect(sortNoticesNewestFirst(notices).map((n) => n.id)).toEqual(['new', 'mid', 'old']);
  });

  it('breaks a tie by id, descending', () => {
    const notices = [
      notice({ id: 'a', posted_at: '2026-01-01T00:00:00Z' }),
      notice({ id: 'z', posted_at: '2026-01-01T00:00:00Z' }),
    ];

    expect(sortNoticesNewestFirst(notices).map((n) => n.id)).toEqual(['z', 'a']);
  });

  it('does not mutate its input', () => {
    const notices = [notice({ id: 'a' }), notice({ id: 'b' })];
    const originalOrder = notices.map((n) => n.id);

    sortNoticesNewestFirst(notices);

    expect(notices.map((n) => n.id)).toEqual(originalOrder);
  });
});

describe('renderBoardHtml: the list', () => {
  it('renders a placeholder for an empty board', () => {
    expect(renderBoardHtml(success([]))).toContain('no current notices');
  });

  it('lists summary, author and posted-at for each notice, newest first', () => {
    const html = renderBoardHtml(
      success([
        notice({ n: 1, id: 'old', posted_at: '2026-01-01T00:00:00Z', summary: 'Older notice' }),
        notice({ n: 2, id: 'new', posted_at: '2026-01-02T00:00:00Z', summary: 'Newer notice' }),
      ]),
    );

    expect(html.indexOf('Newer notice')).toBeLessThan(html.indexOf('Older notice'));
    expect(html).toContain('op-pierre');
    expect(html).toContain('2026-01-02T00:00:00Z');
  });

  it('shows the expiry only when until is set', () => {
    const withExpiry = renderBoardHtml(success([notice({ until: '2026-06-01T00:00:00Z' })]));
    const withoutExpiry = renderBoardHtml(success([notice({ until: null })]));

    expect(withExpiry).toContain('expires 2026-06-01T00:00:00Z');
    expect(withoutExpiry).not.toContain('expires');
  });

  it('renders a multi-line summary as written, one line per line', () => {
    const html = renderBoardHtml(success([notice({ summary: 'first line\nsecond line' })]));

    expect(html).toContain('first line<br>second line');
  });

  it('escapes HTML-significant characters in the summary and the author', () => {
    const html = renderBoardHtml(
      success([notice({ summary: '<img src=x onerror=alert(1)>', author: '<b>x</b>' })]),
    );

    expect(html).not.toContain('<img src=x onerror=alert(1)>');
    expect(html).not.toContain('<b>x</b>');
    expect(html).toContain('&lt;img');
  });

  it('renders the failure message as the whole document on a failed fetch', () => {
    const html = renderBoardHtml({ kind: 'runtime-error', message: 'sq exploded', exitCode: 1 });

    expect(html).toContain('sq exploded');
  });

  it('renders the readable notices plus a partial-listing line on a partial read, never blank', () => {
    const html = renderBoardHtml({
      kind: 'success',
      data: [notice({ id: 'a', summary: 'Still readable' })],
      omissions: [{ code: 'unreadable', source: 'BOARD-2', message: 'bad' }],
    });

    expect(html).toContain('Still readable');
    expect(html).toContain('listing partial');
  });

  it('states the listing is partial even when the omissions report has no per-item detail', () => {
    const html = renderBoardHtml({
      kind: 'success',
      data: [notice({ id: 'a', summary: 'Still readable' })],
      omissions: [],
    });

    expect(html).toContain('Still readable');
    expect(html).toContain('listing partial');
  });

  it('does not mention a partial listing on a genuinely clean read', () => {
    const html = renderBoardHtml(success([notice()]));

    expect(html).not.toContain('partial');
  });
});

describe('renderBoardHtml: credits and body', () => {
  it('puts the credits above the summary in the comment form: full name, slug, timestamp', () => {
    const html = renderBoardHtml(success([notice({ summary: 'The summary' })]));

    expect(html).toContain('Pierre Chat</span>');
    expect(html).toContain('(op-pierre)</span> — <span class="sq-comment-ts">2026-01-01T00:00:00Z');
    expect(html.indexOf('Pierre Chat')).toBeLessThan(html.indexOf('The summary'));
  });

  it('falls back to the slug alone when the row has no author_name', () => {
    const { author_name: _name, ...row } = notice();
    const html = renderBoardHtml(success([row]));

    expect(html).toContain('<span class="sq-comment-author">op-pierre</span> — ');
    expect(html).not.toContain('(op-pierre)');
  });

  it('shows the body under the summary without any click', () => {
    const html = renderBoardHtml(
      success([notice({ summary: 'The summary', body: 'The **full** text.' })]),
    );

    expect(html).toContain('<strong>full</strong>');
    expect(html.indexOf('The summary')).toBeLessThan(html.indexOf('full'));
  });

  it('escapes the expiry', () => {
    const html = renderBoardHtml(success([notice({ until: '<i>soon</i>' })]));

    expect(html).not.toContain('<i>soon</i>');
    expect(html).toContain('expires &lt;i&gt;');
  });

  it('renders no body block for a notice without a body', () => {
    expect(renderBoardHtml(success([notice({ body: '' })]))).not.toContain('sq-notice-body');
  });

  it('escapes the body and the full name', () => {
    const html = renderBoardHtml(
      success([notice({ body: '<script>alert(1)</script>', author_name: '<b>x</b>' })]),
    );

    expect(html).not.toContain('<script>alert(1)</script>');
    expect(html).not.toContain('<b>x</b>');
    expect(html).toContain('&lt;script&gt;');
  });
});
