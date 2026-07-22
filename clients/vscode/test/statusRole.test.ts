import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  buildRoleCatalogMap,
  buildStatusRoleMap,
  NO_ROLES,
  NO_STATUS_ROLES,
  resolveRole,
} from '../src/domain/statusRole';
import type { SqRoleCatalogEntry, SqStatusCatalogEntry } from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const STATUSES_CATALOG_FIXTURE = JSON.parse(
  readFixture('statuses-catalog.json'),
) as SqStatusCatalogEntry[];
const ROLES_CATALOG_FIXTURE = JSON.parse(readFixture('roles-catalog.json')) as SqRoleCatalogEntry[];

describe('buildStatusRoleMap', () => {
  it('preserves the declared role name for any status, including a non-"active" one', () => {
    const statusRoles = buildStatusRoleMap(STATUSES_CATALOG_FIXTURE);

    expect(statusRoles.get('Superseded')).toBe('superseded');
    expect(statusRoles.get('InProgress')).toBe('active');
  });
});

describe('buildRoleCatalogMap', () => {
  it('resolves each declared role to its settled/hidden/color object', () => {
    const roles = buildRoleCatalogMap(ROLES_CATALOG_FIXTURE);

    expect(roles.get('active')).toEqual({ settled: false, hidden: false, color: 'positive' });
    expect(roles.get('in_force')).toEqual({ settled: true, hidden: false, color: 'info' });
    expect(roles.get('done')).toEqual({ settled: true, hidden: true, color: 'positive' });
  });

  it('falls back to "neutral" for a color intent outside the closed vocabulary', () => {
    const roles = buildRoleCatalogMap([
      { role: 'custom', settled: false, hidden: false, color: 'not-a-real-intent' },
    ]);

    expect(roles.get('custom')?.color).toBe('neutral');
  });
});

describe('resolveRole', () => {
  const statusRoles = buildStatusRoleMap(STATUSES_CATALOG_FIXTURE);
  const roles = buildRoleCatalogMap(ROLES_CATALOG_FIXTURE);

  it('joins a status through its declared role name to the role catalog object', () => {
    expect(resolveRole('InProgress', statusRoles, roles)).toEqual({
      settled: false,
      hidden: false,
      color: 'positive',
    });
  });

  it('resolves the "in_force" role for Accepted — settled but NOT hidden, unlike "done"', () => {
    const accepted = resolveRole('Accepted', statusRoles, roles);
    expect(accepted).toEqual({ settled: true, hidden: false, color: 'info' });
  });

  it('resolves the "done" role for Done — settled AND hidden', () => {
    const done = resolveRole('Done', statusRoles, roles);
    expect(done).toEqual({ settled: true, hidden: true, color: 'positive' });
  });

  it('returns null for a status absent from the catalog (a custom/unrecognized status)', () => {
    expect(resolveRole('SomeCustomStatus', statusRoles, roles)).toBeNull();
  });

  it('returns null when the statuses catalog names a role absent from the roles catalog', () => {
    const partialStatusRoles = buildStatusRoleMap([
      { status: 'Weird', role: 'nonexistent', badge: null },
    ]);
    expect(resolveRole('Weird', partialStatusRoles, roles)).toBeNull();
  });

  it('with NO_STATUS_ROLES/NO_ROLES (the graceful fallback), every status resolves to null', () => {
    expect(resolveRole('InProgress', NO_STATUS_ROLES, NO_ROLES)).toBeNull();
    expect(resolveRole('InProgress', statusRoles, NO_ROLES)).toBeNull();
  });
});
