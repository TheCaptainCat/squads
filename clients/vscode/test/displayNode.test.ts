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
    hidden: false,
    colorIntent: null,
    children: [],
  };
}

describe('emphasisForNode', () => {
  it('is "none" when blocked/hidden are false and colorIntent is null', () => {
    expect(emphasisForNode({ blocked: false, hidden: false, colorIntent: null })).toBe('none');
  });

  it('is "none" when colorIntent resolves to "neutral" — the default appearance, not a distinct colour', () => {
    expect(emphasisForNode({ blocked: false, hidden: false, colorIntent: 'neutral' })).toBe('none');
  });

  it('is the resolved colour intent when only colorIntent is set (non-neutral)', () => {
    expect(emphasisForNode({ blocked: false, hidden: false, colorIntent: 'positive' })).toBe(
      'positive',
    );
    expect(emphasisForNode({ blocked: false, hidden: false, colorIntent: 'info' })).toBe('info');
  });

  it('is "hidden" (dimmed) when only hidden is true', () => {
    expect(emphasisForNode({ blocked: false, hidden: true, colorIntent: null })).toBe('hidden');
  });

  it('is "blocked" (red) when only blocked is true', () => {
    expect(emphasisForNode({ blocked: true, hidden: false, colorIntent: null })).toBe('blocked');
  });

  it('hidden wins over a colour intent when somehow both are set — a settled-AND-hidden role (e.g. "done") still just dims', () => {
    expect(emphasisForNode({ blocked: false, hidden: true, colorIntent: 'positive' })).toBe(
      'hidden',
    );
  });

  it('blocked wins over both hidden and colour — the highest-priority emphasis', () => {
    expect(emphasisForNode({ blocked: true, hidden: true, colorIntent: 'positive' })).toBe(
      'blocked',
    );
    expect(emphasisForNode({ blocked: true, hidden: false, colorIntent: 'danger' })).toBe(
      'blocked',
    );
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

  it('carries none of the emphasis flags — no error/blocked/hidden/colour styling', () => {
    const node = emptyStateDisplayNode('No squad detected here');
    expect(node.blocked).toBe(false);
    expect(node.closed).toBe(false);
    expect(node.hidden).toBe(false);
    expect(node.colorIntent).toBeNull();
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
