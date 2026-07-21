import { describe, expect, it } from 'vitest';

import {
  buildTooltip,
  collectNodeIds,
  type DisplayNode,
  emphasisForNode,
  emptyStateDisplayNode,
  errorDisplayNode,
  groupDisplayNode,
} from '../src/domain/displayNode';

function leaf(id: string): DisplayNode {
  return {
    id,
    itemId: id,
    label: id,
    description: '',
    tooltip: '',
    iconId: 'circle-outline',
    blocked: false,
    closed: false,
    active: false,
    children: [],
  };
}

describe('emphasisForNode', () => {
  it('is "none" when blocked/closed/active are all false', () => {
    expect(emphasisForNode({ blocked: false, closed: false, active: false })).toBe('none');
  });

  it('is "active" (green) when only active is true', () => {
    expect(emphasisForNode({ blocked: false, closed: false, active: true })).toBe('active');
  });

  it('is "closed" (dimmed) when only closed is true', () => {
    expect(emphasisForNode({ blocked: false, closed: true, active: false })).toBe('closed');
  });

  it('is "blocked" (red) when only blocked is true', () => {
    expect(emphasisForNode({ blocked: true, closed: false, active: false })).toBe('blocked');
  });

  it('closed wins over active when somehow both are set (F26/F7 disjoint-in-practice, but the precedence still resolves deterministically)', () => {
    expect(emphasisForNode({ blocked: false, closed: true, active: true })).toBe('closed');
  });

  it('blocked wins over both closed and active — the highest-priority emphasis', () => {
    expect(emphasisForNode({ blocked: true, closed: true, active: true })).toBe('blocked');
    expect(emphasisForNode({ blocked: true, closed: false, active: true })).toBe('blocked');
  });
});

describe('buildTooltip', () => {
  it('backslash-escapes markdown metacharacters in the assignee name (REV-485 F3)', () => {
    const tooltip = buildTooltip({
      id: 'TASK-1',
      type: 'task',
      status: 'InProgress',
      assignee: '_Ada_ *Typescript* `dev`',
      badges: [],
      blocked: false,
    });
    expect(tooltip).toContain('Assignee: \\_Ada\\_ \\*Typescript\\* \\`dev\\`');
  });

  it('leaves an unassigned tooltip line unescaped', () => {
    const tooltip = buildTooltip({
      id: 'TASK-1',
      type: 'task',
      status: 'InProgress',
      assignee: null,
      badges: [],
      blocked: false,
    });
    expect(tooltip).toContain('Assignee: unassigned');
  });
});

describe('emptyStateDisplayNode', () => {
  it('renders the message as a plain, non-error label', () => {
    const node = emptyStateDisplayNode('No squad detected here');
    expect(node.label).toBe('No squad detected here');
    expect(node.description).toBe('');
    expect(node.tooltip).toBe('No squad detected here');
    expect(node.children).toEqual([]);
  });

  it('carries none of the emphasis flags — no error/blocked/closed styling', () => {
    const node = emptyStateDisplayNode('No squad detected here');
    expect(node.blocked).toBe(false);
    expect(node.closed).toBe(false);
    expect(node.active).toBe(false);
  });

  it('uses a distinct icon and id from errorDisplayNode, so the two never collide or share styling', () => {
    const empty = emptyStateDisplayNode('No squad detected here');
    const error = errorDisplayNode('boom');
    expect(empty.iconId).not.toBe(error.iconId);
    expect(empty.id).not.toBe(error.id);
  });
});

describe('collectNodeIds', () => {
  it('collects a single root leaf with no children', () => {
    expect(collectNodeIds([leaf('node-1')])).toEqual(new Set(['node-1']));
  });

  it('walks nested children, collecting every id at every depth', () => {
    const child = leaf('node-2');
    const grandchild = leaf('node-3');
    const withChildren: DisplayNode = { ...child, children: [grandchild] };
    const root: DisplayNode = { ...leaf('node-1'), children: [withChildren] };

    expect(collectNodeIds([root])).toEqual(new Set(['node-1', 'node-2', 'node-3']));
  });

  it('collects group node ids alongside their leaves (the flat/grouped and meta views)', () => {
    const group = groupDisplayNode('group:type:task', 'task', 1, [leaf('node-1')]);

    expect(collectNodeIds([group])).toEqual(new Set(['group:type:task', 'node-1']));
  });

  it('returns an empty set for an empty tree', () => {
    expect(collectNodeIds([])).toEqual(new Set());
  });
});
