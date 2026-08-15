import { describe, expect, it } from 'vitest';

import { buildItemDirectory, NO_ITEM_DIRECTORY } from '../src/domain/itemDirectory';
import type { SqListItem } from '../src/types';

function listItem(overrides: Partial<SqListItem> & { id: string }): SqListItem {
  return {
    sequence_id: 1,
    type: 'task',
    title: 'A task title',
    slug: 'a-task-title',
    status: 'Ready',
    description: '',
    parent: null,
    author: 'tech-lead',
    assignee: null,
    priority: null,
    severity: null,
    labels: [],
    refs: [],
    path: 'tasks/x.md',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('buildItemDirectory', () => {
  it('maps an id to hover text carrying that id and its title', () => {
    const directory = buildItemDirectory([listItem({ id: 'TASK-688', title: 'Narrow the view' })]);

    expect(directory.get('TASK-688')).toBe('TASK-688 — Narrow the view');
  });

  it('resolves every id shape a declared prefix can produce', () => {
    // The directory keys off whatever `sq list --json` reports as the id — it never re-derives
    // or validates the id's shape, so a hyphenated/lowercase/single-character prefix resolves
    // the same as a conventional one.
    const directory = buildItemDirectory([
      listItem({ id: 'MY-WIDGET-19', title: 'Hyphenated' }),
      listItem({ id: 'MY_WIDGET-19', title: 'Underscored' }),
      listItem({ id: 'W-1', title: 'Single character' }),
      listItem({ id: 'widget-19', title: 'Lowercase' }),
    ]);

    expect(directory.get('MY-WIDGET-19')).toBe('MY-WIDGET-19 — Hyphenated');
    expect(directory.get('MY_WIDGET-19')).toBe('MY_WIDGET-19 — Underscored');
    expect(directory.get('W-1')).toBe('W-1 — Single character');
    expect(directory.get('widget-19')).toBe('widget-19 — Lowercase');
  });

  it('skips a row whose title is blank rather than storing the id twice over', () => {
    const directory = buildItemDirectory([
      listItem({ id: 'TASK-1', title: '' }),
      listItem({ id: 'TASK-2', title: '   ' }),
    ]);

    expect(directory.get('TASK-1')).toBeUndefined();
    expect(directory.get('TASK-2')).toBeUndefined();
  });

  it('trims a padded title', () => {
    const directory = buildItemDirectory([listItem({ id: 'TASK-1', title: '  Padded  ' })]);

    expect(directory.get('TASK-1')).toBe('TASK-1 — Padded');
  });

  it('leaves an id absent from the fetch unresolved', () => {
    const directory = buildItemDirectory([listItem({ id: 'TASK-1' })]);

    expect(directory.get('TASK-999')).toBeUndefined();
  });

  it('resolves nothing at all through the degrade default', () => {
    expect(NO_ITEM_DIRECTORY.get('TASK-1')).toBeUndefined();
    expect(NO_ITEM_DIRECTORY.size).toBe(0);
  });

  it('builds an empty directory from an empty fetch, not an error', () => {
    expect(buildItemDirectory([]).size).toBe(0);
  });
});
