/**
 * Shared vscode-facing rendering: turns a vscode-free `DisplayNode` into a `vscode.TreeItem`.
 * Used by both activity-bar `TreeDataProvider`s (the work tree and the meta/roster view) so the
 * icon/command wiring can't drift between them.
 */
import * as vscode from 'vscode';

import type { DisplayNode } from './domain/displayNode';

function iconForNode(node: DisplayNode): vscode.ThemeIcon {
  if (node.blocked) {
    return new vscode.ThemeIcon(node.iconId, new vscode.ThemeColor('problemsErrorIcon.foreground'));
  }
  if (node.closed) {
    // Only ever true when the show-closed toggle (work tree) or a terminal roster status (meta
    // view) pulled a closed/terminal item into the current fetch — dim it so open vs closed
    // reads at a glance without a separate grouping.
    return new vscode.ThemeIcon(node.iconId, new vscode.ThemeColor('disabledForeground'));
  }
  return new vscode.ThemeIcon(node.iconId);
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
    item.tooltip = node.tooltip;
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
