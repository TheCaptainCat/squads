/**
 * Pure domain logic for a Role/Operator identity's eagerly-fetched memory pool, nested as
 * children under its node in the Roster tree (`domain/metaView.ts`). Vscode-free so the
 * count/age glance text, child ordering, and age-humanizing formatting run under vitest with no
 * VS Code host — mirrors `sq ui`'s own decisions (`_tui/_tree.py`) so the two clients read the
 * same way for the same underlying data: a count+age suffix on the identity node, entries
 * oldest-touched first with a slug tiebreak, and a distinct rendering for a pool that failed to
 * load at all.
 */
import type { SqOutcome } from '../sqAdapter';
import type { SqListItem, SqMemoryDetail, SqMemoryListRow } from '../types';
import { type DisplayNode, escapeTooltipMarkdown } from './displayNode';
import { renderMarkdownToHtml } from './markdown';
import { DEFAULT_META_VIEW_STATE, matchesMetaFilter, type MetaViewState } from './metaFilter';
import { META_BUCKETS } from './reservedTypes';
import { NO_ROLES, NO_STATUS_ROLES, type RoleCatalogMap, type StatusRoleMap } from './statusRole';

/** Only Role and Operator identities carry a memory notebook — Skills don't (`META_BUCKETS`
 * minus its `skill` entry, rather than a fresh literal pair, so this stays tied to the one
 * canonical reserved-type list instead of drifting from it). */
const MEMORY_ELIGIBLE_TYPES: ReadonlySet<string> = new Set(
  META_BUCKETS.map((bucket) => bucket.type).filter((type) => type !== 'skill'),
);

export function isMemoryEligibleType(type: string): boolean {
  return MEMORY_ELIGIBLE_TYPES.has(type);
}

/** One role/operator identity's eagerly-fetched memory pool: either its entries loaded, or the
 * whole fetch failed outright (a bad role slug, `sq` not found, malformed output — a subprocess-
 * level failure, not a per-entry one). There is no partial/degraded state modelled here:
 * `sq memory <role> list --json` never fails the array for one unreadable entry (it's silently
 * omitted and named on stderr, which this client doesn't inspect on a successful exit) — only a
 * genuine fetch failure reaches `'failed'`. */
export type MemoryFetchResult =
  | { readonly kind: 'loaded'; readonly entries: readonly SqMemoryListRow[] }
  | { readonly kind: 'failed'; readonly message: string };

/** Every Role/Operator identity's memory pool, keyed by its own roster slug (`SqListItem.slug`,
 * the same slug `sq memory <role> ...` takes as its subject) — populated by
 * `metaTreeDataProvider.ts::refresh`'s eager fetch. An identity absent from the map was never
 * fetched (not memory-eligible, e.g. a Skill, or filtered out of the current Roster view) —
 * `itemToLeaf` then renders it exactly as it did before this feature: no suffix, no children. */
export type MemoryPoolsBySlug = ReadonlyMap<string, MemoryFetchResult>;

export const NO_MEMORY_POOLS: MemoryPoolsBySlug = new Map();

/** The catalog-derived state `metaView.ts::itemToLeaf` needs to render a Role/Operator's memory
 * children, bundled into one object (rather than two more trailing parameters) to stay under
 * the project's max-params bar — same rationale as `domain/listView.ts`'s
 * `GroupListItemsOptions`. `now` is threaded explicitly (never read from the system clock in
 * here) so the age-humanizing text stays deterministic under test. */
export interface MemoryRenderContext {
  readonly pools: MemoryPoolsBySlug;
  readonly now: Date;
}

export const NO_MEMORY_CONTEXT: MemoryRenderContext = { pools: NO_MEMORY_POOLS, now: new Date(0) };

/** Every Role/Operator roster slug in `items` that survives `state`'s current filter — the
 * exact set `metaTreeDataProvider.ts::refresh` should fire a memory fetch for, so a filtered
 * Roster view never pays for an identity it isn't about to show. Mirrors `buildMetaView`'s own
 * `matchesMetaFilter` gate rather than re-deriving a separate notion of "visible". */
export function memoryEligibleSlugs(
  items: readonly SqListItem[],
  statusRoles: StatusRoleMap = NO_STATUS_ROLES,
  roleCatalog: RoleCatalogMap = NO_ROLES,
  state: MetaViewState = DEFAULT_META_VIEW_STATE,
): string[] {
  return items
    .filter(
      (item) =>
        isMemoryEligibleType(item.type) && matchesMetaFilter(item, state, statusRoles, roleCatalog),
    )
    .map((item) => item.slug);
}

type AgeUnit = readonly [seconds: number, suffix: string];

/** Coarsest-fitting unit wins — a fixed-length tuple (not a bare array) so indexing/destructuring
 * the first element stays sound under `noUncheckedIndexedAccess` without a runtime fallback that
 * could never actually trigger. */
const AGE_UNITS: readonly [AgeUnit, AgeUnit, AgeUnit, AgeUnit, AgeUnit] = [
  [60, 'm'],
  [60 * 60, 'h'],
  [60 * 60 * 24, 'd'],
  [60 * 60 * 24 * 30, 'mo'],
  [60 * 60 * 24 * 365, 'y'],
];

/** A short "how long ago" rendering of an ISO-8601 timestamp, coarsest unit only — mirrors
 * `sq ui`'s `_tui/_tree.py::_humanize_age`. `"unknown age"` for a timestamp this client can't
 * parse, rather than throwing or silently reporting a wrong age. */
export function humanizeAge(createdAt: string, now: Date): string {
  const created = new Date(createdAt);
  if (Number.isNaN(created.getTime())) {
    return 'unknown age';
  }
  const seconds = Math.max(0, Math.floor((now.getTime() - created.getTime()) / 1000));
  if (seconds < AGE_UNITS[0][0]) {
    return 'just now';
  }
  let [unitSeconds, suffix] = AGE_UNITS[0];
  for (const candidate of AGE_UNITS.slice(1)) {
    if (seconds < candidate[0]) {
      break;
    }
    [unitSeconds, suffix] = candidate;
  }
  return `${Math.floor(seconds / unitSeconds).toString()}${suffix} ago`;
}

/** True only when every entry carries `created_at` — the CLI surface this feature depends on.
 * One `sq` invocation emits one uniform JSON shape, so "some rows have it, some don't" isn't a
 * case this needs to reconcile: it only ever needs to tell "all present" (a current `sq`) from
 * "none present" (one predating the field). */
function hasAgeData(entries: readonly SqMemoryListRow[]): entries is readonly (SqMemoryListRow & {
  created_at: string;
})[] {
  return entries.every((entry) => typeof entry.created_at === 'string');
}

/** Oldest-touched first, slug as the tiebreak — the within-role comparison order the feature
 * is built around. Falls back to the CLI's own stable return order when `created_at` isn't
 * present on every row (an older `sq`), rather than inventing an ordering from nothing —
 * stated here, not just left implicit, per the "stable and stated" fallback the feature calls
 * for. */
export function sortMemoryEntries(entries: readonly SqMemoryListRow[]): SqMemoryListRow[] {
  if (!hasAgeData(entries)) {
    return [...entries];
  }
  return [...entries].sort(
    (a, b) => a.created_at.localeCompare(b.created_at) || a.slug.localeCompare(b.slug),
  );
}

/** The bare "N" / "N · age" / "error" fragment shared by a Role/Operator's own glance suffix and
 * its tooltip's memory line, so the two never drift apart. A pool with zero entries still
 * renders `"0"` — a quiet role reads as a signal, not as nothing to show. */
export function memoryGlanceText(pool: MemoryFetchResult, now: Date): string {
  if (pool.kind === 'failed') {
    return 'error';
  }
  const { entries } = pool;
  if (entries.length === 0) {
    return '0';
  }
  if (!hasAgeData(entries)) {
    return entries.length.toString();
  }
  const newest = entries.reduce((latest, entry) =>
    entry.created_at > latest.created_at ? entry : latest,
  );
  return `${entries.length.toString()} · ${humanizeAge(newest.created_at, now)}`;
}

/** The `"  memory: ..."` fragment appended to a Role/Operator's own tree-node label. */
export function memoryLabelSuffix(pool: MemoryFetchResult, now: Date): string {
  return `  memory: ${memoryGlanceText(pool, now)}`;
}

/** The extra tooltip line describing a Role/Operator's memory pool — appended (as a markdown
 * hard-break continuation) to `buildTooltip`'s own lines. A failed fetch's message is escaped
 * the same way `buildTooltip` already escapes `assignee`: free-form, sq-authored text landing
 * in a `vscode.MarkdownString`. */
export function memoryTooltipLine(pool: MemoryFetchResult, now: Date): string {
  const glance = memoryGlanceText(pool, now);
  if (pool.kind === 'failed') {
    return `  \nMemory: ${glance} (${escapeTooltipMarkdown(pool.message)})`;
  }
  return `  \nMemory: ${glance}`;
}

/** One memory entry's tree-child label: slug, summary, and age when available. Plain text — a
 * `vscode.TreeItem.label`, never markdown/HTML — so a summary containing HTML- or markdown-
 * significant characters renders as literal text, not injected markup. */
export function memoryEntryLabel(entry: SqMemoryListRow, now: Date): string {
  const age =
    typeof entry.created_at === 'string' ? `  (${humanizeAge(entry.created_at, now)})` : '';
  return `${entry.slug}  ${entry.description}${age}`;
}

/** One memory entry's tooltip: its full summary (the label may have been visually truncated by
 * the tree width) plus its timestamp, escaped the same way a free-form sq-authored string always
 * is before landing in a `vscode.MarkdownString`. */
export function memoryEntryTooltip(entry: SqMemoryListRow): string {
  const created = entry.created_at ?? 'unknown age';
  return `${escapeTooltipMarkdown(entry.description)}  \n${created}`;
}

const MEMORY_ENTRY_ICON = 'note';

function memoryEntryNode(roleSlug: string, entry: SqMemoryListRow, now: Date): DisplayNode {
  return {
    id: `memory:${roleSlug}:${entry.slug}`,
    itemId: null,
    memoryRef: { roleSlug, entrySlug: entry.slug },
    label: memoryEntryLabel(entry, now),
    description: '',
    tooltip: memoryEntryTooltip(entry),
    iconId: MEMORY_ENTRY_ICON,
    blocked: false,
    closed: false,
    hidden: false,
    colorIntent: null,
    anchor: false,
    children: [],
  };
}

/** A Role/Operator identity's memory children, oldest-touched first — `[]` for an identity
 * never fetched (not memory-eligible, or filtered out), a failed fetch (renders without
 * children, per the feature's degrade rule), or a genuinely empty pool. */
export function memoryChildren(
  roleSlug: string,
  pool: MemoryFetchResult | undefined,
  now: Date,
): DisplayNode[] {
  if (pool === undefined || pool.kind === 'failed') {
    return [];
  }
  return sortMemoryEntries(pool.entries).map((entry) => memoryEntryNode(roleSlug, entry, now));
}

/** Renders a `getMemoryShow` outcome to the memory-entry panel's body HTML — the drill-to-body
 * step: summary, timestamp, and tags in the header, then the full body, both through the
 * same `renderMarkdownToHtml` path the item preview uses (the one thing that actually escapes
 * HTML-significant characters here; this module never emits raw HTML of its own). Same
 * outcome-to-HTML shape as `domain/boardView.ts::renderBoardHtml` /
 * `previewDocument.ts::renderWorkflowHtml` — the failure message becomes the whole document body
 * rather than the panel rendering blank. */
export function renderMemoryEntryHtml(outcome: SqOutcome<SqMemoryDetail>): string {
  if (outcome.kind !== 'success') {
    return renderMarkdownToHtml(`# Squads: unable to load memory entry\n\n${outcome.message}`);
  }
  const entry = outcome.data;
  const tagsLine = entry.tags.length > 0 ? `\n\nTags: ${entry.tags.join(', ')}` : '';
  const header = `# ${entry.slug}\n\n${entry.summary}\n\n*${entry.created_at}*${tagsLine}`;
  const body = entry.body.trim() === '' ? '*(no body yet)*' : entry.body;
  return renderMarkdownToHtml(`${header}\n\n---\n\n${body}`);
}

/** The memory panel's tab title for one entry — plain text, used both as the webview panel
 * `title` and `buildPreviewHtml`'s document `<title>`. */
export function memoryEntryPanelTitle(roleSlug: string, entrySlug: string): string {
  return `${roleSlug}: ${entrySlug}`;
}
