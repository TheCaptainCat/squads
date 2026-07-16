// ESLint flat config for clients/vscode. Isolated from the Python core's ruff/pyright gate —
// this file and its toolchain are self-contained under clients/vscode/.
import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import prettierConfig from 'eslint-config-prettier';
import simpleImportSort from 'eslint-plugin-simple-import-sort';
import tseslint from 'typescript-eslint';

export default defineConfig(
  {
    ignores: ['out/**', 'node_modules/**', 'test/fixtures/**'],
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
