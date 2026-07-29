/**
 * Pure domain logic for the third activity-bar view (the "Records" section):
 * buckets `sq list --json` rows into one group per `records`-category type (decision/guide, plus
 * any custom records type a project declares) — the complement of the work tree's records
 * exclusion (`domain/reservedTypes.ts::isReservedType`). Mirrors
 * `domain/metaView.ts::buildMetaView`'s shape (fixed buckets, each always present, numeric id
 * order within a bucket, narrowable by `state` before bucketing — `domain/recordsFilter.ts`),
 * with one difference: unlike roster's 3 fixed buckets, the records bucket LIST itself is
 * spec-driven — derived from `domain/typeCategory.ts`'s category map, never a hardcoded
 * decision/guide/contract list, so a project's own custom records type gets a bucket with no
 * client change. `state.groupByType: false` flattens every bucket into one id-sorted list, same
 * flattening `domain/listView.ts::groupListItems` does for the work tree.
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
import {
  DEFAULT_RECORDS_VIEW_STATE,
  matchesRecordsFilter,
  type RecordsViewState,
} from './recordsFilter';
import {
  NO_ROLES,
  NO_STATUS_ROLES,
  resolveRole,
  type RoleCatalogMap,
  type StatusRoleMap,
} from './statusRole';
import { NO_CATEGORIES, recordsTypes, type TypeCategoryMap } from './typeCategory';
import { NO_LABELS, pluralLabel, type TypeLabelMap } from './typeLabels';
import { NO_TYPE_ORDER, sortTypesByOrder, type TypeOrderMap } from './typeOrder';

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
    // Status alone — same as `metaView.ts`: a records item's assignee (an ADR, a guide) isn't
    // the operative field the way it is for work items.
    description: item.status,
    tooltip: buildTooltip({
      id: item.id,
      type: item.type,
      status: item.status,
      assignee: item.assignee,
      badges: resolveItemBadges(item.type, item.badges, fieldBindings, badgeVocabulary),
      blocked: false,
    }),
    iconId: iconForType(item.type, iconOverrides),
    blocked: false,
    closed: role?.settled ?? false,
    hidden: role?.hidden ?? false,
    colorIntent: role?.color ?? null,
    children: [],
  };
}

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

/** The rendering-only trailing inputs to `buildRecordsView`, bundled into one options object
 * (rather than 6 trailing parameters) to stay under the project's max-params bar — same
 * rationale as `domain/listView.ts::FilteredGroupedViewOptions`. `categoryMap`/`orderMap` stay
 * positional: they decide which buckets exist at all, not just how a bucket renders. Every
 * field defaults to its own graceful-fallback empty value. */
export interface RecordsViewOptions {
  readonly iconOverrides?: TypeIconOverrides;
  readonly fieldBindings?: FieldBindingsByType;
  readonly badgeVocabulary?: BadgeVocabulary;
  readonly statusRoles?: StatusRoleMap;
  readonly roleCatalog?: RoleCatalogMap;
  /** Resolves each bucket's header to its spec-driven plural label (`domain/typeLabels.ts`) —
   * defaults to `NO_LABELS`, which falls back to the raw type string. */
  readonly labelMap?: TypeLabelMap;
}

/** Builds the records view's roots: one group per declared `records`-category type
 * (`domain/typeCategory.ts::recordsTypes`, ordered by the spec's per-type `order` — `orderMap`
 * defaults to `NO_TYPE_ORDER`, degrading to type-name order), each always present (even with 0
 * items, whether from an empty fetch or `state.showTerminal: false` filtering a bucket empty).
 * `state.groupByType: false` (default `true`) skips the per-type buckets and returns every
 * surviving item as one id-sorted flat list instead. When `categoryMap` is empty (the
 * type-catalog fetch failed or hasn't completed), there is no way to know which types are
 * records, so this returns no buckets/leaves at all rather than guessing at a hardcoded list —
 * the same "can't tell yet" default `isReservedType` uses to keep those same rows in the work
 * tree meanwhile. `options` (icons/badges/status-role/labels) defaults every field to its own
 * graceful-fallback empty value when omitted. */
export function buildRecordsView(
  items: readonly SqListItem[],
  categoryMap: TypeCategoryMap = NO_CATEGORIES,
  orderMap: TypeOrderMap = NO_TYPE_ORDER,
  state: RecordsViewState = DEFAULT_RECORDS_VIEW_STATE,
  options: RecordsViewOptions = {},
): DisplayNode[] {
  const {
    iconOverrides = {},
    fieldBindings = NO_FIELD_BINDINGS,
    badgeVocabulary = NO_BADGE_VOCABULARY,
    statusRoles = NO_STATUS_ROLES,
    roleCatalog = NO_ROLES,
    labelMap = NO_LABELS,
  } = options;
  const types = sortTypesByOrder(recordsTypes(categoryMap), orderMap);
  const recordsTypeSet = new Set(types);
  const visible = items.filter(
    (item) =>
      recordsTypeSet.has(item.type) && matchesRecordsFilter(item, state, statusRoles, roleCatalog),
  );
  if (!state.groupByType) {
    return sortedLeaves(
      visible,
      iconOverrides,
      fieldBindings,
      badgeVocabulary,
      statusRoles,
      roleCatalog,
    );
  }
  return types.map((type) => {
    const bucketItems = visible.filter((item) => item.type === type);
    return groupDisplayNode(
      `records:${type}`,
      pluralLabel(type, labelMap),
      bucketItems.length,
      sortedLeaves(
        bucketItems,
        iconOverrides,
        fieldBindings,
        badgeVocabulary,
        statusRoles,
        roleCatalog,
      ),
    );
  });
}
