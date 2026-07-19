/**
 * Extension-host smoke-test entry point — ADR-427 #3's third test layer ("a minimal
 * `@vscode/test-electron` smoke test that the tree loads and a preview opens"). Launches a
 * real Extension Development Host, activates this extension inside it, and runs the
 * assertions in `./suite/index.ts`.
 *
 * Wired to `npm run test:e2e` (see package.json) and the `e2e` job in
 * `.github/workflows/vscode-client.yml`, which runs it headless under `xvfb-run` on ubuntu.
 * There is no display in this repo's own dev/agent sandbox, so this script is verified for
 * correctness (config, wiring, compiled paths) but only actually *executes* in that CI job —
 * same caveat as the skew canary's real `sq` run, just for a display instead of a binary.
 *
 * Prerequisite: `npm run compile` — this loads the compiled `out/` tree the same way a real
 * install would (via `package.json`'s `main`), not `src/` directly. `npm run test:e2e` runs
 * the compile itself, so it's runnable standalone.
 */
import { mkdtempSync, rmSync } from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

import { runTests } from '@vscode/test-electron';

async function main(): Promise<void> {
  // Compiled to out/test/extensionHost/runTest.js, so the package root (where package.json
  // lives) is three levels up, not two — out/test/extensionHost -> out/test -> out -> root.
  const extensionDevelopmentPath = path.resolve(__dirname, '../../..');
  const extensionTestsPath = path.resolve(__dirname, './suite/index');

  // A throwaway empty folder to open as the host's workspace: activate() no-ops with no
  // workspace folder present (see src/extension.ts), and the smoke assertions in the suite
  // don't need real squad data — only a folder open so the real activation path runs.
  const workspacePath = mkdtempSync(path.join(os.tmpdir(), 'squads-vscode-e2e-workspace-'));
  try {
    await runTests({
      extensionDevelopmentPath,
      extensionTestsPath,
      launchArgs: [workspacePath, '--disable-extensions'],
    });
  } finally {
    rmSync(workspacePath, { recursive: true, force: true });
  }
}

main().catch((error: unknown) => {
  // runTests() rejects with a TestRunFailedError when the host process exits non-zero (e.g. an
  // assertion in the suite threw) — surface it and fail the script explicitly rather than
  // relying on Node's default unhandled-rejection exit behaviour.
  console.error('Extension-host smoke test failed:', error);
  process.exitCode = 1;
});
