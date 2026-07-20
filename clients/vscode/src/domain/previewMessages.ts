/**
 * Wire format + routing logic for the item-preview webview, in both directions. Webview ->
 * extension: `postMessage`ing a navigable item-link click (`OpenItemMessage`), or a click on the
 * in-content back/forward toolbar (`NavigateHistoryMessage` — VS Code's `editor/title/navigation`
 * menu doesn't reliably surface inline buttons for a plain `createWebviewPanel`, confirmed by
 * screenshot, so the toolbar rendered inside the page itself is the primary back/forward
 * control; see `itemPreviewManager.ts`'s module doc comment). Extension -> webview:
 * `postMessage`ing fresh section HTML for a same-item refresh so the panel can patch its DOM in
 * place rather than reload (`UpdateContentMessage`) — see `itemPreviewManager.ts`'s `render`,
 * which reloads `panel.webview.html` wholesale only on an actual navigation (a fresh item id,
 * scrolling to top), and posts this message instead on a same-item `.squads.json`-watcher
 * refresh (preserving the reader's scroll position, since the page itself never reloads). Kept
 * `vscode`-free/pure: the shape guards and the same-panel-vs-new-panel decision are unit-testable
 * with no host; only the actual `WebviewPanel` creation/reuse/`postMessage` touches the real
 * `vscode` API.
 */

/** The one message the webview's inline script ever posts (see `previewDocument.ts`'s
 * `CLIENT_SCRIPT`) — a click on an `a.sq-item-link`. */
export const OPEN_ITEM_COMMAND = 'openItem';

export interface OpenItemMessage {
  readonly command: typeof OPEN_ITEM_COMMAND;
  readonly id: string;
  readonly newTab: boolean;
}

/** Shape guard for `window.postMessage` payloads arriving from the webview — untrusted input
 * from script running in the panel, so every field is checked rather than cast. */
export function parseOpenItemMessage(data: unknown): OpenItemMessage | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const record = data as Record<string, unknown>;
  if (record.command !== OPEN_ITEM_COMMAND) {
    return null;
  }
  if (typeof record.id !== 'string' || record.id === '') {
    return null;
  }
  if (typeof record.newTab !== 'boolean') {
    return null;
  }
  return { command: OPEN_ITEM_COMMAND, id: record.id, newTab: record.newTab };
}

/** Posted by a click on the in-content back/forward toolbar (`previewDocument.ts`'s
 * `buildHistoryToolbarHtml`/`clientScript`) — the panel-specific counterpart to the global
 * `squads.previewBack`/`squads.previewForward` commands the `alt+left`/`alt+right` keybindings
 * invoke. Unlike those (which act on whichever panel VS Code reports as focused), a message
 * always names the exact panel it came from, so `itemPreviewManager.ts`'s handler steps *that*
 * panel's history with no ambiguity. */
export const NAVIGATE_HISTORY_COMMAND = 'navigateHistory';

export type HistoryDirection = 'back' | 'forward';

export interface NavigateHistoryMessage {
  readonly command: typeof NAVIGATE_HISTORY_COMMAND;
  readonly direction: HistoryDirection;
}

/** Shape guard for a `NavigateHistoryMessage` — same untrusted-input treatment as
 * `parseOpenItemMessage`. The toolbar never renders an enabled button at an end of history (see
 * `buildHistoryToolbarHtml`), but this is checked anyway since the payload still crosses an
 * untrusted boundary. */
export function parseNavigateHistoryMessage(data: unknown): NavigateHistoryMessage | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const record = data as Record<string, unknown>;
  if (record.command !== NAVIGATE_HISTORY_COMMAND) {
    return null;
  }
  if (record.direction !== 'back' && record.direction !== 'forward') {
    return null;
  }
  return { command: NAVIGATE_HISTORY_COMMAND, direction: record.direction };
}

/** The message the extension host posts to an already-open panel's webview for a same-item
 * refresh (see the module doc comment) — `itemPreviewManager.ts`'s `render` builds
 * `articleHtml` via `previewDocument.ts`'s `buildArticleHtml` so it's byte-identical to what
 * `buildPreviewHtml` would have put inside `<article>` on a fresh load. The webview's inline
 * script (`previewDocument.ts`'s `clientScript`) swaps these into the three stable mount
 * points (`#sq-article`, `#sq-subentities`, `#sq-discussion`) and re-runs the mermaid render
 * pass — no navigation, so the browser's scroll position is left untouched. */
export const UPDATE_CONTENT_COMMAND = 'updateContent';

export interface UpdateContentMessage {
  readonly command: typeof UPDATE_CONTENT_COMMAND;
  readonly title: string;
  readonly articleHtml: string;
  readonly subEntitiesHtml: string;
  readonly discussionHtml: string;
}

export type OpenRoute = 'same-panel' | 'new-panel';

/** A plain click (or ctrl/cmd-click) navigates the panel that sent the message in place;
 * middle-click (`newTab`) opens a brand new panel. */
export function routeForMessage(message: OpenItemMessage): OpenRoute {
  return message.newTab ? 'new-panel' : 'same-panel';
}

/** Tree-node selection / palette entry point: reuse the single owned preview panel if one is
 * already open (mirroring the pre-webview single dynamic preview's UX), otherwise open a
 * fresh one. */
export function routeForTreeSelection(hasActivePanel: boolean): OpenRoute {
  return hasActivePanel ? 'same-panel' : 'new-panel';
}
