import { describe, expect, it } from 'vitest';

import {
  describeTriedOrder,
  type DiscoveryEnvironment,
  resolveSqInvocation,
  SqDiscovery,
} from '../src/discovery';

const WORKSPACE_ROOT = '/workspace/example';

function makeEnvironment(opts: {
  platform?: NodeJS.Platform;
  files?: readonly string[];
  onPath?: readonly string[];
  onFileExists?: (path: string) => void;
  onIsOnPath?: (name: string) => void;
}): DiscoveryEnvironment {
  const files = new Set(opts.files ?? []);
  const onPath = new Set(opts.onPath ?? []);
  return {
    platform: opts.platform ?? 'linux',
    fileExists(path) {
      opts.onFileExists?.(path);
      return files.has(path);
    },
    isOnPath(name) {
      opts.onIsOnPath?.(name);
      return onPath.has(name);
    },
  };
}

describe('resolveSqInvocation', () => {
  it('prefers squads.sqPath over every other strategy when the file exists', () => {
    const env = makeEnvironment({
      files: ['/custom/sq', `${WORKSPACE_ROOT}/.venv/bin/sq`],
      onPath: ['uv', 'sq'],
    });
    const result = resolveSqInvocation(WORKSPACE_ROOT, { sqPath: '/custom/sq' }, env);
    expect(result).toEqual({
      ok: true,
      invocation: { command: '/custom/sq', args: [], source: 'config-sq-path' },
    });
  });

  it('falls through to later strategies when squads.sqPath does not exist on disk', () => {
    const env = makeEnvironment({ files: [`${WORKSPACE_ROOT}/.venv/bin/sq`] });
    const result = resolveSqInvocation(WORKSPACE_ROOT, { sqPath: '/missing/sq' }, env);
    expect(result).toEqual({
      ok: true,
      invocation: { command: `${WORKSPACE_ROOT}/.venv/bin/sq`, args: [], source: 'venv' },
    });
  });

  it('uses squads.command as a full argv prefix when its first element is on PATH', () => {
    const env = makeEnvironment({ onPath: ['python3'] });
    const result = resolveSqInvocation(
      WORKSPACE_ROOT,
      { command: ['python3', '-m', 'squads'] },
      env,
    );
    expect(result).toEqual({
      ok: true,
      invocation: { command: 'python3', args: ['-m', 'squads'], source: 'config-command' },
    });
  });

  it('resolves squads.command when its first element is an absolute posix path', () => {
    const env = makeEnvironment({ files: ['/opt/py/bin/python'] });
    const result = resolveSqInvocation(
      WORKSPACE_ROOT,
      { command: ['/opt/py/bin/python', '-m', 'squads'] },
      env,
    );
    expect(result).toEqual({
      ok: true,
      invocation: {
        command: '/opt/py/bin/python',
        args: ['-m', 'squads'],
        source: 'config-command',
      },
    });
  });

  it('resolves squads.command when its first element is an absolute windows path', () => {
    const env = makeEnvironment({ files: ['C:\\Python\\python.exe'] });
    const result = resolveSqInvocation(
      WORKSPACE_ROOT,
      { command: ['C:\\Python\\python.exe', '-m', 'squads'] },
      env,
    );
    expect(result.ok && result.invocation.command).toBe('C:\\Python\\python.exe');
  });

  it('does not fall back to a PATH scan for a path-shaped squads.command that does not exist', () => {
    const env = makeEnvironment({ onPath: ['/opt/py/bin/python'] });
    const result = resolveSqInvocation(
      WORKSPACE_ROOT,
      { command: ['/opt/py/bin/python', '-m', 'squads'] },
      env,
    );
    expect(result.ok).toBe(false);
  });

  it('resolves the workspace .venv on posix', () => {
    const env = makeEnvironment({ platform: 'linux', files: [`${WORKSPACE_ROOT}/.venv/bin/sq`] });
    const result = resolveSqInvocation(WORKSPACE_ROOT, {}, env);
    expect(result).toEqual({
      ok: true,
      invocation: { command: `${WORKSPACE_ROOT}/.venv/bin/sq`, args: [], source: 'venv' },
    });
  });

  it('resolves the workspace .venv on windows using the Scripts/sq.exe layout', () => {
    const env = makeEnvironment({
      platform: 'win32',
      files: [`${WORKSPACE_ROOT}/.venv/Scripts/sq.exe`],
    });
    const result = resolveSqInvocation(WORKSPACE_ROOT, {}, env);
    expect(result).toEqual({
      ok: true,
      invocation: { command: `${WORKSPACE_ROOT}/.venv/Scripts/sq.exe`, args: [], source: 'venv' },
    });
  });

  it('falls to `uv run sq` when uv is on PATH and a pyproject.toml exists', () => {
    const env = makeEnvironment({
      onPath: ['uv'],
      files: [`${WORKSPACE_ROOT}/pyproject.toml`],
    });
    const result = resolveSqInvocation(WORKSPACE_ROOT, {}, env);
    expect(result).toEqual({
      ok: true,
      invocation: { command: 'uv', args: ['run', 'sq'], source: 'uv' },
    });
  });

  it('does not use uv when there is no project at the workspace root', () => {
    const env = makeEnvironment({ onPath: ['uv', 'sq'] });
    const result = resolveSqInvocation(WORKSPACE_ROOT, {}, env);
    expect(result).toEqual({
      ok: true,
      invocation: { command: 'sq', args: [], source: 'path' },
    });
  });

  it('falls to `poetry run sq` when poetry is on PATH and a project exists but uv is absent', () => {
    const env = makeEnvironment({
      onPath: ['poetry'],
      files: [`${WORKSPACE_ROOT}/pyproject.toml`],
    });
    const result = resolveSqInvocation(WORKSPACE_ROOT, {}, env);
    expect(result).toEqual({
      ok: true,
      invocation: { command: 'poetry', args: ['run', 'sq'], source: 'poetry' },
    });
  });

  it('prefers uv over poetry when both are present', () => {
    const env = makeEnvironment({
      onPath: ['uv', 'poetry'],
      files: [`${WORKSPACE_ROOT}/pyproject.toml`],
    });
    const result = resolveSqInvocation(WORKSPACE_ROOT, {}, env);
    expect(result.ok && result.invocation.source).toBe('uv');
  });

  it('prefers the workspace .venv over uv/poetry even when both toolchains are present', () => {
    const env = makeEnvironment({
      onPath: ['uv', 'poetry'],
      files: [`${WORKSPACE_ROOT}/pyproject.toml`, `${WORKSPACE_ROOT}/.venv/bin/sq`],
    });
    const result = resolveSqInvocation(WORKSPACE_ROOT, {}, env);
    expect(result.ok && result.invocation.source).toBe('venv');
  });

  it('falls back to bare sq on PATH as the last resort', () => {
    const env = makeEnvironment({ onPath: ['sq'] });
    const result = resolveSqInvocation(WORKSPACE_ROOT, {}, env);
    expect(result).toEqual({
      ok: true,
      invocation: { command: 'sq', args: [], source: 'path' },
    });
  });

  it('reports every strategy tried, in order, when none resolve', () => {
    const env = makeEnvironment({});
    const result = resolveSqInvocation(WORKSPACE_ROOT, { sqPath: '/missing/sq' }, env);
    expect(result).toEqual({
      ok: false,
      triedOrder: ['config-sq-path', 'venv', 'uv', 'poetry', 'path'],
    });
  });

  it('never resolves from PATH alone without at least trying the earlier strategies', () => {
    const seen: string[] = [];
    const env = makeEnvironment({
      onPath: ['sq'],
      onIsOnPath: (name) => seen.push(name),
    });
    resolveSqInvocation(WORKSPACE_ROOT, {}, env);
    expect(seen).toEqual(['uv', 'poetry', 'sq']);
  });
});

describe('SqDiscovery', () => {
  it('caches the resolved invocation across calls', () => {
    let probes = 0;
    const env = makeEnvironment({
      onPath: ['sq'],
      onIsOnPath: () => {
        probes += 1;
      },
    });
    const discovery = new SqDiscovery(WORKSPACE_ROOT, () => ({}), env);

    const first = discovery.resolve();
    const second = discovery.resolve();

    expect(first).toEqual(second);
    expect(probes).toBeGreaterThan(0);
    const probesAfterFirst = probes;
    discovery.resolve();
    expect(probes).toBe(probesAfterFirst);
  });

  it('re-probes after invalidate()', () => {
    let onPathNames = new Set<string>();
    const env = makeEnvironment({ onPath: [] });
    const dynamicEnv: DiscoveryEnvironment = {
      ...env,
      isOnPath: (name) => onPathNames.has(name),
    };
    const discovery = new SqDiscovery(WORKSPACE_ROOT, () => ({}), dynamicEnv);

    expect(discovery.resolve()).toEqual({
      ok: false,
      triedOrder: ['venv', 'uv', 'poetry', 'path'],
    });

    onPathNames = new Set(['sq']);
    // Still cached as a failure isn't cached, so this should already re-probe and succeed.
    expect(discovery.resolve()).toEqual({
      ok: true,
      invocation: { command: 'sq', args: [], source: 'path' },
    });

    discovery.invalidate();
    onPathNames = new Set();
    expect(discovery.resolve().ok).toBe(false);
  });
});

describe('describeTriedOrder', () => {
  it('renders a readable, ordered trail', () => {
    expect(describeTriedOrder(['config-sq-path', 'venv', 'uv', 'poetry', 'path'])).toBe(
      'squads.sqPath -> .venv -> uv run -> poetry run -> sq on PATH',
    );
  });
});
