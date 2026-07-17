/**
 * Filter/group logic over `sq list --json` for the flat/filtered/grouped tree view. Open/closed
 * is a show/hide fetch toggle owned by the caller (whether closed items are present in `items`
 * at all), not a grouping axis or an in-memory classification step here — this module only
 * type-filters and optionally groups by type.
 */
import type { SqListItem } from '../types';
import { buildTooltip, type DisplayNode, groupDisplayNode, iconForType } from './displayNode';
import { compareIds } from './idOrder';
import { isReservedType } from './reservedTypes';

export interface ListFilter {
  readonly type: string | null;
}

export const NO_FILTER: ListFilter = { type: null };

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

export function matchesFilter(item: SqListItem, filter: ListFilter): boolean {
  return filter.type === null || item.type === filter.type;
}

export function filterListItems(items: readonly SqListItem[], filter: ListFilter): SqListItem[] {
  return items.filter((item) => matchesFilter(item, filter));
}

function itemToLeaf(item: SqListItem): DisplayNode {
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
    closed: !item.is_open,
    children: [],
  };
}

function sortedTypeEntries<T>(map: ReadonlyMap<string, T>): [string, T][] {
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
}

/** Items sorted by id using shared numeric collation (a lower sequence number sorts first, never
 * plain lexicographic), mapped to leaf display nodes. */
function sortedLeaves(items: readonly SqListItem[]): DisplayNode[] {
  return [...items].sort((a, b) => compareIds(a.id, b.id)).map(itemToLeaf);
}

/** Groups `items` by type (one bucket per distinct type, sorted by type name) when
 * `groupByType`, otherwise returns the items themselves as sorted leaves. There is no
 * open/closed grouping axis: open/closed is a separate show/hide toggle plus a dimmed visual
 * treatment applied by the tree-item renderer, not a grouping mode. */
export function groupListItems(items: readonly SqListItem[], groupByType: boolean): DisplayNode[] {
  if (!groupByType) {
    return sortedLeaves(items);
  }
  const buckets = new Map<string, SqListItem[]>();
  for (const item of items) {
    const bucket = buckets.get(item.type);
    if (bucket === undefined) {
      buckets.set(item.type, [item]);
    } else {
      bucket.push(item);
    }
  }
  return sortedTypeEntries(buckets).map(([type, groupItems]) =>
    groupDisplayNode(`group:type:${type}`, type, groupItems.length, sortedLeaves(groupItems)),
  );
}

/** End-to-end: exclude reserved types, filter by type, then group by type if requested. Whether
 * closed items appear in `items` at all is the caller's fetch-time decision (the show-closed
 * toggle), not something this function classifies or filters. */
export function buildFilteredGroupedView(
  items: readonly SqListItem[],
  filter: ListFilter,
  groupByType: boolean,
): DisplayNode[] {
  return groupListItems(filterListItems(excludeReservedTypes(items), filter), groupByType);
}
