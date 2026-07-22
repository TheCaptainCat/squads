import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import { buildBadgeVocabulary, buildFieldBindings } from '../src/domain/badgeCatalog';
import { buildRoleCatalogMap, buildStatusRoleMap } from '../src/domain/statusRole';
import { distinctTypesInTree, treeNodesToDisplay } from '../src/domain/treeMapping';
import { buildTypeOrderMap } from '../src/domain/typeOrder';
import type {
  SqCollectionCatalogEntry,
  SqRoleCatalogEntry,
  SqStatusCatalogEntry,
  SqTreeNode,
  SqTypeCatalogEntry,
} from '../src/types';

function readFixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const TREE_FIXTURE = JSON.parse(readFixture('tree.json')) as SqTreeNode[];
const TYPE_CATALOG_FIXTURE = JSON.parse(readFixture('type-catalog.json')) as SqTypeCatalogEntry[];
const STATUSES_CATALOG_FIXTURE = JSON.parse(
  readFixture('statuses-catalog.json'),
) as SqStatusCatalogEntry[];
const ROLES_CATALOG_FIXTURE = JSON.parse(readFixture('roles-catalog.json')) as SqRoleCatalogEntry[];

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

  it('marks a node closed/hidden/coloured via the statuses/roles catalog join, never a literal status check', () => {
    const nodes: SqTreeNode[] = [
      {
        id: 'TASK-1',
        type: 'task',
        title: 'An in-progress task',
        status: 'InProgress',
        priority: null,
        assignee: null,
        blocked: false,
        children: [],
      },
      {
        id: 'TASK-2',
        type: 'task',
        title: 'A ready (not yet started) task',
        status: 'Ready',
        priority: null,
        assignee: null,
        blocked: false,
        children: [],
      },
      {
        id: 'TASK-3',
        type: 'task',
        title: 'A done task',
        status: 'Done',
        priority: null,
        assignee: null,
        blocked: false,
        children: [],
      },
      {
        id: 'ADR-1',
        type: 'decision',
        title: 'An accepted decision',
        status: 'Accepted',
        priority: null,
        assignee: null,
        blocked: false,
        children: [],
      },
    ];
    const statusRoles = buildStatusRoleMap(STATUSES_CATALOG_FIXTURE);
    const roleCatalog = buildRoleCatalogMap(ROLES_CATALOG_FIXTURE);

    const mapped = treeNodesToDisplay(nodes, {}, undefined, undefined, statusRoles, roleCatalog);

    // InProgress ("active" role): not settled, not hidden, positive colour.
    const inProgress = mapped.find((node) => node.id === 'TASK-1');
    expect(inProgress?.closed).toBe(false);
    expect(inProgress?.hidden).toBe(false);
    expect(inProgress?.colorIntent).toBe('positive');

    // Ready ("pending" role): not settled, not hidden, no distinct colour.
    const ready = mapped.find((node) => node.id === 'TASK-2');
    expect(ready?.closed).toBe(false);
    expect(ready?.hidden).toBe(false);
    expect(ready?.colorIntent).toBe('neutral');

    // Done ("done" role): settled AND hidden — the dimmed/greyed-out finished-work case.
    const done = mapped.find((node) => node.id === 'TASK-3');
    expect(done?.closed).toBe(true);
    expect(done?.hidden).toBe(true);

    // Accepted ("in_force" role): settled but NOT hidden — shows in its own colour rather than
    // greyed out like finished work.
    const accepted = mapped.find((node) => node.id === 'ADR-1');
    expect(accepted?.closed).toBe(true);
    expect(accepted?.hidden).toBe(false);
    expect(accepted?.colorIntent).toBe('info');
  });

  it('with no statusRoles/roleCatalog (the graceful fallback), no node is ever hidden or coloured', () => {
    const nodes: SqTreeNode[] = [
      {
        id: 'TASK-1',
        type: 'task',
        title: 'An in-progress task',
        status: 'InProgress',
        priority: null,
        assignee: null,
        blocked: false,
        children: [],
      },
    ];

    const [node] = treeNodesToDisplay(nodes);
    expect(node?.closed).toBe(false);
    expect(node?.hidden).toBe(false);
    expect(node?.colorIntent).toBeNull();
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
        children: [],
      },
    ];
    const [node] = treeNodesToDisplay(blockedFixture);

    expect(node?.blocked).toBe(true);
    expect(node?.description).toBe('Ready · unassigned · blocked');
    expect(node?.tooltip).toContain('Blocked: yes');
  });

  it('includes a badge in the tooltip only when the item carries it (empty badges map -> no lines)', () => {
    const baseNode: SqTreeNode = {
      id: 'EPIC-1',
      type: 'epic',
      title: 'Some epic',
      status: 'Ready',
      priority: 'high',
      assignee: null,
      blocked: false,
      badges: { priority: 'high' },
      children: [],
    };
    const withBadge: SqTreeNode[] = [baseNode];
    const withoutBadge: SqTreeNode[] = [{ ...baseNode, badges: {} }];

    expect(treeNodesToDisplay(withBadge)[0]?.tooltip).toContain('priority: high');
    expect(treeNodesToDisplay(withoutBadge)[0]?.tooltip).not.toContain('priority');
  });

  it('renders a resolved collection badge (glyph + label), joined through the type/collections catalogs (F19)', () => {
    const nodes: SqTreeNode[] = [
      {
        id: 'BUG-1',
        type: 'bug',
        title: 'Some bug',
        status: 'Open',
        priority: null,
        assignee: null,
        blocked: false,
        badges: { priority: 'high', severity: 'critical' },
        children: [],
      },
    ];
    const typeCatalog: SqTypeCatalogEntry[] = [
      {
        type: 'bug',
        order: 40,
        prefix: 'BUG',
        reserved: false,
        category: 'work',
        fields: [
          { code: 'priority', label: 'Priority', collection: 'priority' },
          { code: 'severity', label: 'Severity', collection: 'severity' },
        ],
      },
    ];
    const collectionsCatalog: SqCollectionCatalogEntry[] = [
      {
        collection: 'priority',
        label: 'Priority',
        ordered: true,
        default: null,
        badges: [{ code: 'high', label: 'High', emoji: '🟠' }],
      },
      {
        collection: 'severity',
        label: 'Severity',
        ordered: true,
        default: 'medium',
        badges: [{ code: 'critical', label: 'Critical', emoji: '🔴' }],
      },
    ];
    const fieldBindings = buildFieldBindings(typeCatalog);
    const badgeVocabulary = buildBadgeVocabulary(collectionsCatalog);

    const tooltip = treeNodesToDisplay(nodes, {}, fieldBindings, badgeVocabulary)[0]?.tooltip;

    expect(tooltip).toContain('Priority: 🟠 High');
    expect(tooltip).toContain('Severity: 🔴 Critical');
  });

  it('falls back to the raw field/badge code when the catalogs are unavailable (graceful degradation, F1-style)', () => {
    const nodes: SqTreeNode[] = [
      {
        id: 'BUG-1',
        type: 'bug',
        title: 'Some bug',
        status: 'Open',
        priority: null,
        assignee: null,
        blocked: false,
        badges: { impact: 'urgent' },
        children: [],
      },
    ];

    // No fieldBindings/badgeVocabulary passed — defaults to the graceful-fallback empty maps.
    const tooltip = treeNodesToDisplay(nodes)[0]?.tooltip;

    expect(tooltip).toContain('impact: urgent');
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
        children: [
          {
            id: 'ROLE-2',
            type: 'role',
            title: 'Nested role',
            status: 'Active',
            priority: null,
            assignee: null,
            blocked: false,
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
        children: [],
      },
    ];
    const mapped = treeNodesToDisplay(nodes);

    expect(mapped.find((node) => node.id === 'BUG-1')?.iconId).toBe('bug');
    expect(mapped.find((node) => node.id === 'CUSTOM-1')?.iconId).toBe('circle-outline');
  });

  it('layers squads.typeIcons overrides over the bundled defaults (F21)', () => {
    const nodes: SqTreeNode[] = [
      {
        id: 'BUG-1',
        type: 'bug',
        title: 'Some bug',
        status: 'Open',
        priority: null,
        assignee: null,
        blocked: false,
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
        children: [],
      },
    ];

    const mapped = treeNodesToDisplay(nodes, { bug: 'flame', widget: 'gear' });

    expect(mapped.find((node) => node.id === 'BUG-1')?.iconId).toBe('flame');
    expect(mapped.find((node) => node.id === 'CUSTOM-1')?.iconId).toBe('gear');
  });

  it('still falls back to the generic icon for a type absent from both the overrides and the bundled defaults', () => {
    const nodes: SqTreeNode[] = [
      {
        id: 'CUSTOM-1',
        type: 'widget',
        title: 'Some widget',
        status: 'Open',
        priority: null,
        assignee: null,
        blocked: false,
        children: [],
      },
    ];

    const mapped = treeNodesToDisplay(nodes, { bug: 'flame' });

    expect(mapped.find((node) => node.id === 'CUSTOM-1')?.iconId).toBe('circle-outline');
  });
});

describe('distinctTypesInTree', () => {
  it('with no orderMap (the graceful fallback), lists distinct non-reserved types alphabetically', () => {
    expect(distinctTypesInTree(TREE_FIXTURE)).toEqual(['epic', 'feature', 'task']);
  });

  it('given the type catalog, orders types by spec order rather than alphabetically (F1)', () => {
    const nodes: SqTreeNode[] = [
      {
        id: 'BUG-1',
        type: 'bug',
        title: 'Some bug',
        status: 'Open',
        priority: null,
        assignee: null,
        blocked: false,
        children: [],
      },
      {
        id: 'TASK-1',
        type: 'task',
        title: 'Some task',
        status: 'Ready',
        priority: null,
        assignee: null,
        blocked: false,
        children: [],
      },
    ];
    const orderMap = buildTypeOrderMap(TYPE_CATALOG_FIXTURE);

    // Alphabetically 'bug' < 'task'; spec order puts task(30) before bug(40).
    expect(distinctTypesInTree(nodes, orderMap)).toEqual(['task', 'bug']);
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
        children: [
          {
            id: 'ROLE-2',
            type: 'role',
            title: 'Nested role',
            status: 'Active',
            priority: null,
            assignee: null,
            blocked: false,
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
            children: [],
          },
        ],
      },
    ];

    expect(distinctTypesInTree(withReserved)).toEqual(['bug', 'epic']);
  });
});
