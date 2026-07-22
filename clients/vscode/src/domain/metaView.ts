/**
 * Pure domain logic for the second activity-bar view (the "Roster" section, F12): buckets
 * `sq list --json` rows into the 3 fixed reserved-type subfolders — Roles, Skills, Operators —
 * the complement of the work tree's reserved-type exclusion (`reservedTypes.ts`). Unlike the
 * work tree, this view is never filterable/groupable: always exactly these 3 buckets, in this
 * fixed order, each present even when empty, with items inside a bucket in numeric id order.
 */
import type { SqListItem } from '../types';
import {
  type BadgeVocabulary,
  type FieldBindingsByType,
  NO_BADGE_VOCABULARY,
  NO_FIELD_BINDINGS,
  resolveItemBadges,
} from './badgeCatalog';
import { buildTooltip, type DisplayNode, groupDisplayNode, iconForMetaType } from './displayNode';
import { compareIds } from './idOrder';
import { META_BUCKETS } from './reservedTypes';
import {
  NO_ROLES,
  NO_STATUS_ROLES,
  resolveRole,
  type RoleCatalogMap,
  type StatusRoleMap,
} from './statusRole';

function itemToLeaf(
  item: SqListItem,
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
    // Status alone — assignee is meaningless for meta items (role/skill/operator), unlike the
    // work tree (`treeMapping`/`listView`), which keeps it.
    description: item.status,
    tooltip: buildTooltip({
      id: item.id,
      type: item.type,
      status: item.status,
      assignee: item.assignee,
      badges: resolveItemBadges(item.type, item.badges, fieldBindings, badgeVocabulary),
      blocked: false,
    }),
    iconId: iconForMetaType(item.type),
    blocked: false,
    closed: role?.settled ?? false,
    hidden: role?.hidden ?? false,
    colorIntent: role?.color ?? null,
    children: [],
  };
}

function sortedLeaves(
  items: readonly SqListItem[],
  fieldBindings: FieldBindingsByType,
  badgeVocabulary: BadgeVocabulary,
  statusRoles: StatusRoleMap,
  roleCatalog: RoleCatalogMap,
): DisplayNode[] {
  return [...items]
    .sort((a, b) => compareIds(a.id, b.id))
    .map((item) => itemToLeaf(item, fieldBindings, badgeVocabulary, statusRoles, roleCatalog));
}

/** Builds the meta/roster view's roots: one group per `META_BUCKETS` entry, in that fixed
 * order, each always present (even with 0 items) and never merged/reordered by content.
 * `fieldBindings`/`badgeVocabulary` (F19) and `statusRoles`/`roleCatalog`  default to the
 * graceful-fallback empty maps, degrading each leaf's tooltip badges to raw codes / disabling
 * the colour highlight rather than breaking the view. */
export function buildMetaView(
  items: readonly SqListItem[],
  fieldBindings: FieldBindingsByType = NO_FIELD_BINDINGS,
  badgeVocabulary: BadgeVocabulary = NO_BADGE_VOCABULARY,
  statusRoles: StatusRoleMap = NO_STATUS_ROLES,
  roleCatalog: RoleCatalogMap = NO_ROLES,
): DisplayNode[] {
  return META_BUCKETS.map(({ type, label }) => {
    const bucketItems = items.filter((item) => item.type === type);
    return groupDisplayNode(
      `meta:${type}`,
      label,
      bucketItems.length,
      sortedLeaves(bucketItems, fieldBindings, badgeVocabulary, statusRoles, roleCatalog),
    );
  });
}
