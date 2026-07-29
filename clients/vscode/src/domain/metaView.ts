/**
 * Pure domain logic for the second activity-bar view (the "Roster" section): buckets
 * `sq list --json` rows into the 3 fixed reserved-type subfolders — Roles, Skills, Operators —
 * the complement of the work tree's reserved-type exclusion (`reservedTypes.ts`). Never
 * groupable (always exactly these 3 buckets, in this fixed order, each present even when empty,
 * items inside a bucket in numeric id order) but — like the work tree's show-closed toggle and
 * type filter — narrowable: `state` (`domain/metaFilter.ts`) hides archived-by-default entries
 * and/or restricts to one status before bucketing, so a bucket's count reflects what's actually
 * shown rather than everything fetched.
 * The 3 bucket *types* are the fixed `META_BUCKETS` list; each bucket's rendered *label* is
 * resolved from the type catalog via the shared `domain/typeLabels.ts::pluralLabel` resolver —
 * the same one the Records and Work trees route through — falling back to the raw type string
 * when the catalog fetch failed, hasn't completed, or the connected `sq` predates the resolved
 * `labels` field.
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
import { DEFAULT_META_VIEW_STATE, matchesMetaFilter, type MetaViewState } from './metaFilter';
import { META_BUCKETS } from './reservedTypes';
import {
  NO_ROLES,
  NO_STATUS_ROLES,
  resolveRole,
  type RoleCatalogMap,
  type StatusRoleMap,
} from './statusRole';
import { NO_LABELS, pluralLabel, type TypeLabelMap } from './typeLabels';

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
 * order, each always present (even with 0 items, whether from an empty fetch or a filter that
 * matched nothing in that bucket) and never merged/reordered by content. `fieldBindings`/
 * `badgeVocabulary` and `statusRoles`/`roleCatalog` default to the graceful-fallback empty maps,
 * degrading each leaf's tooltip badges to raw codes / disabling the colour highlight rather than
 * breaking the view. `labelMap` defaults to `NO_LABELS`, resolving each bucket's header via the
 * shared `pluralLabel` resolver rather than a hardcoded literal — falls back to the raw type
 * string the same way every other tree does. `state` defaults to `DEFAULT_META_VIEW_STATE`
 * (archived hidden, no status filter) — see `domain/metaFilter.ts` for the predicate. */
export function buildMetaView(
  items: readonly SqListItem[],
  fieldBindings: FieldBindingsByType = NO_FIELD_BINDINGS,
  badgeVocabulary: BadgeVocabulary = NO_BADGE_VOCABULARY,
  statusRoles: StatusRoleMap = NO_STATUS_ROLES,
  roleCatalog: RoleCatalogMap = NO_ROLES,
  labelMap: TypeLabelMap = NO_LABELS,
  state: MetaViewState = DEFAULT_META_VIEW_STATE,
): DisplayNode[] {
  const visible = items.filter((item) => matchesMetaFilter(item, state, statusRoles, roleCatalog));
  return META_BUCKETS.map(({ type }) => {
    const bucketItems = visible.filter((item) => item.type === type);
    return groupDisplayNode(
      `meta:${type}`,
      pluralLabel(type, labelMap),
      bucketItems.length,
      sortedLeaves(bucketItems, fieldBindings, badgeVocabulary, statusRoles, roleCatalog),
    );
  });
}
