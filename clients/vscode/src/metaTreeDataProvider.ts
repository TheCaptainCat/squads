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
import {
  buildBadgeVocabulary,
  buildFieldBindings,
  NO_BADGE_VOCABULARY,
  NO_FIELD_BINDINGS,
} from './domain/badgeCatalog';
import { type DisplayNode, errorDisplayNode } from './domain/displayNode';
import { buildMetaView } from './domain/metaView';
import { buildStatusRoleMap, NO_STATUS_ROLES } from './domain/statusRole';
import type { ProcessRunner } from './processRunner';
import {
  describeFailure,
  getCollectionsCatalog,
  getList,
  getStatusesCatalog,
  getTypeCatalog,
  type SqOutcome,
} from './sqAdapter';
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
    // Same catalogs the work tree fetches (F19/F26), so the roster's tooltip renders real
    // collection badges and an Active role/skill/operator gets the same green highlight; a
    // failed fetch degrades to raw-code badge text / no highlight rather than breaking the view
    // (`buildFieldBindings`/`buildBadgeVocabulary`/`buildStatusRoleMap` on an empty array is the
    // same as each graceful-fallback default).
    const [outcome, catalogOutcome, collectionsOutcome, statusesOutcome] = await Promise.all([
      getList(this.runner, invocation, this.workspaceRoot, ['--all']),
      getTypeCatalog(this.runner, invocation, this.workspaceRoot),
      getCollectionsCatalog(this.runner, invocation, this.workspaceRoot),
      getStatusesCatalog(this.runner, invocation, this.workspaceRoot),
    ]);
    if (outcome.kind !== 'success') {
      this.failFrom(outcome);
      return;
    }
    const fieldBindings =
      catalogOutcome.kind === 'success'
        ? buildFieldBindings(catalogOutcome.data)
        : NO_FIELD_BINDINGS;
    const badgeVocabulary =
      collectionsOutcome.kind === 'success'
        ? buildBadgeVocabulary(collectionsOutcome.data)
        : NO_BADGE_VOCABULARY;
    const statusRoles =
      statusesOutcome.kind === 'success'
        ? buildStatusRoleMap(statusesOutcome.data)
        : NO_STATUS_ROLES;
    this.roots = buildMetaView(outcome.data, fieldBindings, badgeVocabulary, statusRoles);
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
