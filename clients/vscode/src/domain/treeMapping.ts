/**
 * Maps `sq tree --json` (id/type/title/status/priority/assignee/blocked/is_open/children) into
 * `DisplayNode`s. The tree payload is now self-sufficient for labels and open/closed state — no
 * sibling `sq list --json` fetch is needed to join titles by id.
 */
import type { SqTreeNode } from '../types';
import { buildTooltip, type DisplayNode, iconForType } from './displayNode';
import { isReservedType } from './reservedTypes';

function describeNode(node: SqTreeNode): string {
  const base = `${node.status} · ${node.assignee ?? 'unassigned'}`;
  return node.blocked ? `${base} · blocked` : base;
}

function mapNode(node: SqTreeNode): DisplayNode {
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
      priority: node.priority,
      blocked: node.blocked,
    }),
    iconId: iconForType(node.type),
    blocked: node.blocked,
    closed: !node.is_open,
    children: node.children.filter((child) => !isReservedType(child.type)).map(mapNode),
  };
}

export function treeNodesToDisplay(nodes: readonly SqTreeNode[]): DisplayNode[] {
  return nodes.filter((node) => !isReservedType(node.type)).map(mapNode);
}

/** Distinct, sorted, non-reserved item types present anywhere in the tree — feeds the "filter by
 * type" quick-pick's option list without a second `sq list --json` fetch just for the type
 * catalog. */
export function distinctTypesInTree(nodes: readonly SqTreeNode[]): string[] {
  const types = new Set<string>();
  const visit = (node: SqTreeNode): void => {
    if (!isReservedType(node.type)) {
      types.add(node.type);
    }
    node.children.forEach(visit);
  };
  nodes.forEach(visit);
  return [...types].sort((a, b) => a.localeCompare(b));
}
