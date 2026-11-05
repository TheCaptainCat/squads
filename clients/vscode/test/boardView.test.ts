import { describe, expect, it } from 'vitest';

import {
  BOARD_CHANGED_NOTE,
  EMPTY_NOTICE_BODY_LINE,
  type NoticeBody,
  renderBoardHtml,
  sortNoticesNewestFirst,
} from '../src/domain/boardView';
import type { SqBoardNotice } from '../src/types';

function notice(overrides: Partial<SqBoardNotice> = {}): SqBoardNotice {
  return {
    n: 1,
    id: 'a1',
    summary: 'A notice.',
    author: 'op-pierre',
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

  it('lists summary, author and posted-at for each notice, newest first, and carries n and id for the click', () => {
    const html = renderBoardHtml(
      success([
        notice({ n: 1, id: 'old', posted_at: '2026-01-01T00:00:00Z', summary: 'Older notice' }),
        notice({ n: 2, id: 'new', posted_at: '2026-01-02T00:00:00Z', summary: 'Newer notice' }),
      ]),
    );

    expect(html.indexOf('Newer notice')).toBeLessThan(html.indexOf('Older notice'));
    expect(html).toContain('op-pierre');
    expect(html).toContain('2026-01-02T00:00:00Z');
    expect(html).toContain('data-sq-notice-n="2" data-sq-notice-id="new"');
  });

  it('shows the expiry only when until is set', () => {
    const withExpiry = renderBoardHtml(success([notice({ until: '2026-06-01T00:00:00Z' })]));
    const withoutExpiry = renderBoardHtml(success([notice({ until: null })]));

    expect(withExpiry).toContain('expires 2026-06-01T00:00:00Z');
    expect(withoutExpiry).not.toContain('expires');
  });

  it('shows no body until one is asked for', () => {
    const html = renderBoardHtml(success([notice()]));

    expect(html).not.toContain('sq-notice-body');
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

  it('escapes the id carried in the click attribute', () => {
    const html = renderBoardHtml(success([notice({ id: 'a" onmouseover="x' })]));

    expect(html).not.toContain('onmouseover="x');
    expect(html).toContain('data-sq-notice-id="a&quot; onmouseover=&quot;x"');
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

describe('renderBoardHtml: an opened notice', () => {
  function withOpened(id: string, state: NoticeBody, other = 'b2'): string {
    return renderBoardHtml(
      success([
        notice({ id, summary: 'Opened one' }),
        notice({ id: other, n: 2, summary: 'Closed' }),
      ]),
      { opened: new Map([[id, state]]) },
    );
  }

  it('renders the body under its own entry only', () => {
    const html = withOpened('a1', { kind: 'body', body: 'The **full** text.' }, 'b2');

    expect(html).toContain('<strong>full</strong>');
    expect(html.match(/sq-notice-body/g)).toHaveLength(1);
    expect(html.indexOf('The ')).toBeGreaterThan(html.indexOf('Opened one'));
  });

  it('says in one line that a notice without a body has none', () => {
    const html = withOpened('a1', { kind: 'body', body: '' });

    expect(html).toContain(EMPTY_NOTICE_BODY_LINE);
  });

  it('escapes the body', () => {
    const html = withOpened('a1', { kind: 'body', body: '<script>alert(1)</script>' });

    expect(html).not.toContain('<script>alert(1)</script>');
    expect(html).toContain('&lt;script&gt;');
  });

  it('renders a failed show as its message in place of the body', () => {
    const html = withOpened('a1', { kind: 'failure', message: 'sq exploded <b>' });

    expect(html).toContain('Unable to load this notice');
    expect(html).toContain('sq exploded');
    expect(html).not.toContain('<b>');
  });

  it('shows the one-line note above the list when the board changed', () => {
    const html = renderBoardHtml(success([notice()]), { note: BOARD_CHANGED_NOTE });

    expect(html.indexOf(BOARD_CHANGED_NOTE)).toBeLessThan(html.indexOf('A notice.'));
  });
});
