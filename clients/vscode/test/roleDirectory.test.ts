import { describe, expect, it } from 'vitest';

import { NO_PRONOUNS_CONTEXT } from '../src/domain/pronouns';
import { buildRoleDirectory, NO_ROLE_DIRECTORY } from '../src/domain/roleDirectory';
import { buildRoleCatalogMap, buildStatusRoleMap } from '../src/domain/statusRole';
import type { SqRoleListRow } from '../src/types';

function makeRole(overrides: Partial<SqRoleListRow> = {}): SqRoleListRow {
  return {
    id: 'ROLE-1',
    slug: 'manager',
    full_name: 'Catherine Manager',
    pronouns: null,
    status: 'Active',
    description: 'Delegates work to the right specialists.',
    ...overrides,
  };
}

describe('buildRoleDirectory', () => {
  it.each([
    {
      kind: 'a catalog role',
      row: makeRole(),
      id: 'ROLE-1',
      hover: 'Catherine Manager (manager) — Delegates work to the right specialists.',
    },
    {
      kind: 'a template role',
      row: makeRole({
        id: 'ROLE-9',
        slug: 'python-dev',
        full_name: 'Elias Python',
        description: 'Writes and reviews Python code.',
      }),
      id: 'ROLE-9',
      hover: 'Elias Python (python-dev) — Writes and reviews Python code.',
    },
    {
      kind: 'an item-defined role',
      row: makeRole({
        id: 'ROLE-12',
        slug: 'release-captain',
        full_name: 'Rhea Captain',
        description: 'Cuts the release.',
      }),
      id: 'ROLE-12',
      hover: 'Rhea Captain (release-captain) — Cuts the release.',
    },
    {
      kind: 'a role with an empty description',
      row: makeRole({ description: '' }),
      id: 'ROLE-1',
      hover: 'Catherine Manager (manager)',
    },
    {
      kind: 'a role whose row omits the description',
      row: { id: 'ROLE-1', slug: 'manager', full_name: 'Catherine Manager', status: 'Active' },
      id: 'ROLE-1',
      hover: 'Catherine Manager (manager)',
    },
  ])('resolves $kind to its id and hover text', ({ row, id, hover }) => {
    const mention = buildRoleDirectory([row]).get(row.slug);
    expect(mention?.id).toBe(id);
    expect(mention?.hoverText).toBe(hover);
  });

  it('leaves out a role whose status resolves to a hidden role', () => {
    const vocabulary = {
      statusRoles: buildStatusRoleMap([
        { status: 'Active', role: 'active', badge: null },
        { status: 'Archived', role: 'retired', badge: null },
      ]),
      roles: buildRoleCatalogMap([
        { role: 'active', settled: false, hidden: false, color: 'positive', live: true },
        { role: 'retired', settled: true, hidden: true, color: 'muted', live: false },
      ]),
    };
    const dir = buildRoleDirectory(
      [makeRole(), makeRole({ id: 'ROLE-7', slug: 'old-role', status: 'Archived' })],
      NO_PRONOUNS_CONTEXT,
      vocabulary,
    );
    expect([...dir.keys()]).toEqual(['manager']);
  });

  it('keeps every role when the status vocabulary is unavailable', () => {
    const dir = buildRoleDirectory([makeRole({ slug: 'old-role', status: 'Archived' })]);
    expect(dir.has('old-role')).toBe(true);
  });

  it('returns an empty directory for an empty role list', () => {
    expect(buildRoleDirectory([]).size).toBe(0);
  });

  it('carries one entry per role, keyed by slug', () => {
    const dir = buildRoleDirectory([
      makeRole(),
      makeRole({ id: 'ROLE-3', slug: 'tech-lead', full_name: 'Olivia Lead' }),
    ]);
    expect(dir.size).toBe(2);
    expect(dir.get('tech-lead')?.id).toBe('ROLE-3');
  });
});

describe('NO_ROLE_DIRECTORY', () => {
  it('is an empty map, the degrade-gracefully default', () => {
    expect(NO_ROLE_DIRECTORY.size).toBe(0);
  });
});

describe('buildRoleDirectory pronouns', () => {
  const pronouns = new Map([['manager', 'she/her']]);

  it('follows the name with the pronouns when enabled', () => {
    const dir = buildRoleDirectory([makeRole({ description: '' })], { pronouns, enabled: true });
    expect(dir.get('manager')?.hoverText).toBe('Catherine Manager (she/her) (manager)');
  });

  it('leaves the hover text unchanged when disabled or unset', () => {
    const off = buildRoleDirectory([makeRole({ description: '' })], { pronouns, enabled: false });
    const unset = buildRoleDirectory([makeRole({ description: '' })], {
      pronouns: new Map(),
      enabled: true,
    });
    expect(off.get('manager')?.hoverText).toBe('Catherine Manager (manager)');
    expect(unset.get('manager')?.hoverText).toBe('Catherine Manager (manager)');
  });
});
