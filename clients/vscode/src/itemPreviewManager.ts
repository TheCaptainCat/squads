/**
 * Owns the item-preview `WebviewPanel` lifecycle: a dedicated tab the
 * extension controls end to end — never hijacked by opening another markdown file (unlike
 * the `markdown.showPreview` path this replaces) — rendering `sq show <id> --raw` as HTML via
 * the vscode-free `domain/markdown` + `domain/previewDocument` helpers, alongside the two
 * collapsible mermaid graphs (`domain/graphDiagrams`) built from `sq tree`/`sq graph --json`,
 * and the collapsible sub-entities + discussion sections built from `sq show <id> --json`'s
 * `subentities`/`discussion` arrays (`getShowJson`) — all fetched in parallel with the `--raw`
 * dossier text.
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
 *
 * Back/forward history: each item-preview panel keeps its own `PreviewHistory`
 * (`domain/previewHistory` — pure, unit-tested) alongside its `openPanels` current-item entry.
 * A real navigation (tree selection, link/`@mention` click) pushes onto the *originating*
 * panel's history through `navigate`; `goBack`/`goForward` only move the index and re-render
 * through the same `'reload'` path — no push. The watcher's `refreshOpenPreviews` (`'patch'`
 * mode) never touches history.
 *
 * Back/forward controls, primary path: a small toolbar rendered *inside* the preview HTML itself
 * (`domain/previewDocument.ts`'s `buildHistoryToolbarHtml`), at the top of `<article>`. This is
 * the primary control because VS Code's `editor/title/navigation` menu contribution — the usual
 * way an extension adds inline title-bar buttons — does not reliably render for a plain
 * `createWebviewPanel` panel; confirmed by screenshot in a real Extension Development Host (with
 * `enablement` already dropped from the commands, ruling that out too), not just inferred from
 * docs. A toolbar button posts a `NavigateHistoryMessage` (`domain/previewMessages.ts`) back to
 * *this specific panel*'s message handler — no ambiguity about which panel's history to step,
 * unlike a global command. The button carries a real `disabled` attribute at the corresponding
 * end of history, computed fresh on every render (`'reload'` and `'patch'` alike) from that
 * panel's current `PreviewHistory`, so it's never stale and the browser itself dims/inert-s it.
 *
 * Secondary path: `alt+left`/`alt+right` keybindings still invoke the workspace-global
 * `squads.previewBack`/`squads.previewForward` commands (also reachable from the Command
 * Palette). Since a command invocation carries no panel reference, `focusedPanel` tracks
 * whichever preview panel VS Code currently reports as the active editor tab
 * (`onDidChangeViewState`, not just at navigation time) and `goBack`/`goForward` act on *that*
 * panel's history, never `activePanel` (the tree-selection reuse target, which can be a
 * different, unfocused panel). Both paths converge on `stepHistoryFor`, which no-ops at the
 * corresponding end of history exactly like the in-content button's `disabled` state implies.
 */
import { randomUUID } from 'node:crypto';

import * as vscode from 'vscode';

import { describeTriedOrder, type SqDiscovery } from './discovery';
import { buildRefGraphMermaid, buildSubtreeMermaid } from './domain/graphDiagrams';
import {
  buildArticleHtml,
  buildDiscussionHtml,
  buildGraphsHtml,
  buildHistoryToolbarHtml,
  buildPreviewHtml,
  buildSubEntitiesHtml,
  type DiscussionOutcome,
  type GraphOutcome,
  renderOutcomeHtml,
  renderWorkflowHtml,
  type SubEntitiesOutcome,
} from './domain/previewDocument';
import {
  canStepBack,
  canStepForward,
  createHistory,
  currentId,
  type PreviewHistory,
  pushHistory,
  stepBack,
  stepForward,
} from './domain/previewHistory';
import {
  parseNavigateHistoryMessage,
  parseOpenItemMessage,
  routeForMessage,
  routeForTreeSelection,
  UPDATE_CONTENT_COMMAND,
  type UpdateContentMessage,
} from './domain/previewMessages';
import { buildRoleDirectory, NO_ROLE_DIRECTORY, type RoleDirectory } from './domain/roleDirectory';
import type { ProcessRunner } from './processRunner';
import {
  describeFailure,
  getGraph,
  getList,
  getRaw,
  getShowJson,
  getTree,
  getWorkflowRaw,
  type SqOutcome,
} from './sqAdapter';
import type { SqGraphNode, SqListItem, SqShowJson, SqTreeNode } from './types';

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

/** Turns a `getShowJson` outcome into the discussion section's content — the parsed comment
 * list on success, or the same human-readable failure message every other surface shows, on
 * failure. Mirrors `toGraphOutcome`'s shape. */
function toDiscussionOutcome(outcome: SqOutcome<SqShowJson>): DiscussionOutcome {
  if (outcome.kind !== 'success') {
    return { entries: null, message: describeFailure(outcome) };
  }
  return { entries: outcome.data.discussion };
}

/** Turns a `getShowJson` outcome into the sub-entities section's content — the parsed
 * sub-entity list on success, or the same human-readable failure message every other surface
 * shows, on failure. Mirrors `toDiscussionOutcome`'s shape (same underlying fetch). */
function toSubEntitiesOutcome(outcome: SqOutcome<SqShowJson>): SubEntitiesOutcome {
  if (outcome.kind !== 'success') {
    return { entities: null, message: describeFailure(outcome) };
  }
  return { entities: outcome.data.subentities };
}

/** Degrades a failed/unreachable `sq list -t role --json` fetch to `NO_ROLE_DIRECTORY` — same
 * graceful-degrade shape `treeDataProvider.ts`'s catalog joins use — so a `@<slug>` mention
 * simply renders as plain text rather than breaking the preview render. */
function roleDirectoryFrom(outcome: SqOutcome<readonly SqListItem[]>): RoleDirectory {
  return outcome.kind === 'success' ? buildRoleDirectory(outcome.data) : NO_ROLE_DIRECTORY;
}

/** The squads icon shown on a webview panel's editor tab (F16). Unlike the activity-bar
 * container icon (`package.json`'s single `currentColor` SVG, themed via VS Code's own
 * icon-masking), a webview tab icon is drawn as a plain image with no such re-tinting — so it
 * needs its own light/dark pair with an explicit stroke color to read against either tab-bar
 * background (`resources/squads-icon-vscode-{light,dark}.svg`, derived from the activity-bar
 * source). */
function panelIconPath(extensionUri: vscode.Uri): {
  readonly light: vscode.Uri;
  readonly dark: vscode.Uri;
} {
  return {
    light: vscode.Uri.joinPath(extensionUri, 'resources', 'squads-icon-vscode-light.svg'),
    dark: vscode.Uri.joinPath(extensionUri, 'resources', 'squads-icon-vscode-dark.svg'),
  };
}

export class ItemPreviewManager {
  private activePanel: vscode.WebviewPanel | undefined;
  private activeWorkflowPanel: vscode.WebviewPanel | undefined;
  // Every currently-open item-preview panel (there may be more than one — middle-click opens a
  // new tab alongside the reused `activePanel`), mapped to the item id it currently shows. Lets
  // the `.squads.json` watcher (F17) refresh every open preview, not just the reused one.
  private readonly openPanels = new Map<vscode.WebviewPanel, string>();
  // Per-panel back/forward navigation history, independent of `openPanels`'s "current id"
  // bookkeeping — a `'patch'` refresh updates `openPanels` but must never touch this.
  private readonly histories = new Map<vscode.WebviewPanel, PreviewHistory>();
  // The item-preview panel VS Code currently reports as the *active* editor tab — distinct from
  // `activePanel` (the panel tree-selection reuses), since more than one preview panel can be
  // open at once and only one of them is visually focused. Drives which panel's history the
  // back/forward commands apply to (see the module doc comment).
  private focusedPanel: vscode.WebviewPanel | undefined;

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
      await this.navigate(panel, id);
      panel.reveal();
      return;
    }
    await this.openNewPanel(id);
  }

  /** The `squads.previewBack`/`squads.previewForward` commands (`alt+left`/`alt+right` — the
   * secondary path, see the module doc comment) act on whichever preview panel is currently the
   * focused editor tab (`focusedPanel`, kept in sync by `onDidChangeViewState`) — not
   * `activePanel`, which tracks the tree-reuse target instead. A no-op with no focused panel. */
  async goBack(): Promise<void> {
    if (this.focusedPanel !== undefined) {
      await this.stepHistoryFor(this.focusedPanel, stepBack);
    }
  }

  async goForward(): Promise<void> {
    if (this.focusedPanel !== undefined) {
      await this.stepHistoryFor(this.focusedPanel, stepForward);
    }
  }

  /** Moves `panel`'s history one step per `step` (`stepBack`/`stepForward`) and re-renders
   * through the existing `'reload'` path — a no-op (no re-render) at the corresponding end of
   * history, whether that's reached via the in-content toolbar's `NavigateHistoryMessage`
   * (`handleMessage`, which already knows the exact panel) or the `alt+left`/`alt+right`
   * keybindings (`goBack`/`goForward`, via `focusedPanel`). */
  private async stepHistoryFor(
    panel: vscode.WebviewPanel,
    step: (history: PreviewHistory) => PreviewHistory,
  ): Promise<void> {
    const history = this.histories.get(panel);
    if (history === undefined) {
      return;
    }
    const next = step(history);
    if (next === history) {
      return;
    }
    this.histories.set(panel, next);
    const id = currentId(next);
    this.openPanels.set(panel, id);
    await this.render(panel, id);
  }

  /** A real navigation (tree selection, or a link/`@mention` click routed to the same panel) —
   * pushes `id` onto `panel`'s history (truncating any forward entries) and re-renders through
   * the existing `'reload'` path. Never called for `goBack`/`goForward` (a position change, not
   * a new entry) or `refreshOpenPreviews` (a same-item `'patch'` refresh). */
  private async navigate(panel: vscode.WebviewPanel, id: string): Promise<void> {
    const history = this.histories.get(panel) ?? createHistory(id);
    this.histories.set(panel, pushHistory(history, id));
    await this.render(panel, id);
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
    panel.iconPath = panelIconPath(this.extensionUri);
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
    panel.iconPath = panelIconPath(this.extensionUri);
    panel.onDidDispose(() => {
      if (this.activePanel === panel) {
        this.activePanel = undefined;
      }
      this.openPanels.delete(panel);
      this.histories.delete(panel);
      if (this.focusedPanel === panel) {
        this.focusedPanel = undefined;
      }
    });
    // Kept in sync on every focus change, not only on navigation (see the module doc comment) —
    // each open panel's history is independent, so `goBack`/`goForward` must always act on
    // whichever panel is actually focused, even when that change wasn't a navigation at all.
    panel.onDidChangeViewState((event) => {
      if (event.webviewPanel.active) {
        this.focusedPanel = panel;
      }
    });
    panel.webview.onDidReceiveMessage((raw: unknown) => {
      void this.handleMessage(panel, raw);
    });
    this.activePanel = panel;
    this.focusedPanel = panel;
    this.histories.set(panel, createHistory(id));
    await this.render(panel, id);
    return panel;
  }

  /** Re-renders every currently-open item-preview panel against its current item id. Called by
   * the `.squads.json` watcher (F17) on an on-disk change — always re-fetches through `sq …
   * --json`, never reads stale state. Rendered in `'patch'` mode: this is a same-item refresh,
   * not a navigation, so the reader's scroll position must be preserved rather than reset — see
   * `render`'s doc comment. */
  async refreshOpenPreviews(): Promise<void> {
    await Promise.all(
      [...this.openPanels.entries()].map(([panel, id]) => this.render(panel, id, 'patch')),
    );
  }

  private async handleMessage(panel: vscode.WebviewPanel, raw: unknown): Promise<void> {
    const navMessage = parseNavigateHistoryMessage(raw);
    if (navMessage !== null) {
      await this.stepHistoryFor(panel, navMessage.direction === 'back' ? stepBack : stepForward);
      return;
    }
    const message = parseOpenItemMessage(raw);
    if (message === null) {
      return;
    }
    if (routeForMessage(message) === 'new-panel') {
      await this.openNewPanel(message.id);
      return;
    }
    this.activePanel = panel;
    await this.navigate(panel, message.id);
    panel.reveal();
  }

  /** Fetches + renders one item into `panel`, in one of two modes:
   *
   * - `'reload'` (the default — every navigation: opening a new panel, reusing the panel for a
   *   *different* item from the tree or a link click) reassigns `panel.webview.html` wholesale,
   *   a fresh page load that starts at the top — the right behavior for a reader landing on a
   *   new item, and exactly what every call did before this distinction existed.
   * - `'patch'` (`refreshOpenPreviews` only — the `.squads.json`-watcher refresh of an item
   *   already on screen) instead `postMessage`s the freshly-rendered sections
   *   (`UpdateContentMessage`) for the webview's own script to swap into place via `innerHTML`.
   *   The page itself never reloads, so the reader's scroll position is simply never disturbed —
   *   no explicit capture/restore needed, since there's no navigation to restore it *from*.
   */
  private async render(
    panel: vscode.WebviewPanel,
    id: string,
    mode: 'reload' | 'patch' = 'reload',
  ): Promise<void> {
    this.openPanels.set(panel, id);
    const resolution = this.discovery.resolve();
    let titleText: string;
    let headerHtml: string;
    let bodyHtml: string;
    let graphsHtml: string;
    let subEntitiesHtml: string;
    let discussionHtml: string;
    if (!resolution.ok) {
      const message = `No sq invocation found. Tried, in order: ${describeTriedOrder(resolution.triedOrder)}.`;
      this.notifyError(`Squads: ${message}`);
      ({ titleText, headerHtml, bodyHtml } = renderOutcomeHtml(id, {
        kind: 'spawn-error',
        message,
      }));
      const unavailable: GraphOutcome = { mermaidSource: null, message };
      graphsHtml = buildGraphsHtml(unavailable, unavailable);
      subEntitiesHtml = buildSubEntitiesHtml({ entities: null, message }, id);
      discussionHtml = buildDiscussionHtml({ entries: null, message }, id);
    } else {
      const { invocation } = resolution;
      const [dossier, tree, graph, showJson, roleList] = await Promise.all([
        getRaw(this.runner, invocation, this.workspaceRoot, id),
        getTree(this.runner, invocation, this.workspaceRoot, id),
        getGraph(this.runner, invocation, this.workspaceRoot, id),
        getShowJson(this.runner, invocation, this.workspaceRoot, id),
        getList(this.runner, invocation, this.workspaceRoot, ['-t', 'role']),
      ]);
      if (dossier.kind !== 'success') {
        if (dossier.kind === 'spawn-error') {
          this.discovery.invalidate();
        }
        this.notifyError(`Squads: ${describeFailure(dossier)}`);
      }
      // A failed role-list fetch degrades to NO_ROLE_DIRECTORY (`@slug` mentions render as
      // plain text) rather than a second notification — same treatment as the tree/graph/
      // sub-entities/discussion fetches below, none of which are the actionable failure.
      const roles = roleDirectoryFrom(roleList);
      ({ titleText, headerHtml, bodyHtml } = renderOutcomeHtml(id, dossier, roles));
      graphsHtml = buildGraphsHtml(
        toGraphOutcome<readonly SqTreeNode[]>(tree, buildSubtreeMermaid),
        toGraphOutcome<SqGraphNode>(graph, buildRefGraphMermaid),
      );
      subEntitiesHtml = buildSubEntitiesHtml(toSubEntitiesOutcome(showJson), id, roles);
      discussionHtml = buildDiscussionHtml(toDiscussionOutcome(showJson), id, roles);
    }
    panel.title = id;
    // Recomputed from this panel's *current* history on every render, patch included — so a
    // watcher refresh never shows a stale enabled/disabled state relative to history that may
    // have moved (via a concurrent back/forward) since the last render.
    const history = this.histories.get(panel);
    const toolbarHtml = buildHistoryToolbarHtml(
      titleText,
      history !== undefined && canStepBack(history),
      history !== undefined && canStepForward(history),
    );
    if (mode === 'patch') {
      await panel.webview.postMessage({
        command: UPDATE_CONTENT_COMMAND,
        title: id,
        articleHtml: buildArticleHtml(toolbarHtml, headerHtml, graphsHtml, bodyHtml),
        subEntitiesHtml,
        discussionHtml,
      } satisfies UpdateContentMessage);
      return;
    }
    const nonce = randomUUID();
    const mermaidScriptUri = panel.webview
      .asWebviewUri(vscode.Uri.joinPath(this.extensionUri, 'media', 'mermaid.min.js'))
      .toString();
    panel.webview.html = buildPreviewHtml({
      title: id,
      toolbarHtml,
      headerHtml,
      bodyHtml,
      graphsHtml,
      subEntitiesHtml,
      discussionHtml,
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
      toolbarHtml: '',
      headerHtml: '',
      bodyHtml,
      graphsHtml: '',
      subEntitiesHtml: '',
      discussionHtml: '',
      nonce,
      mermaidScriptUri,
    });
  }
}
