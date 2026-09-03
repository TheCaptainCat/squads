import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  buildRefGraphMermaid,
  buildSubtreeMermaid,
  decodeMermaidNodeId,
  mermaidNodeId,
} from '../src/domain/graphDiagrams';
import { isSqGraphNode } from '../src/sqAdapter';
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
    edge_semantic: null,
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
        '  TASK_002d1["`TASK-1: Do the thing (Ready)`"]',
        '  TASK_002d1 --> TASK_002d2',
        '  TASK_002d2["`TASK-2: Sub thing (Done)`"]',
        '  TASK_002d1 --> TASK_002d3',
        '  TASK_002d3["`TASK-3: Blocked thing (Open) [blocked]`"]',
        '  TASK_002d3 --> TASK_002d4',
        '  TASK_002d4["`TASK-4: Leaf (Draft)`"]',
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
    expect(source).toContain('TASK_002d1["`TASK-1: ');
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
    expect(source).toContain('EPIC_002d99[');
    expect(source).toContain('EPIC_002d99 --> FEAT_002d100');
    expect(source).toContain('FEAT_002d100 --> TASK_002d428');
  });
});

describe('buildRefGraphMermaid', () => {
  it('gives a dependency-semantic edge a direction-sensitive label under a renamed kind, and any other kind its name verbatim', () => {
    // The kind is deliberately NOT the bundled 'depends-on' spelling — a project that renames
    // its dependency kind must still get "depends on" / "required by", because the label is
    // driven by `edge_semantic`, never by comparing `edge_kind` against a literal.
    const root = graphNode({
      id: 'TASK-10',
      type: 'task',
      status: 'Ready',
      children: [
        graphNode({
          id: 'TASK-11',
          type: 'task',
          status: 'Done',
          edge_kind: 'requires',
          edge_semantic: 'dependency',
          direction: 'out',
        }),
        graphNode({
          id: 'TASK-12',
          type: 'bug',
          status: 'Open',
          priority: 'high',
          edge_kind: 'requires',
          edge_semantic: 'dependency',
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
        '  TASK_002d10["`TASK-10 (task): Ready`"]',
        '  TASK_002d11["`TASK-11 (task): Done`"]',
        '  TASK_002d12["`TASK-12 (bug, high): Open`"]',
        '  TASK_002d10 -->|depends on| TASK_002d11',
        '  TASK_002d10 -->|required by| TASK_002d12',
        '  TASK_002d12 -->|related| TASK_002d11',
      ].join('\n'),
    );
  });

  it('renders a navigational edge (no declared semantic) as its own kind spelling', () => {
    const root = graphNode({
      id: 'TASK-1',
      children: [
        graphNode({ id: 'TASK-2', edge_kind: 'related', edge_semantic: null, direction: 'out' }),
      ],
    });

    expect(buildRefGraphMermaid(root)).toContain('-->|related|');
  });

  it('renders an edge whose declared semantic is not "dependency" as its own kind spelling, rather than throwing or blanking', () => {
    // 'preload' and 'supersession' are real declared roles (ADR-775 §2); 'default' is the
    // bundled default kind's own declared role (`related` in the bundled spec) — none of them
    // is 'dependency', so all three fall through to the kind's spelling exactly like an
    // unrecognised/future role would.
    const root = graphNode({
      id: 'TASK-1',
      children: [
        graphNode({
          id: 'TASK-2',
          edge_kind: 'scopes',
          edge_semantic: 'preload',
          direction: 'out',
        }),
        graphNode({
          id: 'TASK-3',
          edge_kind: 'supersedes',
          edge_semantic: 'supersession',
          direction: 'out',
        }),
        graphNode({
          id: 'TASK-4',
          edge_kind: 'related',
          edge_semantic: 'default',
          direction: 'out',
        }),
      ],
    });

    const source = buildRefGraphMermaid(root);
    expect(source).toContain('-->|scopes|');
    expect(source).toContain('-->|supersedes|');
    expect(source).toContain('-->|related|');
  });

  it('accepts a graph node whose edge_semantic field is entirely absent (an older sq predates it) instead of rejecting the graph', () => {
    // Deliberately not built through the `graphNode()` helper, which always sets the key — this
    // mirrors the literal shape `JSON.parse` produces from an `sq` build that predates A2.
    const legacyChild = {
      id: 'TASK-2',
      type: 'task',
      status: 'Ready',
      priority: null,
      assignee: null,
      edge_kind: 'depends-on',
      direction: 'out',
      seen: false,
      children: [],
    };
    const legacyRoot = {
      id: 'TASK-1',
      type: 'task',
      status: 'Ready',
      priority: null,
      assignee: null,
      edge_kind: null,
      direction: null,
      seen: false,
      children: [legacyChild],
    };

    expect(isSqGraphNode(legacyRoot)).toBe(true);
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
        '  FEAT_002d449["`FEAT-449 (feature): Draft`"]',
        '  FEAT_002d100["`FEAT-100 (feature, low): Done`"]',
        '  ADR_002d427["`ADR-427 (decision): Accepted`"]',
        '  REV_002d448["`REV-448 (review): Requested`"]',
        '  FEAT_002d100 -->|related| ADR_002d427',
        '  FEAT_002d100 -->|related| FEAT_002d449',
        '  FEAT_002d100 -->|related| REV_002d448',
        '  FEAT_002d449 -->|related| FEAT_002d100',
        '  FEAT_002d449 -->|addresses| REV_002d448',
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

/**
 * A mermaid node id has to survive the trip back: the webview reads it off the rendered SVG and
 * stamps the decoded value on as the item id a click navigates to. A fold loses that, and loses
 * it differently for each prefix shape, so the round trip is checked per shape family rather
 * than on one example.
 */
describe('mermaidNodeId / decodeMermaidNodeId round trip', () => {
  const ids = [
    'TASK-452',
    'MY-WIDGET-19',
    'MY_WIDGET-19',
    'MY_WIDGET_MORE-19',
    'W-1',
    'widget-19',
    'MyWidget-19',
    'A1-19',
    'C++-19',
    'é-19',
    '𝔘-19',
  ];

  for (const id of ids) {
    it(`round-trips ${id}`, () => {
      expect(decodeMermaidNodeId(mermaidNodeId(id))).toBe(id);
    });
  }

  it('emits only characters mermaid accepts in a node identifier', () => {
    for (const id of ids) {
      expect(mermaidNodeId(id)).toMatch(/^[A-Za-z0-9_]+$/);
    }
  });

  it('keeps two ids distinct that a hyphen->underscore fold collapsed into one node', () => {
    // The defect: folding mapped these to the same node id, so mermaid merged two items into
    // one node and the decoded click target was a guess.
    expect(mermaidNodeId('MY-WIDGET-1')).not.toBe(mermaidNodeId('MY_WIDGET-1'));
    expect(decodeMermaidNodeId(mermaidNodeId('MY_WIDGET-1'))).toBe('MY_WIDGET-1');
  });

  it('renders one node per item when two ids differ only in hyphen-versus-underscore', () => {
    const source = buildSubtreeMermaid([
      treeNode({
        id: 'MY-WIDGET-1',
        title: 'Hyphenated',
        children: [treeNode({ id: 'MY_WIDGET-1', title: 'Underscored' })],
      }),
    ]);
    const nodeLines = source.split('\n').filter((line) => line.includes('["`'));

    expect(nodeLines).toHaveLength(2);
    expect(new Set(nodeLines.map((line) => line.trim().split('[')[0])).size).toBe(2);
  });

  it('leaves text carrying no escape untouched', () => {
    expect(decodeMermaidNodeId('InProgress')).toBe('InProgress');
    expect(decodeMermaidNodeId('')).toBe('');
  });

  it('decodes an escape immediately followed by hex-looking characters, taking exactly four', () => {
    // `A-1234` encodes to `A_002d1234`; a greedy decoder would eat the item number.
    expect(decodeMermaidNodeId(mermaidNodeId('A-1234'))).toBe('A-1234');
  });
});
