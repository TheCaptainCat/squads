import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['test/**/*.test.ts'],
    // The integration skew canary is its own layer (run via `npm run test:canary` /
    // vitest.canary.config.ts) — excluded here so the plain `npm test` run stays hermetic
    // (no `sq` binary, no shelling out) and fast.
    exclude: ['**/node_modules/**', 'test/canary/**'],
  },
});
