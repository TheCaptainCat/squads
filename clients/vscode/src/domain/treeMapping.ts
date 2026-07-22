/**
 * Maps `sq tree --json` (id/type/title/status/priority/assignee/blocked/badges/children) into
 * `DisplayNode`s. Open/closed/colour state  is derived by joining each node's `status`
 * through the statuses/roles catalogs (`domain/statusRole.ts`) — `sq tree` itself carries no
 * per-node open/closed field any more.
 */
import type { SqTreeNode } from '../types';
import {
  type BadgeVocabulary,
  type FieldBindingsByType,
  NO_BADGE_VOCABULARY,
  NO_FIELD_BINDINGS,
  resolveItemBadges,
} from './badgeCatalog';
import { buildTooltip, type DisplayNode, iconForType, type TypeIconOverrides } from './displayNode';
import { isReservedType } from './reservedTypes';
import {
  NO_ROLES,
  NO_STATUS_ROLES,
  resolveRole,
  type RoleCatalogMap,
  type StatusRoleMap,
} from './statusRole';
import { NO_CATEGORIES, type TypeCategoryMap } from './typeCategory';
import { NO_TYPE_ORDER, sortTypesByOrder, type TypeOrderMap } from './typeOrder';

function describeNode(node: SqTreeNode): string {
  const base = `${node.status} · ${node.assignee ?? 'unassigned'}`;
  return node.blocked ? `${base} · blocked` : base;
}

function mapNode(
  node: SqTreeNode,
  iconOverrides: TypeIconOverrides,
  fieldBindings: FieldBindingsByType,
  badgeVocabulary: BadgeVocabulary,
  statusRoles: StatusRoleMap,
  roleCatalog: RoleCatalogMap,
  categoryMap: TypeCategoryMap,
): DisplayNode {
  const role = resolveRole(node.status, statusRoles, roleCatalog);
  return {
    id: node.id,
    itemId: node.id,
    label: `${node.id}  ${node.title}`,
    description: describeNode(node),
    tooltip: buildTooltip({
      id: node.id,
      type: node.type,
      status: node.status,
      assignee: node.assignee,
      badges: resolveItemBadges(node.type, node.badges, fieldBindings, badgeVocabulary),
      blocked: node.blocked,
    }),
    iconId: iconForType(node.type, iconOverrides),
    blocked: node.blocked,
    closed: role?.settled ?? false,
    hidden: role?.hidden ?? false,
    colorIntent: role?.color ?? null,
    children: node.children
      .filter((child) => !isReservedType(child.type, categoryMap))
      .map((child) =>
        mapNode(
          child,
          iconOverrides,
          fieldBindings,
          badgeVocabulary,
          statusRoles,
          roleCatalog,
          categoryMap,
        ),
      ),
  };
}

/** `iconOverrides` (the `squads.typeIcons` setting, F21) defaults to none, layered over the
 * bundled per-type icon defaults for every node in the tree. `fieldBindings`/`badgeVocabulary`
 * (F19), `statusRoles`/`roleCatalog` , and `categoryMap`  default to the
 * graceful-fallback empty maps, degrading the tooltip's badge rendering to raw codes / disabling
 * the colour highlight / falling back to roster-only exclusion rather than breaking the tree when
 * a catalog fetch failed. */
export function treeNodesToDisplay(
  nodes: readonly SqTreeNode[],
  iconOverrides: TypeIconOverrides = {},
  fieldBindings: FieldBindingsByType = NO_FIELD_BINDINGS,
  badgeVocabulary: BadgeVocabulary = NO_BADGE_VOCABULARY,
  statusRoles: StatusRoleMap = NO_STATUS_ROLES,
  roleCatalog: RoleCatalogMap = NO_ROLES,
  categoryMap: TypeCategoryMap = NO_CATEGORIES,
): DisplayNode[] {
  return nodes
    .filter((node) => !isReservedType(node.type, categoryMap))
    .map((node) =>
      mapNode(
        node,
        iconOverrides,
        fieldBindings,
        badgeVocabulary,
        statusRoles,
        roleCatalog,
        categoryMap,
      ),
    );
}

/** Distinct, non-reserved item types present anywhere in the tree, ordered by the spec's
 * per-type `order` (F1; `orderMap` defaults to `NO_TYPE_ORDER`, degrading gracefully to a
 * type-name sort when the catalog fetch failed) — feeds the "filter by type" quick-pick's
 * option list without a second `sq list --json` fetch just for the type catalog. */
export function distinctTypesInTree(
  nodes: readonly SqTreeNode[],
  orderMap: TypeOrderMap = NO_TYPE_ORDER,
  categoryMap: TypeCategoryMap = NO_CATEGORIES,
): string[] {
  const types = new Set<string>();
  const visit = (node: SqTreeNode): void => {
    if (!isReservedType(node.type, categoryMap)) {
      types.add(node.type);
    }
    node.children.forEach(visit);
  };
  nodes.forEach(visit);
  return sortTypesByOrder([...types], orderMap);
}
