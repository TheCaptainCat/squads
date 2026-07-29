/**
 * Wire format + routing logic for the item-preview webview, in both directions: webview ->
 * extension click/toolbar/fold events, and extension -> webview content patches for a same-item
 * refresh. The in-content back/forward/refresh toolbar exists because VS Code's
 * `editor/title/navigation` menu doesn't reliably surface inline buttons for a plain
 * `createWebviewPanel` (confirmed by screenshot) — see `itemPreviewManager.ts`. Kept
 * `vscode`-free/pure: the shape guards and routing decisions here are unit-testable with no host;
 * only the actual `WebviewPanel` creation/reuse/`postMessage` touches the real `vscode` API.
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

/** Posted by the in-content back/forward toolbar — the panel-specific counterpart to the global
 * `squads.previewBack`/`squads.previewForward` commands bound to `alt+left`/`alt+right`. Unlike
 * those (which act on whichever panel VS Code reports as focused), this message always names the
 * exact panel it came from. */
export const NAVIGATE_HISTORY_COMMAND = 'navigateHistory';

export type HistoryDirection = 'back' | 'forward';

export interface NavigateHistoryMessage {
  readonly command: typeof NAVIGATE_HISTORY_COMMAND;
  readonly direction: HistoryDirection;
}

/** Shape guard for a `NavigateHistoryMessage` — same untrusted-input treatment as
 * `parseOpenItemMessage`. Checked even though the toolbar never renders an enabled button at an
 * end of history, since the payload still crosses an untrusted boundary. */
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

/** Patches an already-open panel's webview in place for a same-item refresh, instead of a full
 * `panel.webview.html` reload — preserving the reader's scroll position. `articleHtml` is built
 * via `buildArticleHtml` so it matches what a fresh load would produce; the webview's inline
 * script swaps all three fields into their mount points (`#sq-article`, `#sq-subentities`,
 * `#sq-discussion`) and re-runs the mermaid render pass. */
export const UPDATE_CONTENT_COMMAND = 'updateContent';

export interface UpdateContentMessage {
  readonly command: typeof UPDATE_CONTENT_COMMAND;
  readonly title: string;
  readonly articleHtml: string;
  readonly subEntitiesHtml: string;
  readonly discussionHtml: string;
}

/** Posted by the in-content toolbar's refresh button — same round trip as
 * `NavigateHistoryMessage`. The handler invokes the same `squads.refreshAll` command the
 * tree-view buttons and the `.squads.json` watcher use, so every refresh path is identical. */
export const REFRESH_COMMAND = 'refresh';

export interface RefreshMessage {
  readonly command: typeof REFRESH_COMMAND;
}

/** Shape guard for a `RefreshMessage` — same untrusted-input treatment as the other parsers
 * here. */
export function parseRefreshMessage(data: unknown): RefreshMessage | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const record = data as Record<string, unknown>;
  return record.command === REFRESH_COMMAND ? { command: REFRESH_COMMAND } : null;
}

/** Posted when a tracked `<details>` fold (a sub-entity body, or one of the two per-diagram
 * graph sections — never the always-`open` "Sub-entities (N)"/"Discussion (N)" wrapper sections)
 * is opened or closed, via a capture-phase `toggle` listener on `document` — a native `toggle`
 * event on `<details>` does not bubble, so a bubbling listener would miss it. `id` is the fold's
 * stable identity: a sub-entity's `local_id`, or one of the two fixed graph-fold ids from
 * `buildGraphsHtml`'s `foldId`. Feeds `itemPreviewManager.ts`'s per-panel `ExpansionTracker` so
 * the next render restores exactly the folds the reader had open. */
export const TOGGLE_FOLD_COMMAND = 'toggleFold';

export interface ToggleFoldMessage {
  readonly command: typeof TOGGLE_FOLD_COMMAND;
  readonly id: string;
  readonly open: boolean;
}

/** Shape guard for a `ToggleFoldMessage` — same untrusted-input treatment as the other parsers
 * here. */
export function parseToggleFoldMessage(data: unknown): ToggleFoldMessage | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }
  const record = data as Record<string, unknown>;
  if (record.command !== TOGGLE_FOLD_COMMAND) {
    return null;
  }
  if (typeof record.id !== 'string' || record.id === '') {
    return null;
  }
  if (typeof record.open !== 'boolean') {
    return null;
  }
  return { command: TOGGLE_FOLD_COMMAND, id: record.id, open: record.open };
}

export type OpenRoute = 'same-panel' | 'new-panel';

/** A plain click (or ctrl/cmd-click) navigates the panel that sent the message in place;
 * middle-click (`newTab`) opens a brand new panel. */
export function routeForMessage(message: OpenItemMessage): OpenRoute {
  return message.newTab ? 'new-panel' : 'same-panel';
}

/** Tree/palette entry point: reuse the single owned panel if one is already open (mirroring the
 * pre-webview single dynamic preview's UX), otherwise open a fresh one. */
export function routeForTreeSelection(hasActivePanel: boolean): OpenRoute {
  return hasActivePanel ? 'same-panel' : 'new-panel';
}
