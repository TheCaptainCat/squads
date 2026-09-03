/**
 * Pure JSON -> Mermaid `flowchart` source builders for the item preview's two collapsible
 * graphs: the children/subtree (`sq tree <id> --json`) and the ref graph (`sq graph <id>
 * --json`). Kept `vscode`-free/pure — same testability discipline as the rest of `domain/` —
 * the actual mermaid *rendering* happens client-side in the webview (see `previewDocument.ts`);
 * this module only produces the diagram source text embedded into that page.
 */
import type { SqGraphNode, SqTreeNode } from '../types';
import { escapeHtml } from './markdown';

/** The escape a `mermaidNodeId` emits for one non-alphanumeric character: `_` then exactly four
 * lowercase hex digits. Exported as source text because the decoder that undoes it runs in the
 * webview, as inlined script (`previewDocument.ts`'s `mermaidRenderScript`) that cannot import
 * from here — interpolating this one constant into that script is what keeps the two ends from
 * drifting into two different escapes. */
export const MERMAID_NODE_ID_ESCAPE_SOURCE = '_([0-9a-f]{4})';

/** Mermaid flowchart node identifiers only allow word characters, but an item id may contain
 * anything a declared type prefix contains — a hyphen, an underscore, a symbol. So every
 * non-alphanumeric character is escaped rather than folded: `-` becomes `_002d`, a literal `_`
 * becomes `_005f`, and an alphanumeric run is left alone.
 *
 * The point of escaping rather than folding is that this must be **reversible**. The webview
 * stamps each rendered node's real item id back on for click-through by decoding its node id
 * (see `decodeMermaidNodeId`), and a fold is many-to-one: `MY-WIDGET-1` and `MY_WIDGET-1` folded
 * to the same node id, which both merged two distinct items into one diagram node and made the
 * decoded id a guess.
 *
 * The core CLI's own `sq graph --format mermaid` (`_mermaid_node_id` in `_services/_refs.py`)
 * escapes the same way now, for the same reason — fixed-width escaping is the only injective
 * option for encoding an arbitrary id into Mermaid's `[A-Za-z0-9_]` node-id alphabet, so there
 * is one correct answer here rather than two. Its output is also no longer bare escaped ids:
 * it now declares each node with the real item id as an explicit label, same as
 * `mermaidNodeLabel` below, since an escaped id with no label would be the only thing a reader
 * ever saw. The two implementations still aren't shared: this one is decoded back by the
 * webview for click-through and the core's is display-only and never decoded, so agreeing is a
 * choice, not a constraint. If that ever stops being true — either side starts decoding the
 * other's output — they must become one shared constant/authority rather than two copies of the
 * same scheme.
 *
 * The pattern carries no `u` flag on purpose: without it a non-BMP character is matched as two
 * surrogate code units, each escaped to four hex digits and each rebuilt on decode. With it,
 * `charCodeAt(0)` would capture only the high surrogate and the round trip would lose data. */
export function mermaidNodeId(id: string): string {
  return id.replace(
    /[^A-Za-z0-9]/g,
    (char) => `_${char.charCodeAt(0).toString(16).padStart(4, '0')}`,
  );
}

/** Inverse of `mermaidNodeId`. Lives here, next to the encoder, so a round trip is unit-testable
 * without a DOM; the webview runs the same pattern against the same input (see
 * `MERMAID_NODE_ID_ESCAPE_SOURCE`). Text carrying no escape — a node id from a hand-authored
 * ```mermaid``` fence rather than from this module — decodes to itself. */
export function decodeMermaidNodeId(nodeId: string): string {
  return nodeId.replace(new RegExp(MERMAID_NODE_ID_ESCAPE_SOURCE, 'g'), (_whole, hex: string) =>
    String.fromCharCode(parseInt(hex, 16)),
  );
}

/** Markdown metacharacters (`` ` ``/`*`/`_`) that would otherwise read as code/emphasis inside
 * a Mermaid markdown-string label (see `mermaidNodeLabel`) are backslash-escaped so the label
 * always renders as the literal text; `escapeHtml` handles `<`/`>`/`"`/`&` so the label can
 * never break out of its own quoting or inject markup, regardless of what an item's title/id
 * happens to contain. */
function escapeMermaidMarkdownLabel(text: string): string {
  return escapeHtml(text).replace(/[`*_]/g, (char) => `\\${char}`);
}

/** Wraps `text` as a Mermaid *markdown-string* node label (`"` + backtick-delimited string +
 * `"`) rather than a plain quoted label — only the markdown-string form auto-wraps a long label
 * across multiple lines via real text-metric measurement (`config.flowchart.wrappingWidth`, set
 * alongside `securityLevel: 'strict'` in `previewDocument.ts`'s `mermaidRenderScript`); a plain
 * quoted label stays a single line and crops at the node's edge. `truncate` is a separate
 * defensive length cap, not the wrapping mechanism. */
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
 * Builds a `flowchart TD` source for the children/subtree graph from `sq tree <id> --json` (an
 * array holding the single requested root — see `sqAdapter.getTree`). Edges are plain, unlabeled
 * `parent --> child` links — parentage needs no label, unlike the ref graph's edges.
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

/** An edge whose declared semantic role (`SqGraphNode.edge_semantic`) is `"dependency"` is the
 * one shown with a direction-sensitive label ("depends on" vs. "required by"); every other edge
 * — navigational (`edge_semantic: null`), some other declared role (`preload`, `supersession`,
 * the bundled default kind's own role, or a project's own), or a semantic this client doesn't
 * otherwise recognise — is shown as its own declared kind spelling (`edge_kind`) verbatim,
 * matching the core CLI's `graph_to_mermaid` label convention
 * (`_services/_refs.py::_collect_edges`) so the two exports read the same way.
 *
 * The branch is on the declared semantic, never on the kind's spelling — a project may rename
 * its dependency kind (or drop it in favour of only the blocker-direction kind) and this still
 * resolves the direction-sensitive label correctly, because `edge_kind` is only ever rendered,
 * never compared. */
function edgeLabel(edgeKind: string, edgeSemantic: string | null, direction: 'in' | 'out'): string {
  if (edgeSemantic === 'dependency') {
    return direction === 'out' ? 'depends on' : 'required by';
  }
  return edgeKind;
}

function graphNodeLabel(node: SqGraphNode): string {
  const badgeSuffix = node.priority !== null ? `, ${node.priority}` : '';
  return `${node.id} (${node.type}${badgeSuffix}): ${node.status}`;
}

/**
 * Builds a `flowchart LR` source for the ref graph from `sq graph <id> --json` (`edge_kind`/
 * `edge_semantic`/`direction` are `null` only on the root; `edge_semantic` may also be absent
 * on an older `sq`, treated the same as `null` — see `edgeLabel`). A revisited node
 * (`seen: true`) is deduplicated by id, same as the core CLI export, so a cycle draws as an edge
 * into the existing box rather than a duplicate node. Edges are deduplicated by the full
 * (from, to, label) triple, then sorted for a deterministic diagram across runs.
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
      const label = edgeLabel(node.edge_kind, node.edge_semantic ?? null, node.direction);
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
