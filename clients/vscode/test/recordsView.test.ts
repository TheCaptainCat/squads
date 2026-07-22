import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import { buildRecordsView } from '../src/domain/recordsView';
import { buildRoleCatalogMap, buildStatusRoleMap } from '../src/domain/statusRole';
import { buildCategoryMap, NO_CATEGORIES } from '../src/domain/typeCategory';
import { buildTypeOrderMap } from '../src/domain/typeOrder';
import type {
  SqListItem,
  SqRoleCatalogEntry,
  SqStatusCatalogEntry,
  SqTypeCatalogEntry,
} from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const TYPE_CATALOG_FIXTURE = JSON.parse(readFixture('type-catalog.json')) as SqTypeCatalogEntry[];
const CATEGORY_MAP = buildCategoryMap(TYPE_CATALOG_FIXTURE);
const ORDER_MAP = buildTypeOrderMap(TYPE_CATALOG_FIXTURE);
const STATUSES_CATALOG_FIXTURE = JSON.parse(
  readFixture('statuses-catalog.json'),
) as SqStatusCatalogEntry[];
const ROLES_CATALOG_FIXTURE = JSON.parse(readFixture('roles-catalog.json')) as SqRoleCatalogEntry[];

function makeItem(id: string, type: string, status = 'Ready'): SqListItem {
  const sequenceId = Number(id.split('-')[1] ?? '0');
  return {
    id,
    sequence_id: sequenceId,
    type,
    title: `${id} title`,
    slug: id.toLowerCase(),
    status,
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

describe('buildRecordsView', () => {
  it('buckets by every declared records-category type, in spec order, from the committed catalog', () => {
    const items: SqListItem[] = [
      makeItem('GUIDE-1', 'guide'),
      makeItem('ADR-1', 'decision'),
      makeItem('TASK-1', 'task'),
    ];

    const nodes = buildRecordsView(items, CATEGORY_MAP, ORDER_MAP);

    // Spec order: decision(50) before guide(70).
    expect(nodes.map((node) => node.label)).toEqual(['decision', 'guide']);
    expect(nodes.every((node) => node.itemId === null)).toBe(true);
  });

  it('never leaks a work or roster item into a records bucket', () => {
    const items: SqListItem[] = [
      makeItem('ADR-1', 'decision'),
      makeItem('TASK-1', 'task'),
      makeItem('ROLE-1', 'role'),
    ];

    const nodes = buildRecordsView(items, CATEGORY_MAP, ORDER_MAP);
    const allLeafIds = nodes.flatMap((group) => group.children.map((leaf) => leaf.itemId));

    expect(allLeafIds).toEqual(['ADR-1']);
  });

  it('each declared records bucket is present even with 0 items', () => {
    const nodes = buildRecordsView([], CATEGORY_MAP, ORDER_MAP);

    expect(nodes.map((node) => node.label)).toEqual(['decision', 'guide']);
    expect(nodes.every((node) => node.children.length === 0)).toBe(true);
    expect(nodes.map((node) => node.description)).toEqual(['0 items', '0 items']);
  });

  it('is spec-driven: a custom records-category type gets its own bucket with no code change', () => {
    const extendedCatalog: SqTypeCatalogEntry[] = [
      ...TYPE_CATALOG_FIXTURE,
      { type: 'contract', order: 55, prefix: 'CTR', reserved: false, category: 'records' },
    ];
    const categoryMap = buildCategoryMap(extendedCatalog);
    const orderMap = buildTypeOrderMap(extendedCatalog);
    const items: SqListItem[] = [makeItem('CTR-1', 'contract')];

    const nodes = buildRecordsView(items, categoryMap, orderMap);

    // Spec order: decision(50) < contract(55) < guide(70).
    expect(nodes.map((node) => node.label)).toEqual(['decision', 'contract', 'guide']);
    expect(nodes.find((node) => node.label === 'contract')?.children.map((c) => c.itemId)).toEqual([
      'CTR-1',
    ]);
  });

  it('sorts leaves within a bucket by numeric id order, not lexicographic', () => {
    const items: SqListItem[] = [
      makeItem('ADR-10', 'decision'),
      makeItem('ADR-2', 'decision'),
      makeItem('ADR-9', 'decision'),
    ];

    const nodes = buildRecordsView(items, CATEGORY_MAP, ORDER_MAP);
    const decisions = nodes.find((node) => node.label === 'decision');

    expect(decisions?.children.map((child) => child.itemId)).toEqual(['ADR-2', 'ADR-9', 'ADR-10']);
  });

  it('with NO_CATEGORIES (the graceful fallback), yields no buckets rather than guessing', () => {
    const items: SqListItem[] = [makeItem('ADR-1', 'decision')];

    expect(buildRecordsView(items, NO_CATEGORIES, ORDER_MAP)).toEqual([]);
  });

  it('marks a closed/hidden/coloured leaf via the statuses/roles catalog join', () => {
    const statusRoles = buildStatusRoleMap(STATUSES_CATALOG_FIXTURE);
    const roleCatalog = buildRoleCatalogMap(ROLES_CATALOG_FIXTURE);
    const items: SqListItem[] = [makeItem('ADR-1', 'decision', 'Accepted')];

    const nodes = buildRecordsView(
      items,
      CATEGORY_MAP,
      ORDER_MAP,
      {},
      undefined,
      undefined,
      statusRoles,
      roleCatalog,
    );
    const leaf = nodes.find((node) => node.label === 'decision')?.children[0];

    // Accepted ("in_force" role): settled but NOT hidden — shows in its own colour.
    expect(leaf?.closed).toBe(true);
    expect(leaf?.hidden).toBe(false);
    expect(leaf?.colorIntent).toBe('info');
  });

  it('gives a leaf its bundled per-type icon (decision -> lightbulb, guide -> book)', () => {
    const items: SqListItem[] = [makeItem('ADR-1', 'decision'), makeItem('GUIDE-1', 'guide')];

    const nodes = buildRecordsView(items, CATEGORY_MAP, ORDER_MAP);

    expect(nodes.find((node) => node.label === 'decision')?.children[0]?.iconId).toBe('lightbulb');
    expect(nodes.find((node) => node.label === 'guide')?.children[0]?.iconId).toBe('book');
  });
});
