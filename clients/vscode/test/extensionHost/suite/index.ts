/**
 * Extension-host smoke suite — runs inside the real Extension Development Host launched by
 * `../runTest.ts`. `run()` is the entry point `@vscode/test-electron` expects; no separate
 * test framework (e.g. Mocha) is pulled in for a single smoke check — an assertion throwing
 * makes this rejected promise itself the failure signal the host process reports as a
 * non-zero exit (see `../runTest.ts`'s doc comment for why this only actually executes in CI).
 */
import * as assert from 'node:assert/strict';

import * as vscode from 'vscode';

const EXTENSION_ID = 'pierre-chat.squads-vscode';

export async function run(): Promise<void> {
  const extension = vscode.extensions.getExtension(EXTENSION_ID);
  assert.ok(extension, `extension ${EXTENSION_ID} is not present in the test host`);

  // Activates for real: registerTreeDataProvider('squadsTree', ...) and registerCommand(...)
  // both run inside activate() (see src/extension.ts) and throw if a contribution point is
  // missing or misdeclared — activate() resolving here is itself proof the tree view and the
  // commands registered clean.
  await extension.activate();
  assert.equal(extension.isActive, true, 'extension did not report active after activate()');

  // Both views' core contributions loaded: VS Code auto-generates a `<view>.focus` command for
  // every contributed view, and executing it would throw if the view/view container
  // contribution had failed to take. `squadsMeta` is the meta/roster view (F12).
  await vscode.commands.executeCommand('squadsTree.focus');
  await vscode.commands.executeCommand('squadsMeta.focus');

  // Opening an item preview via the owned WebviewPanel doesn't throw. `ItemPreviewManager`'s
  // render path (src/itemPreviewManager.ts) always resolves to panel content — an actionable
  // error message when `sq`/the id can't be resolved, never a rejection — so this exercises
  // the real webview-creation code path with no `sq` binary or real squad item required.
  await vscode.commands.executeCommand('squads.openItemPreview', 'SMOKE-0');

  // Back/forward wiring: on a freshly opened panel with a single history entry, both are
  // inert — the manager's `goBack`/`goForward` no-op rather than throw (see
  // `ItemPreviewManager.stepHistory`). Reusing the same panel for a second id pushes a new
  // history entry, so back/forward round-trip between the two ids without throwing either.
  // The `squads.previewCanGoBack`/`previewCanGoForward` context keys (and the resulting
  // title-bar button enablement) aren't readable from an extension's own test code — VS Code
  // exposes no API to query a `setContext` key back out — so that half of the wiring is
  // reason-verified from `src/itemPreviewManager.ts`'s `recomputeContextKeys`, not asserted here.
  await vscode.commands.executeCommand('squads.previewBack');
  await vscode.commands.executeCommand('squads.previewForward');
  await vscode.commands.executeCommand('squads.openItemPreview', 'SMOKE-1');
  await vscode.commands.executeCommand('squads.previewBack');
  await vscode.commands.executeCommand('squads.previewForward');
}
