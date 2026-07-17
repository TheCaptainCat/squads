/**
 * Extension-host smoke-test scaffold — ADR-427 #3's third test layer ("a minimal
 * `@vscode/test-electron` smoke test that the tree loads and a preview opens").
 *
 * STATUS: scaffold only. This is the standard `@vscode/test-electron` entry point
 * (download/launch a real VS Code, activate this extension inside it, run the suite in
 * `./suite/index.ts`) but it is deliberately NOT wired into any npm script or CI job yet —
 * running it needs a headless display (Xvfb on Linux CI) and a compiled `out/` build, neither
 * of which this task sets up. The skew canary (`test/canary/`) is this task's actual
 * deliverable; wiring the real headless extension-host run is a tracked follow-up.
 *
 * Once picked up, the intended shape is: compile (`npm run compile`), then run this file
 * with `ts-node`/`tsx` (or compile it too and run the emitted JS with plain `node`) under
 * `xvfb-run` in CI.
 */
import * as path from 'node:path';

import { runTests } from '@vscode/test-electron';

async function main(): Promise<void> {
  const extensionDevelopmentPath = path.resolve(__dirname, '../..');
  const extensionTestsPath = path.resolve(__dirname, './suite/index');
  await runTests({ extensionDevelopmentPath, extensionTestsPath });
}

void main();
