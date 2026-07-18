import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  buildFilteredGroupedView,
  distinctTypes,
  excludeReservedTypes,
  filterListItems,
  groupListItems,
  matchesFilter,
  NO_FILTER,
} from '../src/domain/listView';
import { buildStatusRoleMap } from '../src/domain/statusRole';
import { buildTypeOrderMap } from '../src/domain/typeOrder';
import type { SqListItem, SqStatusCatalogEntry, SqTypeCatalogEntry } from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const LIST_FIXTURE = JSON.parse(readFixture('list.json')) as SqListItem[];
const TYPE_CATALOG_FIXTURE = JSON.parse(readFixture('type-catalog.json')) as SqTypeCatalogEntry[];
const TYPE_ORDER_MAP = buildTypeOrderMap(TYPE_CATALOG_FIXTURE);
const STATUSES_CATALOG_FIXTURE = JSON.parse(
  readFixture('statuses-catalog.json'),
) as SqStatusCatalogEntry[];

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
  it('with no orderMap (the graceful fallback), lists distinct non-reserved types alphabetically', () => {
    expect(distinctTypes(LIST_FIXTURE)).toEqual([
      'bug',
      'decision',
      'epic',
      'feature',
      'guide',
      'review',
      'task',
    ]);
  });

  it('given the type catalog, orders types by spec order rather than alphabetically (F1)', () => {
    expect(distinctTypes(LIST_FIXTURE, TYPE_ORDER_MAP)).toEqual([
      'epic',
      'feature',
      'task',
      'bug',
      'decision',
      'review',
      'guide',
    ]);
  });
});

describe('matchesFilter / filterListItems', () => {
  const items: SqListItem[] = [
    makeItem('TASK-1', 'task', true),
    makeItem('BUG-1', 'bug', false),
    makeItem('TASK-2', 'task', false),
  ];

  it('with NO_FILTER, matches everything', () => {
    expect(filterListItems(items, NO_FILTER)).toHaveLength(3);
  });

  it('filters by type', () => {
    const filtered = filterListItems(items, { type: 'task' });
    expect(filtered.map((item) => item.id)).toEqual(['TASK-1', 'TASK-2']);
  });

  it('matchesFilter is a straight type equality check (no open/closed axis)', () => {
    const [task] = items;
    expect(task).toBeDefined();
    if (task === undefined) {
      return;
    }
    expect(matchesFilter(task, { type: 'task' })).toBe(true);
    expect(matchesFilter(task, { type: 'bug' })).toBe(false);
    expect(matchesFilter(task, NO_FILTER)).toBe(true);
  });
});

describe('groupListItems', () => {
  // Deliberately out of both id-numeric-order and type-alpha-order, so a passing test can't be
  // a lucky coincidence of insertion order.
  const items: SqListItem[] = [
    makeItem('REV-447', 'review', true),
    makeItem('TASK-2', 'task', true),
    makeItem('REV-48', 'review', true),
    makeItem('TASK-1', 'task', false),
    makeItem('BUG-1', 'bug', true),
  ];

  it('with groupByType false, returns sorted leaves by numeric id order (no type grouping)', () => {
    const nodes = groupListItems(items, false);

    expect(nodes.map((node) => node.id)).toEqual([
      'BUG-1',
      'REV-48',
      'REV-447',
      'TASK-1',
      'TASK-2',
    ]);
    expect(nodes.every((node) => node.itemId !== null && node.children.length === 0)).toBe(true);
  });

  it('with no orderMap (the graceful fallback), groups by type name', () => {
    const nodes = groupListItems(items, true);

    expect(nodes.map((node) => node.label)).toEqual(['bug', 'review', 'task']);
    expect(nodes.find((node) => node.label === 'task')?.description).toBe('2 items');
    expect(nodes.find((node) => node.label === 'bug')?.description).toBe('1 item');
    expect(nodes.every((node) => node.itemId === null)).toBe(true);
  });

  it('given the type catalog, orders groups by spec order rather than type name (F1)', () => {
    const nodes = groupListItems(items, true, TYPE_ORDER_MAP);

    // Spec order is task(30) < bug(40) < review(60); alphabetical would be bug, review, task.
    expect(nodes.map((node) => node.label)).toEqual(['task', 'bug', 'review']);
  });

  it('sorts leaves within each type bucket by numeric id order too', () => {
    const nodes = groupListItems(items, true);
    const reviewGroup = nodes.find((node) => node.label === 'review');

    expect(reviewGroup?.children.map((child) => child.id)).toEqual(['REV-48', 'REV-447']);
  });

  it('marks a closed leaf via DisplayNode.closed, derived from the item is_open field', () => {
    const nodes = groupListItems(items, false);

    expect(nodes.find((node) => node.id === 'TASK-1')?.closed).toBe(true);
    expect(nodes.find((node) => node.id === 'TASK-2')?.closed).toBe(false);
  });

  it('marks a leaf active via DisplayNode.active, joined through the statuses catalog (F26) — never a literal status check', () => {
    const statusRoles = buildStatusRoleMap(STATUSES_CATALOG_FIXTURE);
    const mixedItems: SqListItem[] = [
      { ...makeItem('TASK-1', 'task', true), status: 'InProgress' },
      { ...makeItem('TASK-2', 'task', true), status: 'Ready' },
      { ...makeItem('TASK-3', 'task', false), status: 'Done' },
    ];

    const nodes = groupListItems(
      mixedItems,
      false,
      undefined,
      undefined,
      undefined,
      undefined,
      statusRoles,
    );

    expect(nodes.find((node) => node.id === 'TASK-1')?.active).toBe(true);
    const ready = nodes.find((node) => node.id === 'TASK-2');
    expect(ready?.active).toBe(false);
    expect(ready?.closed).toBe(false);
    // Done is closed and never carries the "active" role — the disjoint sets F26/F7 rely on.
    const done = nodes.find((node) => node.id === 'TASK-3');
    expect(done?.active).toBe(false);
    expect(done?.closed).toBe(true);
  });

  it('with no statusRoles (the graceful fallback), no leaf is ever marked active', () => {
    const inProgressItem: SqListItem[] = [
      { ...makeItem('TASK-1', 'task', true), status: 'InProgress' },
    ];

    expect(groupListItems(inProgressItem, false)[0]?.active).toBe(false);
  });

  it('layers squads.typeIcons overrides over the bundled per-type icon defaults (F21)', () => {
    const nodes = groupListItems(items, false, undefined, { task: 'flame' });

    expect(nodes.find((node) => node.id === 'TASK-1')?.iconId).toBe('flame');
    // A type absent from the overrides still gets its bundled default.
    expect(nodes.find((node) => node.id === 'BUG-1')?.iconId).toBe('bug');
  });
});

describe('buildFilteredGroupedView (end to end)', () => {
  it('excludes reserved types, filters by type, and groups the committed fixture', () => {
    const nodes = buildFilteredGroupedView(LIST_FIXTURE, { type: 'task' }, true);

    expect(nodes.every((node) => node.itemId === null)).toBe(true);
    const allLeafIds = nodes.flatMap((group) => group.children.map((leaf) => leaf.itemId));
    expect(allLeafIds.every((id) => id !== null)).toBe(true);
    expect(nodes.every((node) => node.label === 'task')).toBe(true);
  });

  it('returns sorted leaves directly when groupByType is false', () => {
    const nodes = buildFilteredGroupedView(LIST_FIXTURE, NO_FILTER, false);

    expect(nodes.every((node) => node.itemId !== null)).toBe(true);
  });

  it('given the type catalog, renders the committed fixture in spec type order end to end (F1)', () => {
    const nodes = buildFilteredGroupedView(LIST_FIXTURE, NO_FILTER, true, TYPE_ORDER_MAP);

    expect(nodes.map((node) => node.label)).toEqual([
      'epic',
      'feature',
      'task',
      'bug',
      'decision',
      'review',
      'guide',
    ]);
  });
});

function makeItem(id: string, type: string, isOpen: boolean): SqListItem {
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
    is_open: isOpen,
  };
}
