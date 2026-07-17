/**
 * Maps `sq tree --json` (id/type/status/priority/assignee/blocked/children — no title) into
 * `DisplayNode`s. Titles aren't part of the tree surface, so the label falls back to the bare
 * id unless a title lookup (built from a sibling `sq list --json` fetch) supplies one; either
 * way the hierarchy, status, assignee, and blocked-state all come from the tree surface itself.
 */
import type { SqListItem, SqTreeNode } from '../types';
import { buildTooltip, type DisplayNode, iconForType } from './displayNode';
import { isReservedType } from './reservedTypes';

export function buildTitleLookup(items: readonly SqListItem[]): ReadonlyMap<string, string> {
  return new Map(items.map((item) => [item.id, item.title]));
}

function describeNode(node: SqTreeNode): string {
  const base = `${node.status} · ${node.assignee ?? 'unassigned'}`;
  return node.blocked ? `${base} · blocked` : base;
}

function mapNode(node: SqTreeNode, titles: ReadonlyMap<string, string>): DisplayNode {
  const title = titles.get(node.id);
  return {
    id: node.id,
    itemId: node.id,
    label: title === undefined ? node.id : `${node.id}  ${title}`,
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
    children: node.children
      .filter((child) => !isReservedType(child.type))
      .map((child) => mapNode(child, titles)),
  };
}

/** `titles` is optional: an empty lookup degrades gracefully to id-only labels rather than
 * failing the whole tree when the enrichment fetch didn't succeed. */
export function treeNodesToDisplay(
  nodes: readonly SqTreeNode[],
  titles: ReadonlyMap<string, string> = new Map(),
): DisplayNode[] {
  return nodes.filter((node) => !isReservedType(node.type)).map((node) => mapNode(node, titles));
}
