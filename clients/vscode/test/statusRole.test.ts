import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import { buildStatusRoleMap, isActiveRole, NO_STATUS_ROLES } from '../src/domain/statusRole';
import type { SqStatusCatalogEntry } from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const STATUSES_CATALOG_FIXTURE = JSON.parse(
  readFixture('statuses-catalog.json'),
) as SqStatusCatalogEntry[];

describe('isActiveRole', () => {
  const statusRoles = buildStatusRoleMap(STATUSES_CATALOG_FIXTURE);

  it('is true for InProgress, the bundled work-item "active" role status (F26)', () => {
    expect(isActiveRole('InProgress', statusRoles)).toBe(true);
  });

  it('is true for Active, the bundled roster "active" role status', () => {
    expect(isActiveRole('Active', statusRoles)).toBe(true);
  });

  it('is false for a terminal status, never keyed on the literal name', () => {
    expect(isActiveRole('Done', statusRoles)).toBe(false);
    expect(isActiveRole('Superseded', statusRoles)).toBe(false);
  });

  it('is false for a non-terminal status with no declared role (e.g. Draft, Ready)', () => {
    expect(isActiveRole('Draft', statusRoles)).toBe(false);
    expect(isActiveRole('Ready', statusRoles)).toBe(false);
  });

  it('is false for a status absent from the catalog (a custom/unrecognized status)', () => {
    expect(isActiveRole('SomeCustomStatus', statusRoles)).toBe(false);
  });

  it('with NO_STATUS_ROLES (the graceful-fallback default), every status is never active', () => {
    expect(isActiveRole('InProgress', NO_STATUS_ROLES)).toBe(false);
  });
});

describe('buildStatusRoleMap', () => {
  it('preserves a non-"active" role (e.g. "superseded") rather than collapsing it to false', () => {
    const statusRoles = buildStatusRoleMap(STATUSES_CATALOG_FIXTURE);

    expect(statusRoles.get('Superseded')).toBe('superseded');
    expect(isActiveRole('Superseded', statusRoles)).toBe(false);
  });
});
