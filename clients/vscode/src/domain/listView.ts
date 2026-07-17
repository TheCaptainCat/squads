/**
 * Filter/group logic over `sq list --json` for the flat/filtered/grouped tree view. Open/closed
 * classification is derived from the CLI's own default-vs-`--all` behaviour (default hides closed
 * items; `--all` reveals them) rather than a locally hand-maintained status list — statuses are
 * workflow-spec-driven per project, so no fixed "these are the terminal statuses" table would
 * stay correct everywhere.
 */
import type { SqListItem } from '../types';
import { buildTooltip, type DisplayNode, groupDisplayNode, iconForType } from './displayNode';
import { isReservedType } from './reservedTypes';

export type OpenClosedState = 'open' | 'closed';
export type GroupKey = 'type' | 'state';

export interface ListFilter {
  readonly type: string | null;
  readonly state: OpenClosedState | null;
}

export const NO_FILTER: ListFilter = { type: null, state: null };

export interface ClassifiedListItem extends SqListItem {
  readonly state: OpenClosedState;
}

/** `openIds` is every id present in the CLI's default (closed-hidden) listing; anything in
 * `items` (the `--all` superset) not in that set is closed. */
export function classifyListItems(
  items: readonly SqListItem[],
  openIds: ReadonlySet<string>,
): ClassifiedListItem[] {
  return items.map((item) => ({ ...item, state: openIds.has(item.id) ? 'open' : 'closed' }));
}

export function excludeReservedTypes(items: readonly SqListItem[]): SqListItem[] {
  return items.filter((item) => !isReservedType(item.type));
}

/** Distinct, sorted, non-reserved item types present in `items` — feeds the "filter by type"
 * quick-pick's option list without the client hardcoding a type catalog. */
export function distinctTypes(items: readonly SqListItem[]): string[] {
  return [...new Set(excludeReservedTypes(items).map((item) => item.type))].sort((a, b) =>
    a.localeCompare(b),
  );
}

export function matchesFilter(item: ClassifiedListItem, filter: ListFilter): boolean {
  if (filter.type !== null && item.type !== filter.type) {
    return false;
  }
  return filter.state === null || item.state === filter.state;
}

export function filterListItems(
  items: readonly ClassifiedListItem[],
  filter: ListFilter,
): ClassifiedListItem[] {
  return items.filter((item) => matchesFilter(item, filter));
}

function itemToLeaf(item: ClassifiedListItem): DisplayNode {
  return {
    id: item.id,
    itemId: item.id,
    label: `${item.id}  ${item.title}`,
    description: `${item.status} · ${item.assignee ?? 'unassigned'}`,
    tooltip: buildTooltip({
      id: item.id,
      type: item.type,
      status: item.status,
      assignee: item.assignee,
      priority: item.priority,
      blocked: false,
    }),
    iconId: iconForType(item.type),
    // `sq list --json` carries no blocked flag (that's a tree-only field, computed from
    // dependency edges); the flat/grouped view doesn't surface blocked-state.
    blocked: false,
    children: [],
  };
}

function groupLabel(key: GroupKey, item: ClassifiedListItem): string {
  return key === 'type' ? item.type : item.state === 'open' ? 'Open' : 'Closed';
}

function sortedEntries<T>(map: ReadonlyMap<string, T>): [string, T][] {
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
}

/** Recursively partitions `items` by each key in `groupBy`, in order; an empty `groupBy`
 * returns the items themselves as leaves (sorted by id for a stable, deterministic view). */
export function groupListItems(
  items: readonly ClassifiedListItem[],
  groupBy: readonly GroupKey[],
): DisplayNode[] {
  const [key, ...restKeys] = groupBy;
  if (key === undefined) {
    return [...items].sort((a, b) => a.id.localeCompare(b.id)).map(itemToLeaf);
  }
  const buckets = new Map<string, ClassifiedListItem[]>();
  for (const item of items) {
    const label = groupLabel(key, item);
    const bucket = buckets.get(label);
    if (bucket === undefined) {
      buckets.set(label, [item]);
    } else {
      bucket.push(item);
    }
  }
  return sortedEntries(buckets).map(([label, groupItems]) => {
    const children = groupListItems(groupItems, restKeys);
    return groupDisplayNode(`group:${key}:${label}`, label, groupItems.length, children);
  });
}

/** End-to-end: exclude reserved types, classify open/closed, filter, then group. */
export function buildFilteredGroupedView(
  items: readonly SqListItem[],
  openIds: ReadonlySet<string>,
  filter: ListFilter,
  groupBy: readonly GroupKey[],
): DisplayNode[] {
  const classified = classifyListItems(excludeReservedTypes(items), openIds);
  return groupListItems(filterListItems(classified, filter), groupBy);
}
