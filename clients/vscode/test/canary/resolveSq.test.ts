import * as path from 'node:path';

import { describe, expect, it } from 'vitest';

import type { DiscoveryEnvironment } from '../../src/discovery';
import { movesCwd, resolveCanarySq } from './resolveSq';

const ROOT = '/repo';

function makeEnv(
  files: readonly string[],
  onPath: readonly string[],
  platform: NodeJS.Platform = 'linux',
): DiscoveryEnvironment {
  return {
    platform,
    fileExists: (p) => files.includes(p),
    isOnPath: (name) => onPath.includes(name),
  };
}

interface Row {
  readonly name: string;
  readonly env: DiscoveryEnvironment;
  readonly pinned?: string;
  readonly expected: { command: string; args: string[]; source: string } | 'unresolved';
}

const ROWS: readonly Row[] = [
  {
    name: '.venv wins over a different sq on PATH',
    env: makeEnv([`${ROOT}/.venv/bin/sq`], ['sq', 'uv']),
    expected: { command: `${ROOT}/.venv/bin/sq`, args: [], source: 'venv' },
  },
  {
    name: 'Windows .venv/Scripts/sq.exe layout',
    env: makeEnv([`${ROOT}/.venv/Scripts/sq.exe`], ['sq'], 'win32'),
    expected: { command: `${ROOT}/.venv/Scripts/sq.exe`, args: [], source: 'venv' },
  },
  {
    name: 'no .venv, uv and a project: uv run sq pointed at the repo',
    env: makeEnv([`${ROOT}/pyproject.toml`], ['uv', 'poetry', 'sq']),
    expected: { command: 'uv', args: ['run', '--project', ROOT, 'sq'], source: 'uv' },
  },
  {
    name: 'only poetry and a project',
    env: makeEnv([`${ROOT}/pyproject.toml`], ['poetry', 'sq']),
    expected: { command: 'poetry', args: ['--project', ROOT, 'run', 'sq'], source: 'poetry' },
  },
  {
    name: 'only bare sq on PATH',
    env: makeEnv([], ['sq']),
    expected: { command: 'sq', args: [], source: 'path' },
  },
  {
    name: 'nothing at all',
    env: makeEnv([], []),
    expected: 'unresolved',
  },
  {
    name: 'a pinned command beats the .venv',
    env: makeEnv([`${ROOT}/.venv/bin/sq`, '/opt/sq'], ['sq']),
    pinned: '/opt/sq',
    expected: { command: '/opt/sq', args: [], source: 'pinned' },
  },
  {
    name: 'a pinned command that does not exist is unresolved, not a fall-through',
    env: makeEnv([`${ROOT}/.venv/bin/sq`], ['sq']),
    pinned: '/gone/sq',
    expected: 'unresolved',
  },
  {
    name: 'a pinned bare name that is not on PATH is unresolved',
    env: makeEnv([`${ROOT}/.venv/bin/sq`], ['sq']),
    pinned: 'nosuchsq',
    expected: 'unresolved',
  },
  {
    name: 'a pinned uv run sq is pointed at the repo',
    env: makeEnv([], ['uv']),
    pinned: 'uv run sq',
    expected: { command: 'uv', args: ['run', '--project', ROOT, 'sq'], source: 'pinned' },
  },
  {
    name: 'a pinned poetry run sq is pointed at the repo',
    env: makeEnv([], ['poetry']),
    pinned: 'poetry run sq',
    expected: { command: 'poetry', args: ['--project', ROOT, 'run', 'sq'], source: 'pinned' },
  },
  {
    name: 'a pinned path with spaces (Windows layout) stays one path',
    env: makeEnv(['C:\\Program Files\\squads\\sq.exe'], [], 'win32'),
    pinned: 'C:\\Program Files\\squads\\sq.exe',
    expected: { command: 'C:\\Program Files\\squads\\sq.exe', args: [], source: 'pinned' },
  },
  {
    name: 'a JSON array pin keeps a spaced interpreter and its args',
    env: makeEnv(['/my tools/py'], []),
    pinned: '["/my tools/py", "-m", "squads"]',
    expected: { command: '/my tools/py', args: ['-m', 'squads'], source: 'pinned' },
  },
];

describe('canary sq resolution', () => {
  it.each(ROWS)('$name', ({ env, pinned, expected }) => {
    const result = resolveCanarySq(ROOT, env, pinned);
    if (expected === 'unresolved') {
      expect(result.ok).toBe(false);
    } else {
      expect(result).toEqual({ ok: true, invocation: expected });
    }
  });
});

describe('canary sq invocation never leaves the scratch cwd', () => {
  it.each(ROWS.filter((row) => row.expected !== 'unresolved'))('$name', ({ env, pinned }) => {
    const result = resolveCanarySq(ROOT, env, pinned);
    if (!result.ok) {
      throw new Error('expected a resolution');
    }
    const { args } = result.invocation;
    expect(args.filter(movesCwd)).toEqual([]);
  });
});

describe('relative pins', () => {
  it('resolves a relative pin path against the process cwd before the check and the spawn', () => {
    const abs = path.resolve('../../.venv/bin/sq');
    const env = makeEnv([abs], []);
    const result = resolveCanarySq(ROOT, env, '../../.venv/bin/sq');
    expect(result).toEqual({ ok: true, invocation: { command: abs, args: [], source: 'pinned' } });
  });
});

describe('a pin that moves the working directory is rejected', () => {
  const pins = [
    'uv --directory /repo run sq',
    'uv --directory=/repo run sq',
    'uv run --directory=/repo sq',
    'poetry -C /repo run sq',
    'poetry -C/repo run sq',
    'poetry --directory /repo run sq',
    'uv --cwd /repo run sq',
  ];
  it.each(pins)('%s', (pin) => {
    expect(resolveCanarySq(ROOT, makeEnv([], ['uv', 'poetry']), pin).ok).toBe(false);
  });
});
