import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import { buildRefGraphMermaid, buildSubtreeMermaid } from '../src/domain/graphDiagrams';
import type { SqGraphNode, SqTreeNode } from '../src/types';

function fixture(name: string): unknown {
  return JSON.parse(readFileSync(path.join(__dirname, 'fixtures', name), 'utf8')) as unknown;
}

function treeNode(overrides: Partial<SqTreeNode> & { id: string; title: string }): SqTreeNode {
  return {
    type: 'task',
    status: 'Ready',
    priority: null,
    assignee: null,
    blocked: false,
    children: [],
    ...overrides,
  };
}

function graphNode(overrides: Partial<SqGraphNode> & { id: string }): SqGraphNode {
  return {
    type: 'task',
    status: 'Ready',
    priority: null,
    assignee: null,
    edge_kind: null,
    direction: null,
    seen: false,
    children: [],
    ...overrides,
  };
}

/** Recursively counts every node in a `sq tree --json` array — used to check the subtree
 * builder emits exactly one node line and one edge per hierarchy link, without hardcoding a
 * magic node count that would silently drift if the fixture changes. */
function countTreeNodes(nodes: readonly SqTreeNode[]): number {
  return nodes.reduce((sum, node) => sum + 1 + countTreeNodes(node.children), 0);
}

describe('buildSubtreeMermaid', () => {
  it('builds a flowchart TD: one labeled node per item, a plain edge per hierarchy link', () => {
    const root = treeNode({
      id: 'TASK-1',
      title: 'Do the thing',
      status: 'Ready',
      children: [
        treeNode({ id: 'TASK-2', title: 'Sub thing', status: 'Done' }),
        treeNode({
          id: 'TASK-3',
          title: 'Blocked thing',
          status: 'Open',
          blocked: true,
          children: [treeNode({ id: 'TASK-4', title: 'Leaf', status: 'Draft' })],
        }),
      ],
    });

    expect(buildSubtreeMermaid([root])).toBe(
      [
        'flowchart TD',
        '  TASK_1["`TASK-1: Do the thing (Ready)`"]',
        '  TASK_1 --> TASK_2',
        '  TASK_2["`TASK-2: Sub thing (Done)`"]',
        '  TASK_1 --> TASK_3',
        '  TASK_3["`TASK-3: Blocked thing (Open) [blocked]`"]',
        '  TASK_3 --> TASK_4',
        '  TASK_4["`TASK-4: Leaf (Draft)`"]',
      ].join('\n'),
    );
  });

  it('truncates a long title and HTML-escapes the label', () => {
    const root = treeNode({
      id: 'TASK-1',
      title: 'A'.repeat(50),
      status: '<script>',
    });
    const source = buildSubtreeMermaid([root]);
    expect(source).toContain(`${'A'.repeat(39)}…`);
    expect(source).not.toContain('A'.repeat(40));
    expect(source).toContain('&lt;script&gt;');
    expect(source).not.toContain('<script>');
  });

  it('wraps the label as a Mermaid markdown-string (F24) and escapes markdown metacharacters', () => {
    const root = treeNode({ id: 'TASK-1', title: 'A `code` and *emphasis* and _underscore_' });
    const source = buildSubtreeMermaid([root]);
    // Markdown-string label syntax: a `"` + backtick-delimited string + `"`.
    expect(source).toContain('TASK_1["`TASK-1: ');
    expect(source).toContain('`"]');
    // Every mermaid markdown metacharacter in the title is backslash-escaped so it renders as
    // literal text rather than emphasis/code formatting.
    expect(source).toContain('A \\`code\\` and \\*emphasis\\* and \\_underscore\\_');
  });

  it('hard-caps a pathologically long node label at 120 characters regardless of title truncation', () => {
    // The title itself is already capped at 40 chars by `subtreeNodeLabel`, but a long status
    // string still pushes the composed label past a sane bound — `mermaidNodeLabel`'s own
    // truncate is the backstop, independent of the wrapping mechanism.
    const root = treeNode({ id: 'TASK-1', title: 'Short', status: 'S'.repeat(200) });
    const source = buildSubtreeMermaid([root]);
    const labelMatch = /\["`(.*)`"\]/.exec(source);
    expect(labelMatch).not.toBeNull();
    expect(labelMatch?.[1]?.length).toBeLessThanOrEqual(120);
  });

  it('produces exactly one node line and (nodeCount - 1) edge lines for a real committed fixture', () => {
    const [root] = fixture('tree.json') as SqTreeNode[];
    if (root === undefined) {
      throw new Error('expected the fixture to have a root node');
    }
    const total = countTreeNodes([root]);
    const source = buildSubtreeMermaid([root]);
    const lines = source.split('\n');

    expect(lines[0]).toBe('flowchart TD');
    expect(lines.length).toBe(1 + total + (total - 1));
    expect(source).toContain('EPIC_99[');
    expect(source).toContain('EPIC_99 --> FEAT_100');
    expect(source).toContain('FEAT_100 --> TASK_428');
  });
});

describe('buildRefGraphMermaid', () => {
  it("gives 'depends-on' a direction-sensitive label and any other kind its name verbatim", () => {
    const root = graphNode({
      id: 'TASK-10',
      type: 'task',
      status: 'Ready',
      children: [
        graphNode({
          id: 'TASK-11',
          type: 'task',
          status: 'Done',
          edge_kind: 'depends-on',
          direction: 'out',
        }),
        graphNode({
          id: 'TASK-12',
          type: 'bug',
          status: 'Open',
          priority: 'high',
          edge_kind: 'depends-on',
          direction: 'in',
          children: [
            graphNode({
              id: 'TASK-11', // revisited — same diagram node, a second distinct edge
              type: 'task',
              status: 'Done',
              edge_kind: 'related',
              direction: 'out',
              seen: true,
            }),
          ],
        }),
      ],
    });

    expect(buildRefGraphMermaid(root)).toBe(
      [
        'flowchart LR',
        '  TASK_10["`TASK-10 (task): Ready`"]',
        '  TASK_11["`TASK-11 (task): Done`"]',
        '  TASK_12["`TASK-12 (bug, high): Open`"]',
        '  TASK_10 -->|depends on| TASK_11',
        '  TASK_10 -->|required by| TASK_12',
        '  TASK_12 -->|related| TASK_11',
      ].join('\n'),
    );
  });

  it('deduplicates an identical (from, to, label) edge reached by two different paths', () => {
    const shared = graphNode({
      id: 'TASK-20',
      edge_kind: 'related',
      direction: 'out',
    });
    const root = graphNode({
      id: 'TASK-1',
      children: [shared, { ...shared }], // same edge twice
    });

    const lines = buildRefGraphMermaid(root).split('\n');
    expect(lines.filter((line) => line.includes('-->'))).toHaveLength(1);
  });

  it('builds the real FEAT-449 ref-graph fixture (includes a revisit back to the root)', () => {
    const root = fixture('graph.json') as SqGraphNode;

    expect(buildRefGraphMermaid(root)).toBe(
      [
        'flowchart LR',
        '  FEAT_449["`FEAT-449 (feature): Draft`"]',
        '  FEAT_100["`FEAT-100 (feature, low): Done`"]',
        '  ADR_427["`ADR-427 (decision): Accepted`"]',
        '  REV_448["`REV-448 (review): Requested`"]',
        '  FEAT_100 -->|related| ADR_427',
        '  FEAT_100 -->|related| FEAT_449',
        '  FEAT_100 -->|related| REV_448',
        '  FEAT_449 -->|related| FEAT_100',
        '  FEAT_449 -->|addresses| REV_448',
      ].join('\n'),
    );
  });

  it('HTML-escapes a node label and folds a stray pipe out of an edge label', () => {
    const root = graphNode({
      id: 'TASK-1',
      status: '<script>',
      children: [graphNode({ id: 'TASK-2', edge_kind: 'a|b', direction: 'out' })],
    });
    const source = buildRefGraphMermaid(root);
    expect(source).toContain('&lt;script&gt;');
    expect(source).not.toContain('<script>');
    expect(source).toContain('-->|a/b|');
  });
});
