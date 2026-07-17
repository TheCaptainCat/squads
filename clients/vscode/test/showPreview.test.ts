import { readFileSync } from 'node:fs';
import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import {
  buildShowUriString,
  extractIdFromUriPath,
  renderShowOutcome,
  SQUADS_SCHEME,
} from '../src/domain/showPreview';

function fixture(name: string): string {
  return readFileSync(path.join(__dirname, 'fixtures', name), 'utf8');
}

const SHOW_RAW_FIXTURE = fixture('show-raw.txt');

describe('buildShowUriString / extractIdFromUriPath', () => {
  it('round-trips an id through the squads: URI string', () => {
    const uriString = buildShowUriString('TASK-430');
    expect(uriString).toBe('squads:/TASK-430');
    expect(uriString.startsWith(`${SQUADS_SCHEME}:`)).toBe(true);

    // `vscode.Uri.parse('squads:/TASK-430').path` would be '/TASK-430' — simulate that here
    // without importing 'vscode' (unavailable outside the extension host).
    expect(extractIdFromUriPath('/TASK-430')).toBe('TASK-430');
  });

  it('handles a path with no leading slash defensively', () => {
    expect(extractIdFromUriPath('TASK-430')).toBe('TASK-430');
  });
});

describe('renderShowOutcome', () => {
  it('returns the raw sq show --raw text verbatim on success', () => {
    const rendered = renderShowOutcome('TASK-430', { kind: 'success', data: SHOW_RAW_FIXTURE });

    expect(rendered).toBe(SHOW_RAW_FIXTURE);
    expect(rendered).toContain('# TASK-430 — Open sq show --raw');
    expect(rendered).not.toContain('╭');
    expect(rendered).not.toMatch(/^status:/m);
  });

  it('renders an actionable markdown message on failure instead of blank/stale content', () => {
    const rendered = renderShowOutcome('TASK-430', {
      kind: 'runtime-error',
      message: 'Schema mismatch: run `sq migrate up`.',
      exitCode: 1,
    });

    expect(rendered).toContain('# Squads: unable to load TASK-430');
    expect(rendered).toContain('Schema mismatch: run `sq migrate up`.');
  });

  it('surfaces a usage-error message too', () => {
    const rendered = renderShowOutcome('BOGUS-1', {
      kind: 'usage-error',
      message: 'No such item: BOGUS-1',
      argv: ['sq', 'show', 'BOGUS-1', '--raw'],
    });

    expect(rendered).toContain('unable to load BOGUS-1');
    expect(rendered).toContain('No such item: BOGUS-1');
  });
});
