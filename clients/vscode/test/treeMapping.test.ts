import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import { distinctTypesInTree, treeNodesToDisplay } from '../src/domain/treeMapping';
import type { SqTreeNode } from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const TREE_FIXTURE = JSON.parse(readFixture('tree.json')) as SqTreeNode[];

describe('treeNodesToDisplay', () => {
  it('maps the committed sq tree --json fixture into DisplayNodes, preserving hierarchy', () => {
    const nodes = treeNodesToDisplay(TREE_FIXTURE);

    expect(nodes).toHaveLength(1);
    expect(nodes[0]?.id).toBe('EPIC-99');
    expect(nodes[0]?.itemId).toBe('EPIC-99');
    expect(nodes[0]?.children[0]?.id).toBe('FEAT-100');
    expect(nodes[0]?.children[0]?.children.map((child) => child.id)).toEqual([
      'TASK-428',
      'TASK-429',
      'TASK-430',
      'TASK-431',
      'TASK-432',
      'TASK-433',
      'TASK-434',
      'TASK-439',
      'TASK-440',
      'TASK-441',
      'TASK-442',
    ]);
  });

  it("labels a node from the tree payload's own title field, with no separate lookup", () => {
    const nodes = treeNodesToDisplay(TREE_FIXTURE);

    expect(nodes[0]?.label).toBe('EPIC-99  VS Code extension — browse the squad in the editor');
    const feature = nodes[0]?.children[0];
    expect(feature?.label).toBe('FEAT-100  Read-only browse: sidebar tree + rendered preview');
    const task = feature?.children.find((child) => child.id === 'TASK-440');
    expect(task?.label).toBe(
      'TASK-440  Client: consume tree title + is_open, collapse to one sq tree call',
    );
  });

  it('surfaces status and assignee in the description, unassigned when null', () => {
    const nodes = treeNodesToDisplay(TREE_FIXTURE);
    const feature = nodes[0]?.children[0];

    expect(feature?.description).toBe('Ready · unassigned');

    const task = feature?.children.find((child) => child.id === 'TASK-428');
    expect(task?.description).toBe('Done · typescript-dev');
  });

  it('marks blocked nodes distinctly in both the flag and the description', () => {
    const blockedFixture: SqTreeNode[] = [
      {
        id: 'TASK-999',
        type: 'task',
        title: 'Some blocked task',
        status: 'Ready',
        priority: null,
        assignee: null,
        blocked: true,
        is_open: true,
        children: [],
      },
    ];
    const [node] = treeNodesToDisplay(blockedFixture);

    expect(node?.blocked).toBe(true);
    expect(node?.description).toBe('Ready · unassigned · blocked');
    expect(node?.tooltip).toContain('Blocked: yes');
  });

  it('includes priority in the tooltip only when present', () => {
    const baseNode: SqTreeNode = {
      id: 'EPIC-1',
      type: 'epic',
      title: 'Some epic',
      status: 'Ready',
      priority: 'high',
      assignee: null,
      blocked: false,
      is_open: true,
      children: [],
    };
    const withPriority: SqTreeNode[] = [baseNode];
    const withoutPriority: SqTreeNode[] = [{ ...baseNode, priority: null }];

    expect(treeNodesToDisplay(withPriority)[0]?.tooltip).toContain('Priority: high');
    expect(treeNodesToDisplay(withoutPriority)[0]?.tooltip).not.toContain('Priority');
  });

  it('filters out the three reserved meta types (role/skill/operator) at every depth', () => {
    const withReserved: SqTreeNode[] = [
      {
        id: 'ROLE-1',
        type: 'role',
        title: 'Some role',
        status: 'Active',
        priority: null,
        assignee: null,
        blocked: false,
        is_open: true,
        children: [],
      },
      {
        id: 'SKILL-1',
        type: 'skill',
        title: 'Some skill',
        status: 'Active',
        priority: null,
        assignee: null,
        blocked: false,
        is_open: true,
        children: [],
      },
      {
        id: 'OP-1',
        type: 'operator',
        title: 'Some operator',
        status: 'Active',
        priority: null,
        assignee: null,
        blocked: false,
        is_open: true,
        children: [],
      },
      {
        id: 'EPIC-1',
        type: 'epic',
        title: 'Some epic',
        status: 'Ready',
        priority: null,
        assignee: null,
        blocked: false,
        is_open: true,
        children: [
          {
            id: 'ROLE-2',
            type: 'role',
            title: 'Nested role',
            status: 'Active',
            priority: null,
            assignee: null,
            blocked: false,
            is_open: true,
            children: [],
          },
          {
            id: 'FEAT-1',
            type: 'feature',
            title: 'Some feature',
            status: 'Ready',
            priority: null,
            assignee: null,
            blocked: false,
            is_open: true,
            children: [],
          },
        ],
      },
    ];

    const nodes = treeNodesToDisplay(withReserved);

    expect(nodes.map((node) => node.id)).toEqual(['EPIC-1']);
    expect(nodes[0]?.children.map((child) => child.id)).toEqual(['FEAT-1']);
  });

  it('assigns a codicon id per type and falls back for unrecognized/custom types', () => {
    const nodes: SqTreeNode[] = [
      {
        id: 'BUG-1',
        type: 'bug',
        title: 'Some bug',
        status: 'Open',
        priority: null,
        assignee: null,
        blocked: false,
        is_open: true,
        children: [],
      },
      {
        id: 'CUSTOM-1',
        type: 'widget',
        title: 'Some widget',
        status: 'Open',
        priority: null,
        assignee: null,
        blocked: false,
        is_open: true,
        children: [],
      },
    ];
    const mapped = treeNodesToDisplay(nodes);

    expect(mapped.find((node) => node.id === 'BUG-1')?.iconId).toBe('bug');
    expect(mapped.find((node) => node.id === 'CUSTOM-1')?.iconId).toBe('circle-outline');
  });
});

describe('distinctTypesInTree', () => {
  it('lists distinct non-reserved types found anywhere in the committed fixture, sorted', () => {
    expect(distinctTypesInTree(TREE_FIXTURE)).toEqual(['epic', 'feature', 'task']);
  });

  it('excludes the three reserved meta types even when present at depth', () => {
    const withReserved: SqTreeNode[] = [
      {
        id: 'EPIC-1',
        type: 'epic',
        title: 'Some epic',
        status: 'Ready',
        priority: null,
        assignee: null,
        blocked: false,
        is_open: true,
        children: [
          {
            id: 'ROLE-2',
            type: 'role',
            title: 'Nested role',
            status: 'Active',
            priority: null,
            assignee: null,
            blocked: false,
            is_open: true,
            children: [],
          },
          {
            id: 'BUG-1',
            type: 'bug',
            title: 'Some bug',
            status: 'Open',
            priority: null,
            assignee: null,
            blocked: false,
            is_open: true,
            children: [],
          },
        ],
      },
    ];

    expect(distinctTypesInTree(withReserved)).toEqual(['bug', 'epic']);
  });
});
