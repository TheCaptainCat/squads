import { describe, expect, it } from 'vitest';

import { buildRoleDirectory, NO_ROLE_DIRECTORY } from '../src/domain/roleDirectory';
import type { SqListItem } from '../src/types';

function makeRole(overrides: Partial<SqListItem> = {}): SqListItem {
  return {
    id: 'ROLE-1',
    sequence_id: 1,
    type: 'role',
    title: 'Catherine Manager',
    slug: 'manager',
    status: 'Active',
    description: 'Delegates work to the right specialists.',
    parent: null,
    author: 'manager',
    assignee: null,
    priority: null,
    severity: null,
    labels: [],
    refs: [],
    path: 'agents/roles/ROLE-000001-manager.md',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

describe('buildRoleDirectory', () => {
  it('resolves a known slug to its role item id and a hover text with name, slug, and mission', () => {
    const dir = buildRoleDirectory([makeRole()]);
    const mention = dir.get('manager');
    expect(mention?.id).toBe('ROLE-1');
    expect(mention?.hoverText).toBe(
      'Catherine Manager (manager) — Delegates work to the right specialists.',
    );
  });

  it('omits the mission suffix when a role has no description', () => {
    const dir = buildRoleDirectory([makeRole({ description: '' })]);
    expect(dir.get('manager')?.hoverText).toBe('Catherine Manager (manager)');
  });

  it('returns an empty directory for an empty role list', () => {
    expect(buildRoleDirectory([]).size).toBe(0);
  });

  it('skips a non-role row rather than asserting against it', () => {
    const dir = buildRoleDirectory([
      makeRole({ type: 'operator', slug: 'op-pierre', title: 'Pierre Chat' }),
    ]);
    expect(dir.size).toBe(0);
  });

  it('carries one entry per role, keyed by slug', () => {
    const dir = buildRoleDirectory([
      makeRole(),
      makeRole({ id: 'ROLE-3', slug: 'tech-lead', title: 'Olivia Lead' }),
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
