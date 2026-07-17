/**
 * Owns the item-preview `WebviewPanel` lifecycle: a dedicated tab the
 * extension controls end to end — never hijacked by opening another markdown file (unlike
 * the `markdown.showPreview` path this replaces) — rendering `sq show <id> --raw` as HTML via
 * the vscode-free `domain/markdown` + `domain/previewDocument` helpers, alongside the two
 * collapsible mermaid graphs (`domain/graphDiagrams`) built from `sq tree`/`sq graph --json`.
 *
 * Navigation: a tree-node selection reuses the single owned panel if one is open (mirroring
 * the old dynamic preview's UX), otherwise opens a fresh one. A link click inside a panel
 * posts a message back (`domain/previewMessages`); a plain click/ctrl-click navigates the
 * *originating* panel in place, a middle-click opens a brand new panel — routed through the
 * same `routeForMessage`/`routeForTreeSelection` pure logic that's unit-tested in isolation.
 * This module's own vscode wiring (panel creation, message subscription) is exercised by the
 * extension-host smoke test, not a unit test — mirrors `treeDataProvider.ts`'s split.
 */
import { randomUUID } from 'node:crypto';

import * as vscode from 'vscode';

import { describeTriedOrder, type SqDiscovery } from './discovery';
import { buildRefGraphMermaid, buildSubtreeMermaid } from './domain/graphDiagrams';
import {
  buildGraphsHtml,
  buildPreviewHtml,
  type GraphOutcome,
  renderOutcomeHtml,
} from './domain/previewDocument';
import {
  parseOpenItemMessage,
  routeForMessage,
  routeForTreeSelection,
} from './domain/previewMessages';
import type { ProcessRunner } from './processRunner';
import { describeFailure, getGraph, getRaw, getTree, type SqOutcome } from './sqAdapter';
import type { SqGraphNode, SqTreeNode } from './types';

const VIEW_TYPE = 'squadsItemPreview';

/** Turns a fetch outcome into the graph section's content: the built mermaid source on
 * success, or the same human-readable failure message every other surface shows, on failure
 * (never a silent/blank section). */
function toGraphOutcome<T>(outcome: SqOutcome<T>, build: (data: T) => string): GraphOutcome {
  if (outcome.kind !== 'success') {
    return { mermaidSource: null, message: describeFailure(outcome) };
  }
  return { mermaidSource: build(outcome.data) };
}

export class ItemPreviewManager {
  private activePanel: vscode.WebviewPanel | undefined;

  constructor(
    private readonly runner: ProcessRunner,
    private readonly discovery: SqDiscovery,
    private readonly workspaceRoot: string,
    private readonly notifyError: (message: string) => void,
    private readonly extensionUri: vscode.Uri,
  ) {}

  /** Entry point for tree-node selection / the `squads.openItemPreview` command. */
  async openFromTree(id: string): Promise<void> {
    const route = routeForTreeSelection(this.activePanel !== undefined);
    if (route === 'same-panel' && this.activePanel !== undefined) {
      const panel = this.activePanel;
      await this.render(panel, id);
      panel.reveal();
      return;
    }
    await this.openNewPanel(id);
  }

  private async openNewPanel(id: string): Promise<vscode.WebviewPanel> {
    const panel = vscode.window.createWebviewPanel(VIEW_TYPE, id, vscode.ViewColumn.Active, {
      enableScripts: true,
      retainContextWhenHidden: true,
      // The bundled mermaid renderer (media/mermaid.min.js) is the only local asset this
      // webview loads — scoped to that one directory, not the whole extension.
      localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, 'media')],
    });
    panel.onDidDispose(() => {
      if (this.activePanel === panel) {
        this.activePanel = undefined;
      }
    });
    panel.webview.onDidReceiveMessage((raw: unknown) => {
      void this.handleMessage(panel, raw);
    });
    this.activePanel = panel;
    await this.render(panel, id);
    return panel;
  }

  private async handleMessage(panel: vscode.WebviewPanel, raw: unknown): Promise<void> {
    const message = parseOpenItemMessage(raw);
    if (message === null) {
      return;
    }
    if (routeForMessage(message) === 'new-panel') {
      await this.openNewPanel(message.id);
      return;
    }
    this.activePanel = panel;
    await this.render(panel, message.id);
    panel.reveal();
  }

  private async render(panel: vscode.WebviewPanel, id: string): Promise<void> {
    const resolution = this.discovery.resolve();
    let bodyHtml: string;
    let graphsHtml: string;
    if (!resolution.ok) {
      const message = `No sq invocation found. Tried, in order: ${describeTriedOrder(resolution.triedOrder)}.`;
      this.notifyError(`Squads: ${message}`);
      bodyHtml = renderOutcomeHtml(id, { kind: 'spawn-error', message });
      const unavailable: GraphOutcome = { mermaidSource: null, message };
      graphsHtml = buildGraphsHtml(unavailable, unavailable);
    } else {
      const { invocation } = resolution;
      const [dossier, tree, graph] = await Promise.all([
        getRaw(this.runner, invocation, this.workspaceRoot, id),
        getTree(this.runner, invocation, this.workspaceRoot, id),
        getGraph(this.runner, invocation, this.workspaceRoot, id),
      ]);
      if (dossier.kind !== 'success') {
        if (dossier.kind === 'spawn-error') {
          this.discovery.invalidate();
        }
        this.notifyError(`Squads: ${describeFailure(dossier)}`);
      }
      bodyHtml = renderOutcomeHtml(id, dossier);
      // Tree/graph fetch failures degrade their own section to an inline message rather than
      // a second notification — the dossier failure above is the one that's actionable.
      graphsHtml = buildGraphsHtml(
        toGraphOutcome<readonly SqTreeNode[]>(tree, buildSubtreeMermaid),
        toGraphOutcome<SqGraphNode>(graph, buildRefGraphMermaid),
      );
    }
    const nonce = randomUUID();
    const mermaidScriptUri = panel.webview
      .asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'mermaid.min.js'))
      .toString();
    panel.title = id;
    panel.webview.html = buildPreviewHtml({
      title: id,
      bodyHtml,
      graphsHtml,
      nonce,
      mermaidScriptUri,
    });
  }
}
