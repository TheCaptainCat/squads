import { defineConfig } from 'vitest/config';

/**
 * Config for the integration skew-canary layer (ADR-427 #3): a separate `vitest` project
 * from the unit-test config (`vitest.config.ts`) so `npm test` never shells out to a real
 * `sq` binary, and `npm run test:canary` never runs the unit suite. The canary itself
 * skips cleanly (not a failure) when no `sq` is resolvable on PATH — see
 * `test/canary/skewCanary.test.ts`.
 */
export default defineConfig({
  test: {
    environment: 'node',
    include: ['test/canary/**/*.test.ts'],
    // The canary shells out to a real `sq` and drives a scratch squad on disk; keep it to
    // one worker so scratch-directory setup/teardown never overlaps.
    fileParallelism: false,
    testTimeout: 30_000,
    hookTimeout: 30_000,
  },
});
