/**
 * Maps `sq tree --json` (id/type/title/status/priority/assignee/blocked/badges/anchor/
 * children) into `DisplayNode`s. Open/closed/colour state is derived by joining each node's
 * `status` through the statuses/roles catalogs (`domain/statusRole.ts`) — `sq tree` itself
 * carries no per-node open/closed field any more.
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
import { CYCLE_ANCHOR_DESCRIPTION_TAG } from './treeAnchor';
import { NO_CATEGORIES, type TypeCategoryMap } from './typeCategory';
import { NO_TYPE_ORDER, sortTypesByOrder, type TypeOrderMap } from './typeOrder';

/** The row's grey secondary line. `blocked` and the cycle-anchor tag are independent states
 * that can both hold on one node, so each appends rather than replacing — a node that is both
 * must not have either fact hidden by the other. */
function describeNode(node: SqTreeNode): string {
  const parts = [`${node.status} · ${node.assignee ?? 'unassigned'}`];
  if (node.blocked) {
    parts.push('blocked');
  }
  if (node.anchor === true) {
    parts.push(CYCLE_ANCHOR_DESCRIPTION_TAG);
  }
  return parts.join(' · ');
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
  // An older `sq` omits the key; absent means the same as `false` (nobody invented this root).
  const anchor = node.anchor ?? false;
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
      anchor,
    }),
    iconId: iconForType(node.type, iconOverrides),
    blocked: node.blocked,
    closed: role?.settled ?? false,
    hidden: role?.hidden ?? false,
    colorIntent: role?.color ?? null,
    anchor,
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

/** `iconOverrides` (the `squads.typeIcons` setting) defaults to none, layered over the
 * bundled per-type icon defaults for every node in the tree. `fieldBindings`/`badgeVocabulary`,
 * `statusRoles`/`roleCatalog` , and `categoryMap`  default to the
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
 * per-type `order` (`orderMap` defaults to `NO_TYPE_ORDER`, degrading gracefully to a
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
