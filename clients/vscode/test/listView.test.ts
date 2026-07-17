import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  buildFilteredGroupedView,
  type ClassifiedListItem,
  classifyListItems,
  distinctTypes,
  excludeReservedTypes,
  filterListItems,
  groupListItems,
  matchesFilter,
  NO_FILTER,
} from '../src/domain/listView';
import type { SqListItem } from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const LIST_FIXTURE = JSON.parse(readFixture('list.json')) as SqListItem[];

describe('excludeReservedTypes', () => {
  it('drops the three reserved meta types (role/skill/operator) from the committed fixture', () => {
    const filtered = excludeReservedTypes(LIST_FIXTURE);

    expect(filtered.some((item) => item.type === 'role')).toBe(false);
    expect(filtered.some((item) => item.type === 'skill')).toBe(false);
    expect(filtered.some((item) => item.type === 'operator')).toBe(false);
    expect(filtered.length).toBeLessThan(LIST_FIXTURE.length);
    expect(filtered.some((item) => item.type === 'epic')).toBe(true);
  });
});

describe('distinctTypes', () => {
  it('lists distinct non-reserved types, sorted, with no local type catalog hardcoded', () => {
    expect(distinctTypes(LIST_FIXTURE)).toEqual(['bug', 'decision', 'epic', 'feature', 'task']);
  });
});

describe('classifyListItems', () => {
  it('marks items present in openIds as open and everything else as closed', () => {
    const items: SqListItem[] = [makeItem('TASK-1', 'task'), makeItem('TASK-2', 'task')];
    const classified = classifyListItems(items, new Set(['TASK-1']));

    expect(classified.find((item) => item.id === 'TASK-1')?.state).toBe('open');
    expect(classified.find((item) => item.id === 'TASK-2')?.state).toBe('closed');
  });
});

describe('matchesFilter / filterListItems', () => {
  const items: ClassifiedListItem[] = [
    { ...makeItem('TASK-1', 'task'), state: 'open' },
    { ...makeItem('BUG-1', 'bug'), state: 'closed' },
    { ...makeItem('TASK-2', 'task'), state: 'closed' },
  ];

  it('with NO_FILTER, matches everything', () => {
    expect(filterListItems(items, NO_FILTER)).toHaveLength(3);
  });

  it('filters by type', () => {
    const filtered = filterListItems(items, { type: 'task', state: null });
    expect(filtered.map((item) => item.id)).toEqual(['TASK-1', 'TASK-2']);
  });

  it('filters by open/closed state', () => {
    const filtered = filterListItems(items, { type: null, state: 'closed' });
    expect(filtered.map((item) => item.id)).toEqual(['BUG-1', 'TASK-2']);
  });

  it('combines type and state filters', () => {
    const openTask = items.find((item) => item.id === 'TASK-1');
    expect(openTask).toBeDefined();
    if (openTask === undefined) {
      return;
    }
    expect(matchesFilter(openTask, { type: 'task', state: 'open' })).toBe(true);
    expect(matchesFilter(openTask, { type: 'bug', state: 'open' })).toBe(false);
    expect(matchesFilter(openTask, { type: 'task', state: 'closed' })).toBe(false);
  });
});

describe('groupListItems', () => {
  const items: ClassifiedListItem[] = [
    { ...makeItem('TASK-2', 'task'), state: 'open' },
    { ...makeItem('TASK-1', 'task'), state: 'closed' },
    { ...makeItem('BUG-1', 'bug'), state: 'open' },
  ];

  it('with no groupBy keys, returns sorted leaves', () => {
    const nodes = groupListItems(items, []);
    expect(nodes.map((node) => node.id)).toEqual(['BUG-1', 'TASK-1', 'TASK-2']);
    expect(nodes.every((node) => node.itemId !== null && node.children.length === 0)).toBe(true);
  });

  it('groups by a single key, sorted by group label, with an item-count description', () => {
    const nodes = groupListItems(items, ['type']);

    expect(nodes.map((node) => node.label)).toEqual(['bug', 'task']);
    expect(nodes.find((node) => node.label === 'task')?.description).toBe('2 items');
    expect(nodes.find((node) => node.label === 'bug')?.description).toBe('1 item');
    expect(nodes.every((node) => node.itemId === null)).toBe(true);
  });

  it('groups by two keys in order, nesting the second level under the first', () => {
    const nodes = groupListItems(items, ['type', 'state']);
    const taskGroup = nodes.find((node) => node.label === 'task');

    expect(taskGroup?.children.map((child) => child.label)).toEqual(['Closed', 'Open']);
    expect(taskGroup?.children.find((child) => child.label === 'Open')?.children[0]?.id).toBe(
      'TASK-2',
    );
  });

  it('reverses nesting order when state is grouped before type', () => {
    const nodes = groupListItems(items, ['state', 'type']);
    expect(nodes.map((node) => node.label)).toEqual(['Closed', 'Open']);
  });
});

describe('buildFilteredGroupedView (end to end)', () => {
  it('excludes reserved types, classifies, filters, and groups the committed fixture', () => {
    const openIds = new Set(
      LIST_FIXTURE.filter((item) => item.type === 'task' && item.status !== 'Done').map(
        (item) => item.id,
      ),
    );
    const nodes = buildFilteredGroupedView(LIST_FIXTURE, openIds, { type: 'task', state: null }, [
      'state',
    ]);

    expect(nodes.every((node) => node.itemId === null)).toBe(true);
    const allLeafIds = nodes.flatMap((group) => group.children.map((leaf) => leaf.itemId));
    expect(allLeafIds.every((id) => id !== null)).toBe(true);
  });
});

function makeItem(id: string, type: string): SqListItem {
  const sequenceId = Number(id.split('-')[1] ?? '0');
  return {
    id,
    sequence_id: sequenceId,
    type,
    title: `${id} title`,
    slug: id.toLowerCase(),
    status: 'Ready',
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
