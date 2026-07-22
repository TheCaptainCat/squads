/**
 * Pure domain logic for the third activity-bar view (the "Records" section):
 * buckets `sq list --json` rows into one group per `records`-category type (decision/guide, plus
 * any custom records type a project declares) — the complement of the work tree's records
 * exclusion (`domain/reservedTypes.ts::isReservedType`). Mirrors
 * `domain/metaView.ts::buildMetaView`'s shape (fixed buckets, each always present, numeric id
 * order within a bucket), with one difference: unlike roster's 3 fixed buckets, the records
 * bucket LIST itself is spec-driven — derived from `domain/typeCategory.ts`'s category map, never
 * a hardcoded decision/guide/contract list, so a project's own custom records type gets a bucket
 * with no client change.
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
  NO_ROLES,
  NO_STATUS_ROLES,
  resolveRole,
  type RoleCatalogMap,
  type StatusRoleMap,
} from './statusRole';
import { NO_CATEGORIES, recordsTypes, type TypeCategoryMap } from './typeCategory';
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

/** Builds the records view's roots: one group per declared `records`-category type
 * (`domain/typeCategory.ts::recordsTypes`, ordered by the spec's per-type `order` — `orderMap`
 * defaults to `NO_TYPE_ORDER`, degrading to type-name order), each always present (even with 0
 * items). When `categoryMap` is empty (the type-catalog fetch failed or hasn't completed), there
 * is no way to know which types are records, so this returns no buckets at all rather than
 * guessing at a hardcoded list — the same "can't tell yet" default `isReservedType` uses to keep
 * those same rows in the work tree meanwhile. `iconOverrides` (F21) defaults to none;
 * `fieldBindings`/`badgeVocabulary` (F19) and `statusRoles`/`roleCatalog`  default to
 * the graceful-fallback empty maps. */
export function buildRecordsView(
  items: readonly SqListItem[],
  categoryMap: TypeCategoryMap = NO_CATEGORIES,
  orderMap: TypeOrderMap = NO_TYPE_ORDER,
  iconOverrides: TypeIconOverrides = {},
  fieldBindings: FieldBindingsByType = NO_FIELD_BINDINGS,
  badgeVocabulary: BadgeVocabulary = NO_BADGE_VOCABULARY,
  statusRoles: StatusRoleMap = NO_STATUS_ROLES,
  roleCatalog: RoleCatalogMap = NO_ROLES,
): DisplayNode[] {
  const types = sortTypesByOrder(recordsTypes(categoryMap), orderMap);
  return types.map((type) => {
    const bucketItems = items.filter((item) => item.type === type);
    return groupDisplayNode(
      `records:${type}`,
      type,
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
