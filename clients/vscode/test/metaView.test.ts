import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import { buildMetaView } from '../src/domain/metaView';
import { buildRoleCatalogMap, buildStatusRoleMap } from '../src/domain/statusRole';
import { buildTypeLabelMap } from '../src/domain/typeLabels';
import type {
  SqListItem,
  SqRoleCatalogEntry,
  SqStatusCatalogEntry,
  SqTypeCatalogEntry,
} from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const LIST_FIXTURE = JSON.parse(readFixture('list.json')) as SqListItem[];
const TYPE_CATALOG_FIXTURE = JSON.parse(readFixture('type-catalog.json')) as SqTypeCatalogEntry[];
const LABEL_MAP = buildTypeLabelMap(TYPE_CATALOG_FIXTURE);
const STATUSES_CATALOG_FIXTURE = JSON.parse(
  readFixture('statuses-catalog.json'),
) as SqStatusCatalogEntry[];
const ROLES_CATALOG_FIXTURE = JSON.parse(readFixture('roles-catalog.json')) as SqRoleCatalogEntry[];

describe('buildMetaView', () => {
  it('always returns exactly the 3 fixed buckets, in Roles/Skills/Operators order, with labels resolved from the catalog (matching the previously hard-coded literals)', () => {
    const nodes = buildMetaView(
      LIST_FIXTURE,
      undefined,
      undefined,
      undefined,
      undefined,
      LABEL_MAP,
    );

    expect(nodes.map((node) => node.label)).toEqual(['Roles', 'Skills', 'Operators']);
    expect(nodes.every((node) => node.itemId === null)).toBe(true);
  });

  it('with no labelMap (the graceful fallback), falls back to the raw type string, same as every other tree', () => {
    const nodes = buildMetaView(LIST_FIXTURE);

    expect(nodes.map((node) => node.label)).toEqual(['role', 'skill', 'operator']);
  });

  it('buckets each reserved type into its matching folder, from the committed fixture', () => {
    const nodes = buildMetaView(LIST_FIXTURE);
    const [roles, skills, operators] = nodes;

    expect(roles?.children.map((child) => child.itemId)).toEqual(['ROLE-1', 'ROLE-2']);
    expect(skills?.children.map((child) => child.itemId)).toEqual(['SKILL-192', 'SKILL-193']);
    expect(operators?.children.map((child) => child.itemId)).toEqual(['OP-10']);
  });

  it('never leaks a non-reserved (work-item) type into any bucket', () => {
    const nodes = buildMetaView(LIST_FIXTURE);
    const allLeafIds = nodes.flatMap((group) => group.children.map((leaf) => leaf.itemId));

    expect(allLeafIds).not.toContain('EPIC-99');
    expect(allLeafIds).not.toContain('TASK-42');
  });

  it('sorts leaves within a bucket by numeric id order, not lexicographic', () => {
    const items: SqListItem[] = [
      makeItem('ROLE-10', 'role'),
      makeItem('ROLE-2', 'role'),
      makeItem('ROLE-9', 'role'),
    ];

    const [roles] = buildMetaView(items);

    expect(roles?.children.map((child) => child.itemId)).toEqual(['ROLE-2', 'ROLE-9', 'ROLE-10']);
  });

  it('still emits all 3 buckets, empty, when no meta items are present', () => {
    const nodes = buildMetaView([], undefined, undefined, undefined, undefined, LABEL_MAP);

    expect(nodes.map((node) => node.label)).toEqual(['Roles', 'Skills', 'Operators']);
    expect(nodes.every((node) => node.children.length === 0)).toBe(true);
    expect(nodes.map((node) => node.description)).toEqual(['0 items', '0 items', '0 items']);
  });

  it('marks a closed/hidden/coloured meta item via the statuses/roles catalog join, once shown', () => {
    const statusRoles = buildStatusRoleMap(STATUSES_CATALOG_FIXTURE);
    const roleCatalog = buildRoleCatalogMap(ROLES_CATALOG_FIXTURE);
    const items: SqListItem[] = [
      { ...makeItem('ROLE-1', 'role'), status: 'Active' },
      { ...makeItem('ROLE-2', 'role'), status: 'Archived' },
    ];

    // showArchived: true — otherwise the archived leaf is excluded before it ever reaches the
    // marking this test checks (see the default-hides-archived test below).
    const [roles] = buildMetaView(
      items,
      undefined,
      undefined,
      statusRoles,
      roleCatalog,
      undefined,
      {
        showArchived: true,
        statusFilter: null,
        groupByType: true,
      },
    );

    // Active ("active" role): not settled, not hidden, positive colour.
    const active = roles?.children.find((child) => child.itemId === 'ROLE-1');
    expect(active?.closed).toBe(false);
    expect(active?.hidden).toBe(false);
    expect(active?.colorIntent).toBe('positive');

    // Archived ("retired" role): settled AND hidden.
    const archived = roles?.children.find((child) => child.itemId === 'ROLE-2');
    expect(archived?.closed).toBe(true);
    expect(archived?.hidden).toBe(true);
  });

  it('hides an archived (hidden-role) item by default, unlike a merely settled-but-visible one', () => {
    const statusRoles = buildStatusRoleMap(STATUSES_CATALOG_FIXTURE);
    const roleCatalog = buildRoleCatalogMap(ROLES_CATALOG_FIXTURE);
    const items: SqListItem[] = [
      { ...makeItem('ROLE-1', 'role'), status: 'Active' },
      { ...makeItem('ROLE-2', 'role'), status: 'Archived' },
    ];

    const [roles] = buildMetaView(items, undefined, undefined, statusRoles, roleCatalog);

    expect(roles?.children.map((child) => child.itemId)).toEqual(['ROLE-1']);
    expect(roles?.description).toBe('1 item');
  });

  it('with groupByType: false, flattens every bucket into one id-sorted list of leaves', () => {
    const items: SqListItem[] = [
      makeItem('SKILL-193', 'skill'),
      makeItem('ROLE-2', 'role'),
      makeItem('OP-10', 'operator'),
      makeItem('ROLE-1', 'role'),
    ];

    const nodes = buildMetaView(items, undefined, undefined, undefined, undefined, undefined, {
      showArchived: false,
      statusFilter: null,
      groupByType: false,
    });

    // compareIds sorts the whole id string (numeric-aware), not grouped by type prefix first —
    // "OP-10" sorts before "ROLE-1" alphabetically on the prefix.
    expect(nodes.map((node) => node.itemId)).toEqual(['OP-10', 'ROLE-1', 'ROLE-2', 'SKILL-193']);
    // Flattened, so there are no group wrapper nodes left to hold children.
    expect(nodes.every((node) => node.children.length === 0)).toBe(true);
  });

  it('flattening still excludes a non-roster type and an archived (hidden-by-default) entry', () => {
    const items: SqListItem[] = [
      makeItem('ROLE-1', 'role'),
      makeItem('EPIC-99', 'epic'),
      { ...makeItem('ROLE-2', 'role'), status: 'Archived' },
    ];
    const statusRoles = buildStatusRoleMap(STATUSES_CATALOG_FIXTURE);
    const roleCatalog = buildRoleCatalogMap(ROLES_CATALOG_FIXTURE);

    const nodes = buildMetaView(items, undefined, undefined, statusRoles, roleCatalog, undefined, {
      showArchived: false,
      statusFilter: null,
      groupByType: false,
    });

    expect(nodes.map((node) => node.itemId)).toEqual(['ROLE-1']);
  });

  it('with no statusRoles/roleCatalog (the graceful fallback), no roster item is ever hidden or coloured', () => {
    const items: SqListItem[] = [{ ...makeItem('ROLE-1', 'role'), status: 'Active' }];

    const [roles] = buildMetaView(items);

    expect(roles?.children[0]?.hidden).toBe(false);
    expect(roles?.children[0]?.colorIntent).toBeNull();
  });

  it('shows status alone in the description, with no assignee segment', () => {
    const items: SqListItem[] = [{ ...makeItem('ROLE-1', 'role'), assignee: 'op-pierre' }];

    const [roles] = buildMetaView(items);

    expect(roles?.children[0]?.description).toBe('Active');
  });

  it('gives each of the 3 reserved meta types a distinct, non-generic codicon', () => {
    const items: SqListItem[] = [
      makeItem('ROLE-1', 'role'),
      makeItem('SKILL-1', 'skill'),
      makeItem('OP-1', 'operator'),
    ];

    const [roles, skills, operators] = buildMetaView(items);

    expect(roles?.children[0]?.iconId).toBe('hubot');
    expect(skills?.children[0]?.iconId).toBe('mortar-board');
    expect(operators?.children[0]?.iconId).toBe('account');
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
