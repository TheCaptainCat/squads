import { describe, expect, it } from 'vitest';

import { NO_BADGE_VOCABULARY, NO_FIELD_BINDINGS } from '../src/domain/badgeCatalog';
import {
  buildTooltip,
  collectNodeIds,
  type DisplayNode,
  emphasisForNode,
  emptyStateDisplayNode,
  errorDisplayNode,
  groupDisplayNode,
  itemLeaf,
  type LeafContext,
  sortedItemLeaves,
} from '../src/domain/displayNode';
import { NO_ROLES, NO_STATUS_ROLES } from '../src/domain/statusRole';
import { CYCLE_ANCHOR_TOOLTIP_LINE } from '../src/domain/treeAnchor';
import type { SqListItem } from '../src/types';

function leaf(id: string): DisplayNode {
  return {
    id,
    itemId: id,
    memoryRef: null,
    label: id,
    description: '',
    tooltip: '',
    iconId: 'circle-outline',
    blocked: false,
    closed: false,
    hidden: false,
    colorIntent: null,
    anchor: false,
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
      anchor: false,
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
      anchor: false,
    });
    expect(tooltip).toContain('Assignee: unassigned');
  });

  it('discloses a cycle anchor on its own line, and says nothing when the node is not one', () => {
    const fields = {
      id: 'TASK-1',
      type: 'task',
      status: 'Ready',
      assignee: null,
      badges: [],
      blocked: false,
    };
    expect(buildTooltip({ ...fields, anchor: true })).toContain(CYCLE_ANCHOR_TOOLTIP_LINE);
    expect(buildTooltip({ ...fields, anchor: false })).not.toContain('ycle anchor');
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

describe('itemLeaf / sortedItemLeaves', () => {
  const NO_CONTEXT: LeafContext = {
    fieldBindings: NO_FIELD_BINDINGS,
    badgeVocabulary: NO_BADGE_VOCABULARY,
    statusRoles: NO_STATUS_ROLES,
    roleCatalog: NO_ROLES,
  };
  const row = (id: string, status = 'Ready'): SqListItem => ({
    id,
    sequence_id: Number(id.split('-')[1]),
    type: 'task',
    title: `Title ${id}`,
    slug: id.toLowerCase(),
    status,
    description: '',
    parent: null,
    author: null,
    assignee: 'ada',
    labels: [],
    refs: [],
    path: '',
    created_at: '',
    updated_at: '',
  });

  it('renders id and title as the label, the given description and icon, and an empty tree', () => {
    const node = itemLeaf(row('TASK-7'), NO_CONTEXT, { description: 'Ready · ada', iconId: 'bug' });
    expect(node).toMatchObject({
      id: 'TASK-7',
      itemId: 'TASK-7',
      memoryRef: null,
      label: 'TASK-7  Title TASK-7',
      description: 'Ready · ada',
      iconId: 'bug',
      blocked: false,
      anchor: false,
      children: [],
    });
    expect(node.tooltip).toContain('TASK-7');
  });

  it('appends the label and tooltip suffixes and carries the given children', () => {
    const child = leaf('child');
    const plain = itemLeaf(row('TASK-7'), NO_CONTEXT, { description: 'd', iconId: 'i' });
    const node = itemLeaf(row('TASK-7'), NO_CONTEXT, {
      description: 'd',
      iconId: 'i',
      labelSuffix: ' (3)',
      tooltipSuffix: '\n\nextra',
      children: [child],
    });
    expect(node.label).toBe('TASK-7  Title TASK-7 (3)');
    expect(node.tooltip).toBe(`${plain.tooltip}\n\nextra`);
    expect(node.children).toEqual([child]);
  });

  it('takes closed, hidden and colour from the status role, and is open with none', () => {
    const context: LeafContext = {
      ...NO_CONTEXT,
      statusRoles: new Map([['Done', 'finished']]),
      roleCatalog: new Map([['finished', { settled: true, hidden: true, color: 'positive' }]]),
    };
    const done = itemLeaf(row('TASK-1', 'Done'), context, { description: '', iconId: 'i' });
    expect(done).toMatchObject({ closed: true, hidden: true, colorIntent: 'positive' });
    const open = itemLeaf(row('TASK-2', 'Unknown'), context, { description: '', iconId: 'i' });
    expect(open).toMatchObject({ closed: false, hidden: false, colorIntent: null });
  });

  it('sorts by numeric id, not lexicographically, without mutating the input', () => {
    const items = [row('TASK-10'), row('TASK-9'), row('TASK-100'), row('TASK-2')];
    const nodes = sortedItemLeaves(items, (item) =>
      itemLeaf(item, NO_CONTEXT, { description: '', iconId: 'i' }),
    );
    expect(nodes.map((n) => n.id)).toEqual(['TASK-2', 'TASK-9', 'TASK-10', 'TASK-100']);
    expect(items.map((i) => i.id)).toEqual(['TASK-10', 'TASK-9', 'TASK-100', 'TASK-2']);
  });
});
