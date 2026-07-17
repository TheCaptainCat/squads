/**
 * `DisplayNode` is the vscode-free intermediate representation both browse views (the
 * hierarchy tree and the flat/filtered/grouped list) render into before a thin, untested-by-unit-tests
 * wrapper turns each node into an actual `vscode.TreeItem`. Keeping this layer free of the
 * `vscode` import is what lets the JSON -> display mapping run under `vitest` with no real
 * VS Code host.
 */

export interface DisplayNode {
  /** Stable identity vscode's TreeView keys on. Real items use their sq id; synthetic group/error
   * nodes use a `group:`/`__squads_error__` prefix so they can never collide with a real id. */
  readonly id: string;
  /** The sq item id backing this node, or `null` for a synthetic group/error node. */
  readonly itemId: string | null;
  readonly label: string;
  readonly description: string;
  readonly tooltip: string;
  /** A codicon id (e.g. `"bug"`); never empty. */
  readonly iconId: string;
  readonly blocked: boolean;
  /** True for a closed/terminal item — only ever populated when the show-closed toggle pulled
   * closed items into the current fetch. Drives the dimmed rendering that makes open vs closed
   * legible at a glance without a separate grouping mode. Always `false` for a synthetic
   * group/error node. */
  readonly closed: boolean;
  readonly children: readonly DisplayNode[];
}

const ICON_BY_TYPE: Readonly<Record<string, string>> = {
  epic: 'milestone',
  feature: 'rocket',
  task: 'checklist',
  bug: 'bug',
  decision: 'lightbulb',
  review: 'eye',
  guide: 'book',
};
const DEFAULT_ICON = 'circle-outline';
const GROUP_ICON = 'folder';
const ERROR_ICON = 'error';

/**
 * Best-effort icon by type name. A project may rename/drop/add work-item types (only the
 * three reserved meta types are fixed), so an unrecognized type falls back to a generic icon
 * rather than the mapping ever needing to be complete.
 */
export function iconForType(type: string): string {
  return ICON_BY_TYPE[type] ?? DEFAULT_ICON;
}

export interface TooltipFields {
  readonly id: string;
  readonly type: string;
  readonly status: string;
  readonly assignee: string | null;
  readonly priority: string | null;
  readonly blocked: boolean;
}

/** The tooltip carries the overflow that doesn't fit the label/description: priority and
 * blocked-state (the tree surface only carries a blocked boolean, not blocking-item ids). */
export function buildTooltip(fields: TooltipFields): string {
  const lines = [
    `${fields.id} (${fields.type})`,
    `Status: ${fields.status}`,
    `Assignee: ${fields.assignee ?? 'unassigned'}`,
  ];
  if (fields.priority !== null) {
    lines.push(`Priority: ${fields.priority}`);
  }
  if (fields.blocked) {
    lines.push('Blocked: yes');
  }
  return lines.join('\n');
}

export function groupDisplayNode(
  id: string,
  label: string,
  itemCount: number,
  children: readonly DisplayNode[],
): DisplayNode {
  return {
    id,
    itemId: null,
    label,
    description: `${itemCount.toString()} item${itemCount === 1 ? '' : 's'}`,
    tooltip: label,
    iconId: GROUP_ICON,
    blocked: false,
    closed: false,
    children,
  };
}

export function errorDisplayNode(message: string): DisplayNode {
  return {
    id: '__squads_error__',
    itemId: null,
    label: 'Squads: unable to load items',
    description: message,
    tooltip: message,
    iconId: ERROR_ICON,
    blocked: false,
    closed: false,
    children: [],
  };
}
