/**
 * Watches `<squad-dir>/.squads.json` for on-disk changes — an agent running `sq`, a `git pull` —
 * and auto-refreshes the tree views + any open item preview (F17), instead of requiring an
 * explicit manual refresh.
 *
 * The extension stays a pure CONSUMER of `sq … --json`. This module never parses `.squads.json`
 * for data — it's a change TRIGGER only; on fire, callers re-fetch through the existing
 * `sq … --json` calls the same way an explicit refresh does.
 *
 * Squad-dir resolution (`domain/squadDir.ts`) is a client-side workspace walk-up mirroring
 * `sq`'s own `.squads.toml` resolution — no new core surface needed. When no `.squads.toml` is
 * found, or the workspace folder isn't backed by a local `file:` filesystem (a remote/virtual
 * workspace), this sets up no watcher and returns a no-op `Disposable`.
 *
 * The index is written atomically (`os.replace`), so one logical update on disk typically fires
 * as create+change (sometimes more) in quick succession; a short debounce window coalesces that
 * burst into a single refresh.
 */
import * as vscode from 'vscode';

import { resolveSquadDir, type SquadDirEnvironment } from './domain/squadDir';

const INDEX_FILENAME = '.squads.json';
const DEBOUNCE_MS = 150;

export interface SquadIndexWatcherTarget {
  /** Called (debounced/coalesced) whenever `.squads.json` changes on disk. */
  onIndexChanged(): void;
}

function noopDisposable(): vscode.Disposable {
  return new vscode.Disposable(() => {
    /* nothing to tear down */
  });
}

/** Sets up the `.squads.json` watcher for `workspaceFolder`, or does nothing (returning a no-op
 * `Disposable`) when the squad dir can't be resolved locally, or the workspace folder isn't a
 * local `file:` filesystem. Dispose the returned value with the extension. */
export function watchSquadIndex(
  workspaceFolder: vscode.WorkspaceFolder,
  env: SquadDirEnvironment,
  target: SquadIndexWatcherTarget,
): vscode.Disposable {
  if (workspaceFolder.uri.scheme !== 'file') {
    return noopDisposable();
  }
  const squadDir = resolveSquadDir(workspaceFolder.uri.fsPath, env);
  if (squadDir === undefined) {
    return noopDisposable();
  }

  const watcher = vscode.workspace.createFileSystemWatcher(
    new vscode.RelativePattern(vscode.Uri.file(squadDir), INDEX_FILENAME),
  );

  let timer: ReturnType<typeof setTimeout> | undefined;
  const scheduleRefresh = (): void => {
    if (timer !== undefined) {
      clearTimeout(timer);
    }
    timer = setTimeout(() => {
      timer = undefined;
      target.onIndexChanged();
    }, DEBOUNCE_MS);
  };

  const subscriptions = [
    watcher.onDidChange(scheduleRefresh),
    watcher.onDidCreate(scheduleRefresh),
    watcher.onDidDelete(scheduleRefresh),
  ];

  return new vscode.Disposable(() => {
    if (timer !== undefined) {
      clearTimeout(timer);
    }
    for (const subscription of subscriptions) {
      subscription.dispose();
    }
    watcher.dispose();
  });
}
