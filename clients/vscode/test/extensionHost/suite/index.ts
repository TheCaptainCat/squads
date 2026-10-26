/**
 * Extension-host smoke suite — runs inside the real Extension Development Host launched by
 * `../runTest.ts`. `run()` is the entry point `@vscode/test-electron` expects; no separate
 * test framework (e.g. Mocha) is pulled in for a single smoke check — an assertion throwing
 * makes this rejected promise itself the failure signal the host process reports as a
 * non-zero exit (see `../runTest.ts`'s doc comment for where it runs).
 */
import * as assert from 'node:assert/strict';

import * as vscode from 'vscode';

import type { RenderReportMessage } from '../../../src/domain/previewMessages';
import type { SquadsExtensionApi } from '../../../src/extension';

const EXTENSION_ID = 'pierre-chat.squads-vscode';

export async function run(): Promise<void> {
  const extension = vscode.extensions.getExtension(EXTENSION_ID);
  assert.ok(extension, `extension ${EXTENSION_ID} is not present in the test host`);

  // Activates for real: registerTreeDataProvider('squadsTree', ...) and registerCommand(...)
  // both run inside activate() (see src/extension.ts) and throw if a contribution point is
  // missing or misdeclared — activate() resolving here is itself proof the tree view and the
  // commands registered clean.
  const api = (await extension.activate()) as SquadsExtensionApi | undefined;
  assert.ok(api, 'activate() did not return the extension API');
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

  // The graph renders under the preview's strict CSP: the page's own report (the host cannot
  // read a webview's DOM) says both of the stub item's graphs became an <svg>, its
  // injected <style> elements carry the page nonce and are live stylesheets, and the browser
  // raised no CSP violation at all, `style-src-attr` included, and every inline `style=""`
  // attribute on the SVGs is reflected in the element's style (none dropped).
  const report = await renderedGraphReport(api, 'SMOKE-2');
  console.log(`[smoke] preview render report: ${JSON.stringify(report)}`);
  assert.equal(report.rendered, 2, 'a preview graph did not render to an svg');
  assert.equal(report.failed, 0, 'a graph output was left as a failure message');
  assert.ok(report.styleElements > 0, 'the rendered svg carries no <style> element');
  assert.equal(report.styleElementsNonced, report.styleElements, 'a <style> lacks the nonce');
  assert.equal(report.styleElementsApplied, report.styleElements, 'a <style> was blocked');
  assert.deepEqual(report.violations, [], 'unexpected CSP violations');
  assert.ok(report.inlineStyleAttributes > 0, 'the rendered svgs carry no inline style attribute');
  assert.equal(
    report.inlineStyleAttributesApplied,
    report.inlineStyleAttributes,
    'an inline style attribute was dropped',
  );

  // The search QuickPick registers and opens without throwing (SearchQuickPickController.open,
  // src/searchQuickPick.ts) — closed immediately via the built-in command so the smoke run
  // doesn't leave it lingering on screen.
  await vscode.commands.executeCommand('squads.search');
  await vscode.commands.executeCommand('workbench.action.closeQuickOpen');
}

async function renderedGraphReport(
  api: SquadsExtensionApi,
  id: string,
): Promise<RenderReportMessage> {
  return new Promise<RenderReportMessage>((resolve, reject) => {
    const timer = setTimeout(() => {
      subscription.dispose();
      reject(new Error('the preview never reported a finished graph render'));
    }, 30_000);
    const subscription = api.onDidReportPreviewRender((report) => {
      clearTimeout(timer);
      subscription.dispose();
      resolve(report);
    });
    void vscode.commands.executeCommand('squads.openItemPreview', id);
  });
}
