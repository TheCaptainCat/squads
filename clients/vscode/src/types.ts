/**
 * Shapes mirroring the frozen `sq --json` surfaces this extension consumes.
 *
 * These are hand-trimmed to the fields the client actually reads; they intentionally
 * don't model every key `sq` may emit (extra/unknown keys are ignored, not rejected).
 */

/** One node of `sq tree <root> --json` (recursive; `children` may be empty). */
export interface SqTreeNode {
  readonly id: string;
  readonly type: string;
  readonly title: string;
  readonly status: string;
  readonly priority: string | null;
  readonly assignee: string | null;
  readonly blocked: boolean;
  readonly is_open: boolean;
  readonly children: readonly SqTreeNode[];
}

/** One node of `sq graph <id> --json` (recursive; the ego-centric ref-graph BFS). The root
 * node's `edge_kind`/`direction` are always `null`; every other node carries the kind/direction
 * of the edge that discovered it. `seen: true` marks a node already visited elsewhere in the
 * traversal (re-emitted so the edge into it still shows, but not re-expanded — `children` is
 * always empty on a `seen` node). */
export interface SqGraphNode {
  readonly id: string;
  readonly type: string;
  readonly status: string;
  readonly priority: string | null;
  readonly assignee: string | null;
  readonly edge_kind: string | null;
  readonly direction: 'in' | 'out' | null;
  readonly seen: boolean;
  readonly children: readonly SqGraphNode[];
}

/** One row of `sq list --json`. */
export interface SqListItem {
  readonly id: string;
  readonly sequence_id: number;
  readonly type: string;
  readonly title: string;
  readonly slug: string;
  readonly status: string;
  readonly description: string;
  readonly parent: string | null;
  readonly author: string | null;
  readonly assignee: string | null;
  readonly priority: string | null;
  readonly severity: string | null;
  readonly labels: readonly string[];
  readonly refs: readonly string[];
  readonly path: string;
  readonly created_at: string;
  readonly updated_at: string;
  readonly is_open: boolean;
}
