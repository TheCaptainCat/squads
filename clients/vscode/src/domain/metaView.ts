/**
 * Pure domain logic for the second activity-bar view (the "Roster" section, F12): buckets
 * `sq list --json` rows into the 3 fixed reserved-type subfolders — Roles, Skills, Operators —
 * the complement of the work tree's reserved-type exclusion (`reservedTypes.ts`). Unlike the
 * work tree, this view is never filterable/groupable: always exactly these 3 buckets, in this
 * fixed order, each present even when empty, with items inside a bucket in numeric id order.
 */
import type { SqListItem } from '../types';
import { buildTooltip, type DisplayNode, groupDisplayNode, iconForType } from './displayNode';
import { compareIds } from './idOrder';
import { META_BUCKETS } from './reservedTypes';

function itemToLeaf(item: SqListItem): DisplayNode {
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
      priority: item.priority,
      blocked: false,
    }),
    iconId: iconForType(item.type),
    blocked: false,
    closed: !item.is_open,
    children: [],
  };
}

function sortedLeaves(items: readonly SqListItem[]): DisplayNode[] {
  return [...items].sort((a, b) => compareIds(a.id, b.id)).map(itemToLeaf);
}

/** Builds the meta/roster view's roots: one group per `META_BUCKETS` entry, in that fixed
 * order, each always present (even with 0 items) and never merged/reordered by content. */
export function buildMetaView(items: readonly SqListItem[]): DisplayNode[] {
  return META_BUCKETS.map(({ type, label }) => {
    const bucketItems = items.filter((item) => item.type === type);
    return groupDisplayNode(`meta:${type}`, label, bucketItems.length, sortedLeaves(bucketItems));
  });
}
