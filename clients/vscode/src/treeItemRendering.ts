/**
 * Shared vscode-facing rendering: turns a vscode-free `DisplayNode` into a `vscode.TreeItem`.
 * Used by both activity-bar `TreeDataProvider`s (the work tree and the meta/roster view) so the
 * icon/command wiring can't drift between them.
 */
import * as vscode from 'vscode';

import { type DisplayNode, emphasisForNode, type NodeEmphasis } from './domain/displayNode';

/** ThemeColor id per `emphasisForNode` outcome (`'none'` excluded — the default icon color, no
 * override). The precedence itself (blocked > hidden > colour) lives in the vscode-free,
 * unit-tested `emphasisForNode`; this is just the presentation mapping (the spec
 * declares a semantic colour *intent*, never a concrete colour — each client picks its own). */
const THEME_COLOR_BY_EMPHASIS: Readonly<Record<Exclude<NodeEmphasis, 'none'>, string>> = {
  blocked: 'problemsErrorIcon.foreground',
  // Only ever true when the show-closed toggle (work tree) or the roster's `--all` fetch pulled
  // an item whose role is `hidden` into view — dim it so open vs closed/put-away reads at a
  // glance without a separate grouping. Deliberately decoupled from `settled`/`closed`: a
  // settled-but-visible role (e.g. `in_force` — Accepted/Published) is NOT hidden, so it renders
  // in its own `info` colour below instead of greyed out like finished work.
  hidden: 'disabledForeground',
  positive: 'charts.green',
  danger: 'charts.red',
  warning: 'charts.yellow',
  muted: 'disabledForeground',
  info: 'charts.blue',
};

function iconForNode(node: DisplayNode): vscode.ThemeIcon {
  const emphasis = emphasisForNode(node);
  if (emphasis === 'none') {
    return new vscode.ThemeIcon(node.iconId);
  }
  return new vscode.ThemeIcon(
    node.iconId,
    new vscode.ThemeColor(THEME_COLOR_BY_EMPHASIS[emphasis]),
  );
}

/**
 * `isExpanded` reports whether a node's id is currently tracked as expanded (an
 * `ExpansionTracker`, kept by the caller's provider) — a leafless node renders `Collapsed` by
 * default and `Expanded` only for a tracked id, so a previously-expanded node stays open across
 * a refresh instead of folding back to its default collapsed state. Defaults to "never
 * expanded" so callers that don't track expansion (there are none left, but keeps this function
 * usable standalone) get the old always-collapsed behavior.
 */
export function toTreeItem(
  node: DisplayNode,
  isExpanded: (id: string) => boolean = () => false,
): vscode.TreeItem {
  const collapsibleState =
    node.children.length === 0
      ? vscode.TreeItemCollapsibleState.None
      : isExpanded(node.id)
        ? vscode.TreeItemCollapsibleState.Expanded
        : vscode.TreeItemCollapsibleState.Collapsed;
  const item = new vscode.TreeItem(node.label, collapsibleState);
  item.id = node.id;
  if (node.description !== '') {
    item.description = node.description;
  }
  if (node.tooltip !== '') {
    // A MarkdownString (F19) rather than a plain string tooltip: `buildTooltip` joins
    // its lines with markdown hard-breaks so a rendered collection badge (e.g. "🟠 High") shows
    // on its own line rather than running the whole tooltip together.
    item.tooltip = new vscode.MarkdownString(node.tooltip);
  }
  item.iconPath = iconForNode(node);
  if (node.itemId !== null) {
    item.contextValue = 'squadsItem';
    item.command = {
      command: 'squads.openItemPreview',
      title: 'Open in Preview',
      arguments: [node.itemId],
    };
  }
  return item;
}
