import { describe, expect, it } from 'vitest';

import {
  humanizeAge,
  isMemoryEligibleType,
  memoryChildren,
  memoryEligibleSlugs,
  memoryEntryLabel,
  memoryEntryPanelTitle,
  type MemoryFetchResult,
  memoryGlanceText,
  memoryLabelSuffix,
  memoryTooltipLine,
  NO_MEMORY_CONTEXT,
  renderMemoryEntryHtml,
  resolveMemoryEntryPanelTitle,
  sortMemoryEntries,
} from '../src/domain/memoryView';
import type { SqListItem, SqMemoryDetail, SqMemoryListRow } from '../src/types';

const NOW = new Date('2026-01-10T00:00:00Z');

function row(slug: string, description: string, createdAt?: string): SqMemoryListRow {
  return {
    slug,
    filename: `${slug}.md`,
    description,
    ...(createdAt !== undefined ? { created_at: createdAt } : {}),
  };
}

describe('isMemoryEligibleType', () => {
  it('is true for role and operator, false for skill and everything else', () => {
    expect(isMemoryEligibleType('role')).toBe(true);
    expect(isMemoryEligibleType('operator')).toBe(true);
    expect(isMemoryEligibleType('skill')).toBe(false);
    expect(isMemoryEligibleType('task')).toBe(false);
  });
});

describe('humanizeAge', () => {
  it('renders "just now" under a minute', () => {
    expect(humanizeAge('2026-01-09T23:59:31Z', NOW)).toBe('just now');
  });

  it('picks the coarsest fitting unit', () => {
    expect(humanizeAge('2026-01-09T23:00:00Z', NOW)).toBe('1h ago');
    expect(humanizeAge('2026-01-08T00:00:00Z', NOW)).toBe('2d ago');
    expect(humanizeAge('2025-01-10T00:00:00Z', NOW)).toBe('1y ago');
  });

  it('reports "unknown age" for a timestamp it cannot parse, rather than throwing', () => {
    expect(humanizeAge('not-a-date', NOW)).toBe('unknown age');
  });
});

describe('sortMemoryEntries', () => {
  it('sorts oldest-touched first when every entry carries created_at', () => {
    const entries = [
      row('c', 'c summary', '2026-01-03T00:00:00Z'),
      row('a', 'a summary', '2026-01-01T00:00:00Z'),
      row('b', 'b summary', '2026-01-02T00:00:00Z'),
    ];

    expect(sortMemoryEntries(entries).map((e) => e.slug)).toEqual(['a', 'b', 'c']);
  });

  it('breaks a tie by slug', () => {
    const entries = [
      row('z', 'z summary', '2026-01-01T00:00:00Z'),
      row('a', 'a summary', '2026-01-01T00:00:00Z'),
    ];

    expect(sortMemoryEntries(entries).map((e) => e.slug)).toEqual(['a', 'z']);
  });

  it('falls back to the CLI-returned order, stably, when created_at is absent on every row', () => {
    const entries = [row('z', 'z summary'), row('a', 'a summary')];

    expect(sortMemoryEntries(entries).map((e) => e.slug)).toEqual(['z', 'a']);
  });
});

describe('memoryGlanceText', () => {
  it('renders "0" for a genuinely empty pool — a signal, not nothing to show', () => {
    const pool: MemoryFetchResult = { kind: 'loaded', entries: [] };
    expect(memoryGlanceText(pool, NOW)).toBe('0');
  });

  it('renders count only when created_at is unavailable', () => {
    const pool: MemoryFetchResult = { kind: 'loaded', entries: [row('a', 'a')] };
    expect(memoryGlanceText(pool, NOW)).toBe('1');
  });

  it("renders count and the most recent entry's age once created_at is available", () => {
    const pool: MemoryFetchResult = {
      kind: 'loaded',
      entries: [row('a', 'a', '2026-01-01T00:00:00Z'), row('b', 'b', '2026-01-09T00:00:00Z')],
    };
    expect(memoryGlanceText(pool, NOW)).toBe('2 · 1d ago');
  });

  it('renders "error" for a fetch that failed outright', () => {
    const pool: MemoryFetchResult = { kind: 'failed', message: 'boom' };
    expect(memoryGlanceText(pool, NOW)).toBe('error');
  });

  it('marks a partial pool as partial rather than reading its short count as the whole notebook', () => {
    const pool: MemoryFetchResult = {
      kind: 'loaded',
      entries: [row('a', 'a', '2026-01-09T00:00:00Z')],
      omissions: [{ code: 'unreadable', source: 'ROLE-1/x.md', message: 'could not be read' }],
    };
    expect(memoryGlanceText(pool, NOW)).toBe('1 · 1d ago (partial)');
  });

  it('still marks partial when the omissions report itself is missing or malformed (empty array)', () => {
    const pool: MemoryFetchResult = { kind: 'loaded', entries: [row('a', 'a')], omissions: [] };
    expect(memoryGlanceText(pool, NOW)).toBe('1 (partial)');
  });

  it('a genuinely empty pool (no omissions key at all) is not marked partial', () => {
    const pool: MemoryFetchResult = { kind: 'loaded', entries: [] };
    expect(memoryGlanceText(pool, NOW)).toBe('0');
  });
});

describe('memoryLabelSuffix and memoryTooltipLine', () => {
  it('both surface the same glance text', () => {
    const pool: MemoryFetchResult = { kind: 'loaded', entries: [row('a', 'a')] };
    expect(memoryLabelSuffix(pool, NOW)).toBe('  memory: 1');
    expect(memoryTooltipLine(pool, NOW)).toBe('  \nMemory: 1');
  });

  it("the tooltip line names a failed fetch's reason, escaped for markdown", () => {
    const pool: MemoryFetchResult = { kind: 'failed', message: 'boom *loud*' };
    expect(memoryTooltipLine(pool, NOW)).toBe('  \nMemory: error (boom \\*loud\\*)');
  });

  it('the tooltip line names how many entries a partial pool left out', () => {
    const pool: MemoryFetchResult = {
      kind: 'loaded',
      entries: [row('a', 'a')],
      omissions: [{ code: 'unreadable', source: 'ROLE-1/x.md', message: 'x' }],
    };
    expect(memoryTooltipLine(pool, NOW)).toBe(
      '  \nMemory: 1 (partial) (1 entry could not be read — listing partial.)',
    );
  });
});

describe('memoryEntryLabel', () => {
  it('includes the age when created_at is present', () => {
    expect(memoryEntryLabel(row('a', 'a summary', '2026-01-09T00:00:00Z'), NOW)).toBe(
      'a  a summary  (1d ago)',
    );
  });

  it('omits the age fragment entirely when created_at is absent (an older sq)', () => {
    expect(memoryEntryLabel(row('a', 'a summary'), NOW)).toBe('a  a summary');
  });
});

describe('memoryChildren', () => {
  it('is empty for an identity that was never fetched', () => {
    expect(memoryChildren('manager', undefined, NOW)).toEqual([]);
  });

  it('is empty (not an error node) for a pool that failed to load — the identity still renders, just childless', () => {
    expect(memoryChildren('manager', { kind: 'failed', message: 'boom' }, NOW)).toEqual([]);
  });

  it('still renders the entries that were read for a partial pool — never treated as failed', () => {
    const pool: MemoryFetchResult = {
      kind: 'loaded',
      entries: [row('a', 'a summary', '2026-01-01T00:00:00Z')],
      omissions: [{ code: 'unreadable', source: 'ROLE-1/x.md', message: 'x' }],
    };

    expect(memoryChildren('manager', pool, NOW).map((c) => c.id)).toEqual(['memory:manager:a']);
  });

  it('produces one leaf per entry, oldest-first, each carrying a memoryRef and no itemId', () => {
    const pool: MemoryFetchResult = {
      kind: 'loaded',
      entries: [
        row('newer', 'n', '2026-01-05T00:00:00Z'),
        row('older', 'o', '2026-01-01T00:00:00Z'),
      ],
    };

    const children = memoryChildren('manager', pool, NOW);

    expect(children.map((c) => c.id)).toEqual(['memory:manager:older', 'memory:manager:newer']);
    expect(children.every((c) => c.itemId === null)).toBe(true);
    expect(children.every((c) => c.children.length === 0)).toBe(true);
    expect(children[0]?.memoryRef).toEqual({ roleSlug: 'manager', entrySlug: 'older' });
  });
});

function makeItem(id: string, type: string): SqListItem {
  return {
    id,
    sequence_id: Number(id.split('-')[1] ?? '0'),
    type,
    title: `${id} title`,
    slug: id.toLowerCase(),
    status: 'Active',
    description: '',
    parent: null,
    author: null,
    assignee: null,
    priority: null,
    severity: null,
    labels: [],
    refs: [],
    path: `${type}s/${id}.md`,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
}

describe('memoryEligibleSlugs', () => {
  it('collects only role/operator slugs, never skill or work-item ones', () => {
    const items = [
      makeItem('ROLE-1', 'role'),
      makeItem('OP-1', 'operator'),
      makeItem('SKILL-1', 'skill'),
    ];

    expect(memoryEligibleSlugs(items)).toEqual(['role-1', 'op-1']);
  });

  it('narrows to a status filter the same way the Roster view itself does', () => {
    const items = [
      { ...makeItem('ROLE-1', 'role'), status: 'Active' },
      { ...makeItem('ROLE-2', 'role'), status: 'Archived' },
    ];

    const slugs = memoryEligibleSlugs(items, undefined, undefined, {
      showArchived: false,
      statusFilter: 'Active',
      groupByType: true,
    });

    expect(slugs).toEqual(['role-1']);
  });
});

describe('renderMemoryEntryHtml', () => {
  const detail: SqMemoryDetail = {
    slug: 'a-fact',
    summary: 'A short punchline.',
    created_at: '2026-01-01T00:00:00Z',
    tags: ['x', 'y'],
    body: 'The **full** body.',
  };

  it('renders the role, summary, timestamp, and tags in the header, plus the body', () => {
    const html = renderMemoryEntryHtml('manager', { kind: 'success', data: detail });

    expect(html).toContain('manager');
    expect(html).toContain('a-fact');
    expect(html).toContain('A short punchline.');
    expect(html).toContain('2026-01-01T00:00:00Z');
    expect(html).toContain('x, y');
    expect(html).toContain('full');
  });

  it('escapes HTML-significant characters in the body rather than injecting them', () => {
    const html = renderMemoryEntryHtml('manager', {
      kind: 'success',
      data: { ...detail, body: '<script>alert(1)</script>' },
    });

    expect(html).not.toContain('<script>alert(1)</script>');
    expect(html).toContain('&lt;script&gt;');
  });

  it('escapes HTML-significant characters in the summary rather than injecting them', () => {
    const html = renderMemoryEntryHtml('manager', {
      kind: 'success',
      data: { ...detail, summary: '<script>alert(2)</script>' },
    });

    expect(html).not.toContain('<script>alert(2)</script>');
    expect(html).toContain('&lt;script&gt;');
  });

  it('renders the failure message as the whole document on a failed fetch', () => {
    const html = renderMemoryEntryHtml('manager', {
      kind: 'runtime-error',
      message: 'not found',
      exitCode: 1,
    });

    expect(html).toContain('not found');
  });
});

describe('memoryEntryPanelTitle', () => {
  it('combines the role slug and entry slug', () => {
    expect(memoryEntryPanelTitle('manager', 'a-fact')).toBe('manager: a-fact');
  });
});

describe('resolveMemoryEntryPanelTitle', () => {
  const detail: SqMemoryDetail = {
    slug: 'a-fact',
    summary: 's',
    created_at: '2026-01-01T00:00:00Z',
    tags: [],
    body: 'b',
  };

  it('keeps naming the role on a successful fetch, rather than dropping to the bare entry slug', () => {
    const title = resolveMemoryEntryPanelTitle('tech-lead', 'tech-lead: a-fact', {
      kind: 'success',
      data: detail,
    });

    expect(title).toBe('tech-lead: a-fact');
    expect(title).toContain('tech-lead');
  });

  it('keeps the fallback title on a failed fetch, unchanged', () => {
    const title = resolveMemoryEntryPanelTitle('tech-lead', 'tech-lead: a-fact', {
      kind: 'runtime-error',
      message: 'not found',
      exitCode: 1,
    });

    expect(title).toBe('tech-lead: a-fact');
  });

  it('names the role for the entry actually returned, not the one requested (e.g. after a rename)', () => {
    const title = resolveMemoryEntryPanelTitle('tech-lead', 'tech-lead: old-slug', {
      kind: 'success',
      data: { ...detail, slug: 'new-slug' },
    });

    expect(title).toBe('tech-lead: new-slug');
  });
});

describe('NO_MEMORY_CONTEXT', () => {
  it('carries an empty pool map', () => {
    expect(NO_MEMORY_CONTEXT.pools.size).toBe(0);
  });
});
