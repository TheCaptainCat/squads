import { readdirSync, readFileSync, statSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * Forward guard for the project's "no ticket IDs in source" rule, scoped to this package.
 * The Python core's own hygiene gate (tests/meta) only walks src/docs/tests and never
 * reaches clients/, so this mirrors that gate locally: production source, the toolchain
 * config, and the README must never cite a squad-item ID. Test data — committed fixtures
 * and assertion literals under test/ — is deliberately excluded, the same carve-out the
 * core gate makes for its own test-assertion data.
 */
const TICKET_ID_PATTERN = /\b(?:ADR|FEAT|TASK|REV|BUG|EPIC)-\d|\bUS\d|\bST\d/;

const PACKAGE_ROOT = path.resolve(__dirname, '..');
const SCAN_DIRS = ['src'];
const SCAN_FILES = [
  'README.md',
  'package.json',
  'tsconfig.json',
  'eslint.config.mjs',
  'vitest.config.ts',
  '.prettierrc.json',
];

function collectFilesUnder(dir: string): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    files.push(...(statSync(full).isDirectory() ? collectFilesUnder(full) : [full]));
  }
  return files;
}

function scanFile(file: string): string[] {
  const text = readFileSync(file, 'utf8');
  const matches: string[] = [];
  for (const line of text.split('\n')) {
    const match = TICKET_ID_PATTERN.exec(line);
    if (match !== null) {
      matches.push(match[0]);
    }
  }
  return matches;
}

describe('ticket-ID hygiene', () => {
  it('keeps production source, toolchain config, and the README free of squad-item IDs', () => {
    const files = [
      ...SCAN_DIRS.flatMap((dir) => collectFilesUnder(path.join(PACKAGE_ROOT, dir))),
      ...SCAN_FILES.map((file) => path.join(PACKAGE_ROOT, file)),
    ];

    const violations = files.flatMap((file) =>
      scanFile(file).map((match) => `${path.relative(PACKAGE_ROOT, file)}: ${match}`),
    );

    expect(violations).toEqual([]);
  });
});
