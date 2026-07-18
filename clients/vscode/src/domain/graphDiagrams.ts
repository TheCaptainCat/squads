/**
 * Pure JSON -> Mermaid `flowchart` source builders for the item preview's two collapsible
 * graphs: the children/subtree (`sq tree <id> --json`) and the ref graph (`sq graph <id>
 * --json`). Kept `vscode`-free/pure — same testability discipline as the rest of `domain/` —
 * the actual mermaid *rendering* happens client-side in the webview (see `previewDocument.ts`);
 * this module only produces the diagram source text embedded into that page.
 */
import type { SqGraphNode, SqTreeNode } from '../types';
import { escapeHtml } from './markdown';

/** Mermaid flowchart node identifiers only allow word characters; item ids are always
 * `[A-Z][A-Z0-9]*-\d+`, so folding the hyphen to an underscore is the only sanitizing needed
 * (mirrors the core CLI's own `sq graph --format mermaid` `_safe_id`, `_services/_refs.py`).
 * Reversible: since an item id has exactly one non-word character (the hyphen), the webview's
 * post-render click wiring (`previewDocument.ts`'s `mermaidRenderScript`) recovers the original
 * id straight from a rendered node's id by undoing this same substitution — see F25. */
function mermaidNodeId(id: string): string {
  return id.replace(/[^A-Za-z0-9_]/g, '_');
}

/** Markdown metacharacters (`` ` ``/`*`/`_`) that would otherwise read as code/emphasis inside
 * a Mermaid markdown-string label (see `mermaidNodeLabel`) are backslash-escaped so the label
 * always renders as the literal text; `escapeHtml` handles `<`/`>`/`"`/`&` so the label can
 * never break out of its own quoting or inject markup, regardless of what an item's title/id
 * happens to contain. */
function escapeMermaidMarkdownLabel(text: string): string {
  return escapeHtml(text).replace(/[`*_]/g, (char) => `\\${char}`);
}

/** Wraps `text` as a Mermaid *markdown-string* node label — `"` + a backtick-delimited string
 * + `"` — mermaid's supported mechanism for auto-wrapping a long label onto multiple lines
 * from real text-metric measurement (`config.flowchart.wrappingWidth`, set alongside
 * `securityLevel: 'strict'` in `previewDocument.ts`'s `mermaidRenderScript`), unlike a plain
 * quoted label's single non-wrapping line — a node whose box doesn't grow to fit its own text
 * crops the label at its edge. `truncate` is a defensive length cap on top of that, not the
 * wrapping mechanism itself (so a pathologically long title still can't produce an unbounded
 * node). */
function mermaidNodeLabel(text: string): string {
  return `"\`${escapeMermaidMarkdownLabel(truncate(text, 120))}\`"`;
}

/** Edge labels sit inside Mermaid's unquoted `-->|label|` syntax, where a literal `|` would
 * break the parse. Edge label vocabulary here is small and internally controlled ("depends
 * on"/"required by"/a validated ref kind), but this stays defensive-in-depth: HTML-escape plus
 * fold any stray pipe to a slash. */
function mermaidEdgeLabel(text: string): string {
  return escapeHtml(text).replace(/\|/g, '/');
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function subtreeNodeLabel(node: SqTreeNode): string {
  const blockedSuffix = node.blocked ? ' [blocked]' : '';
  return `${node.id}: ${truncate(node.title, 40)} (${node.status})${blockedSuffix}`;
}

/**
 * Builds a `flowchart TD` source for the children/subtree graph from `sq tree <id> --json`
 * (an array holding the single requested root — see `sqAdapter.getTree`). Emits one labeled
 * node per item plus a plain, unlabeled `parent --> child` edge per hierarchy link (parentage
 * needs no label, unlike the ref graph's edges).
 */
export function buildSubtreeMermaid(roots: readonly SqTreeNode[]): string {
  const lines = ['flowchart TD'];

  const visit = (node: SqTreeNode): void => {
    const nodeId = mermaidNodeId(node.id);
    lines.push(`  ${nodeId}[${mermaidNodeLabel(subtreeNodeLabel(node))}]`);
    for (const child of node.children) {
      lines.push(`  ${nodeId} --> ${mermaidNodeId(child.id)}`);
      visit(child);
    }
  };
  for (const root of roots) {
    visit(root);
  }

  return lines.join('\n');
}

interface Edge {
  readonly from: string;
  readonly to: string;
  readonly label: string;
}

/** `depends-on` is the one edge kind whose display label depends on direction ("depends on"
 * vs. "required by"); every other kind (`addresses`, `related`, `supersedes`, `fixes`, or any
 * future spec-driven kind) is shown as-is, matching the core CLI's `graph_to_mermaid` label
 * convention (`_services/_refs.py::_collect_edges`) so the two exports read the same way. */
function edgeLabel(edgeKind: string, direction: 'in' | 'out'): string {
  if (edgeKind === 'depends-on') {
    return direction === 'out' ? 'depends on' : 'required by';
  }
  return edgeKind;
}

function graphNodeLabel(node: SqGraphNode): string {
  const badgeSuffix = node.priority !== null ? `, ${node.priority}` : '';
  return `${node.id} (${node.type}${badgeSuffix}): ${node.status}`;
}

/**
 * Builds a `flowchart LR` source for the ref graph from `sq graph <id> --json` (a single
 * nested root object; `edge_kind`/`direction` are `null` only on the root itself). A node
 * revisited elsewhere in the BFS (`seen: true`) collapses to the same diagram node — it's
 * looked up/deduplicated by id, same as the core CLI export — so a cycle back to the root (or
 * any other already-visited node) draws as a real edge into the existing box rather than a
 * duplicate. Edges are deduplicated by the full (from, to, label) triple, then sorted for a
 * deterministic diagram across runs.
 */
export function buildRefGraphMermaid(root: SqGraphNode): string {
  const nodesById = new Map<string, SqGraphNode>();
  const edges: Edge[] = [];
  const seenEdgeKeys = new Set<string>();

  const visit = (node: SqGraphNode, parent: SqGraphNode | null): void => {
    if (!nodesById.has(node.id)) {
      nodesById.set(node.id, node);
    }
    if (parent !== null && node.edge_kind !== null && node.direction !== null) {
      const label = edgeLabel(node.edge_kind, node.direction);
      const key = `${parent.id}|${node.id}|${label}`;
      if (!seenEdgeKeys.has(key)) {
        seenEdgeKeys.add(key);
        edges.push({ from: parent.id, to: node.id, label });
      }
    }
    for (const child of node.children) {
      visit(child, node);
    }
  };
  visit(root, null);

  const sortedEdges = [...edges].sort((a, b) =>
    `${a.from}|${a.to}|${a.label}`.localeCompare(`${b.from}|${b.to}|${b.label}`),
  );

  const lines = ['flowchart LR'];
  for (const node of nodesById.values()) {
    lines.push(`  ${mermaidNodeId(node.id)}[${mermaidNodeLabel(graphNodeLabel(node))}]`);
  }
  for (const edge of sortedEdges) {
    lines.push(
      `  ${mermaidNodeId(edge.from)} -->|${mermaidEdgeLabel(edge.label)}| ${mermaidNodeId(edge.to)}`,
    );
  }
  return lines.join('\n');
}
