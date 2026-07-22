/**
 * Filter/group logic over `sq list --json` for the flat/filtered/grouped tree view. Open/closed
 * is a show/hide fetch toggle owned by the caller (whether closed items are present in `items`
 * at all), not a grouping axis or an in-memory classification step here — this module only
 * type-filters and optionally groups by type.
 */
import type { SqListItem } from '../types';
import {
  type BadgeVocabulary,
  type FieldBindingsByType,
  NO_BADGE_VOCABULARY,
  NO_FIELD_BINDINGS,
  resolveItemBadges,
} from './badgeCatalog';
import {
  buildTooltip,
  type DisplayNode,
  groupDisplayNode,
  iconForType,
  type TypeIconOverrides,
} from './displayNode';
import { compareIds } from './idOrder';
import { isReservedType } from './reservedTypes';
import {
  NO_ROLES,
  NO_STATUS_ROLES,
  resolveRole,
  type RoleCatalogMap,
  type StatusRoleMap,
} from './statusRole';
import { NO_CATEGORIES, type TypeCategoryMap } from './typeCategory';
import {
  compareTypesByOrder,
  NO_TYPE_ORDER,
  sortTypesByOrder,
  type TypeOrderMap,
} from './typeOrder';

export interface ListFilter {
  readonly type: string | null;
}

export const NO_FILTER: ListFilter = { type: null };

/** `categoryMap` defaults to `NO_CATEGORIES`  — see `isReservedType`'s doc comment
 * for the graceful-degradation contract. */
export function excludeReservedTypes(
  items: readonly SqListItem[],
  categoryMap: TypeCategoryMap = NO_CATEGORIES,
): SqListItem[] {
  return items.filter((item) => !isReservedType(item.type, categoryMap));
}

/** Distinct, non-reserved item types present in `items`, ordered by the spec's per-type `order`
 * (F1) — feeds the "filter by type" quick-pick's option list without the client hardcoding a
 * type catalog or its ordering. `orderMap`/`categoryMap` default to their graceful fallbacks
 * when the catalog fetch failed. */
export function distinctTypes(
  items: readonly SqListItem[],
  orderMap: TypeOrderMap = NO_TYPE_ORDER,
  categoryMap: TypeCategoryMap = NO_CATEGORIES,
): string[] {
  return sortTypesByOrder(
    [...new Set(excludeReservedTypes(items, categoryMap).map((item) => item.type))],
    orderMap,
  );
}

export function matchesFilter(item: SqListItem, filter: ListFilter): boolean {
  return filter.type === null || item.type === filter.type;
}

export function filterListItems(items: readonly SqListItem[], filter: ListFilter): SqListItem[] {
  return items.filter((item) => matchesFilter(item, filter));
}

function itemToLeaf(
  item: SqListItem,
  iconOverrides: TypeIconOverrides,
  fieldBindings: FieldBindingsByType,
  badgeVocabulary: BadgeVocabulary,
  statusRoles: StatusRoleMap,
  roleCatalog: RoleCatalogMap,
): DisplayNode {
  const role = resolveRole(item.status, statusRoles, roleCatalog);
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
      badges: resolveItemBadges(item.type, item.badges, fieldBindings, badgeVocabulary),
      blocked: false,
    }),
    iconId: iconForType(item.type, iconOverrides),
    // `sq list --json` carries no blocked flag (that's a tree-only field, computed from
    // dependency edges); the flat/grouped view doesn't surface blocked-state.
    blocked: false,
    closed: role?.settled ?? false,
    hidden: role?.hidden ?? false,
    colorIntent: role?.color ?? null,
    children: [],
  };
}

function sortedTypeEntries<T>(map: ReadonlyMap<string, T>, orderMap: TypeOrderMap): [string, T][] {
  return [...map.entries()].sort(([a], [b]) => compareTypesByOrder(orderMap, a, b));
}

/** Items sorted by id using shared numeric collation (a lower sequence number sorts first, never
 * plain lexicographic), mapped to leaf display nodes. */
function sortedLeaves(
  items: readonly SqListItem[],
  iconOverrides: TypeIconOverrides,
  fieldBindings: FieldBindingsByType,
  badgeVocabulary: BadgeVocabulary,
  statusRoles: StatusRoleMap,
  roleCatalog: RoleCatalogMap,
): DisplayNode[] {
  return [...items]
    .sort((a, b) => compareIds(a.id, b.id))
    .map((item) =>
      itemToLeaf(item, iconOverrides, fieldBindings, badgeVocabulary, statusRoles, roleCatalog),
    );
}

/** Groups `items` by type (one bucket per distinct type, ordered by the spec's per-type `order`
 * — F1, `orderMap` defaults to `NO_TYPE_ORDER` which degrades gracefully to a type-name sort)
 * when `groupByType`, otherwise returns the items themselves as sorted leaves. There is no
 * open/closed grouping axis: open/closed is a separate show/hide toggle plus a dimmed visual
 * treatment applied by the tree-item renderer, not a grouping mode. `iconOverrides` (the
 * `squads.typeIcons` setting, F21) defaults to none. `fieldBindings`/`badgeVocabulary` (F19) and
 * `statusRoles`/`roleCatalog`  default to the graceful-fallback empty maps. */
export function groupListItems(
  items: readonly SqListItem[],
  groupByType: boolean,
  orderMap: TypeOrderMap = NO_TYPE_ORDER,
  iconOverrides: TypeIconOverrides = {},
  fieldBindings: FieldBindingsByType = NO_FIELD_BINDINGS,
  badgeVocabulary: BadgeVocabulary = NO_BADGE_VOCABULARY,
  statusRoles: StatusRoleMap = NO_STATUS_ROLES,
  roleCatalog: RoleCatalogMap = NO_ROLES,
): DisplayNode[] {
  if (!groupByType) {
    return sortedLeaves(
      items,
      iconOverrides,
      fieldBindings,
      badgeVocabulary,
      statusRoles,
      roleCatalog,
    );
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
  return sortedTypeEntries(buckets, orderMap).map(([type, groupItems]) =>
    groupDisplayNode(
      `group:type:${type}`,
      type,
      groupItems.length,
      sortedLeaves(
        groupItems,
        iconOverrides,
        fieldBindings,
        badgeVocabulary,
        statusRoles,
        roleCatalog,
      ),
    ),
  );
}

/** The catalog-derived inputs `buildFilteredGroupedView` threads through to `groupListItems` —
 * bundled into one options object (rather than 7 trailing parameters) to stay under the
 * project's max-params bar. Every field defaults to its own graceful-fallback empty value, same
 * as the un-bundled parameters on `groupListItems`/`treeNodesToDisplay`. */
export interface FilteredGroupedViewOptions {
  readonly orderMap?: TypeOrderMap;
  readonly iconOverrides?: TypeIconOverrides;
  readonly fieldBindings?: FieldBindingsByType;
  readonly badgeVocabulary?: BadgeVocabulary;
  readonly statusRoles?: StatusRoleMap;
  readonly roleCatalog?: RoleCatalogMap;
  readonly categoryMap?: TypeCategoryMap;
}

/** End-to-end: exclude reserved types, filter by type, then group by type if requested, groups
 * ordered by the spec's per-type `order` (F1). Whether closed items appear in `items` at all is
 * the caller's fetch-time decision (the show-closed toggle), not something this function
 * classifies or filters. `options` (badges/icons/status-role/category, F19/F21) defaults every
 * field to its own graceful-fallback empty value when omitted. */
export function buildFilteredGroupedView(
  items: readonly SqListItem[],
  filter: ListFilter,
  groupByType: boolean,
  options: FilteredGroupedViewOptions = {},
): DisplayNode[] {
  const {
    orderMap = NO_TYPE_ORDER,
    iconOverrides = {},
    fieldBindings = NO_FIELD_BINDINGS,
    badgeVocabulary = NO_BADGE_VOCABULARY,
    statusRoles = NO_STATUS_ROLES,
    roleCatalog = NO_ROLES,
    categoryMap = NO_CATEGORIES,
  } = options;
  return groupListItems(
    filterListItems(excludeReservedTypes(items, categoryMap), filter),
    groupByType,
    orderMap,
    iconOverrides,
    fieldBindings,
    badgeVocabulary,
    statusRoles,
    roleCatalog,
  );
}
