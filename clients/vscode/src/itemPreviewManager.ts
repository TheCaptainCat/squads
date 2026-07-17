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
 *
 * Alongside the per-item panel pool, this also owns a single, separate panel for the workflow
 * cheatsheet (`sq workflow --raw`) — not an item, so it's tracked independently of
 * `activePanel`/`openFromTree`: opening the cheatsheet never steals the item-preview panel's
 * slot, and vice versa. It renders the same clean-markdown body through `renderWorkflowHtml`,
 * which opts into live ```mermaid``` rendering the plain item dossier doesn't.
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
  renderWorkflowHtml,
} from './domain/previewDocument';
import {
  parseOpenItemMessage,
  routeForMessage,
  routeForTreeSelection,
} from './domain/previewMessages';
import type { ProcessRunner } from './processRunner';
import {
  describeFailure,
  getGraph,
  getRaw,
  getTree,
  getWorkflowRaw,
  type SqOutcome,
} from './sqAdapter';
import type { SqGraphNode, SqTreeNode } from './types';

const VIEW_TYPE = 'squadsItemPreview';
const WORKFLOW_VIEW_TYPE = 'squadsWorkflowPreview';
const WORKFLOW_TITLE = 'Squads Workflow Cheatsheet';

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
  private activeWorkflowPanel: vscode.WebviewPanel | undefined;

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

  /** Entry point for the `squads.openWorkflow` view-title command. Reveals the single owned
   * workflow panel if one is already open (re-fetching so it's current), otherwise opens one —
   * mirroring `openFromTree`'s reuse-or-create shape but against its own panel slot. */
  async openWorkflow(): Promise<void> {
    if (this.activeWorkflowPanel !== undefined) {
      const panel = this.activeWorkflowPanel;
      await this.renderWorkflow(panel);
      panel.reveal();
      return;
    }
    const panel = vscode.window.createWebviewPanel(
      WORKFLOW_VIEW_TYPE,
      WORKFLOW_TITLE,
      vscode.ViewColumn.Active,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(this.extensionUri, 'media')],
      },
    );
    panel.onDidDispose(() => {
      if (this.activeWorkflowPanel === panel) {
        this.activeWorkflowPanel = undefined;
      }
    });
    this.activeWorkflowPanel = panel;
    await this.renderWorkflow(panel);
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

  /** Fetches and renders the workflow cheatsheet into the owned workflow panel. No tree/graph
   * fetch (there's no children/refs graph for a document that isn't an item) — `graphsHtml` is
   * always empty, and the cheatsheet's own diagrams render inline through `renderWorkflowHtml`. */
  private async renderWorkflow(panel: vscode.WebviewPanel): Promise<void> {
    const resolution = this.discovery.resolve();
    let bodyHtml: string;
    if (!resolution.ok) {
      const message = `No sq invocation found. Tried, in order: ${describeTriedOrder(resolution.triedOrder)}.`;
      this.notifyError(`Squads: ${message}`);
      bodyHtml = renderWorkflowHtml({ kind: 'spawn-error', message });
    } else {
      const { invocation } = resolution;
      const outcome = await getWorkflowRaw(this.runner, invocation, this.workspaceRoot);
      if (outcome.kind !== 'success') {
        if (outcome.kind === 'spawn-error') {
          this.discovery.invalidate();
        }
        this.notifyError(`Squads: ${describeFailure(outcome)}`);
      }
      bodyHtml = renderWorkflowHtml(outcome);
    }
    const nonce = randomUUID();
    const mermaidScriptUri = panel.webview
      .asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'mermaid.min.js'))
      .toString();
    panel.webview.html = buildPreviewHtml({
      title: WORKFLOW_TITLE,
      bodyHtml,
      graphsHtml: '',
      nonce,
      mermaidScriptUri,
    });
  }
}
