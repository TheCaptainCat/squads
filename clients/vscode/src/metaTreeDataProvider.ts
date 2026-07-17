/**
 * The second activity-bar view's `TreeDataProvider` (F12, "Roster"): renders the 3 fixed
 * reserved-type buckets (Roles/Skills/Operators) built by the vscode-free `domain/metaView.ts`.
 * Unlike `SquadsTreeDataProvider` there is no filter/group/show-closed state — one `sq list
 * --json --all` fetch (`--all` so a role/skill/operator that ever reaches a terminal status
 * still shows up in its bucket) feeds the 3 buckets directly. Thin glue only, same split as
 * `treeDataProvider.ts`: this module's vscode wiring is exercised by the extension-host smoke
 * test, `buildMetaView` is what's unit-tested.
 */
import * as vscode from 'vscode';

import { describeTriedOrder, type SqDiscovery } from './discovery';
import { type DisplayNode, errorDisplayNode } from './domain/displayNode';
import { buildMetaView } from './domain/metaView';
import type { ProcessRunner } from './processRunner';
import { describeFailure, getList, type SqOutcome } from './sqAdapter';
import { toTreeItem } from './treeItemRendering';

export class SquadsMetaTreeDataProvider implements vscode.TreeDataProvider<DisplayNode> {
  private readonly changeEmitter = new vscode.EventEmitter<DisplayNode | undefined>();
  readonly onDidChangeTreeData = this.changeEmitter.event;

  private roots: DisplayNode[] = [];

  constructor(
    private readonly runner: ProcessRunner,
    private readonly discovery: SqDiscovery,
    private readonly workspaceRoot: string,
    private readonly notifyError: (message: string) => void,
  ) {}

  getTreeItem(node: DisplayNode): vscode.TreeItem {
    return toTreeItem(node);
  }

  getChildren(node?: DisplayNode): DisplayNode[] {
    return node === undefined ? this.roots : [...node.children];
  }

  async refresh(): Promise<void> {
    const resolution = this.discovery.resolve();
    if (!resolution.ok) {
      const message = `No sq invocation found. Tried, in order: ${describeTriedOrder(resolution.triedOrder)}.`;
      this.fail(message);
      return;
    }
    const { invocation } = resolution;
    const outcome = await getList(this.runner, invocation, this.workspaceRoot, ['--all']);
    if (outcome.kind !== 'success') {
      this.failFrom(outcome);
      return;
    }
    this.roots = buildMetaView(outcome.data);
    this.changeEmitter.fire(undefined);
  }

  private failFrom(outcome: Exclude<SqOutcome<unknown>, { kind: 'success' }>): void {
    if (outcome.kind === 'spawn-error') {
      this.discovery.invalidate();
    }
    this.fail(describeFailure(outcome));
  }

  private fail(message: string): void {
    this.roots = [errorDisplayNode(message)];
    this.notifyError(`Squads: ${message}`);
    this.changeEmitter.fire(undefined);
  }
}
