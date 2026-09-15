import { describe, expect, it } from 'vitest';

import {
  buildBoardMarkdown,
  renderBoardHtml,
  sortNoticesNewestFirst,
} from '../src/domain/boardView';
import type { SqBoardNotice } from '../src/types';

function notice(overrides: Partial<SqBoardNotice> = {}): SqBoardNotice {
  return {
    n: 1,
    id: 'a1',
    author: 'op-pierre',
    posted_at: '2026-01-01T00:00:00Z',
    until: null,
    body: 'A notice.',
    ...overrides,
  };
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

describe('buildBoardMarkdown', () => {
  it('renders a placeholder for an empty board', () => {
    expect(buildBoardMarkdown([])).toContain('no current notices');
  });

  it('includes author, posted-at, and body for each notice, newest-first', () => {
    const markdown = buildBoardMarkdown([
      notice({ id: 'old', posted_at: '2026-01-01T00:00:00Z', body: 'Older notice' }),
      notice({ id: 'new', posted_at: '2026-01-02T00:00:00Z', body: 'Newer notice' }),
    ]);

    expect(markdown.indexOf('Newer notice')).toBeLessThan(markdown.indexOf('Older notice'));
    expect(markdown).toContain('op-pierre');
    expect(markdown).toContain('2026-01-02T00:00:00Z');
  });

  it('shows the expiry only when until is set', () => {
    const withExpiry = buildBoardMarkdown([notice({ until: '2026-06-01T00:00:00Z' })]);
    const withoutExpiry = buildBoardMarkdown([notice({ until: null })]);

    expect(withExpiry).toContain('expires 2026-06-01T00:00:00Z');
    expect(withoutExpiry).not.toContain('expires');
  });
});

describe('renderBoardHtml', () => {
  it('renders every notice body, escaping HTML-significant characters rather than injecting them', () => {
    const html = renderBoardHtml({
      kind: 'success',
      data: [notice({ body: '<img src=x onerror=alert(1)>' })],
    });

    expect(html).not.toContain('<img src=x onerror=alert(1)>');
    expect(html).toContain('&lt;img');
  });

  it('renders the failure message as the whole document on a failed fetch', () => {
    const html = renderBoardHtml({ kind: 'runtime-error', message: 'sq exploded', exitCode: 1 });

    expect(html).toContain('sq exploded');
  });

  it('renders the readable notices plus a partial-listing line on a partial read, never blank', () => {
    const html = renderBoardHtml({
      kind: 'success',
      data: [notice({ id: 'a', body: 'Still readable' })],
      omissions: [{ code: 'unreadable', source: 'BOARD-2', message: 'bad' }],
    });

    expect(html).toContain('Still readable');
    expect(html).toContain('listing partial');
  });

  it('states the listing is partial even when the omissions report has no per-item detail', () => {
    const html = renderBoardHtml({
      kind: 'success',
      data: [notice({ id: 'a', body: 'Still readable' })],
      omissions: [],
    });

    expect(html).toContain('Still readable');
    expect(html).toContain('listing partial');
  });

  it('does not mention a partial listing on a genuinely clean read', () => {
    const html = renderBoardHtml({ kind: 'success', data: [notice()] });

    expect(html).not.toContain('partial');
  });
});
