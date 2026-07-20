/**
 * Pure per-panel navigation history for the item-preview webview — browser-style back/forward
 * semantics with no `vscode` dependency, so it's unit-testable without an extension host. A
 * history is a list of item ids plus the index of the one currently shown.
 *
 * `itemPreviewManager.ts` is the only caller: it keeps one `PreviewHistory` per open panel,
 * mutating it only on an actual *navigation* (a tree selection or a link/`@mention` click that
 * lands a new item in the panel) via `pushHistory` — never on the `.squads.json`-watcher
 * `'patch'` refresh (same item, not a navigation) and never on `stepBack`/`stepForward`
 * themselves (a position change within existing history, not a new entry).
 */

export interface PreviewHistory {
  /** Items visited, oldest first. Never empty once a panel exists. */
  readonly ids: readonly string[];
  /** Index into `ids` of the item currently shown. */
  readonly index: number;
}

/** Seeds a fresh single-entry history for a newly opened panel. */
export function createHistory(id: string): PreviewHistory {
  return { ids: [id], index: 0 };
}

/** The item currently shown per `history` — `ids[index]`. The `?? ''` fallback is unreachable
 * given the invariant every function here maintains (`ids` non-empty, `index` always in
 * bounds) — just satisfying `noUncheckedIndexedAccess`. */
export function currentId(history: PreviewHistory): string {
  return history.ids[history.index] ?? '';
}

export function canStepBack(history: PreviewHistory): boolean {
  return history.index > 0;
}

export function canStepForward(history: PreviewHistory): boolean {
  return history.index < history.ids.length - 1;
}

/** Records a navigation to `id`: appends after the current position and drops any forward
 * entries (standard browser-style truncation — those items become unreachable via
 * `stepForward` afterward). Navigating to the id already current is a no-op — the reader hasn't
 * moved anywhere new, so nothing is pushed. */
export function pushHistory(history: PreviewHistory, id: string): PreviewHistory {
  if (currentId(history) === id) {
    return history;
  }
  const retained = history.ids.slice(0, history.index + 1);
  return { ids: [...retained, id], index: retained.length };
}

/** Moves one step back in history. A no-op (returns `history` unchanged) when already at the
 * oldest entry — callers checking `canStepBack` first is recommended but not required. */
export function stepBack(history: PreviewHistory): PreviewHistory {
  return canStepBack(history) ? { ids: history.ids, index: history.index - 1 } : history;
}

/** Moves one step forward in history. A no-op (returns `history` unchanged) when already at the
 * newest entry — callers checking `canStepForward` first is recommended but not required. */
export function stepForward(history: PreviewHistory): PreviewHistory {
  return canStepForward(history) ? { ids: history.ids, index: history.index + 1 } : history;
}
