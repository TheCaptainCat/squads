import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import { buildMetaView } from '../src/domain/metaView';
import type { SqListItem } from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const LIST_FIXTURE = JSON.parse(readFixture('list.json')) as SqListItem[];

describe('buildMetaView', () => {
  it('always returns exactly the 3 fixed buckets, in Roles/Skills/Operators order', () => {
    const nodes = buildMetaView(LIST_FIXTURE);

    expect(nodes.map((node) => node.label)).toEqual(['Roles', 'Skills', 'Operators']);
    expect(nodes.every((node) => node.itemId === null)).toBe(true);
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
    const nodes = buildMetaView([]);

    expect(nodes.map((node) => node.label)).toEqual(['Roles', 'Skills', 'Operators']);
    expect(nodes.every((node) => node.children.length === 0)).toBe(true);
    expect(nodes.map((node) => node.description)).toEqual(['0 items', '0 items', '0 items']);
  });

  it('marks a closed meta item via DisplayNode.closed, derived from is_open', () => {
    const items: SqListItem[] = [
      { ...makeItem('OP-1', 'operator'), is_open: false },
      { ...makeItem('OP-2', 'operator'), is_open: true },
    ];

    const [, , operators] = buildMetaView(items);

    expect(operators?.children.find((child) => child.itemId === 'OP-1')?.closed).toBe(true);
    expect(operators?.children.find((child) => child.itemId === 'OP-2')?.closed).toBe(false);
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
    is_open: true,
  };
}
