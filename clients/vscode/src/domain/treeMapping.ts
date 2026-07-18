/**
 * Maps `sq tree --json` (id/type/title/status/priority/assignee/blocked/is_open/badges/children)
 * into `DisplayNode`s. The tree payload is now self-sufficient for labels and open/closed state
 * — no sibling `sq list --json` fetch is needed to join titles by id.
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
import { isActiveRole, NO_STATUS_ROLES, type StatusRoleMap } from './statusRole';
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
): DisplayNode {
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
    closed: !node.is_open,
    active: isActiveRole(node.status, statusRoles),
    children: node.children
      .filter((child) => !isReservedType(child.type))
      .map((child) => mapNode(child, iconOverrides, fieldBindings, badgeVocabulary, statusRoles)),
  };
}

/** `iconOverrides` (the `squads.typeIcons` setting, F21) defaults to none, layered over the
 * bundled per-type icon defaults for every node in the tree. `fieldBindings`/`badgeVocabulary`
 * (F19) and `statusRoles` (F26) default to the graceful-fallback empty maps, degrading the
 * tooltip's badge rendering to raw codes / disabling the active-green highlight rather than
 * breaking the tree when a catalog fetch failed. */
export function treeNodesToDisplay(
  nodes: readonly SqTreeNode[],
  iconOverrides: TypeIconOverrides = {},
  fieldBindings: FieldBindingsByType = NO_FIELD_BINDINGS,
  badgeVocabulary: BadgeVocabulary = NO_BADGE_VOCABULARY,
  statusRoles: StatusRoleMap = NO_STATUS_ROLES,
): DisplayNode[] {
  return nodes
    .filter((node) => !isReservedType(node.type))
    .map((node) => mapNode(node, iconOverrides, fieldBindings, badgeVocabulary, statusRoles));
}

/** Distinct, non-reserved item types present anywhere in the tree, ordered by the spec's
 * per-type `order` (F1; `orderMap` defaults to `NO_TYPE_ORDER`, degrading gracefully to a
 * type-name sort when the catalog fetch failed) — feeds the "filter by type" quick-pick's
 * option list without a second `sq list --json` fetch just for the type catalog. */
export function distinctTypesInTree(
  nodes: readonly SqTreeNode[],
  orderMap: TypeOrderMap = NO_TYPE_ORDER,
): string[] {
  const types = new Set<string>();
  const visit = (node: SqTreeNode): void => {
    if (!isReservedType(node.type)) {
      types.add(node.type);
    }
    node.children.forEach(visit);
  };
  nodes.forEach(visit);
  return sortTypesByOrder([...types], orderMap);
}
