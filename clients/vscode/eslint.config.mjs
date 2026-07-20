/// <reference types="node" />
// ESLint flat config for clients/vscode. Isolated from the Python core's ruff/pyright gate —
// this file and its toolchain are self-contained under clients/vscode/.
import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import prettierConfig from 'eslint-config-prettier';
import simpleImportSort from 'eslint-plugin-simple-import-sort';
import tseslint from 'typescript-eslint';

export default defineConfig(
  {
    // scripts/** is a plain-CommonJS build helper (vendors the mermaid webview asset), not
    // part of the tsconfig project this strict type-aware config resolves against.
    //
    // .vscode-test/** and coverage/** are the two *downloaded/generated* trees `.gitignore`
    // already excludes from version control (`npm run test:e2e` pulls a full VS Code + Electron
    // build into `.vscode-test/` — several hundred MB of bundled JS and ambient `.d.ts` files,
    // e.g. the full `vscode.d.ts` API surface — and a future coverage run would populate
    // `coverage/`). Neither is `node_modules/**` or `out/**`, so ESLint's own file walk doesn't
    // skip them for free, and *this* is what actually blows the type-aware `projectService`'s
    // heap: left unignored, `eslint .` hands it hundreds of large/foreign files that aren't
    // part of `tsconfig.json`'s `include` — each one forces the language service to spin up an
    // ad hoc program (or scan for one) well outside anything this config is meant to check, on
    // top of megabyte-scale `.d.ts` parses. Once present on disk (e.g. after running
    // `test:e2e` once) it stays until manually removed, so this reproduces on an otherwise
    // clean tree — a config gap, not a fundamental heap limit (raising `--max-old-space-size`
    // alone does not fix it). CI's `check` job never runs `test:e2e` first, so it never has
    // `.vscode-test/` on disk and was never hitting this.
    ignores: [
      'out/**',
      'node_modules/**',
      'test/fixtures/**',
      'media/**',
      'scripts/**',
      '.vscode-test/**',
      'coverage/**',
    ],
  },
  js.configs.recommended,
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: {
          allowDefaultProject: ['eslint.config.mjs'],
        },
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      'simple-import-sort': simpleImportSort,
    },
    rules: {
      // Mirrors ruff's C901 (mccabe) / PLR0913, same thresholds as the Python core.
      complexity: ['error', 12],
      'max-params': ['error', 8],

      // Import ordering (~= ruff's I / isort).
      'simple-import-sort/imports': 'error',
      'simple-import-sort/exports': 'error',

      // tsc's noUnusedLocals/noUnusedParameters already enforce this at the type-check
      // step; disable the ESLint duplicate to avoid double-reporting the same defect.
      '@typescript-eslint/no-unused-vars': 'off',
    },
  },
  // Disable stylistic rules that fight Prettier's formatting; must stay last.
  prettierConfig,
);
