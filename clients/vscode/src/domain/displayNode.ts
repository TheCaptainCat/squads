/**
 * `DisplayNode` is the vscode-free intermediate representation both browse views (the
 * hierarchy tree and the flat/filtered/grouped list) render into before a thin, untested-by-unit-tests
 * wrapper turns each node into an actual `vscode.TreeItem`. Keeping this layer free of the
 * `vscode` import is what lets the JSON -> display mapping run under `vitest` with no real
 * VS Code host.
 */
import type { ResolvedBadge } from './badgeCatalog';

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
  /** True when the item's status carries the spec-declared `"active"` semantic role ("work in
   * flight" — F26), joined through the statuses catalog, never a literal status-name check.
   * Disjoint with `closed` by construction (a terminal status is never role `"active"`).
   * Drives the green highlight. Always `false` for a synthetic group/error node. */
  readonly active: boolean;
  readonly children: readonly DisplayNode[];
}

/** The visual emphasis a `TreeItem` should render for a node's `blocked`/`closed`/`active`
 * flags, in priority order — kept as a pure, vscode-free function so the precedence itself
 * (and the F26 claim that `closed` and `active` never both apply) is unit-testable without a
 * VS Code host; `treeItemRendering.ts` only turns the result into a `vscode.ThemeColor` id. */
export type NodeEmphasis = 'blocked' | 'closed' | 'active' | 'none';

export function emphasisForNode(
  node: Pick<DisplayNode, 'blocked' | 'closed' | 'active'>,
): NodeEmphasis {
  if (node.blocked) {
    return 'blocked';
  }
  if (node.closed) {
    return 'closed';
  }
  if (node.active) {
    return 'active';
  }
  return 'none';
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

/** A user-configured `squads.typeIcons` map: type name -> codicon id, layered over the
 * bundled `ICON_BY_TYPE` defaults (F21). Keeps icons spec-agnostic/client-side with no core
 * change — the one place the client hardcodes work-item type names, made overridable. */
export type TypeIconOverrides = Readonly<Record<string, string>>;

/**
 * Best-effort icon by type name. A project may rename/drop/add work-item types (only the
 * three reserved meta types are fixed): `overrides` (the `squads.typeIcons` setting) wins when
 * it names `type`, falling back to the bundled default, and finally to a generic icon for
 * anything still unmapped — the mapping never needs to be complete.
 */
export function iconForType(type: string, overrides: TypeIconOverrides = {}): string {
  return overrides[type] ?? ICON_BY_TYPE[type] ?? DEFAULT_ICON;
}

/** Codicons for the 3 reserved meta types (`domain/metaView.ts`'s Roster buckets). Unlike
 * `ICON_BY_TYPE` above — a project's own work-item types, fully overridable via the
 * `squads.typeIcons` setting — role/skill/operator are fixed by contract, so hardcoding these
 * is correct and they're deliberately kept out of that override path. */
const META_ICON_BY_TYPE: Readonly<Record<string, string>> = {
  role: 'hubot',
  operator: 'account',
  skill: 'mortar-board',
};

/** Best-effort icon for a reserved meta type; falls back to the same generic icon as
 * `iconForType` for anything unrecognized (never expected in practice — the 3 buckets are
 * fixed — but keeps the fallback total rather than partial). */
export function iconForMetaType(type: string): string {
  return META_ICON_BY_TYPE[type] ?? DEFAULT_ICON;
}

export interface TooltipFields {
  readonly id: string;
  readonly type: string;
  readonly status: string;
  readonly assignee: string | null;
  /** Already-resolved collection badges (F19) — whatever the spec declares for this
   * item (priority, severity, any custom axis), pre-joined through the type/collections
   * catalogs by the caller. `buildTooltip` itself hardcodes no collection name. */
  readonly badges: readonly ResolvedBadge[];
  readonly blocked: boolean;
}

/** Backslash-escapes the markdown metacharacters (`` ` ``/`*`/`_`) that would otherwise read as
 * code/emphasis inside the `vscode.MarkdownString` tooltip (F19) — mirrors `graphDiagrams.ts`'s
 * `escapeMermaidMarkdownLabel`, minus its HTML-escaping step: this string is handed straight to
 * VS Code's own markdown renderer, never through this client's HTML renderer. Applied to
 * `assignee`, the only user-derived line in the tooltip — id/type/status/badges are all
 * spec-controlled and safe as-is. */
function escapeTooltipMarkdown(text: string): string {
  return text.replace(/[`*_]/g, (char) => `\\${char}`);
}

/** The tooltip carries the overflow that doesn't fit the label/description: the item's
 * collection badges and blocked-state (the tree surface only carries a blocked boolean, not
 * blocking-item ids). Markdown hard-breaks (`  \n`) between lines so the caller can render this
 * as a `vscode.MarkdownString` and have the real badge glyphs display on their own line. */
export function buildTooltip(fields: TooltipFields): string {
  const lines = [
    `${fields.id} (${fields.type})`,
    `Status: ${fields.status}`,
    `Assignee: ${fields.assignee !== null ? escapeTooltipMarkdown(fields.assignee) : 'unassigned'}`,
  ];
  for (const badge of fields.badges) {
    const value = badge.emoji !== null ? `${badge.emoji} ${badge.badgeLabel}` : badge.badgeLabel;
    lines.push(`${badge.fieldLabel}: ${value}`);
  }
  if (fields.blocked) {
    lines.push('Blocked: yes');
  }
  return lines.join('  \n');
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
    active: false,
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
    active: false,
    children: [],
  };
}
