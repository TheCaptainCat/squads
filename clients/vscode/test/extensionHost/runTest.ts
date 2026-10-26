/**
 * Extension-host smoke-test entry point: launches a real Extension Development Host, activates
 * this extension inside it, and runs the assertions in `./suite/index.ts`.
 *
 * Wired to `npm run test:e2e` (see package.json) and the `e2e` job in
 * `.github/workflows/vscode-client.yml`, which runs it headless under `xvfb-run` on ubuntu. It
 * also runs locally wherever a display is available.
 *
 * The workspace is a throwaway folder holding a stub `sq` (see `writeStubSq`) that
 * `squads.sqPath` points at, so the preview has an item and graphs to render with no real squad
 * or `sq` binary. The stub is a node script with a shebang, so this runs on POSIX hosts.
 *
 * Prerequisite: `npm run compile` — this loads the compiled `out/` tree the same way a real
 * install would (via `package.json`'s `main`), not `src/` directly. `npm run test:e2e` runs
 * the compile itself, so it's runnable standalone.
 */
import { chmodSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

import { runTests } from '@vscode/test-electron';

/** A minimal stand-in `sq` (a node script) so the item preview has something to render: for
 * `SMOKE-2` it answers `show --raw` with a short dossier and `tree`/`graph --json` with the
 * committed fixtures, which is what the preview's two mermaid graphs are built from. Every other
 * call fails and the preview degrades. Pointed at through the workspace's `squads.sqPath`. */
function writeStubSq(workspacePath: string): void {
  const fixtures = path.resolve(__dirname, '../../../test/fixtures');
  const dossier = '# SMOKE-2 — Graph smoke\n\n- **status:** Ready\n\nA body.\n';
  const stubPath = path.join(workspacePath, 'sq-stub.js');
  writeFileSync(
    stubPath,
    `#!/usr/bin/env node
const fs = require('node:fs');
const args = process.argv.slice(2);
const answer = (text) => process.stdout.write(text);
if (args[1] !== 'SMOKE-2') {
  process.stderr.write('stub sq: unsupported');
  process.exit(1);
} else if (args[0] === 'show' && args.includes('--raw')) {
  answer(${JSON.stringify(dossier)});
} else if (args[0] === 'tree' && args.includes('--json')) {
  answer(fs.readFileSync(${JSON.stringify(path.join(fixtures, 'tree.json'))}, 'utf8'));
} else if (args[0] === 'graph' && args.includes('--json')) {
  answer(fs.readFileSync(${JSON.stringify(path.join(fixtures, 'graph.json'))}, 'utf8'));
} else {
  process.stderr.write('stub sq: unsupported');
  process.exit(1);
}
`,
  );
  chmodSync(stubPath, 0o755);
  mkdirSync(path.join(workspacePath, '.vscode'));
  writeFileSync(
    path.join(workspacePath, '.vscode', 'settings.json'),
    JSON.stringify({ 'squads.sqPath': stubPath }),
  );
}

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
    writeStubSq(workspacePath);
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
