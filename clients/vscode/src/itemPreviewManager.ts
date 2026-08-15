/**
 * Owns the item-preview `WebviewPanel` lifecycle: a dedicated tab the extension controls end to
 * end (never hijacked by opening another markdown file), rendering `sq show <id> --raw` as HTML
 * via `domain/markdown` + `domain/previewDocument`, alongside the two collapsible mermaid graphs
 * (`domain/graphDiagrams`, from `sq tree`/`sq graph --json`) and the collapsible sub-entities +
 * discussion sections (from `sq show <id> --json`'s `subentities`/`discussion` arrays) — all
 * fetched in parallel with the `--raw` dossier text.
 *
 * Two spec catalogs are fetched alongside them, for the same reason every other view fetches
 * them: so the rendering reads the project's declared vocabulary instead of assuming a bundled
 * one. `sq workflow types --json` gives the declared id prefixes that decide what text is a
 * navigable item reference (`domain/itemIdPattern.ts`), and joins to
 * `sq workflow subentity-kinds --json` for the labels a sub-entity's badge fields carry. Each
 * degrades on its own (see `itemIdMatcherFrom`/`subEntityFieldsFrom`); neither can fail the
 * render.
 *
 * Two `sq list --json` fetches sit alongside them, and they are two on purpose: the roster one
 * (`-t role`) keeps the default view because an archived role is not a mention target, while the
 * id->hover-text one passes `--all` because prose overwhelmingly cites settled work. Both are
 * batched — a render's cost never scales with how many ids a body happens to mention.
 *
 * Navigation and back/forward history are covered by the methods below (`openFromTree`,
 * `navigate`, `goBack`/`goForward`, `stepHistoryFor`) and by `domain/previewMessages.ts`'s
 * routing logic. The in-content toolbar (`domain/previewDocument.ts`'s
 * `buildHistoryToolbarHtml`) is the primary back/forward control rather than a
 * `editor/title/navigation` menu contribution because that VS Code mechanism doesn't reliably
 * render inline buttons for a plain `createWebviewPanel` panel — confirmed by screenshot in a
 * real Extension Development Host, with `enablement` also tried and dropped from the commands
 * before landing on this approach.
 *
 * Alongside the per-item panel pool, this also owns a single, separate panel for the workflow
 * cheatsheet (`sq workflow --raw`, `openWorkflow`) — tracked independently of
 * `activePanel`/`openPanels`, so opening one never steals the other's slot.
 */
import { randomUUID } from 'node:crypto';

import * as vscode from 'vscode';

import { REFRESH_ALL_COMMAND } from './commandIds';
import { describeTriedOrder, type SqDiscovery } from './discovery';
import { buildSubEntityFieldBindings, NO_FIELD_BINDINGS } from './domain/badgeCatalog';
import { ExpansionTracker } from './domain/expansionTracker';
import { buildRefGraphMermaid, buildSubtreeMermaid } from './domain/graphDiagrams';
import { buildItemDirectory, type ItemDirectory, NO_ITEM_DIRECTORY } from './domain/itemDirectory';
import {
  buildItemIdMatcher,
  DEFAULT_ITEM_ID_MATCHER,
  type ItemIdMatcher,
} from './domain/itemIdPattern';
import {
  buildArticleHtml,
  buildDiscussionHtml,
  buildGraphsHtml,
  buildHistoryToolbarHtml,
  buildPreviewHtml,
  buildSubEntitiesHtml,
  CHILDREN_GRAPH_FOLD_ID,
  type DiscussionOutcome,
  type GraphOutcome,
  REFS_GRAPH_FOLD_ID,
  renderOutcomeHtml,
  renderWorkflowHtml,
  type SubEntitiesOutcome,
  type SubEntityFieldContext,
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
  parseRefreshMessage,
  parseToggleFoldMessage,
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
  getSubentityKindsCatalog,
  getTree,
  getTypeCatalog,
  getWorkflowRaw,
  type SqOutcome,
} from './sqAdapter';
import type {
  SqGraphNode,
  SqListItem,
  SqShowJson,
  SqSubEntityKindCatalogEntry,
  SqTreeNode,
  SqTypeCatalogEntry,
} from './types';

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
 * list on success. Mirrors `toGraphOutcome`'s failure-handling shape. */
function toDiscussionOutcome(outcome: SqOutcome<SqShowJson>): DiscussionOutcome {
  if (outcome.kind !== 'success') {
    return { entries: null, message: describeFailure(outcome) };
  }
  return { entries: outcome.data.discussion };
}

/** Turns a `getShowJson` outcome into the sub-entities section's content — the parsed
 * sub-entity list on success. Mirrors `toDiscussionOutcome`'s shape (same underlying fetch). */
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

/** Hover text for every id the prose may link, from one batched `sq list --json --all`. Same
 * degrade as `roleDirectoryFrom`: a failed fetch leaves anchors without a `title`, which costs
 * the tooltip and nothing else — the link still navigates. */
function itemDirectoryFrom(outcome: SqOutcome<readonly SqListItem[]>): ItemDirectory {
  return outcome.kind === 'success' ? buildItemDirectory(outcome.data) : NO_ITEM_DIRECTORY;
}

/** The id grammar the preview linkifies against, from the squad's own declared type prefixes.
 * A failed/unreachable type-catalog fetch degrades to the generic default matcher — the same
 * graceful-degrade shape `roleDirectoryFrom` uses — rather than dropping every link. */
function itemIdMatcherFrom(outcome: SqOutcome<readonly SqTypeCatalogEntry[]>): ItemIdMatcher {
  return outcome.kind === 'success' ? buildItemIdMatcher(outcome.data) : DEFAULT_ITEM_ID_MATCHER;
}

/** The sub-entity badge-field labels for the item on screen, joined from the two catalogs that
 * carry them (item type -> `subentity_kind` -> that kind's declared `fields`). Either fetch
 * failing — including against an `sq` too old to publish the kind catalog at all — leaves the
 * bindings empty, which labels each badge by its raw field code instead of hiding it. */
function subEntityFieldsFrom(
  showJson: SqOutcome<SqShowJson>,
  types: SqOutcome<readonly SqTypeCatalogEntry[]>,
  kinds: SqOutcome<readonly SqSubEntityKindCatalogEntry[]>,
): SubEntityFieldContext {
  return {
    itemType: showJson.kind === 'success' ? showJson.data.type : undefined,
    fieldBindings:
      types.kind === 'success' && kinds.kind === 'success'
        ? buildSubEntityFieldBindings(types.data, kinds.data)
        : NO_FIELD_BINDINGS,
  };
}

/** The squads icon shown on a webview panel's editor tab. Unlike the activity-bar
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
  // the `.squads.json` watcher refresh every open preview, not just the reused one.
  private readonly openPanels = new Map<vscode.WebviewPanel, string>();
  // Per-panel back/forward navigation history, independent of `openPanels`'s "current id"
  // bookkeeping — a `'patch'` refresh updates `openPanels` but must never touch this.
  private readonly histories = new Map<vscode.WebviewPanel, PreviewHistory>();
  // Per-panel record of which sub-entity body/graph folds the reader has open, keyed by the
  // same `ExpansionTracker` the activity-bar trees use for expand/collapse — fed
  // by `ToggleFoldMessage`s the webview posts on a native `toggle` event, and consulted on every
  // render to stamp the right `open` attribute back onto the matching `<details>`. Reset to
  // empty on every navigation to a *different* item (never on a same-item `'patch'` refresh):
  // a sub-entity's `local_id` is scoped to its parent item, not globally unique, so carrying a
  // previous item's tracked ids into a new one would be at best meaningless and at worst wrong.
  private readonly foldState = new Map<vscode.WebviewPanel, ExpansionTracker>();
  // The item-preview panel VS Code currently reports as the *active* editor tab — distinct from
  // `activePanel` (the panel tree-selection reuses), since more than one preview panel can be
  // open at once and only one of them is visually focused. Drives which panel's history
  // `goBack`/`goForward` apply to.
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

  /** The `squads.previewBack`/`squads.previewForward` commands (`alt+left`/`alt+right` — a
   * secondary path to the in-content toolbar buttons) act on whichever preview panel is
   * currently the focused editor tab (`focusedPanel`, kept in sync by `onDidChangeViewState`) —
   * not `activePanel`, which tracks the tree-reuse target instead. A no-op with no focused
   * panel. */
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
      this.foldState.delete(panel);
      if (this.focusedPanel === panel) {
        this.focusedPanel = undefined;
      }
    });
    // Kept in sync on every focus change, not only on navigation — each open panel's history is
    // independent, so `goBack`/`goForward` must always act on whichever panel is actually
    // focused, even when that change wasn't a navigation at all.
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
   * the `.squads.json` watcher on an on-disk change — always re-fetches through `sq …
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
    // The in-content toolbar's refresh button — fires the exact same global
    // refresh a tree view-title button or the `.squads.json` watcher does, rather than a
    // preview-only refresh, so "refresh" means one thing everywhere it's triggered from.
    if (parseRefreshMessage(raw) !== null) {
      await vscode.commands.executeCommand(REFRESH_ALL_COMMAND);
      return;
    }
    // A tracked fold's open/closed state changed in the webview — recorded against
    // this panel's tracker for the next render to restore, never triggers one itself.
    const foldMessage = parseToggleFoldMessage(raw);
    if (foldMessage !== null) {
      let tracker = this.foldState.get(panel);
      if (tracker === undefined) {
        tracker = new ExpansionTracker();
        this.foldState.set(panel, tracker);
      }
      tracker.setExpanded(foldMessage.id, foldMessage.open);
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
   *   different item from the tree or a link click) reassigns `panel.webview.html` wholesale, a
   *   fresh page load that starts at the top.
   * - `'patch'` (`refreshOpenPreviews` only — the `.squads.json`-watcher refresh of an item
   *   already on screen) instead `postMessage`s the freshly-rendered sections
   *   (`UpdateContentMessage`) for the webview's own script to swap into place via `innerHTML`.
   *   The page never reloads, so the reader's scroll position is never disturbed.
   */
  private async render(
    panel: vscode.WebviewPanel,
    id: string,
    mode: 'reload' | 'patch' = 'reload',
  ): Promise<void> {
    this.openPanels.set(panel, id);
    if (mode !== 'patch') {
      // A different item (or the very first render of a fresh panel) starts with every fold
      // closed — see `foldState`'s field comment for why a previous tracker can't just carry
      // over. `refreshOpenPreviews`'s `'patch'` mode is the only caller that must *not* do this:
      // it's always the same item already on screen, which is exactly why patch mode must
      // leave the reader's open folds alone.
      this.foldState.set(panel, new ExpansionTracker());
    }
    const foldTracker = this.foldState.get(panel) ?? new ExpansionTracker();
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
      const [dossier, tree, graph, showJson, roleList, itemList, typeCatalog, kindCatalog] =
        await Promise.all([
          getRaw(this.runner, invocation, this.workspaceRoot, id),
          getTree(this.runner, invocation, this.workspaceRoot, id),
          getGraph(this.runner, invocation, this.workspaceRoot, id),
          getShowJson(this.runner, invocation, this.workspaceRoot, id),
          getList(this.runner, invocation, this.workspaceRoot, ['-t', 'role']),
          getList(this.runner, invocation, this.workspaceRoot, ['--all']),
          getTypeCatalog(this.runner, invocation, this.workspaceRoot),
          getSubentityKindsCatalog(this.runner, invocation, this.workspaceRoot),
        ]);
      if (dossier.kind !== 'success') {
        if (dossier.kind === 'spawn-error') {
          this.discovery.invalidate();
        }
        this.notifyError(`Squads: ${describeFailure(dossier)}`);
      }
      // Degrades via `roleDirectoryFrom` rather than a second notification — same treatment as
      // the tree/graph/sub-entities/discussion fetches below, none of which are the actionable
      // failure.
      const roles = roleDirectoryFrom(roleList);
      const ids = itemIdMatcherFrom(typeCatalog);
      const items = itemDirectoryFrom(itemList);
      ({ titleText, headerHtml, bodyHtml } = renderOutcomeHtml(id, dossier, roles, ids, items));
      graphsHtml = buildGraphsHtml(
        toGraphOutcome<readonly SqTreeNode[]>(tree, buildSubtreeMermaid),
        toGraphOutcome<SqGraphNode>(graph, buildRefGraphMermaid),
        foldTracker.isExpanded(CHILDREN_GRAPH_FOLD_ID),
        foldTracker.isExpanded(REFS_GRAPH_FOLD_ID),
      );
      const subEntitiesOutcome = toSubEntitiesOutcome(showJson);
      // Only prune on a *successful* fetch: `entities === null` here means the fetch failed, not
      // that the item genuinely has no sub-entities, and pruning against that would wipe every
      // tracked fold on a transient failure rather than leaving them for the next good fetch.
      if (subEntitiesOutcome.entities !== null) {
        foldTracker.prune(
          new Set([
            ...subEntitiesOutcome.entities.map((entity) => entity.local_id),
            CHILDREN_GRAPH_FOLD_ID,
            REFS_GRAPH_FOLD_ID,
          ]),
        );
      }
      subEntitiesHtml = buildSubEntitiesHtml(
        subEntitiesOutcome,
        id,
        roles,
        (localId) => foldTracker.isExpanded(localId),
        subEntityFieldsFrom(showJson, typeCatalog, kindCatalog),
        ids,
        items,
      );
      discussionHtml = buildDiscussionHtml(toDiscussionOutcome(showJson), id, roles, ids, items);
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
