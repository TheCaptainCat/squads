/**
 * Wire format + routing logic for the item-preview webview's navigable item links (webview ->
 * extension `postMessage`). Kept `vscode`-free/pure: the shape guard and the
 * same-panel-vs-new-panel decision are unit-testable with no host; only the actual
 * `WebviewPanel` creation/reuse (`itemPreviewManager.ts`) touches the real `vscode` API.
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
