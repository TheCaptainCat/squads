import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  allDeclaredStatuses,
  DEFAULT_META_VIEW_STATE,
  describeMetaFilterState,
  matchesMetaFilter,
  type MetaViewState,
} from '../src/domain/metaFilter';
import { buildRoleCatalogMap, buildStatusRoleMap } from '../src/domain/statusRole';
import type { SqListItem, SqRoleCatalogEntry, SqStatusCatalogEntry } from '../src/types';

// `groupByType` is irrelevant to every test below (it doesn't affect matchesMetaFilter or
// describeMetaFilterState), so tests only ever override showArchived/statusFilter through this.
function state(overrides: Partial<MetaViewState>): MetaViewState {
  return { ...DEFAULT_META_VIEW_STATE, ...overrides };
}

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const STATUSES_CATALOG_FIXTURE = JSON.parse(
  readFixture('statuses-catalog.json'),
) as SqStatusCatalogEntry[];
const ROLES_CATALOG_FIXTURE = JSON.parse(readFixture('roles-catalog.json')) as SqRoleCatalogEntry[];
const STATUS_ROLES = buildStatusRoleMap(STATUSES_CATALOG_FIXTURE);
const ROLE_CATALOG = buildRoleCatalogMap(ROLES_CATALOG_FIXTURE);

function makeItem(status: string): SqListItem {
  return {
    id: 'ROLE-1',
    sequence_id: 1,
    type: 'role',
    title: 'ROLE-1 title',
    slug: 'role-1',
    status,
    description: '',
    parent: null,
    author: null,
    assignee: null,
    priority: null,
    severity: null,
    labels: [],
    refs: [],
    path: 'roles/ROLE-1.md',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
}

describe('allDeclaredStatuses', () => {
  it('lists every status the catalog declares, sorted, not only ones a roster item happens to carry', () => {
    const statuses = allDeclaredStatuses(STATUSES_CATALOG_FIXTURE);

    // A decision-only status, never a role/skill/operator one, from the fixture — proves the
    // list isn't filtered down to roster-observed values.
    expect(statuses).toContain('Superseded');
    expect(statuses).toEqual([...statuses].sort((a, b) => a.localeCompare(b)));
  });
});

describe('matchesMetaFilter', () => {
  it('hides an archived (hidden-role) item by default', () => {
    const archived = makeItem('Archived');

    expect(
      matchesMetaFilter(
        archived,
        state({ showArchived: false, statusFilter: null }),
        STATUS_ROLES,
        ROLE_CATALOG,
      ),
    ).toBe(false);
  });

  it('shows an archived item once showArchived is on', () => {
    const archived = makeItem('Archived');

    expect(
      matchesMetaFilter(
        archived,
        state({ showArchived: true, statusFilter: null }),
        STATUS_ROLES,
        ROLE_CATALOG,
      ),
    ).toBe(true);
  });

  it('never hides a live (non-hidden-role) item, regardless of showArchived', () => {
    const active = makeItem('Active');

    expect(
      matchesMetaFilter(
        active,
        state({ showArchived: false, statusFilter: null }),
        STATUS_ROLES,
        ROLE_CATALOG,
      ),
    ).toBe(true);
  });

  it('a status filter matching a hidden-role status wins over showArchived being off', () => {
    const archived = makeItem('Archived');

    expect(
      matchesMetaFilter(
        archived,
        state({ showArchived: false, statusFilter: 'Archived' }),
        STATUS_ROLES,
        ROLE_CATALOG,
      ),
    ).toBe(true);
  });

  it('a status filter excludes anything not matching it, even when showArchived is on', () => {
    const active = makeItem('Active');

    expect(
      matchesMetaFilter(
        active,
        state({ showArchived: true, statusFilter: 'Draft' }),
        STATUS_ROLES,
        ROLE_CATALOG,
      ),
    ).toBe(false);
  });
});

describe('describeMetaFilterState', () => {
  it('is undefined at the default state', () => {
    expect(
      describeMetaFilterState(state({ showArchived: false, statusFilter: null })),
    ).toBeUndefined();
  });

  it('names the status filter when set, regardless of showArchived', () => {
    expect(describeMetaFilterState(state({ showArchived: false, statusFilter: 'Draft' }))).toBe(
      'Filtered: Draft',
    );
  });

  it('reports archived-shown when the toggle is on and no status filter is set', () => {
    expect(describeMetaFilterState(state({ showArchived: true, statusFilter: null }))).toBe(
      'Archived shown',
    );
  });
});
