/**
 * Shared vscode-facing rendering: turns a vscode-free `DisplayNode` into a `vscode.TreeItem`.
 * Used by both activity-bar `TreeDataProvider`s (the work tree and the meta/roster view) so the
 * icon/command wiring can't drift between them.
 */
import * as vscode from 'vscode';

import { type DisplayNode, emphasisForNode, type NodeEmphasis } from './domain/displayNode';

/** ThemeColor id per `emphasisForNode` outcome (`'none'` excluded — the default icon color, no
 * override). The precedence itself (blocked > closed > active) lives in the vscode-free,
 * unit-tested `emphasisForNode`; this is just the presentation mapping. */
const THEME_COLOR_BY_EMPHASIS: Readonly<Record<Exclude<NodeEmphasis, 'none'>, string>> = {
  blocked: 'problemsErrorIcon.foreground',
  // Only ever true when the show-closed toggle (work tree) or a terminal roster status (meta
  // view) pulled a closed/terminal item into the current fetch — dim it so open vs closed
  // reads at a glance without a separate grouping.
  closed: 'disabledForeground',
  // "Work in flight" (F26): the item's status carries the spec-declared "active" role, joined
  // through the statuses catalog by the mapping layer — never a literal status-name check here.
  active: 'charts.green',
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

export function toTreeItem(node: DisplayNode): vscode.TreeItem {
  const collapsibleState =
    node.children.length > 0
      ? vscode.TreeItemCollapsibleState.Collapsed
      : vscode.TreeItemCollapsibleState.None;
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
